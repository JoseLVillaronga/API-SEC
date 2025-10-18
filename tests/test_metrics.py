import os, sys
sys.path.insert(0, os.path.abspath("."))

import math

from src.utils.metrics import get_metrics


def test_metrics_sanitize_inf_nan_on_empty_summaries():
    m = get_metrics()
    # Reset to known state
    m.reset_all()

    data = m.get_all_metrics()
    summaries = data.get("summaries", {})
    assert "response_time_seconds" in summaries
    s = summaries["response_time_seconds"]

    # When there are no observations, min and max should be None (not inf/-inf)
    assert s["count"] == 0
    assert s["min"] is None
    assert s["max"] is None
    assert s["mean"] == 0.0


def test_metrics_after_observation_are_finite():
    m = get_metrics()
    m.reset_all()

    # Observe a couple of values
    m.observe_summary("response_time_seconds", 0.2)
    m.observe_summary("response_time_seconds", 0.4)

    data = m.get_all_metrics()
    s = data["summaries"]["response_time_seconds"]

    # After observations, min/max/mean should be finite numbers
    assert s["count"] == 2
    assert isinstance(s["min"], float) and math.isfinite(s["min"]) and s["min"] == 0.2
    assert isinstance(s["max"], float) and math.isfinite(s["max"]) and s["max"] == 0.4
    assert isinstance(s["mean"], float) and math.isfinite(s["mean"]) and math.isclose(s["mean"], 0.3, rel_tol=1e-9)

