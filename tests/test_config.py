"""Налаштування часових параметрів."""

import json

from obd_studio.config import Timing, load_timing, save_timing


def test_defaults_match_original_draft_constants():
    t = Timing()
    assert t.baud == 10400
    assert (t.fast_idle, t.fast_low, t.fast_high) == (0.4, 0.025, 0.025)
    assert (t.fast_360_baud, t.fast_360_total) == (360, 0.050)
    assert (t.slow_idle, t.slow_bit, t.slow_sync_timeout) == (2.6, 0.2, 0.8)
    assert (t.slow_kb_timeout, t.slow_kb2_delay, t.slow_ack_timeout) == (0.1, 0.03, 0.2)
    assert t.start_comm_timeout == 0.3
    assert (t.response_first_timeout, t.response_gap, t.response_max_total) == (0.35, 0.08, 2.0)
    assert (t.retry_pause, t.session_timeout, t.p3_min, t.iso_interbyte) == (3.0, 4.0, 0.06, 0.006)
    assert t.try_fast_break and t.try_fast_360 and t.try_slow


def test_every_field_has_label_and_kind():
    for f in Timing.fields():
        assert f.metadata["label"]
        assert f.metadata["kind"] in ("ms", "num", "bool")


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "s.json"
    t = Timing(fast_low=0.027, baud=10400, try_slow=False)
    save_timing(t, path)
    assert load_timing(path) == t


def test_load_ignores_garbage(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"fast_low": "abc", "fast_high": 0.03, "unknown": 1}), encoding="utf-8")
    t = load_timing(path)
    assert t.fast_low == 0.025
    assert t.fast_high == 0.03


def test_load_missing_or_broken_file(tmp_path):
    assert load_timing(tmp_path / "none.json") == Timing()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_timing(bad) == Timing()
    bad.write_text("[1, 2]", encoding="utf-8")
    assert load_timing(bad) == Timing()


def test_describe_shows_milliseconds():
    lines = Timing().describe()
    assert "  fast_low = 25 мс" in lines
    assert "  baud = 10400 бод" in lines
    assert "  try_slow = так" in lines
