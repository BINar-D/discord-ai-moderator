from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ModerationResult:
    score: float
    categories: dict[str, float]
    flagged: bool

    @property
    def category_summary(self) -> str:
        high = sorted(self.categories.items(), key=lambda x: x[1], reverse=True)
        high = [(name, score) for name, score in high if score >= 0.05]
        return ", ".join(f"{name}: {score * 10:.1f}" for name, score in high[:5])

    @property
    def test_emoji(self) -> str:
        if self.score >= 8:
            return "🔴"
        if self.score >= 5:
            return "🟡"
        return "🟢"


def _to_float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def build_result(response: Any) -> ModerationResult:
    item = response.results[0]
    raw = getattr(item, "category_scores", {})
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()
    elif not isinstance(raw, dict):
        raw = vars(raw)

    categories = {str(k): _to_float(v) for k, v in raw.items()}
    # Use the highest category score as the risk signal. This avoids averaging
    # unrelated categories and makes a severe single-category result visible.
    peak = max(categories.values(), default=0.0)
    flagged = bool(getattr(item, "flagged", False))
    return ModerationResult(score=round(peak * 10, 2), categories=categories, flagged=flagged)
