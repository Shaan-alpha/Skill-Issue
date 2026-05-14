from app.models import Evidence, ScoreResult


def make_result(points: int, max_points: int, evidence: list[Evidence]) -> ScoreResult:
    return ScoreResult(points=min(points, max_points), max_points=max_points, evidence=evidence)
