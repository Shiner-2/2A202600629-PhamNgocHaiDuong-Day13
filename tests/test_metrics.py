import app.metrics as metrics
from app.metrics import percentile


def test_percentile_basic() -> None:
    assert percentile([100, 200, 300, 400], 50) >= 100


def test_snapshot_includes_error_rate(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "TRAFFIC", 3)
    monkeypatch.setattr(metrics, "ERRORS", metrics.Counter({"RuntimeError": 1}))
    result = metrics.snapshot()
    assert result["total_requests"] == 4
    assert result["error_rate_pct"] == 25.0
