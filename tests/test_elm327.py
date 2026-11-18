"""Адаптер ELM327: розбір кадрів (CAN, ISO-TP, K-лінія), підключення, запити OBD-II."""

import pytest

from obd_studio import elm327
from obd_studio.elm327 import Elm327, parse_frames, wifi_url
from obd_studio.obd import ALLOWED_MODES, ObdClient
from obd_studio.protocol import ObdError

from fakes import FakeElm, can_frames

VIN = b"JMBSRCS3A5U012345"
ANSWERS = {
    b"\x01\x00": [[0x41, 0x00, 0xBE, 0x3E, 0xB8, 0x13]],          # підтримує й PID 20
    b"\x01\x20": [[0x41, 0x20, 0x80, 0x00, 0x00, 0x01]],          # 21 і 40
    b"\x01\x40": [[0x41, 0x40, 0x40, 0x00, 0x00, 0x00]],          # 42
    b"\x01\x01": [[0x41, 0x01, 0x82, 0x07, 0x65, 0x04]],
    b"\x01\x0C": [[0x41, 0x0C, 0x0B, 0xB8]],
    b"\x01\x42": [[0x41, 0x42, 0x36, 0xB0]],
    b"\x03": [[0x43, 0x02, 0x01, 0x33, 0x04, 0x20]],
    b"\x07": [[0x47, 0x00]],
    b"\x0A": [[0x4A, 0x01, 0x04, 0x20]],
    b"\x04": [[0x44]],
    b"\x09\x00": [[0x49, 0x00, 0x55, 0x40, 0x00, 0x00]],          # 02, 04, 06, 0A
    b"\x09\x02": [[0x49, 0x02, 0x01] + list(VIN)],
    b"\x09\x04": [[0x49, 0x04, 0x01] + list(b"1860A123\x00\x00\x00\x00\x00\x00\x00\x00")],
    b"\x09\x06": [[0x49, 0x06, 0x01, 0xDE, 0xAD, 0xBE, 0xEF]],
    b"\x09\x0A": [[0x49, 0x0A, 0x01] + list(b"ECM\x00-EngineControl\x00\x00")],
    b"\x02\x02\x00": [[0x42, 0x02, 0x00, 0x01, 0x33]],
    b"\x02\x00\x00": [[0x42, 0x00, 0x00, 0x18, 0x18, 0x00, 0x00]],   # 04, 05, 0C, 0D
    b"\x02\x04\x00": [[0x42, 0x04, 0x00, 0x80]],
    b"\x02\x05\x00": [[0x42, 0x05, 0x00, 0x7B]],
    b"\x02\x0C\x00": [[0x42, 0x0C, 0x00, 0x0B, 0xB8]],
    b"\x02\x0D\x00": [[0x42, 0x0D, 0x00, 0x3C]],
}


@pytest.fixture
def make_elm(monkeypatch):
    def factory(fake, **kw):
        monkeypatch.setattr(elm327.serial, "serial_for_url", lambda *a, **k: fake)
        logs = []
        e = Elm327("COM_TEST", logs.append, timeout=0.3, **kw)
        e.reset_timeout = 0.2
        e.settle = 0.0
        e.search_timeout = 0.5
        return e, logs
    return factory


# ───────────── parse_frames ─────────────

def test_can_single_frame():
    assert parse_frames(["7E8 06 41 00 BE 3E B8 11 00"], "6") == [("7E8", bytes([0x41, 0, 0xBE, 0x3E, 0xB8, 0x11]))]


def test_can_multi_frame_vin():
    payload = bytes([0x49, 0x02, 0x01]) + VIN
    lines = can_frames(payload)
    assert len(lines) == 3
    assert parse_frames(lines, "6") == [("7E8", payload)]


def test_can_two_ecus_are_separated():
    lines = ["7E8 03 43 01 33", "7E9 03 43 07 00"]
    assert parse_frames(lines, "6") == [("7E8", bytes([0x43, 0x01, 0x33])), ("7E9", bytes([0x43, 0x07, 0x00]))]


def test_can_29bit():
    assert parse_frames(["18 DA F1 10 03 41 0D 3C"], "7") == [("18 DA F1 10", bytes([0x41, 0x0D, 0x3C]))]


def test_kline_through_elm_drops_header_and_checksum():
    assert parse_frames(["48 6B 10 41 0C 0B B8 EF"], "3") == [("48 6B 10", bytes([0x41, 0x0C, 0x0B, 0xB8]))]


def test_garbage_lines_are_ignored():
    assert parse_frames(["SEARCHING...", "BUS INIT: ...OK", "NO DATA", "", "?"], "6") == []


def test_wifi_url():
    assert wifi_url("192.168.0.10", 35000) == "socket://192.168.0.10:35000"


# ───────────── підключення ─────────────

def test_connect_can(make_elm):
    fake = FakeElm(ANSWERS)
    e, logs = make_elm(fake)
    desc = e.connect()
    assert e.is_connected and e.protocol == "6"
    assert "CAN" in desc and "ELM327 v1.5" in desc
    assert {"ATZ", "ATE0", "ATH1", "ATSP0", "0100", "ATDPN"} <= set(fake.commands)


def test_connect_with_fixed_protocol(make_elm):
    fake = FakeElm(ANSWERS)
    e, _ = make_elm(fake, protocol="6")
    e.connect()
    assert "ATSP6" in fake.commands


def test_connect_no_ecu(make_elm):
    e, _ = make_elm(FakeElm({}))
    with pytest.raises(ObdError, match="NO DATA"):
        e.connect()
    assert not e.is_connected


def test_connect_silent_adapter(make_elm):
    e, _ = make_elm(FakeElm(ANSWERS, silent=True))
    with pytest.raises(ObdError, match="не відповідає"):
        e.connect()


def test_request_before_connect(make_elm):
    e, _ = make_elm(FakeElm(ANSWERS))
    with pytest.raises(ObdError):
        e.request([0x01, 0x0C], 0x41)


def test_voltage(make_elm):
    e, _ = make_elm(FakeElm(ANSWERS))
    e.connect()
    assert e.read_voltage() == pytest.approx(12.6)


# ───────────── ObdClient поверх ELM327 ─────────────

def connected(make_elm, **kw):
    fake = FakeElm(ANSWERS, **kw)
    e, logs = make_elm(fake)
    e.connect()
    return fake, e, ObdClient(e)


def test_supported_pids_several_ranges(make_elm):
    _, _, obd = connected(make_elm)
    sup = obd.supported_pids()
    assert {0x01, 0x0C, 0x20, 0x21, 0x40, 0x42} <= sup


def test_read_pid_and_dtcs_can(make_elm):
    _, _, obd = connected(make_elm)
    assert obd.read_pid(0x0C) == bytes([0x0B, 0xB8])
    assert obd.read_dtcs(0x03) == (["P0133", "P0420"], True)
    assert obd.read_dtcs(0x07) == ([], True)
    assert obd.read_dtcs(0x0A) == (["P0420"], True)
    assert obd.clear_dtcs()


def test_dtcs_from_two_ecus(make_elm):
    _, _, obd = connected(make_elm, extra_ecus={b"\x03": [[0x43, 0x01, 0x07, 0x00]]})
    codes, ok = obd.read_dtcs(0x03)
    assert ok and codes == ["P0133", "P0420", "P0700"]


def test_unsupported_request_returns_nothing(make_elm):
    _, _, obd = connected(make_elm)
    assert obd.read_pid(0x5E) is None


def test_readiness(make_elm):
    _, _, obd = connected(make_elm)
    rd = obd.readiness()
    assert rd["mil"] and rd["dtc_count"] == 2


def test_vehicle_info(make_elm):
    _, _, obd = connected(make_elm)
    info = obd.vehicle_info()
    assert info["supported"]
    assert info["vin"] == VIN.decode()
    assert info["calibration_ids"] == ["1860A123"]
    assert info["cvn"] == ["DEADBEEF"]
    assert info["ecu_name"] == "ECM - EngineControl"


def test_vehicle_info_not_supported(make_elm):
    answers = {k: v for k, v in ANSWERS.items() if k[:1] != b"\x09"}
    fake = FakeElm(answers)
    e, _ = make_elm(fake)
    e.connect()
    info = ObdClient(e).vehicle_info()
    assert not info["supported"] and info["vin"] == ""
    assert [c for c in fake.commands if c.startswith("09")] == ["0900"]


def test_freeze_frame(make_elm):
    _, _, obd = connected(make_elm)
    code, values = obd.freeze_frame()
    assert code == "P0133"
    assert values == {0x04: b"\x80", 0x05: b"\x7B", 0x0C: b"\x0B\xB8", 0x0D: b"\x3C"}


def test_kline_vehicle_through_elm(make_elm):
    fake = FakeElm(ANSWERS, protocol="3")
    e, _ = make_elm(fake)
    assert "ISO 9141-2" in e.connect()
    obd = ObdClient(e)
    assert obd.read_pid(0x0C) == bytes([0x0B, 0xB8])


def test_only_standard_requests_are_sent(make_elm):
    fake, _, obd = connected(make_elm)
    obd.supported_pids()
    obd.read_dtcs(0x03)
    obd.read_dtcs(0x07)
    obd.read_dtcs(0x0A)
    obd.freeze_frame()
    obd.vehicle_info()
    obd.clear_dtcs()
    obd.transport.read_voltage()
    obd_cmds = [c for c in fake.commands if not c.startswith("AT")]
    assert {int(c[:2], 16) for c in obd_cmds} <= ALLOWED_MODES
    at_cmds = {c for c in fake.commands if c.startswith("AT")}
    assert at_cmds <= {"ATZ", "ATE0", "ATL0", "ATS1", "ATH1", "ATAT1", "ATSP0", "ATDPN", "ATRV"}
    # режим 04 — лише один раз, за явною командою
    assert obd_cmds.count("04") == 1


def test_forbidden_mode_is_rejected(make_elm):
    _, _, obd = connected(make_elm)
    with pytest.raises(AssertionError):
        obd._request([0x2E, 0x01], 0x6E)
