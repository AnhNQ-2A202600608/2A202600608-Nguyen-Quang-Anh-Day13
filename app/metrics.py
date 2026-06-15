from __future__ import annotations

import json
import os
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

REQUEST_LATENCIES: list[int] = []
REQUEST_COSTS: list[float] = []
REQUEST_TOKENS_IN: list[int] = []
REQUEST_TOKENS_OUT: list[int] = []
ERRORS: Counter[str] = Counter()
TRAFFIC: int = 0
QUALITY_SCORES: list[float] = []

# Persistent variables & Lock
METRICS_HISTORY: list[dict] = []
metrics_lock = threading.Lock()
HISTORY_PATH = Path(os.getenv("HISTORY_PATH", "data/metrics_history.jsonl"))

# Cumulative Seeds (Restored from history on boot)
TOKENS_IN_SEED = 0
TOKENS_OUT_SEED = 0
COST_SEED = 0.0


def record_request(latency_ms: int, cost_usd: float, tokens_in: int, tokens_out: int, quality_score: float) -> None:
    global TRAFFIC
    with metrics_lock:
        TRAFFIC += 1
        REQUEST_LATENCIES.append(latency_ms)
        REQUEST_COSTS.append(cost_usd)
        REQUEST_TOKENS_IN.append(tokens_in)
        REQUEST_TOKENS_OUT.append(tokens_out)
        QUALITY_SCORES.append(quality_score)
        save_snapshot_unlocked()


def record_error(error_type: str) -> None:
    with metrics_lock:
        ERRORS[error_type] += 1
        save_snapshot_unlocked()


def percentile(values: list[int], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def snapshot_unlocked() -> dict:
    p50 = percentile(REQUEST_LATENCIES, 50)
    p95 = percentile(REQUEST_LATENCIES, 95)
    p99 = percentile(REQUEST_LATENCIES, 99)
    total_cost = round(sum(REQUEST_COSTS) + COST_SEED, 4)
    avg_cost = round(total_cost / TRAFFIC, 4) if TRAFFIC > 0 else 0.0
    under_50_count = sum(1 for q in QUALITY_SCORES if q < 0.5)
    
    return {
        "traffic": TRAFFIC,
        "latency_p50": p50,
        "latency_p95": p95,
        "latency_p99": p99,
        "avg_cost_usd": avg_cost,
        "total_cost_usd": total_cost,
        "tokens_in_total": sum(REQUEST_TOKENS_IN) + TOKENS_IN_SEED,
        "tokens_out_total": sum(REQUEST_TOKENS_OUT) + TOKENS_OUT_SEED,
        "error_breakdown": dict(ERRORS),
        "quality_avg": round(mean(QUALITY_SCORES), 4) if QUALITY_SCORES else 0.0,
        "under_50_quality_count": under_50_count
    }


def snapshot() -> dict:
    with metrics_lock:
        return snapshot_unlocked()


def save_snapshot_unlocked() -> None:
    snap = snapshot_unlocked()
    snap["ts"] = datetime.now(timezone.utc).isoformat()
    
    METRICS_HISTORY.append(snap)
    if len(METRICS_HISTORY) > 100:
        METRICS_HISTORY.pop(0)
        
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with HISTORY_PATH.open("w", encoding="utf-8") as f:
            for s in METRICS_HISTORY:
                f.write(json.dumps(s) + "\n")
    except Exception:
        pass


def load_history() -> None:
    global TRAFFIC, TOKENS_IN_SEED, TOKENS_OUT_SEED, COST_SEED
    if not HISTORY_PATH.exists():
        return
    try:
        snapshots = []
        with HISTORY_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    snapshots.append(json.loads(line))
        
        snapshots = snapshots[-100:]
        with metrics_lock:
            METRICS_HISTORY.clear()
            METRICS_HISTORY.extend(snapshots)
            
            if snapshots:
                last_snap = snapshots[-1]
                TRAFFIC = last_snap.get("traffic", 0)
                ERRORS.clear()
                ERRORS.update(last_snap.get("error_breakdown", {}))
                
                TOKENS_IN_SEED = last_snap.get("tokens_in_total", 0)
                TOKENS_OUT_SEED = last_snap.get("tokens_out_total", 0)
                COST_SEED = last_snap.get("total_cost_usd", 0.0)
                
                # Seed latency values from the last snapshot
                p50 = last_snap.get("latency_p50", 0.0)
                p95 = last_snap.get("latency_p95", 0.0)
                p99 = last_snap.get("latency_p99", 0.0)
                REQUEST_LATENCIES.clear()
                if p50 > 0:
                    REQUEST_LATENCIES.extend([int(p50), int(p95), int(p99)])
                
                # Seed quality scores
                quality_avg = last_snap.get("quality_avg", 0.0)
                QUALITY_SCORES.clear()
                if quality_avg > 0:
                    QUALITY_SCORES.append(quality_avg)
    except Exception:
        pass


def get_history() -> list[dict]:
    with metrics_lock:
        return list(METRICS_HISTORY)
