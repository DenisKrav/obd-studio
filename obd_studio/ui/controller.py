"""Логіка програми без інтерфейсу: з’єднання, черга завдань у фоновому потоці, дані наживо.

Уся робота з портом іде в одному фоновому потоці. Під час «даних наживо» інші
завдання (наприклад, зчитати помилки) виконуються між циклами опитування.
"""

import datetime
import queue
import threading
import time
import traceback

from PySide6.QtCore import QObject, Signal

from ..config import AppSettings, Timing
from ..elm327 import CAN11, CAN29, Elm327, wifi_url
from ..kline import KLine
from ..obd import ObdClient
from ..pids import PIDS, decode_value
from ..protocol import ObdError
from ..vehicles import BRANDS_BY_KEY, decode_vin

try:
    import serial
except ImportError:
    serial = None


MIN_CYCLE = 0.05     # не частіше 20 оновлень інтерфейсу за секунду

ADAPTER_NAMES = {"kkl": "Кабель KKL (K-лінія)", "elm_serial": "ELM327 USB / Bluetooth",
                 "elm_wifi": "ELM327 Wi-Fi"}


class Controller(QObject):
    log = Signal(str)
    busy = Signal(bool, str)
    error = Signal(str)
    connection_changed = Signal()
    dtcs_ready = Signal(object)
    readiness_ready = Signal(object)
    freeze_ready = Signal(object)
    info_ready = Signal(object)
    live_values = Signal(object, float)
    live_state = Signal(bool)
    voltage = Signal(object)
    cleared = Signal()
    scan_done = Signal(object)

    def __init__(self, timing: Timing, app: AppSettings):
        super().__init__()
        self.timing = timing
        self.app = app
        self.transport = None
        self.obd = None
        self.protocol_desc = ""
        self.adapter_desc = ""
        self.vin_info = {}
        self.vin_decoded = None
        self.dtcs = None
        self.readiness = None
        self.freeze = None
        self.live_last = {}
        self.live_pids = []
        self._live = False
        self._jobs = queue.Queue()
        self._busy = False
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ── стан ──
    @property
    def connected(self):
        return self.transport is not None and self.transport.is_connected

    @property
    def is_busy(self):
        return self._busy

    @property
    def is_live(self):
        return self._live

    def brand(self):
        """Профіль марки: вибраний вручну або визначений за VIN."""
        if self.app.brand != "auto":
            return BRANDS_BY_KEY.get(self.app.brand)
        return self.vin_decoded["brand"] if self.vin_decoded else None

    def brand_name(self):
        b = self.brand()
        return b.name if b else None

    def vehicle_title(self):
        b = self.brand()
        year = self.vin_decoded["year"] if self.vin_decoded else None
        if b and year:
            return f"{b.name} · {year}"
        if b:
            return b.name
        return "Авто не визначено"

    def is_can(self):
        return isinstance(self.transport, Elm327) and self.transport.protocol in (CAN11 | CAN29)

    # ── черга завдань ──
    def _log(self, text):
        self.log.emit(text)

    def submit(self, title, fn, busy=True):
        self._jobs.put((title, fn, busy))

    def _worker(self):
        while True:
            try:
                job = self._jobs.get(timeout=0.5)
            except queue.Empty:
                self._keepalive()
                continue
            if job is None:
                return
            self._run(job)

    def _keepalive(self):
        t = self.transport
        if t is None or self._live or not t.is_connected:
            return
        try:
            t.keepalive()
        except Exception as e:      # noqa: BLE001 — збій підтримки сесії не має заважати роботі
            self._log(f"Підтримка сесії не вдалася: {e}")
        if not t.is_connected:
            self.connection_changed.emit()

    def _run(self, job):
        title, fn, busy = job
        if busy:
            self._busy = True
            self.busy.emit(True, title)
        try:
            fn()
        except ObdError as e:
            self._log(f"ПОМИЛКА: {e}")
            self.error.emit(str(e))
        except Exception as e:      # noqa: BLE001 — показуємо будь-яку несподівану помилку
            self._log(traceback.format_exc())
            self.error.emit(f"Неочікувана помилка: {e}\n\nЗбережіть журнал і надішліть його.")
        finally:
            if self.transport:
                self.transport.quiet = self._live
            if busy:
                self._busy = False
                self.busy.emit(False, "")
            self.connection_changed.emit()

    def _drain(self):
        """Виконує завдання, що накопичилися, поки йдуть дані наживо."""
        while True:
            try:
                job = self._jobs.get_nowait()
            except queue.Empty:
                return
            if job is None:
                self._jobs.put(None)
                self._live = False
                return
            if self.transport:
                self.transport.quiet = False
            self._run(job)

    def shutdown(self):
        self._live = False
        self._jobs.put(None)
        self._thread.join(timeout=3)
        if self.transport:
            self.transport.close()

    # ── з’єднання ──
    def connect(self):
        self.stop_live()
        app, timing = self.app, self.timing

        def job():
            if self.transport:
                self.transport.close()
            self.vin_info, self.vin_decoded = {}, None
            self.dtcs = self.readiness = self.freeze = None
            self.live_last = {}
            if app.adapter == "kkl":
                if not app.port:
                    raise ObdError("Виберіть COM-порт кабелю KKL.")
                self.transport = KLine(app.port, self._log, timing)
                where = app.port
            else:
                if app.adapter == "elm_wifi":
                    url, where = wifi_url(app.wifi_host, app.wifi_port), f"{app.wifi_host}:{app.wifi_port}"
                else:
                    if not app.port:
                        raise ObdError("Виберіть COM-порт адаптера ELM327.")
                    url = where = app.port
                self.transport = Elm327(url, self._log, app.elm_baud, app.elm_protocol, app.elm_timeout)
            self.obd = ObdClient(self.transport)
            self.adapter_desc = f"{ADAPTER_NAMES[app.adapter]}, {where}"
            self._log(f"Підключення: {self.adapter_desc}")
            try:
                self.protocol_desc = self.transport.connect()
            except Exception:
                self.transport.close()
                raise
            self._log(f"З’єднання встановлено: {self.protocol_desc}")
            self.connection_changed.emit()
            sup = self.obd.supported_pids()
            self._log(f"Блок підтримує {len(sup)} параметрів режиму 01")
            self._read_readiness()
            if isinstance(self.transport, Elm327):
                self.voltage.emit(self.transport.read_voltage())
                self._read_info()

        self.submit("Підключення…", job)

    def disconnect(self):
        self.stop_live()

        def job():
            if self.transport:
                self.transport.close()
                self._log("Відключено")
            self.protocol_desc = ""

        self.submit("Відключення…", job)

    def _require(self):
        if not self.connected:
            raise ObdError("Немає з’єднання з авто. Спершу підключіться на сторінці «Підключення».")

    # ── діагностика ──
    def _read_readiness(self):
        self.readiness = self.obd.readiness()
        self.readiness_ready.emit(self.readiness)
        return self.readiness

    def _read_dtcs(self):
        stored, ok = self.obd.read_dtcs(0x03)
        inferred = False
        if not ok:
            rd = self.readiness or self._read_readiness()
            if not rd or rd["dtc_count"]:
                raise ObdError("Блок не відповів на запит помилок. Спробуйте ще раз.")
            # деякі блоки ISO 9141 мовчать на запит 03, коли кодів немає
            self._log("Блок не відповів на запит 03, але за PID 01 підтверджених помилок 0 — "
                      "вважаю, що збережених кодів немає")
            stored, inferred = [], True
        pending, ok7 = self.obd.read_dtcs(0x07)
        result = {"stored": stored, "pending": pending if ok7 else [], "permanent": [],
                  "pending_supported": ok7, "stored_inferred": inferred}
        if self.is_can():
            permanent, _ = self.obd.read_dtcs(0x0A)
            result["permanent"] = permanent
        self.dtcs = result
        self.dtcs_ready.emit(result)
        return result

    def _read_info(self):
        info = self.obd.vehicle_info()
        self.vin_info = info
        self.vin_decoded = decode_vin(info["vin"], datetime.date.today().year) if info["vin"] else None
        self.info_ready.emit(info)
        return info

    def read_dtcs(self):
        def job():
            self._require()
            self._read_dtcs()
        self.submit("Зчитування кодів помилок…", job)

    def read_readiness(self):
        def job():
            self._require()
            if self._read_readiness() is None:
                raise ObdError("Блок не відповів на запит стану систем.")
        self.submit("Зчитування готовності систем…", job)

    def read_freeze(self):
        def job():
            self._require()
            fr = self.obd.freeze_frame()
            self.freeze = None if fr is None else (fr[0], {pid: decode_value(pid, raw)
                                                           for pid, raw in fr[1].items()})
            self.freeze_ready.emit(self.freeze)
        self.submit("Зчитування стоп-кадру…", job)

    def read_info(self):
        def job():
            self._require()
            self._read_info()
            if isinstance(self.transport, Elm327):
                self.voltage.emit(self.transport.read_voltage())
        self.submit("Зчитування даних авто…", job)

    def clear_dtcs(self):
        def job():
            self._require()
            if not self.obd.clear_dtcs():
                raise ObdError("Блок не підтвердив стирання. Переконайтеся, що двигун заглушено.")
            self._log("Коди помилок стерто")
            self.dtcs = {"stored": [], "pending": [], "permanent": [], "pending_supported": True}
            self.freeze = None
            self.cleared.emit()
            self.dtcs_ready.emit(self.dtcs)
            self._read_readiness()
        self.submit("Стирання кодів помилок…", job)

    def quick_scan(self):
        """Готовність + усі коди + стоп-кадр (якщо є збережені коди) за один раз."""
        def job():
            self._require()
            self._read_readiness()
            dtcs = self._read_dtcs()
            if dtcs["stored"]:
                fr = self.obd.freeze_frame()
                self.freeze = None if fr is None else (fr[0], {pid: decode_value(pid, raw)
                                                               for pid, raw in fr[1].items()})
                self.freeze_ready.emit(self.freeze)
            if isinstance(self.transport, Elm327):
                self.voltage.emit(self.transport.read_voltage())
            self.scan_done.emit({
                "vehicle": self.vehicle_title(), "vin": self.vin_info.get("vin", ""),
                "protocol": self.protocol_desc, "stored": dtcs["stored"], "pending": dtcs["pending"],
                "permanent": dtcs["permanent"],
                "mil": bool(self.readiness and self.readiness["mil"]),
            })
        self.submit("Повне сканування…", job)

    # ── дані наживо ──
    def set_live_pids(self, pids):
        self.live_pids = [p for p in pids if p in PIDS]

    def start_live(self):
        if self._live:
            return
        self._live = True
        self.live_state.emit(True)

        def job():
            try:
                self._require()
                first = True
                last_volt = 0.0
                while self._live:
                    t0 = time.perf_counter()
                    values = {}
                    for pid in list(self.live_pids):
                        if not self._live:
                            break
                        values[pid] = decode_value(pid, self.obd.read_pid(pid))
                        self._drain()
                        if not self.connected:
                            raise ObdError("Зв’язок із машиною втрачено.")
                    if not self.live_pids:
                        time.sleep(0.2)
                        self._drain()
                        continue
                    self.live_last.update({k: v for k, v in values.items() if v is not None})
                    dt = time.perf_counter() - t0
                    if dt < MIN_CYCLE:            # дуже швидкий адаптер: не завантажуємо інтерфейс
                        time.sleep(MIN_CYCLE - dt)
                    dt = time.perf_counter() - t0
                    self.live_values.emit(values, 1 / dt if dt > 0 else 0.0)
                    if isinstance(self.transport, Elm327) and time.perf_counter() - last_volt > 5:
                        self.voltage.emit(self.transport.read_voltage())
                        last_volt = time.perf_counter()
                    if first:
                        self.transport.quiet = True
                        self._log("(дані наживо: подальший обмін у журнал не пишеться)")
                        first = False
            finally:
                self._live = False
                self.live_state.emit(False)

        self.submit("Дані наживо", job, busy=False)

    def stop_live(self):
        self._live = False
