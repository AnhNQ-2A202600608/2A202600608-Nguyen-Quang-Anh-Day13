import os
from pathlib import Path
from app.metrics import (
    percentile,
    record_request,
    record_error,
    snapshot,
    get_history,
    load_history,
    HISTORY_PATH
)


def test_percentile_basic() -> None:
    assert percentile([100, 200, 300, 400], 50) == 200.0
    assert percentile([10, 20, 30, 40], 95) == 40.0
    assert percentile([], 50) == 0.0


def reset_metrics_state() -> None:
    import app.metrics
    app.metrics.TRAFFIC = 0
    app.metrics.REQUEST_LATENCIES.clear()
    app.metrics.REQUEST_COSTS.clear()
    app.metrics.REQUEST_TOKENS_IN.clear()
    app.metrics.REQUEST_TOKENS_OUT.clear()
    app.metrics.QUALITY_SCORES.clear()
    app.metrics.ERRORS.clear()
    app.metrics.COST_SEED = 0.0
    app.metrics.TOKENS_IN_SEED = 0
    app.metrics.TOKENS_OUT_SEED = 0
    app.metrics.METRICS_HISTORY.clear()


def test_record_request_and_snapshot() -> None:
    reset_metrics_state()
    # Set custom history path for isolation
    test_history = Path("data/test_metrics_history.jsonl")
    if test_history.exists():
        test_history.unlink()
        
    import app.metrics
    original_path = app.metrics.HISTORY_PATH
    app.metrics.HISTORY_PATH = test_history
    
    try:
        record_request(
            latency_ms=150,
            cost_usd=0.0015,
            tokens_in=100,
            tokens_out=200,
            quality_score=0.85
        )
        
        snap = snapshot()
        assert snap["traffic"] == 1
        assert snap["latency_p50"] == 150.0
        assert snap["total_cost_usd"] == 0.0015
        assert snap["tokens_in_total"] == 100
        assert snap["tokens_out_total"] == 200
        assert snap["quality_avg"] == 0.85
        
        history = get_history()
        assert len(history) == 1
        assert history[-1]["traffic"] == snap["traffic"]
        
    finally:
        if test_history.exists():
            test_history.unlink()
        app.metrics.HISTORY_PATH = original_path


def test_record_error() -> None:
    reset_metrics_state()
    record_error("ValueError")
    snap = snapshot()
    assert "ValueError" in snap["error_breakdown"]
    assert snap["error_breakdown"]["ValueError"] == 1
