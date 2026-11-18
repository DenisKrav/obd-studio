"""Головне вікно: бокове меню, сторінки, рядок стану."""

import csv
import datetime
import platform
import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFileDialog, QFrame, QHBoxLayout,
                               QMainWindow, QMessageBox, QProgressBar, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from .. import APP_NAME, __version__
from ..config import save_all, settings_path
from ..history import add_entry, history_path, load_history
from ..pids import DEFAULT_LIVE, PIDS, format_value
from ..report import build_html
from . import icons
from .controller import Controller
from .pages import (ConnectionPage, DtcPage, FreezePage, LivePage, LogPage, OverviewPage, ReadinessPage,
                    SettingsPage, VehiclePage)
from .theme import Theme, stylesheet
from .widgets import StatusDot, label

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

NAV = [
    ("Діагностика", [("overview", "overview", "Огляд"), ("dtc", "alert", "Коди помилок"),
                     ("live", "activity", "Дані наживо"), ("readiness", "check", "Готовність систем"),
                     ("freeze", "camera", "Стоп-кадр")]),
    ("Авто", [("vehicle", "car", "Про авто"), ("connection", "plug", "Підключення")]),
    ("Система", [("log", "terminal", "Журнал"), ("settings", "settings", "Налаштування")]),
]


def resource_path(name):
    """Файли з obd_studio/resources (у зібраному .exe — з тимчасової теки PyInstaller)."""
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "obd_studio"
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "resources" / name


def app_stylesheet():
    return stylesheet(resource_path("check.svg").as_posix(), resource_path("chevron.svg").as_posix())


def app_icon():
    ico = resource_path("icon.ico")
    return QIcon(str(ico)) if ico.exists() else QIcon()


def list_ports():
    if serial is None:
        return []
    out = []
    for p in sorted(serial.tools.list_ports.comports(), key=lambda p: p.device):
        desc = p.description or ""
        if p.manufacturer and p.manufacturer not in desc:
            desc += f" ({p.manufacturer})"
        out.append((p.device, desc))
    return out


class MainWindow(QMainWindow):
    def __init__(self, timing, app_settings):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}")
        self.setWindowIcon(app_icon())
        self.resize(1320, 860)
        self.setMinimumSize(1060, 700)
        self.ctl = Controller(timing, app_settings)
        self.log_lines = []
        self.history = load_history()
        self.recorder = None
        self.status_msg = ""
        self.current = "overview"

        c = self.ctl
        c.log.connect(self.on_log)
        c.busy.connect(self.on_busy)
        c.error.connect(self.on_error)
        c.connection_changed.connect(self.on_connection_changed)
        c.dtcs_ready.connect(lambda d: (self.p_dtc.show_dtcs(d), self.refresh_all()))
        c.readiness_ready.connect(lambda r: (self.p_ready.show_readiness(r), self.refresh_all()))
        c.freeze_ready.connect(lambda f: self.p_freeze.show_freeze(f, loaded=True))
        c.info_ready.connect(lambda _i: (self.p_vehicle.update_view(), self.refresh_all()))
        c.live_values.connect(self.on_live_values)
        c.live_state.connect(lambda _on: self.refresh_all())
        c.voltage.connect(lambda v: self.p_over.set_voltage(v))
        c.cleared.connect(lambda: self.toast("Коди помилок стерто. Вимкніть і знову увімкніть запалювання."))
        c.scan_done.connect(self.on_scan_done)

        self.build_ui()
        self.on_log(f"{APP_NAME} {__version__}, Python {platform.python_version()}, "
                    f"pyserial {getattr(serial, '__version__', '?')}, {platform.system()} {platform.release()}")
        self.on_log(f"Файл налаштувань: {settings_path()}")
        for dev, desc in list_ports():
            self.on_log(f"Порт {dev}: {desc}")

    # ─────────── побудова інтерфейсу ───────────
    def build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._sidebar())

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        sp = self.progress.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.progress.setSizePolicy(sp)
        self.progress.hide()
        right.addWidget(self.progress)
        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        right.addWidget(self._statusbar())
        root.addLayout(right, 1)

        c = self.ctl
        self.p_over = OverviewPage(c)
        self.p_conn = ConnectionPage(c, list_ports)
        self.p_dtc = DtcPage(c)
        self.p_live = LivePage(c)
        self.p_ready = ReadinessPage(c)
        self.p_freeze = FreezePage(c)
        self.p_vehicle = VehiclePage(c)
        self.p_log = LogPage()
        self.p_settings = SettingsPage(
            c, f"Налаштування: {settings_path()}\nІсторія: {history_path()}",
            f"{APP_NAME} {__version__} — універсальна діагностика OBD-II для кабелю KKL і адаптерів "
            "ELM327. Програма надсилає лише стандартні запити OBD-II на читання; єдина команда, що "
            "змінює стан блока, — стирання кодів помилок (режим 04), і лише за вашим підтвердженням.")
        self.pages = {"overview": self.p_over, "connection": self.p_conn, "dtc": self.p_dtc,
                      "live": self.p_live, "readiness": self.p_ready, "freeze": self.p_freeze,
                      "vehicle": self.p_vehicle, "log": self.p_log, "settings": self.p_settings}
        for p in self.pages.values():
            self.stack.addWidget(p)

        self.p_over.go.connect(self.on_go)
        self.p_conn.changed.connect(self.save_settings)
        self.p_dtc.report.connect(self.export_report)
        self.p_live.pids_changed.connect(self.set_live_pids)
        self.p_live.record_toggled.connect(self.on_record)
        self.p_log.save.connect(self.save_log)
        self.p_settings.theme_changed.connect(self.set_theme)
        self.p_settings.timing_saved.connect(self.on_timing_saved)
        self.p_settings.app_changed.connect(self.save_settings)

        # відновлення стану після перебудови (зміна теми)
        self.p_log.text.setPlainText("\n".join(self.log_lines))
        self.p_dtc.show_dtcs(c.dtcs)
        self.p_ready.show_readiness(c.readiness)
        if c.freeze is not None:
            self.p_freeze.show_freeze(c.freeze, loaded=True)
        self.p_vehicle.update_view()
        self.p_over.set_history(self.history)
        self.p_over.set_voltage(None)
        self._init_live_tiles()

        self.setCentralWidget(central)
        self.navigate(self.current)
        self.refresh_all()

    def _sidebar(self):
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(248)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(14, 18, 14, 14)
        lay.setSpacing(2)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = label()
        logo.setPixmap(app_icon().pixmap(QSize(38, 38)))
        brand.addWidget(logo)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(label(APP_NAME, "brandTitle"))
        col.addWidget(label("Діагностика OBD-II", "brandSub"))
        brand.addLayout(col, 1)
        lay.addLayout(brand)
        lay.addSpacing(14)

        self.nav = {}
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for section, items in NAV:
            lay.addWidget(label(section.upper(), "navSection"))
            for key, icon_name, text in items:
                b = QPushButton(f"  {text}")
                b.setObjectName("nav")
                b.setCheckable(True)
                b.setCursor(Qt.PointingHandCursor)
                b.setIcon(icons.icon(icon_name, Theme.c["muted"], Theme.c["accent"], 18))
                b.setIconSize(QSize(18, 18))
                b.clicked.connect(lambda _=False, k=key: self.navigate(k))
                self.nav_group.addButton(b)
                self.nav[key] = b
                lay.addWidget(b)
        lay.addStretch(1)

        box = QFrame()
        box.setObjectName("connBox")
        bl = QHBoxLayout(box)
        bl.setContentsMargins(12, 10, 12, 10)
        bl.setSpacing(10)
        self.conn_dot = StatusDot()
        bl.addWidget(self.conn_dot, 0, Qt.AlignVCenter)
        tcol = QVBoxLayout()
        tcol.setSpacing(0)
        self.conn_title = label("Не підключено", "connTitle")
        self.conn_sub = label("Адаптер не вибрано", "connSub")
        self.conn_sub.setWordWrap(True)
        tcol.addWidget(self.conn_title)
        tcol.addWidget(self.conn_sub)
        bl.addLayout(tcol, 1)
        box.setCursor(Qt.PointingHandCursor)
        box.mousePressEvent = lambda _e: self.navigate("connection")
        lay.addWidget(box)
        return side

    def _statusbar(self):
        bar = QFrame()
        bar.setObjectName("statusBar")
        bar.setFixedHeight(30)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        self.status_text = label("Готово", "statusText")
        lay.addWidget(self.status_text, 1)
        self.status_right = label("", "statusText")
        lay.addWidget(self.status_right)
        return bar

    # ─────────── навігація та оновлення ───────────
    def navigate(self, key):
        self.current = key
        self.stack.setCurrentWidget(self.pages[key])
        self.nav[key].setChecked(True)
        self.pages[key].refresh()

    def on_go(self, what):
        if what == "start_live":
            self.ctl.start_live()
            return
        self.navigate(what)

    def refresh_all(self):
        for p in self.pages.values():
            p.refresh()
        c = self.ctl
        if c.connected:
            self.conn_dot.set_tone("success")
            self.conn_title.setText("Підключено")
            self.conn_sub.setText(c.vehicle_title())
            self.status_right.setText(f"{c.protocol_desc}   ·   {c.adapter_desc}")
        else:
            self.conn_dot.set_tone("warning" if c.is_busy else "neutral")
            self.conn_title.setText("Підключення…" if c.is_busy else "Не підключено")
            from .controller import ADAPTER_NAMES
            where = c.app.port if c.app.adapter != "elm_wifi" else c.app.wifi_host
            self.conn_sub.setText(f"{ADAPTER_NAMES[c.app.adapter]}" + (f", {where}" if where else ""))
            self.status_right.setText("")

    def toast(self, text):
        self.status_text.setText(text)
        QTimer.singleShot(8000, lambda: self.status_text.setText(self.status_msg or "Готово")
                          if self.status_text.text() == text else None)

    # ─────────── сигнали контролера ───────────
    def on_log(self, text):
        stamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"{stamp}  {text}"
        self.log_lines.append(line)
        if len(self.log_lines) > 50000:
            del self.log_lines[:10000]
        if hasattr(self, "p_log"):
            self.p_log.text.appendPlainText(line)

    def on_busy(self, busy, title):
        self.progress.setVisible(busy)
        self.status_msg = title if busy else ""
        self.status_text.setText(title if busy else "Готово")
        self.refresh_all()

    def on_error(self, text):
        self.status_text.setText("Помилка: " + text.splitlines()[0])
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(APP_NAME)
        box.setText(text.split("\n\n")[0])
        rest = "\n\n".join(text.split("\n\n")[1:])
        if rest:
            box.setInformativeText(rest)
        box.addButton("Гаразд", QMessageBox.AcceptRole)
        log_btn = box.addButton("Відкрити журнал", QMessageBox.ActionRole)
        box.exec()
        if box.clickedButton() is log_btn:
            self.navigate("log")

    def on_connection_changed(self):
        if self.ctl.connected and self.current == "connection" and self.ctl.protocol_desc \
                and not self.ctl.is_busy and not getattr(self, "_jumped", False):
            self._jumped = True
            self.navigate("overview")
        if not self.ctl.connected:
            self._jumped = False
        self._init_live_tiles()
        self.p_vehicle.update_view()
        self.refresh_all()

    def _init_live_tiles(self):
        c = self.ctl
        cands = set(c.obd.live_candidates()) if c.obd and c.obd.supported else set(PIDS)
        pids = [p for p in (c.app.live_pids or DEFAULT_LIVE) if p in cands] or \
            [p for p in DEFAULT_LIVE if p in cands]
        if pids != c.live_pids or not self.p_live.tiles:
            c.set_live_pids(pids)
            self.p_live.build_tiles(pids)

    def set_live_pids(self, pids):
        self.ctl.app.live_pids = pids
        self.ctl.set_live_pids(pids)
        self.p_live.build_tiles(pids)
        self.save_settings()

    def on_live_values(self, values, rate):
        self.p_live.set_values(values, rate)
        self.p_over.set_live(values)
        if self.recorder:
            f, writer, pids = self.recorder
            writer.writerow([datetime.datetime.now().isoformat(timespec="milliseconds")] +
                            [format_value(p, values.get(p), with_unit=False) if values.get(p) is not None
                             else "" for p in pids])
            f.flush()

    def on_scan_done(self, entry):
        try:
            self.history = add_entry(entry)
        except OSError as e:
            self.on_log(f"Не вдалося зберегти історію: {e}")
            self.history = self.history + [dict(entry, date=datetime.datetime.now().isoformat())]
        self.p_over.set_history(self.history)
        n = len(set(entry["stored"]) | set(entry["pending"]) | set(entry["permanent"]))
        self.toast("Сканування завершено: " + ("помилок не знайдено" if not n else f"знайдено кодів: {n}"))
        self.refresh_all()

    # ─────────── дії ───────────
    def on_record(self, on):
        if not on:
            if self.recorder:
                self.recorder[0].close()
                self.on_log("Запис CSV зупинено")
            self.recorder = None
            return
        name = datetime.datetime.now().strftime("obd_studio_live_%Y-%m-%d_%H-%M.csv")
        path, _ = QFileDialog.getSaveFileName(self, "Записувати дані у файл", name, "CSV (*.csv)")
        if not path:
            self.p_live.btn_rec.setChecked(False)
            return
        pids = list(self.ctl.live_pids)
        f = open(path, "w", newline="", encoding="utf-8-sig")
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Час"] + [f"{PIDS[p].name}, {PIDS[p].unit}".rstrip(", ") for p in pids])
        self.recorder = (f, writer, pids)
        self.on_log(f"Запис CSV: {path}")
        if not self.ctl.is_live and self.ctl.connected:
            self.ctl.start_live()

    def export_report(self):
        c = self.ctl
        now = datetime.datetime.now()
        data = {
            "date": now.strftime("%d.%m.%Y %H:%M"), "vehicle": c.vehicle_title(),
            "vin_info": c.vin_info, "protocol": c.protocol_desc, "adapter": c.adapter_desc,
            "dtcs": c.dtcs, "readiness": c.readiness, "freeze": c.freeze,
            "live": dict(c.live_last), "brand": c.brand_name(),
        }
        name = now.strftime("obd_studio_report_%Y-%m-%d_%H-%M.html")
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти звіт", name, "HTML (*.html)")
        if not path:
            return
        Path(path).write_text(build_html(data), encoding="utf-8")
        self.toast(f"Звіт збережено: {path}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def save_log(self):
        name = datetime.datetime.now().strftime("obd_studio_%Y-%m-%d_%H-%M.txt")
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти журнал", name, "Текстовий файл (*.txt)")
        if not path:
            return
        c = self.ctl
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"=== {APP_NAME} {__version__} ===\n")
            f.write(f"Авто: {c.vehicle_title()}\nVIN: {c.vin_info.get('vin', '')}\n")
            f.write(f"Адаптер: {c.adapter_desc}\nПротокол: {c.protocol_desc}\n")
            if c.dtcs is not None:
                f.write(f"Коди: {c.dtcs}\n")
            f.write("\n=== Журнал ===\n")
            f.write("\n".join(self.log_lines) + "\n")
        self.toast(f"Журнал збережено: {path}")

    def save_settings(self):
        try:
            save_all(self.ctl.timing, self.ctl.app)
        except OSError as e:
            self.on_log(f"Не вдалося зберегти налаштування: {e}")
        self.p_vehicle.update_view() if hasattr(self, "p_vehicle") else None
        self.refresh_all()

    def on_timing_saved(self, timing):
        self.ctl.timing = timing
        self.save_settings()
        self.on_log("Нові параметри K-лінії (діють з наступного підключення):")
        for line in timing.describe():
            self.on_log(line)
        self.toast("Параметри збережено. Вони діятимуть з наступного підключення.")

    def set_theme(self, name):
        if name == Theme.name:
            return
        self.ctl.app.theme = name
        Theme.set(name)
        QApplication.instance().setStyleSheet(app_stylesheet())
        old = self.centralWidget()
        self.build_ui()
        old.deleteLater()
        self.save_settings()

    def closeEvent(self, e):
        if self.recorder:
            self.recorder[0].close()
        self.ctl.shutdown()
        self.save_settings()
        super().closeEvent(e)
