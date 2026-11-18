"""Малює іконку програми й зберігає obd_studio/resources/icon.ico та icon.png.

Запуск:  .venv\\Scripts\\python tools\\make_icon.py
Потрібні PySide6 і Pillow (є в requirements-dev.txt).
"""

import io
import math
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath,
                           QPen, QRadialGradient)

OUT = Path(__file__).resolve().parent.parent / "obd_studio" / "resources"
S = 1024


def squircle(rect, n=5.0, steps=720):
    """Суперелліпс — форма сучасних іконок (м’якша за заокруглений квадрат)."""
    cx, cy = rect.center().x(), rect.center().y()
    a, b = rect.width() / 2, rect.height() / 2
    path = QPainterPath()
    for i in range(steps + 1):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        x = cx + a * math.copysign(abs(c) ** (2 / n), c)
        y = cy + b * math.copysign(abs(s) ** (2 / n), s)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()
    return path


def draw():
    img = QImage(S, S, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    m = S * 0.04
    body = squircle(QRectF(m, m, S - 2 * m, S - 2 * m))
    bg = QLinearGradient(0, 0, S, S)
    bg.setColorAt(0.0, QColor("#1E2A4A"))
    bg.setColorAt(0.55, QColor("#0F1730"))
    bg.setColorAt(1.0, QColor("#070B18"))
    p.fillPath(body, bg)

    # м’яке сяйво за приладом
    p.save()
    p.setClipPath(body)
    glow = QRadialGradient(QPointF(S * 0.5, S * 0.56), S * 0.48)
    glow.setColorAt(0.0, QColor(59, 130, 246, 120))
    glow.setColorAt(0.6, QColor(34, 211, 238, 25))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.fillRect(QRectF(0, 0, S, S), glow)
    hl = QLinearGradient(0, 0, 0, S * 0.5)       # легкий відблиск зверху
    hl.setColorAt(0, QColor(255, 255, 255, 28))
    hl.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, 0, S, S * 0.5), hl)
    p.restore()

    # тонка світла облямівка
    p.setPen(QPen(QColor(255, 255, 255, 30), S * 0.006))
    p.drawPath(body)

    cx, cy = S * 0.5, S * 0.55
    r = S * 0.30
    thick = S * 0.075
    arc = QRectF(cx - r, cy - r, 2 * r, 2 * r)
    start, span = 215, -250

    p.setPen(QPen(QColor(255, 255, 255, 34), thick, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(arc, int(start * 16), int(span * 16))

    frac = 0.68
    grad = QLinearGradient(arc.bottomLeft(), arc.topRight())
    grad.setColorAt(0.0, QColor("#22D3EE"))
    grad.setColorAt(1.0, QColor("#3B82F6"))
    p.setPen(QPen(grad, thick, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(arc, int(start * 16), int(span * frac * 16))

    # поділки всередині дуги
    p.setPen(QPen(QColor(255, 255, 255, 90), S * 0.012, Qt.SolidLine, Qt.RoundCap))
    for i in range(6):
        a = math.radians(start + span * i / 5)
        r1, r2 = r - thick * 0.95, r - thick * 1.45
        p.drawLine(QPointF(cx + r1 * math.cos(a), cy - r1 * math.sin(a)),
                   QPointF(cx + r2 * math.cos(a), cy - r2 * math.sin(a)))

    # стрілка
    a = math.radians(start + span * frac)
    tip = QPointF(cx + (r - thick * 1.1) * math.cos(a), cy - (r - thick * 1.1) * math.sin(a))
    w = S * 0.03
    perp = a + math.pi / 2
    base1 = QPointF(cx + w * math.cos(perp), cy - w * math.sin(perp))
    base2 = QPointF(cx - w * math.cos(perp), cy + w * math.sin(perp))
    needle = QPainterPath(base1)
    needle.lineTo(tip)
    needle.lineTo(base2)
    needle.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#F8FAFC"))
    p.drawPath(needle)
    p.setBrush(QColor("#F8FAFC"))
    p.drawEllipse(QPointF(cx, cy), S * 0.058, S * 0.058)
    p.setBrush(QColor("#0F1730"))
    p.drawEllipse(QPointF(cx, cy), S * 0.026, S * 0.026)

    # роз’єм OBD-II знизу (трапеція з контактами)
    cw_top, cw_bot, ch = S * 0.30, S * 0.24, S * 0.095
    top_y = S * 0.775
    conn = QPainterPath()
    conn.moveTo(cx - cw_top / 2, top_y)
    conn.lineTo(cx + cw_top / 2, top_y)
    conn.lineTo(cx + cw_bot / 2, top_y + ch)
    conn.lineTo(cx - cw_bot / 2, top_y + ch)
    conn.closeSubpath()
    p.setPen(QPen(QColor(255, 255, 255, 150), S * 0.012, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPath(conn)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(34, 211, 238, 220))
    for row, count in ((0, 6), (1, 5)):
        y = top_y + ch * (0.33 + row * 0.36)
        span_w = cw_top * (0.62 - row * 0.1)
        for i in range(count):
            x = cx - span_w / 2 + span_w * i / (count - 1)
            p.drawEllipse(QPointF(x, y), S * 0.0095, S * 0.0095)
    p.end()
    return img


def to_pil(qimg):
    buf = QBuffer()
    buf.open(QBuffer.ReadWrite)
    qimg.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


def main():
    QGuiApplication(sys.argv)
    OUT.mkdir(parents=True, exist_ok=True)
    big = to_pil(draw())
    big.resize((256, 256), Image.LANCZOS).save(OUT / "icon.png")
    sizes = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)]
    big.save(OUT / "icon.ico", sizes=sizes)
    print(f"Збережено {OUT / 'icon.ico'} і icon.png")


if __name__ == "__main__":
    main()
