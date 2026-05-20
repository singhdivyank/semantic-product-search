"""
Rolling latency statistics (in-process, no external dependency)
"""

from collections import deque
from typing import Optional


class RollingStats:
    """Tracks a sliding window of latency samples for p50/p95 computation."""

    def __init__(self, window: int = 200) -> None:
        self.samples = deque(maxlen=window)

    def record(self, value_ms: float) -> None:
        self.samples.append(value_ms)

    def p50(self) -> Optional[float]:
        if not self.samples:
            return None

        sorted_s = sorted(self.samples)
        return sorted_s[len(sorted_s) // 2]

    def p95(self) -> Optional[float]:
        if not self.samples:
            return None

        sorted_s = sorted(self.samples)
        idx = int(len(sorted_s) * 0.95)
        return sorted_s[min(idx, len(sorted_s) - 1)]

    def mean(self) -> Optional[float]:
        if not self.samples:
            return None

        return sum(self.samples) / len(self.samples)

    def as_dict(self, prefix: str = "") -> dict[str, float]:
        p = f"{prefix}_" if prefix else ""
        return {
            k: v
            for k, v in {
                f"{p}p50_ms": self.p50(),
                f"{p}p95_ms": self.p95(),
                f"{p}mean_ms": self.mean(),
            }.items()
            if v is not None
        }
