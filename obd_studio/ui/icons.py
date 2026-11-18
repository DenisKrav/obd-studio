"""Лінійні іконки (SVG 24×24), які перефарбовуються під поточну тему."""

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_PATHS = {
    "overview": '<path d="M4 15a8 8 0 1 1 16 0"/><path d="M12 15l4.5-5"/><circle cx="12" cy="15" r="1.4"/>'
                '<path d="M4 19h16"/>',
    "plug": '<path d="M9 3v5M15 3v5"/><path d="M6.5 8h11v3.5a5.5 5.5 0 0 1-11 0z"/><path d="M12 17v4"/>',
    "alert": '<path d="M10.3 3.9 2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>'
             '<path d="M12 9v4.5M12 17h.01"/>',
    "activity": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8 12.3 2.8 2.7L16.2 9"/>',
    "camera": '<rect x="3" y="7" width="18" height="13" rx="2.5"/><path d="M8.5 7l1.5-2.5h4L15.5 7"/>'
              '<circle cx="12" cy="13.5" r="3.3"/>',
    "car": '<path d="M5 11l1.6-4.3A2 2 0 0 1 8.5 5.4h7a2 2 0 0 1 1.9 1.3L19 11"/>'
           '<rect x="3" y="11" width="18" height="6" rx="2"/><path d="M6 17v2M18 17v2"/>'
           '<circle cx="7.5" cy="14" r=".9"/><circle cx="16.5" cy="14" r=".9"/>',
    "terminal": '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="m7 9 3 3-3 3M12.5 15H17"/>',
    "settings": '<path d="M4 7h9M17 7h3M4 12h3M11 12h9M4 17h11M19 17h1"/>'
                '<circle cx="15" cy="7" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="17" r="2"/>',
    "refresh": '<path d="M20 11a8 8 0 0 0-14.3-4.3L4 8.5"/><path d="M4 4v4.5h4.5"/>'
               '<path d="M4 13a8 8 0 0 0 14.3 4.3L20 15.5"/><path d="M20 20v-4.5h-4.5"/>',
    "play": '<path d="M7 4.5v15l12-7.5z"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    "record": '<circle cx="12" cy="12" r="6"/>',
    "trash": '<path d="M4 7h16M10 11v6M14 11v6"/><path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12"/>'
             '<path d="M9 7V4.5h6V7"/>',
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>'
            '<path d="M9 13h6M9 17h6"/>',
    "scan": '<path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2"/>'
            '<path d="M7 12h10"/>',
    "list": '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r=".9"/><circle cx="4.5" cy="12" r=".9"/>'
            '<circle cx="4.5" cy="18" r=".9"/>',
    "power": '<path d="M12 3v8"/><path d="M6.4 6.6a8 8 0 1 0 11.2 0"/>',
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
    "usb": '<path d="M12 3v15"/><circle cx="12" cy="19.5" r="1.8"/><path d="M12 13l-5-3V7.5M12 11l5-3V6"/>'
           '<rect x="5.5" y="5" width="3" height="2.5"/><circle cx="17" cy="5" r="1.4"/>',
    "wifi": '<path d="M2.5 9a14 14 0 0 1 19 0M5.5 12.5a9.5 9.5 0 0 1 13 0M8.6 16a5 5 0 0 1 6.8 0"/>'
            '<circle cx="12" cy="19.3" r="1"/>',
    "cable": '<path d="M4 20v-3a3 3 0 0 1 3-3h10a3 3 0 0 0 3-3V4"/><rect x="2" y="17" width="4" height="4" rx="1"/>'
             '<rect x="18" y="2" width="4" height="4" rx="1"/>',
    "bolt": '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    "engine": '<path d="M4 10v6M4 13h2M6 9h3V7h5v2h2l2 2h2v6h-2l-2 2H8l-2-2V9z"/>',
    "history": '<path d="M3.5 12a8.5 8.5 0 1 0 2.5-6"/><path d="M3 4v4h4"/><path d="M12 8v4.5l3 1.8"/>',
}


def svg(name, color, stroke=1.8):
    fill = color if name in ("play", "record") else "none"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{fill}" '
            f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round">{_PATHS[name]}</svg>')


def pixmap(name, color, size=20, ratio=2.0):
    renderer = QSvgRenderer(QByteArray(svg(name, color).encode()))
    pm = QPixmap(int(size * ratio), int(size * ratio))
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    renderer.render(p, QRectF(0, 0, pm.width(), pm.height()))
    p.end()
    pm.setDevicePixelRatio(ratio)
    return pm


def icon(name, color, checked_color=None, size=20):
    ic = QIcon()
    ic.addPixmap(pixmap(name, color, size), QIcon.Normal, QIcon.Off)
    ic.addPixmap(pixmap(name, checked_color or color, size), QIcon.Normal, QIcon.On)
    return ic
