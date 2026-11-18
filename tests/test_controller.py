"""Контролер інтерфейсу: черга завдань у фоновому потоці, сканування, дані наживо (без вікна)."""

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt  # noqa: E402

from obd_studio import elm327  # noqa: E402
from obd_studio.config import AppSettings, Timing  # noqa: E402
from obd_studio.ui.controller import Controller  # noqa: E402

from fakes import FakeElm  # noqa: E402
from test_elm327 import ANSWERS  # noqa: E402


@pytest.fixture
def ctl(qapp, monkeypatch):
    fake = FakeElm(dict(ANSWERS))
    monkeypatch.setattr(elm327.serial, "serial_for_url", lambda *a, **k: fake)
    monkeypatch.setattr(elm327.Elm327, "settle", 0.0)
    c = Controller(Timing(), AppSettings(adapter="elm_wifi", elm_timeout=0.3))
    c.events = []
    for name in ("error", "dtcs_ready", "readiness_ready", "info_ready", "scan_done", "voltage",
                 "freeze_ready", "live_values"):
        getattr(c, name).connect(lambda *a, n=name: c.events.append((n, a)), Qt.DirectConnection)
    c.fake = fake
    yield c
    c.shutdown()


def wait_idle(c, timeout=5.0):
    end = time.time() + timeout
    time.sleep(0.05)
    while time.time() < end:
        if c._jobs.empty() and not c.is_busy:
            return
        time.sleep(0.01)
    raise AssertionError("контролер не завершив завдання")


def events(c, name):
    return [a for n, a in c.events if n == name]


def test_connect_reads_readiness_and_vin(ctl):
    ctl.connect()
    wait_idle(ctl)
    assert ctl.connected
    assert "CAN" in ctl.protocol_desc
    assert ctl.vin_info["vin"] == "JMBSRCS3A5U012345"
    assert ctl.brand_name() == "Mitsubishi"
    assert ctl.vehicle_title() == "Mitsubishi · 2005"
    assert events(ctl, "readiness_ready")[0][0]["mil"]
    assert events(ctl, "voltage")[0][0] == pytest.approx(12.6)


def test_manual_brand_overrides_vin(ctl):
    ctl.app.brand = "toyota"
    ctl.connect()
    wait_idle(ctl)
    assert ctl.brand_name() == "Toyota / Lexus"


def test_quick_scan(ctl):
    ctl.connect()
    wait_idle(ctl)
    ctl.quick_scan()
    wait_idle(ctl)
    entry = events(ctl, "scan_done")[0][0]
    assert entry["stored"] == ["P0133", "P0420"] and entry["permanent"] == ["P0420"]
    assert entry["mil"] and entry["vin"] == "JMBSRCS3A5U012345"
    assert ctl.freeze[0] == "P0133" and ctl.freeze[1][0x0C] == 750


def test_live_values_and_jobs_during_live(ctl):
    ctl.connect()
    wait_idle(ctl)
    ctl.set_live_pids([0x0C, 0x42])
    ctl.start_live()
    time.sleep(0.3)
    ctl.read_dtcs()               # виконується між циклами опитування
    time.sleep(0.3)
    ctl.stop_live()
    wait_idle(ctl)
    vals = events(ctl, "live_values")
    assert vals and vals[-1][0][0x0C] == 750 and vals[-1][0][0x42] == pytest.approx(14.0)
    assert events(ctl, "dtcs_ready")
    assert not ctl.is_live


def test_action_without_connection_reports_error(ctl):
    ctl.read_dtcs()
    wait_idle(ctl)
    assert "Немає з’єднання" in events(ctl, "error")[0][0]


def test_clear_and_disconnect(ctl):
    ctl.connect()
    wait_idle(ctl)
    ctl.clear_dtcs()
    wait_idle(ctl)
    assert ctl.dtcs["stored"] == [] and "04" in ctl.fake.commands
    ctl.disconnect()
    wait_idle(ctl)
    assert not ctl.connected


def test_silent_mode03_with_zero_confirmed_codes(ctl):
    ctl.fake.answers[b"\x01\x01"] = [[0x41, 0x01, 0x00, 0x07, 0x61, 0x21]]   # як у Lancer
    del ctl.fake.answers[b"\x03"]
    ctl.connect()
    wait_idle(ctl)
    ctl.read_dtcs()
    wait_idle(ctl)
    assert not events(ctl, "error")
    assert ctl.dtcs["stored"] == [] and ctl.dtcs["stored_inferred"]


def test_silent_mode03_with_confirmed_codes_is_error(ctl):
    del ctl.fake.answers[b"\x03"]                 # PID 01 каже: 2 підтверджені помилки
    ctl.connect()
    wait_idle(ctl)
    ctl.read_dtcs()
    wait_idle(ctl)
    assert "не відповів на запит помилок" in events(ctl, "error")[0][0]
