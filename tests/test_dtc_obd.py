"""Коди помилок, готовність систем, живі параметри."""

import pytest

from obd_studio.dtc import DTC_TEXT, decode_dtc, describe_dtc
from obd_studio.obd import decode_readiness, extract_dtcs, parse_supported_pids
from obd_studio.pids import PIDS, decode_value, format_value


# ───────────── decode_dtc / describe_dtc ─────────────

@pytest.mark.parametrize("a, b, code", [
    (0x01, 0x33, "P0133"),
    (0x03, 0x00, "P0300"),
    (0x04, 0x20, "P0420"),
    (0x11, 0x23, "P1123"),
    (0x2A, 0xBC, "P2ABC"),
    (0x41, 0x23, "C0123"),
    (0x81, 0x00, "B0100"),
    (0xC1, 0x00, "U0100"),
    (0xFF, 0xFF, "U3FFF"),
])
def test_decode_dtc(a, b, code):
    assert decode_dtc(a, b) == code


def test_describe_known_codes():
    assert describe_dtc("P0420") == "Ефективність каталізатора нижча за поріг"
    assert describe_dtc("P0302") == "Пропуски запалювання в циліндрі 2"
    assert describe_dtc("P0204") == "Несправність ланцюга форсунки, циліндр 4"


def test_describe_unknown_codes():
    assert "Mitsubishi" in describe_dtc("P1500", "Mitsubishi")
    assert "Mitsubishi" in describe_dtc("P3000", "Mitsubishi")
    assert "група: система запалювання" in describe_dtc("P0399")
    assert describe_dtc("C1234").startswith("шасі")
    assert describe_dtc("B1234").startswith("кузов")
    assert describe_dtc("U1234").startswith("зв’язок")


def test_dtc_table_extends_original_draft(draft):
    # усі описи з першої версії збережено без змін, словник лише доповнено
    for code, text in draft.DTC_TEXT.items():
        assert DTC_TEXT[code] == text
    assert len(DTC_TEXT) > len(draft.DTC_TEXT)
    for code in ["P0000", "P2999", "P0999", "C0000", "B3FFF"]:
        assert describe_dtc(code) == draft.describe_dtc(code)


# ───────────── extract_dtcs (режими 03/07) ─────────────

def test_extract_dtcs_basic():
    payloads = [bytes([0x43, 0x01, 0x33, 0x03, 0x00, 0x00, 0x00])]
    assert extract_dtcs(payloads) == ["P0133", "P0300"]


def test_extract_dtcs_with_count_byte():
    # деякі блоки вставляють кількість кодів перед ними
    payloads = [bytes([0x43, 0x02, 0x01, 0x33, 0x04, 0x20])]
    assert extract_dtcs(payloads) == ["P0133", "P0420"]


def test_extract_dtcs_several_frames_without_duplicates():
    payloads = [bytes([0x43, 0x01, 0x33, 0x00, 0x00, 0x00, 0x00]),
                bytes([0x43, 0x01, 0x33, 0x01, 0x71, 0x00, 0x00])]
    assert extract_dtcs(payloads) == ["P0133", "P0171"]


def test_extract_dtcs_empty():
    assert extract_dtcs([bytes([0x43, 0, 0, 0, 0, 0, 0])]) == []
    assert extract_dtcs([]) == []
    assert extract_dtcs([b"\x43"]) == []


# ───────────── PID 00 і готовність (PID 01) ─────────────

def test_parse_supported_pids():
    sup = parse_supported_pids(bytes([0xBE, 0x3E, 0xB8, 0x11]))
    assert sup == {1, 3, 4, 5, 6, 7, 11, 12, 13, 14, 15, 17, 19, 20, 21, 28, 32}
    assert parse_supported_pids(None) == set()
    assert parse_supported_pids(b"\xFF\xFF") == set()


def test_readiness_mil_on_and_count():
    text = decode_readiness(bytes([0x83, 0x07, 0x65, 0x00]))
    assert "Лампа Check Engine: УВІМКНЕНА" in text
    assert "Кількість підтверджених помилок: 3" in text


def test_readiness_mil_off():
    text = decode_readiness(bytes([0x00, 0x07, 0x65, 0x00]))
    assert "Лампа Check Engine: вимкнена" in text
    assert "Кількість підтверджених помилок: 0" in text


def test_readiness_complete_and_incomplete():
    # безперервні: усі 3 підтримуються, паливна система ще не готова (біт 5)
    # періодичні: підтримуються каталізатор (0), EVAP (2), кисневі датчики (5), підігрів (6);
    # не готові каталізатор і EVAP
    text = decode_readiness(bytes([0x00, 0x27, 0x65, 0x05]))
    assert "  Пропуски запалювання: готово" in text
    assert "  Паливна система: НЕ готово" in text
    assert "  Компоненти: готово" in text
    assert "  Каталізатор: НЕ готово" in text
    assert "  Система EVAP: НЕ готово" in text
    assert "  Кисневі датчики: готово" in text
    assert "  Підігрів кисневих датчиків: готово" in text
    # непідтримувані системи не показуються
    assert "EGR" not in text
    assert "Вторинне повітря" not in text
    assert "Підігрів каталізатора" not in text


def test_readiness_matches_original_draft(draft):
    for d in ([0, 0, 0, 0], [0x83, 0x77, 0xFF, 0xAA], [0x01, 0x07, 0x65, 0x00]):
        assert decode_readiness(bytes(d)) == draft.decode_readiness(bytes(d))


# ───────────── живі параметри ─────────────

@pytest.mark.parametrize("pid, data, shown", [
    (0x0C, [0x0B, 0xB8], "750 об/хв"),
    (0x05, [0x7B], "83 °C"),
    (0x0D, [0x3C], "60 км/год"),
    (0x04, [0xFF], "100.0 %"),
    (0x0E, [0x8C], "6.0 °"),
    (0x06, [0x80], "0.0 %"),
    (0x07, [0x70], "-12.5 %"),
    (0x10, [0x01, 0xF4], "5.00 г/с"),
    (0x14, [0x5A], "0.450 В"),
])
def test_live_values(pid, data, shown):
    assert format_value(pid, decode_value(pid, bytes(data))) == shown


def test_live_value_missing_or_short():
    assert format_value(0x0C, decode_value(0x0C, None)) == "—"
    assert format_value(0x0C, decode_value(0x0C, b"")) == "—"


def test_live_formulas_match_original_draft(draft):
    # формули, одиниці й точність параметрів першої версії не змінилися
    for pid, _name, unit, fn, dec in draft.LIVE_PIDS:
        d = PIDS[pid]
        assert (d.unit, d.decimals) == (unit, dec)
        for sample in (bytes([0x00, 0x00]), bytes([0x7B, 0x10]), bytes([0xFF, 0xFF])):
            assert d.decode(sample) == pytest.approx(fn(sample))
