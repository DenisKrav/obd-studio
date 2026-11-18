"""Переклад: кожен рядок tr("…") і кожен рядок із таблиць даних має англійський відповідник."""

import ast
import os
import re
import string
from pathlib import Path

import pytest

from obd_studio import i18n
from obd_studio.config import Timing
from obd_studio.dtc import DTC_TEXT, KIND_NAMES, P_GROUPS, describe_dtc
from obd_studio.elm327 import PROTOCOLS
from obd_studio.i18n import set_language, tr
from obd_studio.locales.en_dtc import DTC_EN
from obd_studio.obd import DIESEL_MONITORS, SPARK_MONITORS, readiness_status
from obd_studio.pids import PIDS, format_value
from obd_studio.vehicles import BRANDS, REGIONS

PKG = Path(__file__).resolve().parent.parent / "obd_studio"
CYRILLIC = re.compile("[А-Яа-яІіЇїЄєҐґ’]")


@pytest.fixture
def english():
    set_language("en")
    yield
    set_language("uk")


def tr_literals():
    """Усі рядки, передані в tr(...) як літерал, з місцем у коді."""
    found = []
    for path in PKG.rglob("*.py"):
        if "locales" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "tr" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    found.append((arg.value, f"{path.name}:{node.lineno}"))
    return found


def placeholders(text):
    return {f for _, f, _, _ in string.Formatter().parse(text) if f is not None}


def data_strings():
    out = []
    for p in PIDS.values():
        out += [p.name, p.short, p.unit]
    for b in BRANDS:
        out += [b.name, b.adapter_hint]
    out += [name for _, name in REGIONS]
    out += [m for m in SPARK_MONITORS + DIESEL_MONITORS if m]
    out += ["Пропуски запалювання", "Паливна система", "Компоненти"]
    out += list(PROTOCOLS.values()) + list(KIND_NAMES.values()) + list(P_GROUPS.values())
    for f in Timing.fields():
        out.append(f.metadata["label"])
        if f.metadata.get("unit"):
            out.append(f.metadata["unit"])
    return [s for s in out if s and CYRILLIC.search(s)]


def test_tr_is_used():
    assert len(tr_literals()) > 100


def test_every_tr_literal_is_translated():
    en = i18n._english()
    missing = sorted({f"{where}: {text!r}" for text, where in tr_literals()
                      if CYRILLIC.search(text) and text not in en})
    assert not missing, "Немає перекладу:\n" + "\n".join(missing)


def test_every_data_string_is_translated():
    en = i18n._english()
    missing = sorted({s for s in data_strings() if s not in en})
    assert not missing, "Немає перекладу:\n" + "\n".join(missing)


def test_translations_are_english_and_keep_placeholders():
    bad = []
    for uk, en in i18n._english().items():
        if CYRILLIC.search(en):
            bad.append(f"кирилиця в перекладі: {uk!r} → {en!r}")
        if placeholders(uk) != placeholders(en):
            bad.append(f"різні {{змінні}}: {uk!r} → {en!r}")
    assert not bad, "\n".join(bad)


def test_dtc_english_complete():
    missing = sorted(set(DTC_TEXT) - set(DTC_EN))
    assert not missing, f"Немає англійського опису: {missing}"
    assert not [c for c, t in DTC_EN.items() if CYRILLIC.search(t)]


def test_describe_dtc_in_english(english):
    assert describe_dtc("P0420") == DTC_EN["P0420"]
    for code in ("P1500", "P0999", "C1234", "B1234", "U1234", "P3000"):
        assert not CYRILLIC.search(describe_dtc(code)), code
        assert not CYRILLIC.search(describe_dtc(code, "Toyota")), code
    assert "Toyota" in describe_dtc("P1500", "Toyota")


def test_units_and_values_in_english(english):
    assert format_value(0x0C, 750.0) == "750 rpm"
    assert format_value(0x0D, 60.0) == "60 km/h"


def test_readiness_names_translate(english):
    st = readiness_status(bytes([0x00, 0x07, 0x65, 0x00]))
    assert all(not CYRILLIC.search(tr(name)) for name, _ in st["monitors"])


def test_language_switch_and_fallback():
    set_language("en")
    try:
        assert tr("Огляд") == "Overview"
        assert tr("рядок, якого немає в словнику") == "рядок, якого немає в словнику"
    finally:
        set_language("uk")
    assert tr("Огляд") == "Огляд"
    set_language("xx")
    assert i18n.language() == "uk"


def test_whole_window_in_english(qapp, english, tmp_path, monkeypatch):
    """Головне вікно англійською: на жодній сторінці немає кирилиці."""
    from PySide6.QtWidgets import (QAbstractButton, QComboBox, QLabel, QLineEdit, QTableWidget,
                                   QTabBar)

    import obd_studio.history as history
    from obd_studio.config import AppSettings
    from obd_studio.ui.main_window import MainWindow

    monkeypatch.setattr(history, "history_path", lambda: tmp_path / "h.json")
    monkeypatch.setattr("obd_studio.ui.main_window.save_all", lambda *a, **k: None)
    win = MainWindow(Timing(), AppSettings(language="en"))
    try:
        bad = []
        allowed = {"Українська"}          # назва мови в перемикачі
        for w in win.findChildren(QLabel) + win.findChildren(QAbstractButton) + \
                win.findChildren(QLineEdit):
            text = w.text() if not isinstance(w, QLineEdit) else w.placeholderText()
            text = text + " " + (w.toolTip() or "")
            if CYRILLIC.search(text) and text.strip() not in allowed:
                bad.append(f"{type(w).__name__}: {text.strip()!r}")
        for box in win.findChildren(QComboBox):
            for i in range(box.count()):
                if CYRILLIC.search(box.itemText(i)) and box.itemText(i) not in allowed:
                    bad.append(f"QComboBox: {box.itemText(i)!r}")
        for t in win.findChildren(QTableWidget):
            for i in range(t.columnCount()):
                h = t.horizontalHeaderItem(i)
                if h and CYRILLIC.search(h.text()):
                    bad.append(f"заголовок таблиці: {h.text()!r}")
        for bar in win.findChildren(QTabBar):
            for i in range(bar.count()):
                if CYRILLIC.search(bar.tabText(i)):
                    bad.append(f"вкладка: {bar.tabText(i)!r}")
        if CYRILLIC.search(win.windowTitle()):
            bad.append(f"заголовок вікна: {win.windowTitle()!r}")
        assert not bad, "Кирилиця в англійському інтерфейсі:\n" + "\n".join(sorted(set(bad)))
    finally:
        win.ctl.shutdown()
        win.deleteLater()
        set_language("uk")


@pytest.mark.skipif(os.name != "nt", reason="мова Windows")
def test_system_language_is_valid():
    assert i18n.system_language() in i18n.LANGUAGES
