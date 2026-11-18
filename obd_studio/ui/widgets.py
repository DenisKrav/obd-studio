"""Віджети з власним малюванням: прилад, графіки, плитки, бейджі."""

import math
import time
from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QComboBox, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                               QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

from ..i18n import tr
from . import icons
from .theme import Theme


def qc(key, alpha=None):
    c = QColor(Theme.c[key])
    if alpha is not None:
        c.setAlpha(alpha)
    return c


def label(text="", name=None, wrap=False):
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


class ComboBox(QComboBox):
    """Звичайний випадаючий список: колесо миші гортає сторінку, а не змінює значення.
    Значення змінюється лише вибором у розкритому списку."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)

    def wheelEvent(self, e):
        e.ignore()


class SpinBox(QSpinBox):
    """Числове поле, яке не змінюється від прокручування сторінки колесом."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class Card(QFrame):
    def __init__(self, title=None, subtitle=None, parent=None, name="card"):
        super().__init__(parent)
        self.setObjectName(name)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(20, 18, 20, 18)
        self.lay.setSpacing(12)
        self.title_label = None
        self.actions = None
        if title:
            row = QHBoxLayout()
            row.setSpacing(8)
            head = QVBoxLayout()
            head.setSpacing(2)
            self.title_label = label(title, "cardTitle")
            head.addWidget(self.title_label)
            if subtitle:
                head.addWidget(label(subtitle, "cardSub", wrap=True))
            row.addLayout(head, 1)
            self.actions = QHBoxLayout()
            self.actions.setSpacing(8)
            row.addLayout(self.actions)
            self.lay.addLayout(row)

    def add_action(self, w):
        self.actions.addWidget(w, 0, Qt.AlignTop)
        return w

    def add(self, w, stretch=0):
        if isinstance(w, QWidget):
            self.lay.addWidget(w, stretch)
        else:
            self.lay.addLayout(w, stretch)
        return w


class Pill(QLabel):
    """Невеликий кольоровий бейдж: tone = success | warning | danger | accent | neutral."""

    def __init__(self, text="", tone="neutral", parent=None):
        super().__init__(text, parent)
        self.set(text, tone)

    def set(self, text, tone="neutral"):
        self.setText(text)
        c = Theme.c
        fg, bg = {
            "success": (c["success"], c["success_bg"]), "warning": (c["warning"], c["warning_bg"]),
            "danger": (c["danger"], c["danger_bg"]), "accent": (c["accent"], c["accent_bg"]),
        }.get(tone, (c["muted"], c["surface2"]))
        self.setStyleSheet(f"background:{bg};color:{fg};border-radius:10px;padding:3px 10px;"
                           "font-weight:600;font-size:8.5pt;")
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)


class StatusDot(QWidget):
    def __init__(self, tone="neutral", parent=None):
        super().__init__(parent)
        self.tone = tone
        self.setFixedSize(12, 12)

    def set_tone(self, tone):
        self.tone = tone
        self.update()

    def paintEvent(self, _):
        key = {"success": "success", "warning": "warning", "danger": "danger"}.get(self.tone, "faint")
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(qc(key, 60))
        p.drawEllipse(QRectF(0, 0, 12, 12))
        p.setBrush(qc(key))
        p.drawEllipse(QRectF(3, 3, 6, 6))


class StatTile(QFrame):
    """Плитка зі значенням: іконка, підпис, велике значення, підказка."""

    def __init__(self, icon_name, title, parent=None):
        super().__init__(parent)
        self.setObjectName("tile")
        self.icon_name = icon_name
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(6)
        top = QHBoxLayout()
        self.icon = QLabel()
        top.addWidget(self.icon)
        top.addWidget(label(title, "tileLabel"), 1)
        lay.addLayout(top)
        self.value = label("—", "tileValue")
        lay.addWidget(self.value)
        self.note = label("", "faint", wrap=True)
        lay.addWidget(self.note)
        self.set_tone("neutral")

    def set_tone(self, tone):
        key = {"success": "success", "warning": "warning", "danger": "danger",
               "accent": "accent"}.get(tone, "muted")
        self.icon.setPixmap(icons.pixmap(self.icon_name, Theme.c[key], 18))
        color = Theme.c[key] if tone != "neutral" else Theme.c["text"]
        self.value.setStyleSheet(f"color:{color};")

    def set(self, value, note="", tone="neutral"):
        self.value.setText(value)
        self.note.setText(note)
        self.set_tone(tone)


class Gauge(QWidget):
    """Круглий прилад на 240° з плавним рухом стрілки."""

    def __init__(self, title, unit, lo, hi, decimals=0, warn=None, parent=None):
        super().__init__(parent)
        self.title, self.unit, self.lo, self.hi = title, unit, lo, hi
        self.decimals = decimals
        self.warn = warn                    # значення, з якого дуга стає попереджувальною
        self.value = None
        self._shown = lo
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(350)
        self.anim.valueChanged.connect(self._on_anim)
        self.setMinimumSize(170, 170)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _on_anim(self, v):
        self._shown = float(v)
        self.update()

    def set_value(self, v):
        self.value = v
        target = self.lo if v is None else max(self.lo, min(self.hi, v))
        self.anim.stop()
        self.anim.setStartValue(float(self._shown))
        self.anim.setEndValue(float(target))
        self.anim.start()

    def heightForWidth(self, w):
        return w

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height()) - 8
        r = QRectF((self.width() - side) / 2, (self.height() - side) / 2 + side * 0.04, side, side)
        thick = max(8.0, side * 0.075)
        arc = r.adjusted(thick, thick, -thick, -thick)
        start, span = 210, -240
        pen = QPen(qc("track"), thick, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(arc, start * 16, span * 16)

        frac = (self._shown - self.lo) / (self.hi - self.lo) if self.hi > self.lo else 0
        frac = max(0.0, min(1.0, frac))
        over = self.warn is not None and self.value is not None and self.value >= self.warn
        grad = QLinearGradient(arc.topLeft(), arc.topRight())
        if over:
            grad.setColorAt(0, qc("warning"))
            grad.setColorAt(1, qc("danger"))
        else:
            grad.setColorAt(0, qc("accent"))
            grad.setColorAt(1, qc("accent2"))
        if frac > 0.002 and self.value is not None:
            pen = QPen(grad, thick, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(arc, start * 16, int(span * frac * 16))

        # поділки
        cx, cy = arc.center().x(), arc.center().y()
        rad_out = arc.width() / 2 - thick * 0.9
        p.setPen(QPen(qc("faint"), 1.2))
        for i in range(11):
            a = math.radians(start + span * i / 10)
            r1 = rad_out - (6 if i % 5 == 0 else 3)
            p.drawLine(QPointF(cx + rad_out * math.cos(a), cy - rad_out * math.sin(a)),
                       QPointF(cx + r1 * math.cos(a), cy - r1 * math.sin(a)))

        # текст
        val = "—" if self.value is None else f"{self.value:.{self.decimals}f}"
        f = QFont(self.font())
        f.setPixelSize(max(14, int(side * 0.19)))
        f.setWeight(QFont.Bold)
        p.setFont(f)
        p.setPen(qc("text"))
        p.drawText(QRectF(r.left(), cy - side * 0.16, r.width(), side * 0.22), Qt.AlignCenter, val)
        f.setPixelSize(max(10, int(side * 0.075)))
        f.setWeight(QFont.Normal)
        p.setFont(f)
        p.setPen(qc("muted"))
        p.drawText(QRectF(r.left(), cy + side * 0.06, r.width(), side * 0.1), Qt.AlignCenter, self.unit)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(qc("text"))
        p.drawText(QRectF(r.left(), cy + side * 0.27, r.width(), side * 0.12), Qt.AlignCenter, self.title)


class Sparkline(QWidget):
    def __init__(self, maxlen=60, parent=None):
        super().__init__(parent)
        self.data = deque(maxlen=maxlen)
        self.setMinimumHeight(34)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def add(self, v):
        if v is not None:
            self.data.append(v)
            self.update()

    def clear(self):
        self.data.clear()
        self.update()

    def paintEvent(self, _):
        if len(self.data) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        lo, hi = min(self.data), max(self.data)
        if hi - lo < 1e-9:
            lo, hi = lo - 1, hi + 1
        w, h = self.width(), self.height() - 4
        n = self.data.maxlen
        step = w / (n - 1)
        x0 = w - step * (len(self.data) - 1)
        pts = [QPointF(x0 + i * step, 2 + h - (v - lo) / (hi - lo) * h) for i, v in enumerate(self.data)]
        path = QPainterPath(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        fill = QPainterPath(path)
        fill.lineTo(pts[-1].x(), h + 2)
        fill.lineTo(pts[0].x(), h + 2)
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, qc("accent", 70))
        grad.setColorAt(1, qc("accent", 0))
        p.fillPath(fill, grad)
        p.setPen(QPen(qc("accent"), 1.8))
        p.drawPath(path)


class ValueTile(QFrame):
    """Плитка параметра наживо: назва, значення, одиниця, міні-графік. Клік — вибір для графіка."""
    clicked = Signal(int)

    def __init__(self, pid, name, unit, parent=None):
        super().__init__(parent)
        self.pid = pid
        self.setObjectName("tile")
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("selected", False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(2)
        name_lb = label(name, "tileLabel")
        name_lb.setToolTip(name)
        lay.addWidget(name_lb)
        self.unit = unit
        self.value = QLabel()
        self.value.setTextFormat(Qt.RichText)
        lay.addWidget(self.value)
        self.spark = Sparkline()
        self.set_value("—", None)
        lay.addWidget(self.spark)
        self.setMinimumWidth(190)

    def set_value(self, text, raw):
        c = Theme.c
        self.value.setText(f"<span style='font-size:20pt;font-weight:700;color:{c['text']}'>{text}</span>"
                           f"<span style='font-size:9pt;color:{c['muted']}'>&nbsp;&nbsp;{self.unit}</span>")
        if raw is not None:
            self.spark.add(raw)

    def set_selected(self, on):
        self.setProperty("selected", on)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, e):
        self.clicked.emit(self.pid)
        super().mousePressEvent(e)


class LiveChart(QWidget):
    """Графік одного параметра за останні window секунд."""

    def __init__(self, window=60, parent=None):
        super().__init__(parent)
        self.window = window
        self.points = deque()
        self.title = ""
        self.unit = ""
        self.decimals = 0
        self.setMinimumHeight(220)

    def configure(self, title, unit, decimals):
        self.title, self.unit, self.decimals = title, unit, decimals
        self.points.clear()
        self.update()

    def add(self, v, t=None):
        if v is None:
            return
        t = time.monotonic() if t is None else t
        self.points.append((t, v))
        while self.points and t - self.points[0][0] > self.window:
            self.points.popleft()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        left, right, top, bottom = 56, 16, 40, 28
        w, h = self.width() - left - right, self.height() - top - bottom
        f = QFont(self.font())
        f.setPixelSize(15)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(qc("text"))
        p.drawText(QRectF(left, 6, w, 24), Qt.AlignLeft | Qt.AlignVCenter, self.title or tr("Графік"))
        if self.points:
            last = self.points[-1][1]
            p.setPen(qc("accent2"))
            p.drawText(QRectF(left, 6, w, 24), Qt.AlignRight | Qt.AlignVCenter,
                       f"{last:.{self.decimals}f} {self.unit}")
        f.setPixelSize(11)
        f.setWeight(QFont.Normal)
        p.setFont(f)

        vals = [v for _, v in self.points]
        lo, hi = (min(vals), max(vals)) if vals else (0.0, 1.0)
        show_axis = len(vals) >= 2
        if hi - lo < 1e-9:
            lo, hi = lo - 1, hi + 1
        pad = (hi - lo) * 0.12
        lo, hi = lo - pad, hi + pad
        for i in range(5):
            y = top + h * i / 4
            p.setPen(QPen(qc("border"), 1, Qt.DashLine if i not in (0, 4) else Qt.SolidLine))
            p.drawLine(QPointF(left, y), QPointF(left + w, y))
            if not show_axis:
                continue
            p.setPen(qc("faint"))
            v = hi - (hi - lo) * i / 4
            p.drawText(QRectF(0, y - 8, left - 8, 16), Qt.AlignRight | Qt.AlignVCenter,
                       f"{v:.{min(self.decimals, 2)}f}")
        for i, sec in enumerate(range(self.window, -1, -15)):
            x = left + w * (1 - sec / self.window)
            p.setPen(qc("faint"))
            p.drawText(QRectF(x - 30, top + h + 6, 60, 16), Qt.AlignCenter,
                       tr("-{sec} с").format(sec=sec) if sec else tr("зараз"))
        if len(self.points) < 2:
            p.setPen(qc("muted"))
            p.drawText(QRectF(left, top, w, h), Qt.AlignCenter,
                       tr("Запустіть дані наживо — тут з’явиться графік"))
            return
        now = self.points[-1][0]
        pts = [QPointF(left + w * (1 - (now - t) / self.window), top + h - (v - lo) / (hi - lo) * h)
               for t, v in self.points]
        path = QPainterPath(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        fill = QPainterPath(path)
        fill.lineTo(pts[-1].x(), top + h)
        fill.lineTo(pts[0].x(), top + h)
        grad = QLinearGradient(0, top, 0, top + h)
        grad.setColorAt(0, qc("accent", 90))
        grad.setColorAt(1, qc("accent", 0))
        p.fillPath(fill, grad)
        p.setPen(QPen(qc("accent"), 2.2))
        p.drawPath(path)
        p.setBrush(qc("accent2"))
        p.setPen(QPen(qc("surface"), 2))
        p.drawEllipse(pts[-1], 4.5, 4.5)


class PageHeader(QWidget):
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(label(title, "pageTitle"))
        if subtitle:
            col.addWidget(label(subtitle, "pageSub", wrap=True))
        lay.addLayout(col, 1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)
        lay.addLayout(self.actions)

    def add_action(self, w):
        self.actions.addWidget(w)
        return w


class EmptyState(QWidget):
    def __init__(self, icon_name, title, text, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 36, 20, 36)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignCenter)
        self.icon = QLabel()
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon_name = icon_name
        lay.addWidget(self.icon)
        self.title = label(title, "cardTitle")
        self.title.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.title)
        self.text = label(text, "muted", wrap=True)
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setMaximumWidth(460)
        lay.addWidget(self.text, 0, Qt.AlignCenter)
        self.set_icon(icon_name, "faint")

    def set_icon(self, name, tone_key):
        self.icon.setPixmap(icons.pixmap(name, Theme.c[tone_key], 44))

    def set(self, icon_name, tone_key, title, text):
        self.set_icon(icon_name, tone_key)
        self.title.setText(title)
        self.text.setText(text)


def shadow(widget, blur=30, alpha=40):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, 6)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)
