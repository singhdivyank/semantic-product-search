from prometheus_client import Counter, Histogram, Gauge

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration for all FastAPI endpoints",
    labelnames=["method", "endpoint", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    labelnames=["method", "endpoint", "status_code"],
)


_SUMMARISE_PROMPT_TEMPLATE = """You are a concise product review analyst.
Given the following customer reviews for a product, write a short pros/cons summary.
 
Reviews:
{reviews}
 
Respond in this format:
Pros:
- <point>
Cons:
- <point>
 
Summary:""".strip()
