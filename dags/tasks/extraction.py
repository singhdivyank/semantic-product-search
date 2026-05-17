import logging

from config.read_configs import read_ingestion_configs

log = logging.getLogger("pipeline.dag")


def task_extract(**context) -> None:
    """Validates that local JSONL files exist and are readable"""

    ingestion_configs = read_ingestion_configs()

    expected = [ingestion_configs["reviews_path"], ingestion_configs["meta_path"]]
    missing = []

    for path in expected:
        gz_path = path.with_suffix(".jsonl.gz")
        if path.exists():
            log.info("Found: %s (%.1f MB)", path, path.stat().st_size / 1e6)
        elif gz_path.exists():
            log.info(
                "Found (gzipped): %s (%.1f MB)", gz_path, gz_path.stat().st_size / 1e6
            )
        else:
            missing.append(path)

    if missing:
        raise FileNotFoundError(
            f"Missing input file(s) in DATA_DIR ({ingestion_configs["data_dir"]}):\n"
            + "\n".join(
                f"  {p.name}  (also tried {p.name.replace('.jsonl', '.jsonl.gz')})"
                for p in missing
            )
            + "\n\nSet DATA_DIR in config.yaml to the folder containing your local JSONL files."
        )
