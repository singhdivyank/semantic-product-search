"""
Singleton client for mistralai/Mistral-7B-Instruct-v0.3
Hugging Face model (review summariser) used at inference time:

Lazily initialised on first use and cached for the lifetime of the
FastAPI process.  The FastAPI dependency `get_generation_client`
in src/api/deps.py inject this into route handlers.

Design notes
------------
- Model is loaded once; concurrent async requests reuse the same instance.
- Generation runs via the HF `pipeline` API; kept in a thread pool to avoid
  blocking the async event loop.
- HF_API_TOKEN is read from cfg for gated models (Mistral-7B is gated).
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

import torch
from transformers import pipeline as hf_pipeline, BitsAndBytesConfig

from config.read_configs import get_generation_conf
from src.consts import _SUMMARISE_PROMPT_TEMPLATE

log = logging.getLogger("app.hf_client")


class GenerationClient:
    """
    Wraps Mistral-7B-Instruct for on-the-fly review summarisation.

    The model is loaded with 4-bit quantisation (bitsandbytes) when a GPU
    is available, falling back to CPU fp32 for local development.
    """

    def __init__(self) -> None:
        self._initialised = False
        self.thread_pool = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="hf-interface"
        )
        self._init_model()

    def _generate_kwargs(self):
        generation_conf = get_generation_conf()["generation"]

        try:
            self.model_name = generation_conf["model_name"]
            token = generation_conf["api_token"]
            self.use_gpu = torch.cuda.is_available()

            self.kwargs = dict(
                model=self.model_name,
                task="text-generation",
                token=token,
                max_new_tokens=generation_conf["max_new_tokens"],
                do_sample=generation_conf["do_sample"],
                temperature=(
                    generation_conf["temperature"]
                    if generation_conf["do_sample"]
                    else None
                ),
            )
        except Exception as error:
            log.error("Unable to generate Generator Model kwargs: %s", str(error))
            raise

    def _init_model(self):

        log.info("Loading generation model: %s (GPU=%s)", self.model_name, self.use_gpu)

        try:
            self._generate_kwargs()

            if not self.use_gpu:
                self.kwargs["device"] = -1

            quant_config = BitsAndBytesConfig(load_in_4bit=True)
            self.kwargs["model_kwargs"] = {"quantization_config": quant_config}
            self.kwargs["device_map"] = "auto"
            self.pipeline = hf_pipeline(**self.kwargs)
            log.info("Generation model ready.")
            self._initialised = True
        except Exception as e:
            log.error("Unable to initialise Generator Model: %s", str(e))

    def summarise(self, reviews: List[str], max_reviews: int = 10) -> str:
        """Summarise a list of review strings into a pros/cons block"""

        if not reviews:
            return "No reviews available for this product"

        if not self._initialised:
            return "No generalisation model found"

        sampled = reviews[:max_reviews]
        numbered = "\n".join(f"{i+1}. {r}" for i, r in enumerate(sampled))
        prompt = _SUMMARISE_PROMPT_TEMPLATE.format(reviews=numbered)

        t0 = time.perf_counter()
        result = self.pipeline(prompt)
        elapsed = time.perf_counter() - t0

        log.debug("Generation latency: %.2f s", elapsed)
        generated = result[0]["generated_text"]

        if "Summary:" in generated:
            generated = generated.split("Summary:")[-1].strip()

        return generated

    async def summarise_async(self, reviews: list[str]) -> str:
        """Non-blocking version for async FastAPI routes."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.thread_pool, self.summarise, reviews)
