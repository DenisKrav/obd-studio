"""Марки й VIN, таблиця параметрів, звіт, історія, налаштування програми."""

import datetime
import json

import pytest

from obd_studio.config import AppSettings, Timing, load_all, save_all
from obd_studio.dtc import describe_dtc, dtc_severity, is_manufacturer_code
from obd_studio.history import add_entry, load_history
from obd_studio.obd import decode_vin as vin_from_payloads
from obd_studio.obd import readiness_status
from obd_studio.pids import DEFAULT_LIVE, GAUGE_PIDS, PIDS, decode_value, format_value
from obd_studio.report import build_html
from obd_studio.vehicles import BRANDS, brand_for_wmi, decode_vin, model_years, vin_check_digit_ok


# ───────────── марки й VIN ─────────────

@pytest.mark.parametrize("vin, key", [
    ("JMBSRCS3A5U012345", "mitsubishi"),
    ("XMCLRCS3A5F000001", "mitsubishi"),
    ("WVWZZZ1KZ8W000001", "vag"),
    ("TMBJJ7NE0K0000001", "vag"),
    ("JTDBR32E720000001", "toyota"),
    ("WBA3A5C50CF000001", "bmw"),
    ("KMHDN41AP7U000001", "hyundai"),
    ("VF1BM0B0H36000001", "renault"),
    ("Y6DTF698K90000001", "zaz"),
])
def test_brand_for_wmi(vin, key):
    assert brand_for_wmi(vin).key == key


def test_unknown_brand():
    assert brand_for_wmi("ZZZ00000000000000") is None
    assert brand_for_wmi("") is None


def test_wmi_prefixes_are_unique():
    seen = {}
    for b in BRANDS:
        for w in b.wmi:
            assert w not in seen, f"{w}: {seen.get(w)} і {b.key}"
            seen[w] = b.key


def test_model_years():
    assert model_years("JMBSRCS3A5U012345", 2026) == [2005]
    assert model_years("WVWZZZ1KZAW000001", 2026) == [1980, 2010]
    assert model_years("WVWZZZ1KZYW000001", 2026) == [2000]
    assert model_years("SHORT", 2026) == []


def test_check_digit():
    assert vin_check_digit_ok("1M8GDM9AXKP042788")
    assert not vin_check_digit_ok("1M8GDM9A1KP042788")


def test_decode_vin():
    d = decode_vin("jmbsrcs3a5u012345", 2026)
    assert d["vin"] == "JMBSRCS3A5U012345" and d["valid"]
    assert d["brand"].name == "Mitsubishi"
    assert d["year"] == 2005 and d["region"] == "Японія"


def test_vin_from_kline_messages():
    # ISO 9141-2: 5 повідомлень «49 02 N 4 байти», перше доповнене нулями
    vin = b"\x00\x00\x00JMBSRCS3A5U012345"
    payloads = [bytes([0x49, 0x02, n + 1]) + vin[n * 4:n * 4 + 4] for n in range(5)]
    assert vin_from_payloads(list(reversed(payloads))) == "JMBSRCS3A5U012345"


# ───────────── коди помилок ─────────────

def test_describe_with_brand():
    assert "Toyota" in describe_dtc("P1500", "Toyota")
    assert "вашої марки" in describe_dtc("P1500")
    assert describe_dtc("P0310") == "Пропуски запалювання в циліндрі 10"
    assert describe_dtc("P0357") == "Несправність ланцюга котушки запалювання, циліндр 7"
    assert describe_dtc("P0157") == "Кисневий датчик 2, ряд 2: низька напруга"


def test_manufacturer_codes():
    assert is_manufacturer_code("P1500") and is_manufacturer_code("P3000")
    assert not is_manufacturer_code("P0420") and not is_manufacturer_code("P3400")
    assert is_manufacturer_code("U1000") and not is_manufacturer_code("U0100")


def test_severity():
    assert dtc_severity("P0301") == "high"
    assert dtc_severity("P0455") == "low"
    assert dtc_severity("P0420") == "medium"


# ───────────── параметри ─────────────

@pytest.mark.parametrize("pid, data, shown", [
    (0x0C, [0x0B, 0xB8], "750 об/хв"),
    (0x05, [0x7B], "83 °C"),
    (0x42, [0x36, 0xB0], "14.00 В"),
    (0x2F, [0x80], "50.2 %"),
    (0x5E, [0x00, 0x64], "5.00 л/год"),
    (0x32, [0xFF, 0xF0], "-4.0 Па"),
    (0x3C, [0x13, 0x88], "460 °C"),
])
def test_format_values(pid, data, shown):
    assert format_value(pid, decode_value(pid, bytes(data))) == shown


def test_missing_or_short_values():
    assert decode_value(0x0C, None) is None
    assert decode_value(0x0C, b"\x0B") is None
    assert decode_value(0xFF, b"\x00") is None
    assert format_value(0x0C, None) == "—"


def test_pid_table_consistency():
    for pid, d in PIDS.items():
        assert d.pid == pid and d.name and d.short and d.lo < d.hi
    assert set(DEFAULT_LIVE) <= set(PIDS) and set(GAUGE_PIDS) <= set(PIDS)


def test_diesel_readiness_names():
    st = readiness_status(bytes([0x00, 0x0F, 0x40, 0x40]))
    assert st["diesel"]
    assert ("Сажовий фільтр (DPF)", False) in st["monitors"]


# ───────────── звіт та історія ─────────────

def test_report_contains_everything():
    html = build_html({
        "date": "18.11.2026 10:00", "vehicle": "Mitsubishi · 2005",
        "vin_info": {"vin": "JMBSRCS3A5U012345", "calibration_ids": ["1860A123"]},
        "protocol": "ISO 9141-2", "adapter": "KKL, COM3", "brand": "Mitsubishi",
        "dtcs": {"stored": ["P0420"], "pending": ["P1500"], "permanent": []},
        "readiness": readiness_status(bytes([0x81, 0x07, 0x65, 0x01])),
        "freeze": ("P0420", {0x0C: 750.0}), "live": {0x05: 90.0},
    })
    for text in ("JMBSRCS3A5U012345", "P0420", "P1500", "Mitsubishi", "УВІМКНЕНА",
                 "750 об/хв", "90 °C", "1860A123"):
        assert text in html


def test_report_no_codes_and_escaping():
    html = build_html({"vehicle": "<script>", "dtcs": {"stored": [], "pending": [], "permanent": []}})
    assert "<script>" not in html and "Помилок не знайдено" in html


def test_history(tmp_path):
    path = tmp_path / "h.json"
    assert load_history(path) == []
    add_entry({"vehicle": "A", "stored": ["P0420"]}, path, now=datetime.datetime(2026, 11, 18, 10, 0))
    entries = add_entry({"vehicle": "B", "stored": []}, path)
    assert [e["vehicle"] for e in entries] == ["A", "B"]
    assert load_history(path)[0]["date"] == "2026-11-18T10:00:00"
    path.write_text("{broken", encoding="utf-8")
    assert load_history(path) == []


# ───────────── налаштування ─────────────

def test_app_settings_roundtrip(tmp_path):
    path = tmp_path / "s.json"
    app = AppSettings(adapter="elm_wifi", wifi_host="10.0.0.5", theme="light", live_pids=[12, 13])
    save_all(Timing(fast_low=0.027), app, path)
    t, a = load_all(path)
    assert t.fast_low == 0.027 and a == app


def test_legacy_settings_are_migrated(tmp_path):
    (tmp_path / "lancer_obd_settings.json").write_text(json.dumps({"fast_low": 0.03}), encoding="utf-8")
    t, a = load_all(tmp_path / "obd_studio_settings.json")
    assert t.fast_low == 0.03 and a == AppSettings()


def test_app_settings_ignore_garbage(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"timing": [], "app": {"wifi_port": "x", "live_pids": "bad",
                                                      "theme": "light"}}), encoding="utf-8")
    t, a = load_all(path)
    assert t == Timing() and a.wifi_port == 35000 and a.live_pids == [] and a.theme == "light"
