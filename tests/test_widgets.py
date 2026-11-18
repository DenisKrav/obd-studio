"""Поведінка полів вводу: колесо миші гортає сторінку, а не змінює значення."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from obd_studio.ui.widgets import ComboBox, SpinBox  # noqa: E402


def wheel(widget, delta=-120):
    ev = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, delta),
                     Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    QApplication.sendEvent(widget, ev)
    return ev


def test_combobox_ignores_wheel(qapp):
    box = ComboBox()
    box.addItems(["Автовизначення", "Mitsubishi", "Toyota"])
    box.setCurrentIndex(1)
    ev = wheel(box)
    assert box.currentIndex() == 1
    assert not ev.isAccepted()            # подія піде далі — до прокрутки сторінки


def test_spinbox_ignores_wheel_without_focus(qapp):
    spin = SpinBox()
    spin.setRange(1, 100)
    spin.setValue(5)
    wheel(spin, 120)
    assert spin.value() == 5
