"""Сторінки головного вікна."""

import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QDialog,
                               QDialogButtonBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                               QHeaderView, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QPushButton, QScrollArea, QSizePolicy, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from ..config import Timing
from ..dtc import DTC_TEXT as DTC_TEXT_KNOWN
from ..dtc import KIND_NAMES, describe_dtc, dtc_severity, is_manufacturer_code
from ..elm327 import PROTOCOLS
from ..pids import GAUGE_PIDS, PIDS, format_value
from ..vehicles import BRANDS
from . import icons
from .theme import Theme
from .widgets import (Card, ComboBox, EmptyState, Gauge, LiveChart, PageHeader, Pill, SpinBox, StatTile,
                      ValueTile, label)

KIND_LABEL = {"stored": ("Збережена", "danger"), "pending": ("Очікує", "warning"),
              "permanent": ("Постійна", "accent")}
SEVERITY = {"high": ("Висока", "danger"), "medium": ("Середня", "warning"), "low": ("Низька", "accent")}


def button(text, icon_name=None, kind=None, tip=None):
    b = QPushButton(text)
    if kind:
        b.setObjectName(kind)
    if icon_name:
        color = Theme.c["accent_text"] if kind == "primary" else \
            Theme.c["danger"] if kind == "danger" else Theme.c["text"]
        b.setIcon(icons.icon(icon_name, color, size=16))
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    return b


class Page(QScrollArea):
    """Сторінка з прокруткою, заголовком і вертикальним вмістом."""

    def __init__(self, title, subtitle=""):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner.setObjectName("page")
        self.body = QVBoxLayout(inner)
        self.body.setContentsMargins(32, 28, 32, 28)
        self.body.setSpacing(18)
        self.header = PageHeader(title, subtitle)
        self.body.addWidget(self.header)
        self.setWidget(inner)

    def finish(self):
        self.body.addStretch(1)


def make_table(headers, stretch_col, pill_cols=()):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setShowGrid(False)
    t.setFocusPolicy(Qt.NoFocus)
    t.verticalHeader().setDefaultSectionSize(44)
    hh = t.horizontalHeader()
    hh.setHighlightSections(False)
    for i in range(len(headers)):
        hh.setSectionResizeMode(i, QHeaderView.Stretch if i == stretch_col else QHeaderView.ResizeToContents)
    for i in pill_cols:            # ширина колонок із бейджами не враховує cell-widget
        hh.setSectionResizeMode(i, QHeaderView.Fixed)
        t.setColumnWidth(i, 150)
    hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    return t


def fit_table(t):
    t.setFixedHeight(t.horizontalHeader().height() + 44 * t.rowCount() + 6)


def pill_cell(text, tone):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(8, 0, 8, 0)
    lay.addWidget(Pill(text, tone))
    lay.addStretch(1)
    return w


# ─────────────────────────── Огляд ───────────────────────────

class OverviewPage(Page):
    go = Signal(str)

    def __init__(self, ctl):
        super().__init__("Огляд", "Стан авто та основні показники одним поглядом")
        self.ctl = ctl
        self.btn_scan = self.header.add_action(button("Повне сканування", "scan", "primary",
                                                      "Готовність систем, усі коди помилок і стоп-кадр"))
        self.btn_scan.clicked.connect(ctl.quick_scan)

        # картка авто
        hero = Card()
        row = QHBoxLayout()
        row.setSpacing(16)
        self.car_icon = label()
        row.addWidget(self.car_icon, 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(4)
        self.car_title = label("Авто не підключено", "heroTitle")
        self.car_sub = label("Підключіть адаптер до роз’єму OBD-II і натисніть «Підключитися»",
                             "muted", wrap=True)
        col.addWidget(self.car_title)
        col.addWidget(self.car_sub)
        chips = QHBoxLayout()
        chips.setSpacing(6)
        self.chip_state = Pill("Не підключено")
        self.chip_proto = Pill("")
        chips.addWidget(self.chip_state)
        chips.addWidget(self.chip_proto)
        chips.addStretch(1)
        col.addLayout(chips)
        row.addLayout(col, 1)
        self.btn_connect = button("Підключитися", "plug", "primary")
        self.btn_connect.clicked.connect(lambda: self.go.emit("connection"))
        row.addWidget(self.btn_connect, 0, Qt.AlignVCenter)
        hero.add(row)
        self.body.addWidget(hero)

        # плитки
        grid = QGridLayout()
        grid.setSpacing(14)
        self.t_mil = StatTile("engine", "Check Engine")
        self.t_dtc = StatTile("alert", "Коди помилок")
        self.t_ready = StatTile("check", "Готовність систем")
        self.t_volt = StatTile("bolt", "Напруга мережі")
        for i, t in enumerate((self.t_mil, self.t_dtc, self.t_ready, self.t_volt)):
            grid.addWidget(t, 0, i)
        self.body.addLayout(grid)

        # прилади
        gauges = Card("Прилади", "Оновлюються, коли запущено дані наживо")
        self.btn_live = gauges.add_action(button("Запустити", "play"))
        self.btn_live.clicked.connect(self.toggle_live)
        g_row = QHBoxLayout()
        g_row.setSpacing(10)
        self.gauges = {}
        warn = {0x0C: 6000, 0x05: 105}
        for pid in GAUGE_PIDS:
            d = PIDS[pid]
            g = Gauge(d.short, d.unit, d.lo, d.hi if pid != 0x05 else 130, d.decimals, warn.get(pid))
            g.setMinimumHeight(190)
            self.gauges[pid] = g
            g_row.addWidget(g)
        gauges.add(g_row)
        self.body.addWidget(gauges)

        # історія
        self.hist_card = Card("Останні сканування", "Зберігаються у файлі obd_studio_history.json")
        self.hist_list = QListWidget()
        self.hist_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.hist_list.setFocusPolicy(Qt.NoFocus)
        self.hist_card.add(self.hist_list)
        self.body.addWidget(self.hist_card)
        self.finish()
        self.refresh()

    def toggle_live(self):
        if self.ctl.is_live:
            self.ctl.stop_live()
        else:
            self.go.emit("start_live")

    def set_history(self, entries):
        self.hist_list.clear()
        for e in reversed(entries[-8:]):
            codes = e.get("stored", []) + e.get("pending", []) + e.get("permanent", [])
            date = e.get("date", "").replace("T", " ")[:16]
            what = ", ".join(dict.fromkeys(codes)) if codes else "помилок немає"
            QListWidgetItem(f"{date}    {e.get('vehicle', '')}    —    {what}", self.hist_list)
        if not entries:
            QListWidgetItem("Ще не було жодного сканування", self.hist_list)
        rows = sum(self.hist_list.sizeHintForRow(i) for i in range(self.hist_list.count()))
        self.hist_list.setFixedHeight(rows + 2 * self.hist_list.frameWidth() + 6)

    def refresh(self):
        ctl = self.ctl
        conn = ctl.connected
        self.car_icon.setPixmap(icons.pixmap("car", Theme.c["accent" if conn else "faint"], 44))
        if conn:
            self.car_title.setText(ctl.vehicle_title())
            vin = ctl.vin_info.get("vin")
            self.car_sub.setText((f"VIN {vin}   ·   " if vin else "") + ctl.adapter_desc)
            self.chip_state.set("Підключено", "success")
            self.chip_proto.set(ctl.protocol_desc, "accent")
            self.chip_proto.show()
        else:
            self.car_title.setText("Авто не підключено")
            self.car_sub.setText("Підключіть адаптер до роз’єму OBD-II, увімкніть запалювання "
                                 "й натисніть «Підключитися»")
            self.chip_state.set("Не підключено", "neutral")
            self.chip_proto.hide()
        self.btn_connect.setVisible(not conn)
        self.btn_scan.setEnabled(conn and not ctl.is_busy)
        self.btn_live.setEnabled(conn)
        live = ctl.is_live
        self.btn_live.setText("Зупинити" if live else "Запустити")
        self.btn_live.setIcon(icons.icon("stop" if live else "play", Theme.c["text"], size=16))

        rd = ctl.readiness
        if rd:
            self.t_mil.set("Горить" if rd["mil"] else "Не горить",
                           f"Підтверджених помилок: {rd['dtc_count']}",
                           "danger" if rd["mil"] else "success")
            total = len(rd["monitors"])
            ready = sum(1 for _, ok in rd["monitors"] if ok)
            self.t_ready.set(f"{ready} / {total}", "систем завершили самоперевірку",
                             "success" if ready == total else "warning")
        else:
            self.t_mil.set("—", "Дані з’являться після підключення")
            self.t_ready.set("—", "")
        d = ctl.dtcs
        if d is not None:
            n = len(set(d["stored"]) | set(d["pending"]) | set(d["permanent"]))
            self.t_dtc.set(str(n), "немає помилок" if not n else
                           f"збережених {len(d['stored'])}, очікують {len(d['pending'])}",
                           "success" if not n else "danger" if d["stored"] else "warning")
        else:
            self.t_dtc.set("—", "Натисніть «Повне сканування»")

    def set_voltage(self, v):
        if v is None:
            self.t_volt.set("—", "Адаптер KKL напругу не міряє" if self.ctl.connected else "")
        else:
            tone = "success" if 12.2 <= v <= 14.8 else "warning" if v >= 11.8 else "danger"
            note = "двигун працює, зарядка є" if v >= 13.2 else "норма без зарядки" if v >= 12.2 \
                else "акумулятор розряджений"
            self.t_volt.set(f"{v:.1f} В", note, tone)

    def set_live(self, values):
        for pid, g in self.gauges.items():
            if pid in values:
                g.set_value(values[pid])


# ─────────────────────────── Підключення ───────────────────────────

class ConnectionPage(Page):
    changed = Signal()

    def __init__(self, ctl, list_ports):
        super().__init__("Підключення", "Виберіть адаптер, порт і марку авто")
        self.ctl = ctl
        self.list_ports = list_ports
        app = ctl.app

        ad = Card("Адаптер", "Чим ноутбук підключено до діагностичного роз’єму авто")
        row = QHBoxLayout()
        row.setSpacing(12)
        self.choice_group = QButtonGroup(self)
        self.choices = {}
        for key, icon_name, title, text in (
                ("kkl", "cable", "Кабель KKL", "VAG KKL 409.1 та подібні\nK-лінія: ISO 9141-2, KWP2000"),
                ("elm_serial", "usb", "ELM327 USB / Bluetooth", "Усі протоколи OBD-II,\nзокрема CAN (авто після 2008)"),
                ("elm_wifi", "wifi", "ELM327 Wi-Fi", "Усі протоколи OBD-II\nчерез Wi-Fi мережу адаптера")):
            b = QPushButton()
            b.setObjectName("choice")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setMinimumHeight(84)
            bl = QHBoxLayout(b)
            bl.setContentsMargins(16, 12, 16, 12)
            bl.setSpacing(14)
            parts = [label(), label(title, "choiceTitle"), label(text, "choiceText")]
            parts[0].setPixmap(icons.pixmap(icon_name, Theme.c["accent"], 28))
            bl.addWidget(parts[0], 0, Qt.AlignVCenter)
            tl = QVBoxLayout()
            tl.setSpacing(2)
            tl.addWidget(parts[1])
            tl.addWidget(parts[2])
            bl.addLayout(tl, 1)
            for w in parts:
                w.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.choice_group.addButton(b)
            self.choices[key] = b
            b.clicked.connect(lambda _=False, k=key: self.set_adapter(k))
            row.addWidget(b)
        ad.add(row)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        port_row = QHBoxLayout()
        self.port = ComboBox()
        self.port.setMinimumWidth(320)
        self.port.currentIndexChanged.connect(self._port_changed)
        port_row.addWidget(self.port, 1)
        self.btn_refresh = button("", "refresh", tip="Оновити список портів")
        self.btn_refresh.clicked.connect(self.refresh_ports)
        port_row.addWidget(self.btn_refresh)
        self.port_row = QWidget()
        self.port_row.setLayout(port_row)
        port_row.setContentsMargins(0, 0, 0, 0)
        form.addRow("COM-порт", self.port_row)

        wifi_row = QHBoxLayout()
        wifi_row.setContentsMargins(0, 0, 0, 0)
        self.host = QLineEdit(app.wifi_host)
        self.wport = SpinBox()
        self.wport.setRange(1, 65535)
        self.wport.setValue(app.wifi_port)
        wifi_row.addWidget(self.host, 1)
        wifi_row.addWidget(label(":", "muted"))
        wifi_row.addWidget(self.wport)
        self.wifi_row = QWidget()
        self.wifi_row.setLayout(wifi_row)
        form.addRow("Адреса адаптера", self.wifi_row)
        self.host.editingFinished.connect(self._save_fields)
        self.wport.valueChanged.connect(self._save_fields)

        self.proto = ComboBox()
        for k, v in PROTOCOLS.items():
            self.proto.addItem(v, k)
        self.proto.setCurrentIndex(max(0, self.proto.findData(app.elm_protocol)))
        self.proto.currentIndexChanged.connect(self._save_fields)
        form.addRow("Протокол", self.proto)
        self.form = form
        ad.add(form)
        self.adapter_hint = label("", "hint", wrap=True)
        ad.add(self.adapter_hint)
        self.body.addWidget(ad)

        car = Card("Марка авто", "Програма працює зі стандартним OBD-II для будь-якої марки. "
                                 "Профіль марки підказує, який адаптер потрібен, і уточнює описи кодів.")
        self.brand = ComboBox()
        self.brand.addItem("Автовизначення за VIN", "auto")
        for b in BRANDS:
            self.brand.addItem(b.name, b.key)
        self.brand.setCurrentIndex(max(0, self.brand.findData(app.brand)))
        self.brand.currentIndexChanged.connect(self._brand_changed)
        car.add(self.brand)
        self.brand_hint = label("", "hint", wrap=True)
        car.add(self.brand_hint)
        self.body.addWidget(car)

        act = QHBoxLayout()
        self.status = label("", "muted", wrap=True)
        act.addWidget(self.status, 1)
        self.btn_connect = button("Підключитися", "plug", "primary")
        self.btn_connect.setMinimumHeight(42)
        self.btn_connect.setMinimumWidth(190)
        self.btn_connect.clicked.connect(self.on_connect)
        act.addWidget(self.btn_connect)
        self.body.addLayout(act)

        tips = Card("Перед підключенням")
        tips.add(label("1.  Вставте адаптер у роз’єм OBD-II (зазвичай під кермом зліва).\n"
                       "2.  Увімкніть запалювання. Двигун можна не заводити.\n"
                       "3.  Закрийте інші діагностичні програми (VCDS-Lite, Torque тощо) — вони займають порт.\n"
                       "4.  Для Bluetooth спершу спарте адаптер у Windows (PIN зазвичай 1234 або 0000).\n"
                       "5.  Кабелю KKL потрібні 12 В від авто: без запалювання він мовчить.",
                       "muted", wrap=True))
        self.body.addWidget(tips)
        self.finish()

        self.choices.get(app.adapter, self.choices["kkl"]).setChecked(True)
        self.refresh_ports()
        self.set_adapter(app.adapter if app.adapter in self.choices else "kkl", save=False)
        self._brand_changed(save=False)

    # ── поля ──
    def refresh_ports(self):
        ports = self.list_ports()
        self.port.blockSignals(True)
        self.port.clear()
        for dev, desc in ports:
            self.port.addItem(f"{dev}   —   {desc}", dev)
        want = self.ctl.app.port
        idx = self.port.findData(want) if want else -1
        if idx < 0:
            adapter = self.ctl.app.adapter
            for i, (dev, desc) in enumerate(ports):
                d = desc.upper()
                if (adapter == "kkl" and ("FTDI" in d or "USB SERIAL" in d)) or \
                        (adapter == "elm_serial" and ("CH340" in d or "BLUETOOTH" in d or "ELM" in d
                                                      or "PL2303" in d or "CP210" in d)):
                    idx = i
                    break
        self.port.setCurrentIndex(max(0, idx) if ports else -1)
        self.port.blockSignals(False)
        if not ports:
            self.port.setPlaceholderText("Портів не знайдено — підключіть адаптер")
        self._port_changed()

    def _port_changed(self, *_):
        self.ctl.app.port = self.port.currentData() or ""
        self.changed.emit()

    def _save_fields(self, *_):
        self.ctl.app.wifi_host = self.host.text().strip() or "192.168.0.10"
        self.ctl.app.wifi_port = self.wport.value()
        self.ctl.app.elm_protocol = self.proto.currentData() or "0"
        self.changed.emit()

    def set_adapter(self, key, save=True):
        self.ctl.app.adapter = key
        self.choices[key].setChecked(True)
        is_wifi, is_elm = key == "elm_wifi", key != "kkl"
        self.form.setRowVisible(self.port_row, not is_wifi)
        self.form.setRowVisible(self.wifi_row, is_wifi)
        self.form.setRowVisible(self.proto, is_elm)
        self.adapter_hint.setText({
            "kkl": "Кабель KKL працює лише з K-лінією (переважно авто до 2008 р.). Програма сама "
                   "по черзі пробує швидкий і повільний старт. Часові параметри — у «Налаштуваннях».",
            "elm_serial": "Для USB-адаптера виберіть його COM-порт. Для Bluetooth — вихідний (Outgoing) "
                          "COM-порт спареного адаптера. Швидкість підбирається автоматично.",
            "elm_wifi": "Підключіть ноутбук до Wi-Fi мережі адаптера (часто «WiFi_OBDII»). Типова адреса — "
                        "192.168.0.10, порт 35000.",
        }[key])
        if save:
            self.refresh_ports()
            self.changed.emit()

    def _brand_changed(self, *_, save=True):
        key = self.brand.currentData()
        self.ctl.app.brand = key
        if key == "auto":
            self.brand_hint.setText("Марку буде визначено за VIN, якщо блок керування його повідомить "
                                    "(зазвичай авто після ~2005 р.). Інакше виберіть марку вручну.")
        else:
            b = next(b for b in BRANDS if b.key == key)
            self.brand_hint.setText(b.adapter_hint)
        if save:
            self.changed.emit()

    def on_connect(self):
        if self.ctl.connected:
            self.ctl.disconnect()
        else:
            self._save_fields()
            self.ctl.connect()

    def refresh(self):
        conn, busy = self.ctl.connected, self.ctl.is_busy
        self.btn_connect.setText("Відключитися" if conn else "Підключитися")
        self.btn_connect.setObjectName("danger" if conn else "primary")
        self.btn_connect.setIcon(icons.icon("power" if conn else "plug",
                                            Theme.c["danger" if conn else "accent_text"], size=16))
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)
        self.btn_connect.setEnabled(not busy)
        for w in list(self.choices.values()) + [self.port, self.btn_refresh, self.host, self.wport, self.proto]:
            w.setEnabled(not conn and not busy)
        if conn:
            self.status.setText(f"Підключено: {self.ctl.protocol_desc}")
        elif busy:
            self.status.setText("Підключення може тривати до 20 секунд…")
        else:
            self.status.setText("")


# ─────────────────────────── Коди помилок ───────────────────────────

class DtcPage(Page):
    report = Signal()

    def __init__(self, ctl):
        super().__init__("Коди помилок", "Збережені, ті, що очікують підтвердження, і постійні (лише CAN)")
        self.ctl = ctl
        self.btn_read = self.header.add_action(button("Зчитати", "refresh", "primary"))
        self.btn_report = self.header.add_action(button("Звіт", "file", tip="Зберегти HTML-звіт"))
        self.btn_clear = self.header.add_action(button("Стерти коди", "trash", "danger"))
        self.btn_read.clicked.connect(ctl.read_dtcs)
        self.btn_report.clicked.connect(self.report.emit)
        self.btn_clear.clicked.connect(self.confirm_clear)

        sums = QHBoxLayout()
        sums.setSpacing(14)
        self.s_stored = StatTile("alert", "Збережені")
        self.s_pending = StatTile("history", "Очікують підтвердження")
        self.s_perm = StatTile("list", "Постійні")
        for t in (self.s_stored, self.s_pending, self.s_perm):
            sums.addWidget(t)
        self.body.addLayout(sums)

        self.card = Card()
        self.table = make_table(["Код", "Тип", "Опис", "Система", "Серйозність"], 2, pill_cols=(1, 4))
        self.table.setWordWrap(True)
        self.card.add(self.table)
        self.empty = EmptyState("scan", "Коди ще не зчитано",
                                "Підключіться до авто й натисніть «Зчитати». Програма покаже коди з "
                                "описом українською та орієнтовною серйозністю.")
        self.card.add(self.empty)
        self.body.addWidget(self.card)
        note = label("Стирання кодів не усуває несправність: якщо вона є, код повернеться. Також "
                     "скинуться статуси готовності систем самодіагностики (це важливо перед техоглядом).",
                     "faint", wrap=True)
        self.body.addWidget(note)
        self.finish()
        self.show_dtcs(None)

    def confirm_clear(self):
        from PySide6.QtWidgets import QMessageBox
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Стерти коди помилок?")
        box.setText("Стерти всі коди помилок і стоп-кадр?")
        box.setInformativeText("Перед стиранням заглушіть двигун, запалювання залиште увімкненим.\n\n"
                               "Стирання не усуває несправність. Також скинуться статуси готовності "
                               "систем самодіагностики.")
        yes = box.addButton("Стерти", QMessageBox.DestructiveRole)
        box.addButton("Скасувати", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is yes:
            self.ctl.clear_dtcs()

    def show_dtcs(self, d):
        self.table.setRowCount(0)
        if d is None:
            for t in (self.s_stored, self.s_pending, self.s_perm):
                t.set("—", "")
            self.table.hide()
            self.empty.show()
            self.empty.set("scan", "faint", "Коди ще не зчитано",
                           "Підключіться до авто й натисніть «Зчитати». Програма покаже коди з описом "
                           "українською та орієнтовною серйозністю.")
            return
        self.s_stored.set(str(len(d["stored"])),
                          "за даними PID 01 (блок не відповів на запит кодів)" if d.get("stored_inferred")
                          else "підтверджені, запалюють Check Engine",
                          "danger" if d["stored"] else "success")
        self.s_pending.set(str(len(d["pending"])) if d.get("pending_supported", True) else "н/д",
                           "виявлені в поточному циклі поїздки" if d.get("pending_supported", True)
                           else "блок не підтримує цей запит",
                           "warning" if d["pending"] else "success")
        perm_known = self.ctl.is_can()
        self.s_perm.set(str(len(d["permanent"])) if perm_known else "н/д",
                        "не стираються вручну, зникають самі" if perm_known else "лише для авто з CAN",
                        "accent" if d["permanent"] else "success" if perm_known else "neutral")
        rows = [(kind, c) for kind in ("stored", "pending", "permanent") for c in d[kind]]
        if not rows:
            self.table.hide()
            self.empty.show()
            self.empty.set("check", "success", "Помилок не знайдено",
                           "Блок керування не повідомив жодного коду помилки.")
            return
        self.empty.hide()
        self.table.show()
        brand = self.ctl.brand_name()
        for kind, code in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            it = QTableWidgetItem(code)
            f = it.font()
            f.setBold(True)
            f.setFamily("Cascadia Mono")
            f.setPointSize(11)
            it.setFont(f)
            self.table.setItem(r, 0, it)
            self.table.setCellWidget(r, 1, pill_cell(*KIND_LABEL[kind]))
            desc = describe_dtc(code, brand)
            if is_manufacturer_code(code) and code in DTC_TEXT_KNOWN:
                desc += f"  (код виробника{', ' + brand if brand else ''})"
            self.table.setItem(r, 2, QTableWidgetItem(desc))
            self.table.setItem(r, 3, QTableWidgetItem(KIND_NAMES.get(code[0], "")))
            self.table.setCellWidget(r, 4, pill_cell(*SEVERITY[dtc_severity(code)]))
        self.table.resizeRowsToContents()
        for r in range(self.table.rowCount()):
            self.table.setRowHeight(r, max(44, self.table.rowHeight(r)))
        self.table.setFixedHeight(self.table.horizontalHeader().height()
                                  + sum(self.table.rowHeight(r) for r in range(self.table.rowCount())) + 6)

    def refresh(self):
        ok = self.ctl.connected and not self.ctl.is_busy
        self.btn_read.setEnabled(ok)
        self.btn_clear.setEnabled(ok)


# ─────────────────────────── Дані наживо ───────────────────────────

class PidChooser(QDialog):
    def __init__(self, parent, candidates, selected, supported_known):
        super().__init__(parent)
        self.setWindowTitle("Параметри для відображення")
        self.resize(520, 600)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(10)
        lay.addWidget(label("Виберіть параметри. Що менше параметрів, то частіше вони оновлюються "
                            "(особливо на K-лінії)." + ("" if supported_known else
                                                         "\nБлок не повідомив, що підтримує, тож "
                                                         "показано всі параметри."), "muted", wrap=True))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Пошук…")
        lay.addWidget(self.search)
        self.list = QListWidget()
        for pid in candidates:
            d = PIDS[pid]
            it = QListWidgetItem(f"{d.name}" + (f"  ({d.unit})" if d.unit else ""), self.list)
            it.setData(Qt.UserRole, pid)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if pid in selected else Qt.Unchecked)
        lay.addWidget(self.list, 1)
        self.search.textChanged.connect(self._filter)
        row = QHBoxLayout()
        b_all = button("Усі")
        b_none = button("Жодного")
        b_all.clicked.connect(lambda: self._set_all(True))
        b_none.clicked.connect(lambda: self._set_all(False))
        row.addWidget(b_all)
        row.addWidget(b_none)
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Застосувати")
        bb.button(QDialogButtonBox.Ok).setObjectName("primary")
        bb.button(QDialogButtonBox.Cancel).setText("Скасувати")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        row.addWidget(bb)
        lay.addLayout(row)

    def _filter(self, text):
        text = text.lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setHidden(text not in it.text().lower())

    def _set_all(self, on):
        for i in range(self.list.count()):
            it = self.list.item(i)
            if not it.isHidden():
                it.setCheckState(Qt.Checked if on else Qt.Unchecked)

    def selected(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.Checked]


class LivePage(Page):
    pids_changed = Signal(list)
    record_toggled = Signal(bool)

    def __init__(self, ctl):
        super().__init__("Дані наживо", "Параметри двигуна в реальному часі. Клацніть плитку, щоб "
                                         "показати її на графіку")
        self.ctl = ctl
        self.rate = label("", "muted")
        self.header.add_action(self.rate)
        self.btn_pids = self.header.add_action(button("Параметри", "list"))
        self.btn_rec = self.header.add_action(button("Запис CSV", "record", tip="Записувати значення у файл CSV"))
        self.btn_rec.setCheckable(True)
        self.btn_live = self.header.add_action(button("Запустити", "play", "primary"))
        self.btn_live.clicked.connect(self.toggle)
        self.btn_pids.clicked.connect(self.choose)
        self.btn_rec.toggled.connect(self.record_toggled.emit)

        chart_card = Card()
        self.chart = LiveChart()
        chart_card.add(self.chart)
        self.body.addWidget(chart_card)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.body.addWidget(self.grid_host)
        self.tiles = {}
        self.selected = None
        self.finish()

    def build_tiles(self, pids):
        for t in self.tiles.values():
            t.setParent(None)
            t.deleteLater()
        self.tiles = {}
        cols = 4
        for i, pid in enumerate(pids):
            d = PIDS[pid]
            t = ValueTile(pid, d.name, d.unit)
            t.clicked.connect(self.select)
            self.tiles[pid] = t
            self.grid.addWidget(t, i // cols, i % cols)
        if pids and self.selected not in pids:
            self.select(pids[0])

    def select(self, pid):
        self.selected = pid
        for p, t in self.tiles.items():
            t.set_selected(p == pid)
        d = PIDS[pid]
        self.chart.configure(d.name, d.unit, d.decimals)

    def choose(self):
        cands = self.ctl.obd.live_candidates() if self.ctl.obd else sorted(PIDS)
        dlg = PidChooser(self, cands, self.ctl.live_pids, bool(self.ctl.obd and self.ctl.obd.supported))
        if dlg.exec():
            pids = dlg.selected()
            self.pids_changed.emit(pids)

    def toggle(self):
        if self.ctl.is_live:
            self.ctl.stop_live()
        else:
            self.ctl.start_live()

    def set_values(self, values, rate):
        for pid, v in values.items():
            t = self.tiles.get(pid)
            if t:
                t.set_value(format_value(pid, v, with_unit=False), v)
            if pid == self.selected:
                self.chart.add(v)
        self.rate.setText(f"{rate:.1f} оновл./с" if rate else "")

    def refresh(self):
        live = self.ctl.is_live
        self.btn_live.setText("Зупинити" if live else "Запустити")
        self.btn_live.setIcon(icons.icon("stop" if live else "play", Theme.c["accent_text"], size=16))
        self.btn_live.setEnabled(self.ctl.connected or live)
        if not live:
            self.rate.setText("")


# ─────────────────────────── Готовність ───────────────────────────

class ReadinessPage(Page):
    def __init__(self, ctl):
        super().__init__("Готовність систем", "Лампа Check Engine і статус самоперевірок (монітори OBD-II)")
        self.ctl = ctl
        self.btn = self.header.add_action(button("Оновити", "refresh", "primary"))
        self.btn.clicked.connect(ctl.read_readiness)
        top = QHBoxLayout()
        top.setSpacing(14)
        self.t_mil = StatTile("engine", "Check Engine")
        self.t_count = StatTile("alert", "Підтверджених помилок")
        self.t_ready = StatTile("check", "Готово систем")
        for t in (self.t_mil, self.t_count, self.t_ready):
            top.addWidget(t)
        self.body.addLayout(top)
        self.card = Card("Монітори самодіагностики")
        self.table = make_table(["Система", "Стан"], 0, pill_cols=(1,))
        self.card.add(self.table)
        self.empty = EmptyState("check", "Дані ще не зчитано", "Підключіться до авто — стан систем "
                                                               "зчитується автоматично.")
        self.card.add(self.empty)
        self.body.addWidget(self.card)
        self.body.addWidget(label("«Не готово» буває після стирання помилок або відключення акумулятора: "
                                  "система ще не завершила самоперевірку. Після кількох днів звичайної "
                                  "їзди статус зазвичай змінюється на «готово». Для техогляду зазвичай "
                                  "потрібно, щоб були готові всі системи (або всі, крім однієї).",
                                  "faint", wrap=True))
        self.finish()
        self.show_readiness(None)

    def show_readiness(self, rd):
        self.table.setRowCount(0)
        if not rd:
            for t in (self.t_mil, self.t_count, self.t_ready):
                t.set("—", "")
            self.table.hide()
            self.empty.show()
            return
        self.empty.hide()
        self.table.show()
        self.t_mil.set("Горить" if rd["mil"] else "Не горить", "", "danger" if rd["mil"] else "success")
        self.t_count.set(str(rd["dtc_count"]), "", "danger" if rd["dtc_count"] else "success")
        ready = sum(1 for _, ok in rd["monitors"] if ok)
        total = len(rd["monitors"])
        self.t_ready.set(f"{ready} / {total}", "дизельний двигун" if rd["diesel"] else "бензиновий двигун",
                         "success" if ready == total else "warning")
        for name, ok in rd["monitors"]:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(name))
            self.table.setCellWidget(r, 1, pill_cell("Готово" if ok else "Не готово",
                                                     "success" if ok else "warning"))
        fit_table(self.table)

    def refresh(self):
        self.btn.setEnabled(self.ctl.connected and not self.ctl.is_busy)


# ─────────────────────────── Стоп-кадр ───────────────────────────

class FreezePage(Page):
    def __init__(self, ctl):
        super().__init__("Стоп-кадр", "Значення датчиків у момент, коли блок зафіксував помилку (режим 02)")
        self.ctl = ctl
        self.btn = self.header.add_action(button("Зчитати", "camera", "primary"))
        self.btn.clicked.connect(ctl.read_freeze)
        self.card = Card()
        self.code = label("", "heroTitle")
        self.code_desc = label("", "muted", wrap=True)
        self.card.add(self.code)
        self.card.add(self.code_desc)
        self.table = make_table(["Параметр", "Значення"], 0)
        self.card.add(self.table)
        self.empty = EmptyState("camera", "Стоп-кадр ще не зчитано",
                                "Стоп-кадр зберігається разом із першою підтвердженою помилкою. "
                                "Він допомагає зрозуміти умови, за яких виникла несправність.")
        self.card.add(self.empty)
        self.body.addWidget(self.card)
        self.finish()
        self.loaded = False
        self.show_freeze(None)

    def show_freeze(self, fr, loaded=False):
        self.table.setRowCount(0)
        self.loaded = loaded or self.loaded
        if not fr:
            self.code.hide()
            self.code_desc.hide()
            self.table.hide()
            self.empty.show()
            if loaded:
                self.empty.set("check", "success", "Стоп-кадру немає",
                               "Блок керування не зберігав стоп-кадр — зазвичай це означає, що "
                               "підтверджених помилок немає.")
            return
        code, values = fr
        self.empty.hide()
        self.code.show()
        self.code_desc.show()
        self.table.show()
        self.code.setText(f"Код {code}")
        self.code_desc.setText(describe_dtc(code, self.ctl.brand_name()))
        for pid, v in values.items():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(PIDS[pid].name))
            it = QTableWidgetItem(format_value(pid, v))
            f = it.font()
            f.setBold(True)
            it.setFont(f)
            self.table.setItem(r, 1, it)
        fit_table(self.table)

    def refresh(self):
        self.btn.setEnabled(self.ctl.connected and not self.ctl.is_busy)


# ─────────────────────────── Про авто ───────────────────────────

class VehiclePage(Page):
    def __init__(self, ctl):
        super().__init__("Про авто", "VIN, ідентифікатори прошивки та дані блока керування (режим 09)")
        self.ctl = ctl
        self.btn = self.header.add_action(button("Зчитати", "car", "primary"))
        self.btn.clicked.connect(ctl.read_info)
        self.card = Card("Ідентифікація")
        self.vin = label("—", "vin")
        self.vin.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.card.add(self.vin)
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(24)
        self.grid.setVerticalSpacing(10)
        self.fields = {}
        for i, (key, title) in enumerate((("brand", "Марка (за VIN)"), ("year", "Модельний рік"),
                                          ("region", "Регіон виробництва"), ("wmi", "Код виробника (WMI)"),
                                          ("calid", "ID калібрування"), ("cvn", "CVN"),
                                          ("ecu", "Блок керування"), ("pids", "Підтримуваних параметрів"),
                                          ("protocol", "Протокол"), ("adapter", "Адаптер"))):
            t = label(title, "muted")
            v = label("—")
            v.setWordWrap(True)
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.grid.addWidget(t, i // 2, (i % 2) * 2)
            self.grid.addWidget(v, i // 2, (i % 2) * 2 + 1)
            self.fields[key] = v
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(3, 1)
        self.card.add(self.grid)
        self.note = label("", "hint", wrap=True)
        self.card.add(self.note)
        self.body.addWidget(self.card)
        self.hint_card = Card("Порада щодо адаптера")
        self.brand_hint = label("", "muted", wrap=True)
        self.hint_card.add(self.brand_hint)
        self.body.addWidget(self.hint_card)
        self.finish()
        self.update_view()

    def update_view(self):
        ctl = self.ctl
        info, dec = ctl.vin_info or {}, ctl.vin_decoded
        f = self.fields
        self.vin.setText(info.get("vin") or "VIN невідомий")
        b = dec["brand"] if dec else None
        f["brand"].setText(b.name if b else "—")
        f["year"].setText(" або ".join(map(str, dec["years"])) if dec and dec["years"] else "—")
        f["region"].setText(dec["region"] if dec and dec["region"] else "—")
        f["wmi"].setText(dec["wmi"] if dec else "—")
        f["calid"].setText("\n".join(info.get("calibration_ids") or []) or "—")
        f["cvn"].setText(", ".join(info.get("cvn") or []) or "—")
        f["ecu"].setText(info.get("ecu_name") or "—")
        f["pids"].setText(str(len(ctl.obd.supported)) if ctl.obd and ctl.obd.supported else "—")
        f["protocol"].setText(ctl.protocol_desc or "—")
        f["adapter"].setText(ctl.adapter_desc or "—")
        if info and not info.get("supported"):
            self.note.setText("Блок керування не підтримує режим 09 — так буває в авто, вироблених до "
                              "~2005 р. для європейського ринку. Марку можна вибрати вручну на сторінці "
                              "«Підключення».")
            self.note.show()
        elif not info:
            self.note.setText("Натисніть «Зчитати», щоб отримати VIN і дані блока керування.")
            self.note.show()
        else:
            self.note.hide()
        brand = ctl.brand()
        self.hint_card.setVisible(brand is not None)
        if brand:
            self.hint_card.title_label.setText(f"Порада щодо адаптера — {brand.name}")
            self.brand_hint.setText(brand.adapter_hint)

    def refresh(self):
        self.btn.setEnabled(self.ctl.connected and not self.ctl.is_busy)


# ─────────────────────────── Журнал ───────────────────────────

class LogPage(Page):
    save = Signal()

    def __init__(self):
        super().__init__("Технічний журнал", "Кожен надісланий і отриманий байт. Надішліть цей журнал, "
                                             "якщо щось не працює")
        self.btn_copy = self.header.add_action(button("Копіювати", "copy"))
        self.btn_clear = self.header.add_action(button("Очистити", "trash"))
        self.btn_save = self.header.add_action(button("Зберегти журнал", "file", "primary"))
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setObjectName("mono")
        self.text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.text.setMaximumBlockCount(20000)
        self.text.setMinimumHeight(520)
        self.body.addWidget(self.text, 1)
        self.btn_copy.clicked.connect(lambda: (self.text.selectAll(), self.text.copy(),
                                               self.text.moveCursor(self.text.textCursor().End)))
        self.btn_clear.clicked.connect(self.text.clear)
        self.btn_save.clicked.connect(self.save.emit)

    def append(self, text):
        stamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.text.appendPlainText(f"{stamp}  {text}")

    def refresh(self):
        pass


# ─────────────────────────── Налаштування ───────────────────────────

def _group_of(name):
    if name.startswith(("try_", "retry_")):
        return "Способи підключення"
    if name.startswith(("fast_", "start_comm")):
        return "Швидкий старт"
    if name.startswith("slow_"):
        return "Повільний старт"
    if name.startswith(("response_", "p3_", "iso_", "session_")):
        return "Обмін"
    return "Загальне"


class SettingsPage(Page):
    theme_changed = Signal(str)
    timing_saved = Signal(object)
    app_changed = Signal()

    GROUPS = ["Способи підключення", "Швидкий старт", "Повільний старт", "Обмін", "Загальне"]

    def __init__(self, ctl, paths_text, about_text):
        super().__init__("Налаштування", "Вигляд програми та часові параметри зв’язку")
        self.ctl = ctl

        look = Card("Вигляд")
        row = QHBoxLayout()
        row.addWidget(label("Тема", "muted"))
        row.addStretch(1)
        seg = QFrame()
        seg.setObjectName("segBox")
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(3, 3, 3, 3)
        sl.setSpacing(2)
        self.theme_group = QButtonGroup(self)
        for key, text in (("dark", "Темна"), ("light", "Світла")):
            b = QPushButton(text)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setChecked(ctl.app.theme == key)
            b.clicked.connect(lambda _=False, k=key: self.theme_changed.emit(k))
            self.theme_group.addButton(b)
            sl.addWidget(b)
        row.addWidget(seg)
        look.add(row)
        self.body.addWidget(look)

        elm = Card("ELM327", "Параметри для адаптерів ELM327")
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        self.elm_timeout = SpinBox()
        self.elm_timeout.setRange(1, 30)
        self.elm_timeout.setSuffix(" с")
        self.elm_timeout.setValue(int(ctl.app.elm_timeout))
        self.elm_timeout.setMinimumWidth(120)
        self.elm_baud = ComboBox()
        self.elm_baud.setMinimumWidth(160)
        for b in (38400, 9600, 115200, 57600, 230400, 500000):
            self.elm_baud.addItem(f"{b} бод", b)
        self.elm_baud.setCurrentIndex(max(0, self.elm_baud.findData(ctl.app.elm_baud)))
        form.addRow("Очікування відповіді", self.elm_timeout)
        form.addRow("Початкова швидкість порту", self.elm_baud)
        elm.add(form)
        elm.add(label("Якщо адаптер не відповідає на вибраній швидкості, програма по черзі пробує інші.",
                      "faint", wrap=True))
        self.elm_timeout.valueChanged.connect(self._elm_changed)
        self.elm_baud.currentIndexChanged.connect(self._elm_changed)
        self.body.addWidget(elm)

        kl = Card("Кабель KKL — часові параметри",
                  "Змінюйте, лише якщо машина не відповідає. Нові значення діють з наступного "
                  "підключення. Усі тривалості — у мілісекундах.")
        tabs = QTabWidget()
        pages = {}
        for g in self.GROUPS:
            w = QWidget()
            fl = QFormLayout(w)
            fl.setContentsMargins(4, 14, 4, 4)
            fl.setHorizontalSpacing(16)
            fl.setVerticalSpacing(8)
            fl.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            tabs.addTab(w, g)
            pages[g] = fl
        self.vars = {}
        defaults = Timing()
        for f in Timing.fields():
            fl = pages[_group_of(f.name)]
            kind = f.metadata["kind"]
            if kind == "bool":
                w = QCheckBox(f.metadata["label"])
                fl.addRow(w)
            else:
                w = QLineEdit()
                w.setMaximumWidth(110)
                w.setAlignment(Qt.AlignRight)
                d = getattr(defaults, f.name)
                unit = "мс" if kind == "ms" else f.metadata.get("unit", "")
                shown = f"{d * 1000:g}" if kind == "ms" else str(d)
                rowl = QHBoxLayout()
                rowl.addWidget(w)
                rowl.addWidget(label(f"{unit}   (стандартно {shown})", "faint"))
                rowl.addStretch(1)
                fl.addRow(f.metadata["label"], rowl)
            self.vars[f.name] = (w, kind)
        kl.add(tabs)
        btns = QHBoxLayout()
        b_def = button("Стандартні значення")
        b_def.clicked.connect(lambda: self.load_timing(Timing()))
        b_save = button("Зберегти", None, "primary")
        b_save.clicked.connect(self.save_timing)
        btns.addWidget(b_def)
        btns.addStretch(1)
        btns.addWidget(b_save)
        kl.add(btns)
        self.body.addWidget(kl)

        about = Card("Про програму")
        about.add(label(about_text, "muted", wrap=True))
        about.add(label(paths_text, "faint", wrap=True))
        self.body.addWidget(about)
        self.finish()
        self.load_timing(ctl.timing)

    def _elm_changed(self, *_):
        self.ctl.app.elm_timeout = float(self.elm_timeout.value())
        self.ctl.app.elm_baud = self.elm_baud.currentData()
        self.app_changed.emit()

    def load_timing(self, t):
        for name, (w, kind) in self.vars.items():
            v = getattr(t, name)
            if kind == "bool":
                w.setChecked(bool(v))
            else:
                w.setText(f"{v * 1000:g}" if kind == "ms" else str(v))

    def save_timing(self):
        from PySide6.QtWidgets import QMessageBox
        t = Timing()
        for f in Timing.fields():
            w, kind = self.vars[f.name]
            if kind == "bool":
                setattr(t, f.name, w.isChecked())
                continue
            text = w.text().strip().replace(",", ".")
            try:
                if kind == "ms":
                    v = float(text) / 1000
                    ok = v >= 0
                else:
                    v = int(float(text))
                    ok = v > 0
            except ValueError:
                ok = False
            if not ok:
                QMessageBox.critical(self, "Помилка", f"Некоректне значення: {f.metadata['label']}")
                return
            setattr(t, f.name, v)
        self.timing_saved.emit(t)

    def refresh(self):
        pass
