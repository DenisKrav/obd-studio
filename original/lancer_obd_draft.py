#!/usr/bin/env python3
"""
Lancer OBD — проста діагностика OBD-II через кабель KKL (VAG KKL 409.1 з чипом FTDI).

Що вміє:
  • підключитися до блока керування двигуном через K-лінію
    (KWP2000 зі швидким стартом, KWP2000 / ISO 9141-2 з повільним стартом);
  • зчитати й розшифрувати коди помилок (збережені й ті, що очікують підтвердження);
  • показати стан лампи Check Engine і готовність систем самодіагностики;
  • показати основні параметри двигуна наживо;
  • стерти коди помилок (лише за вашим підтвердженням).

Програма надсилає тільки стандартні запити OBD-II і нічого не записує
в блок керування, крім стирання помилок за вашою командою.

Потрібно: Python 3.8+ і бібліотека pyserial  (pip install pyserial)
"""

import datetime
import queue
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None


# ─────────────────────────── Допоміжні функції ───────────────────────────

def wait_until(t):
    """Точне очікування до моменту t (time.perf_counter)."""
    while True:
        rem = t - time.perf_counter()
        if rem <= 0:
            return
        if rem > 0.02:
            time.sleep(rem - 0.017)


def busy_wait(seconds):
    wait_until(time.perf_counter() + seconds)


def checksum(data):
    return sum(data) & 0xFF


def hexs(data):
    return " ".join(f"{b:02X}" for b in data)


def parse_kwp(buf):
    """Розбирає потік байтів на повідомлення KWP2000. Повертає список корисних даних."""
    out = []
    i, n = 0, len(buf)
    while i < n:
        fmt = buf[i]
        length = fmt & 0x3F
        hdr = 1
        if fmt & 0xC0:          # у заголовку є адреси одержувача й відправника
            hdr += 2
        if length == 0:         # довжина записана окремим байтом
            if i + hdr >= n:
                break
            length = buf[i + hdr]
            hdr += 1
        end = i + hdr + length  # індекс байта контрольної суми
        if length == 0 or end >= n:
            i += 1
            continue
        frame = buf[i:end + 1]
        if checksum(frame[:-1]) == frame[-1]:
            out.append(bytes(buf[i + hdr:end]))
            i = end + 1
        else:
            i += 1
    return out


def parse_iso9141(buf):
    """Розбирає відповіді ISO 9141-2 (заголовок 48 6B xx)."""
    out = []
    starts = [i for i in range(len(buf) - 1) if buf[i] == 0x48 and buf[i + 1] == 0x6B]
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(buf)
        frame = buf[s:e]
        if len(frame) >= 5 and checksum(frame[:-1]) == frame[-1]:
            out.append(bytes(frame[3:-1]))
    return out


def decode_dtc(a, b):
    letter = "PCBU"[a >> 6]
    return f"{letter}{(a >> 4) & 3}{a & 0xF:X}{b >> 4:X}{b & 0xF:X}"


# ─────────────────────────── Опис кодів помилок ───────────────────────────

DTC_TEXT = {
    "P0100": "Несправність ланцюга датчика масової витрати повітря (ДМРВ)",
    "P0101": "ДМРВ: сигнал поза допустимим діапазоном",
    "P0102": "ДМРВ: низький рівень сигналу",
    "P0103": "ДМРВ: високий рівень сигналу",
    "P0105": "Несправність ланцюга датчика тиску у впускному колекторі (MAP)",
    "P0106": "Датчик MAP: сигнал поза допустимим діапазоном",
    "P0107": "Датчик MAP: низький рівень сигналу",
    "P0108": "Датчик MAP: високий рівень сигналу",
    "P0110": "Несправність ланцюга датчика температури повітря на впуску",
    "P0112": "Датчик температури повітря на впуску: низький рівень сигналу",
    "P0113": "Датчик температури повітря на впуску: високий рівень сигналу",
    "P0115": "Несправність ланцюга датчика температури охолоджувальної рідини",
    "P0117": "Датчик температури охолоджувальної рідини: низький рівень сигналу",
    "P0118": "Датчик температури охолоджувальної рідини: високий рівень сигналу",
    "P0120": "Несправність ланцюга датчика положення дросельної заслінки",
    "P0121": "Датчик положення дроселя: сигнал поза допустимим діапазоном",
    "P0122": "Датчик положення дроселя: низький рівень сигналу",
    "P0123": "Датчик положення дроселя: високий рівень сигналу",
    "P0125": "Двигун надто довго прогрівається до робочої температури",
    "P0128": "Температура охолоджувальної рідини нижча за норму (часто — несправний термостат)",
    "P0130": "Несправність ланцюга кисневого датчика 1 (до каталізатора)",
    "P0131": "Кисневий датчик 1: низька напруга",
    "P0132": "Кисневий датчик 1: висока напруга",
    "P0133": "Кисневий датчик 1: повільна реакція",
    "P0134": "Кисневий датчик 1: немає активності",
    "P0135": "Несправність нагрівача кисневого датчика 1",
    "P0136": "Несправність ланцюга кисневого датчика 2 (після каталізатора)",
    "P0137": "Кисневий датчик 2: низька напруга",
    "P0138": "Кисневий датчик 2: висока напруга",
    "P0139": "Кисневий датчик 2: повільна реакція",
    "P0140": "Кисневий датчик 2: немає активності",
    "P0141": "Несправність нагрівача кисневого датчика 2",
    "P0170": "Несправність корекції подачі палива",
    "P0171": "Надто бідна паливна суміш",
    "P0172": "Надто багата паливна суміш",
    "P0300": "Випадкові або множинні пропуски запалювання",
    "P0325": "Несправність ланцюга датчика детонації",
    "P0335": "Несправність ланцюга датчика положення колінчастого валу",
    "P0340": "Несправність ланцюга датчика положення розподільного валу",
    "P0400": "Несправність системи рециркуляції відпрацьованих газів (EGR)",
    "P0401": "EGR: недостатній потік",
    "P0403": "EGR: несправність ланцюга керування",
    "P0420": "Ефективність каталізатора нижча за поріг",
    "P0421": "Ефективність каталізатора під час прогріву нижча за поріг",
    "P0440": "Несправність системи вловлювання парів палива (EVAP)",
    "P0441": "EVAP: некоректний потік продувки",
    "P0442": "EVAP: виявлено невеликий витік",
    "P0443": "EVAP: несправність ланцюга клапана продувки адсорбера",
    "P0446": "EVAP: несправність ланцюга керування вентиляцією",
    "P0450": "Несправність датчика тиску системи EVAP",
    "P0455": "EVAP: виявлено великий витік (часто — нещільно закрита кришка бака)",
    "P0456": "EVAP: виявлено дуже малий витік",
    "P0500": "Несправність датчика швидкості автомобіля",
    "P0505": "Несправність системи керування холостим ходом",
    "P0506": "Оберти холостого ходу нижчі за норму",
    "P0507": "Оберти холостого ходу вищі за норму",
    "P0510": "Несправність вимикача закритого положення дроселя",
    "P0560": "Несправність напруги бортової мережі",
    "P0562": "Низька напруга бортової мережі",
    "P0563": "Висока напруга бортової мережі",
    "P0600": "Несправність лінії зв’язку блока керування",
    "P0601": "Блок керування: помилка контрольної суми пам’яті",
    "P0603": "Блок керування: помилка енергонезалежної пам’яті",
    "P0605": "Блок керування: помилка постійної пам’яті",
    "P0700": "У блоці автоматичної коробки передач є помилка",
    "P0705": "Несправність датчика положення селектора АКПП",
    "P0715": "Несправність датчика швидкості вхідного валу АКПП",
    "P0720": "Несправність датчика швидкості вихідного валу АКПП",
    "P0740": "Несправність муфти блокування гідротрансформатора",
    "P0750": "Несправність соленоїда перемикання A (АКПП)",
    "P0755": "Несправність соленоїда перемикання B (АКПП)",
}
for _n in range(1, 5):
    DTC_TEXT[f"P020{_n}"] = f"Несправність ланцюга форсунки, циліндр {_n}"
    DTC_TEXT[f"P030{_n}"] = f"Пропуски запалювання в циліндрі {_n}"

P_GROUPS = {
    "0": "подача палива й повітря, допоміжні системи викидів",
    "1": "подача палива й повітря",
    "2": "подача палива й повітря (ланцюги форсунок)",
    "3": "система запалювання або пропуски запалювання",
    "4": "допоміжні системи контролю викидів",
    "5": "швидкість, холостий хід, допоміжні входи",
    "6": "блок керування та його виходи",
    "7": "коробка передач",
    "8": "коробка передач",
    "9": "коробка передач",
}


def describe_dtc(code):
    if code in DTC_TEXT:
        return DTC_TEXT[code]
    kind = code[0]
    if kind == "P":
        if code[1] in "13":
            return "код виробника (Mitsubishi) — точний опис шукайте за кодом для Lancer IX"
        group = P_GROUPS.get(code[2], "")
        return f"загальний код OBD-II, група: {group}. Точний опис шукайте за кодом"
    return {
        "C": "шасі (ABS, підвіска тощо) — шукайте опис за кодом",
        "B": "кузов (подушки безпеки, комфорт) — шукайте опис за кодом",
        "U": "зв’язок між блоками — шукайте опис за кодом",
    }.get(kind, "невідомий тип коду")


# ─────────────────────────── Параметри наживо ───────────────────────────

LIVE_PIDS = [
    (0x0C, "Оберти двигуна", "об/хв", lambda d: (d[0] * 256 + d[1]) / 4, 0),
    (0x05, "Температура охолоджувальної рідини", "°C", lambda d: d[0] - 40, 0),
    (0x0D, "Швидкість", "км/год", lambda d: d[0], 0),
    (0x04, "Навантаження двигуна", "%", lambda d: d[0] * 100 / 255, 1),
    (0x11, "Положення дроселя", "%", lambda d: d[0] * 100 / 255, 1),
    (0x0F, "Температура повітря на впуску", "°C", lambda d: d[0] - 40, 0),
    (0x0E, "Кут випередження запалювання", "°", lambda d: d[0] / 2 - 64, 1),
    (0x06, "Коротка корекція палива", "%", lambda d: (d[0] - 128) * 100 / 128, 1),
    (0x07, "Довга корекція палива", "%", lambda d: (d[0] - 128) * 100 / 128, 1),
    (0x0B, "Тиск у впускному колекторі", "кПа", lambda d: d[0], 0),
    (0x10, "Витрата повітря", "г/с", lambda d: (d[0] * 256 + d[1]) / 100, 2),
    (0x14, "Кисневий датчик 1 (до каталізатора)", "В", lambda d: d[0] / 200, 3),
    (0x15, "Кисневий датчик 2 (після каталізатора)", "В", lambda d: d[0] / 200, 3),
]


def decode_readiness(d):
    a, b, c, dd = d[:4]
    lines = [
        f"Лампа Check Engine: {'УВІМКНЕНА' if a & 0x80 else 'вимкнена'}",
        f"Кількість підтверджених помилок: {a & 0x7F}",
        "",
        "Готовність систем самодіагностики:",
    ]
    for sup_bit, inc_bit, name in ((0, 4, "Пропуски запалювання"),
                                   (1, 5, "Паливна система"),
                                   (2, 6, "Компоненти")):
        if b & (1 << sup_bit):
            lines.append(f"  {name}: {'НЕ готово' if b & (1 << inc_bit) else 'готово'}")
    names = ["Каталізатор", "Підігрів каталізатора", "Система EVAP", "Вторинне повітря",
             "Кондиціонер (холодоагент)", "Кисневі датчики", "Підігрів кисневих датчиків", "EGR"]
    for i, name in enumerate(names):
        if c & (1 << i):
            lines.append(f"  {name}: {'НЕ готово' if dd & (1 << i) else 'готово'}")
    lines += ["",
              "«НЕ готово» буває після стирання помилок або відключення акумулятора: "
              "система ще не завершила самоперевірку. Після кількох днів звичайної їзди "
              "статус зазвичай змінюється на «готово»."]
    return "\n".join(lines)


# ─────────────────────────── Робота з K-лінією ───────────────────────────

class ObdError(Exception):
    pass


class KLine:
    BAUD = 10400

    def __init__(self, port, log):
        self.port = port
        self._log = log
        self.ser = None
        self.protocol = None      # "KWP" або "ISO9141"
        self.method = None
        self.method_name = ""
        self.last_comm = 0.0
        self.supported = set()
        self.quiet = False

    def log(self, text, raw=False):
        if raw and self.quiet:
            return
        self._log(text)

    # ── порт ──
    def open(self):
        if self.ser is None:
            try:
                self.ser = serial.Serial(self.port, self.BAUD, timeout=0.01, write_timeout=1)
            except serial.SerialException as e:
                raise ObdError(f"Не вдалося відкрити {self.port}: {e}\n"
                               "Можливо, порт зайнятий іншою програмою (наприклад, VCDS-Lite).")
            self.ser.break_condition = False
            self.log(f"Порт {self.port} відкрито, {self.BAUD} бод")

    def close(self):
        if self.ser:
            try:
                self.ser.break_condition = False
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.protocol = None

    # ── читання/запис ──
    def _read_exact(self, n, timeout=0.3):
        buf = bytearray()
        end = time.perf_counter() + timeout
        while len(buf) < n and time.perf_counter() < end:
            buf += self.ser.read(n - len(buf))
        return bytes(buf)

    def _read_until_silence(self, first_timeout=0.35, gap=0.08, max_total=2.0):
        buf = bytearray()
        start = time.perf_counter()
        last = None
        while True:
            chunk = self.ser.read(256)
            now = time.perf_counter()
            if chunk:
                buf += chunk
                last = now
            elif last is None:
                if now - start > first_timeout:
                    break
            elif now - last > gap:
                break
            if now - start > max_total:
                break
        return bytes(buf)

    def _send_raw(self, data, interbyte=0.0):
        """Надсилає байти й відкидає «луну» (кабель KKL повертає все надіслане)."""
        data = bytes(data)
        odd = bytearray()
        if interbyte > 0:
            for b in data:
                self.ser.write(bytes([b]))
                echo = self._read_exact(1)
                if echo != bytes([b]):
                    odd += echo
                busy_wait(interbyte)
        else:
            self.ser.write(data)
            echo = self._read_exact(len(data))
            if echo != data:
                odd += echo
        self.log(f"→ {hexs(data)}", raw=True)
        if odd:
            self.log(f"   (луна не збіглася: {hexs(odd) or 'немає'})", raw=True)

    # ── способи ініціалізації ──
    def _idle(self, seconds):
        self.ser.break_condition = False
        time.sleep(seconds)
        self.ser.reset_input_buffer()

    def _start_comm(self):
        req = bytes([0xC1, 0x33, 0xF1, 0x81])
        req += bytes([checksum(req)])
        self._send_raw(req)
        resp = self._read_until_silence(first_timeout=0.3)
        self.log(f"← {hexs(resp) if resp else '(тиша)'}")
        for p in parse_kwp(resp):
            if p and p[0] == 0xC1:
                self.log(f"Блок відповів! Ключові байти: {hexs(p[1:3])}")
                return True
        return False

    def _fast_init_break(self):
        self._idle(0.4)
        self.ser.break_condition = True       # лінія в 0 на 25 мс
        busy_wait(0.025)
        self.ser.break_condition = False      # лінія в 1 на 25 мс
        t = time.perf_counter() + 0.025
        self.ser.reset_input_buffer()
        wait_until(t)
        return self._start_comm()

    def _fast_init_360(self):
        self._idle(0.4)
        self.ser.baudrate = 360               # байт 0x00 на 360 бод = 25 мс нуля
        t0 = time.perf_counter()
        self.ser.write(b"\x00")
        self._read_exact(1, timeout=0.2)
        self.ser.baudrate = self.BAUD
        self.ser.reset_input_buffer()
        wait_until(t0 + 0.050)
        return self._start_comm()

    def _slow_init(self):
        self._idle(2.6)
        bits = [0] + [(0x33 >> i) & 1 for i in range(8)]   # старт-біт + адреса 0x33
        t = time.perf_counter()
        for bit in bits:
            self.ser.break_condition = (bit == 0)
            t += 0.2                                        # 5 бод = 200 мс на біт
            wait_until(t)
        self.ser.break_condition = False                    # стоп-біт
        self.ser.reset_input_buffer()
        sync = None
        end = time.perf_counter() + 0.8
        while time.perf_counter() < end:
            b = self.ser.read(1)
            if b == b"\x55":
                sync = b
                break
            if b:
                self.log(f"   (сторонній байт {hexs(b)})")
        if not sync:
            self.log("← немає байта синхронізації 0x55")
            return False
        kb = self._read_exact(2, timeout=0.1)
        if len(kb) < 2:
            self.log(f"← 55 {hexs(kb)} (ключові байти неповні)")
            return False
        self.log(f"← 55 {hexs(kb)}  (синхронізація OK, ключові байти {hexs(kb)})")
        busy_wait(0.03)
        self._send_raw([(~kb[1]) & 0xFF])
        ack = self._read_exact(1, timeout=0.2)
        self.log(f"← {hexs(ack) if ack else '(тиша)'}")
        if ack != b"\xCC":
            return False
        if kb[0] == kb[1] and kb[0] in (0x08, 0x94):
            self.protocol = "ISO9141"
        else:
            self.protocol = "KWP"
        return True

    # ── сесія ──
    def connect(self):
        self.open()
        attempts = [
            ("KWP2000, швидкий старт", self._fast_init_break, "KWP"),
            ("KWP2000, швидкий старт (спосіб 2)", self._fast_init_360, "KWP"),
            ("повільний старт 5 бод", self._slow_init, None),
        ]
        for i, (name, func, proto) in enumerate(attempts):
            if i:
                self.log("Пауза 3 с перед наступною спробою…")
                time.sleep(3)
            self.log(f"── Спроба {i + 1}/3: {name}")
            try:
                ok = func()
            except serial.SerialException as e:
                raise ObdError(f"Помилка порту: {e}")
            finally:
                if self.ser:
                    self.ser.break_condition = False
                    if self.ser.baudrate != self.BAUD:
                        self.ser.baudrate = self.BAUD
            if ok:
                if proto:
                    self.protocol = proto
                self.method, self.method_name = func, name
                self.last_comm = time.perf_counter()
                proto_name = "ISO 9141-2" if self.protocol == "ISO9141" else "ISO 14230-4 (KWP2000)"
                return f"{proto_name}, {name}"
        raise ObdError("Машина не відповіла жодним способом.\n\n"
                       "Перевірте, що запалювання увімкнене, кабель щільно сидить у роз’ємі, "
                       "і спробуйте ще раз. Якщо не вийде — збережіть журнал і надішліть його.")

    def ensure_session(self):
        if self.protocol is None:
            raise ObdError("Спершу натисніть «Підключитися».")
        if time.perf_counter() - self.last_comm > 4.0:
            self.log("Сесія могла завершитися — перепідключаюся…")
            ok = self.method()
            if not ok:
                time.sleep(3)
                ok = self.method()
            if not ok:
                self.protocol = None
                raise ObdError("Зв’язок із машиною втрачено. Натисніть «Підключитися» ще раз.")
            self.last_comm = time.perf_counter()
        wait_until(self.last_comm + 0.06)

    def request(self, data, expect_sid):
        self.ensure_session()
        self.ser.reset_input_buffer()
        data = bytes(data)
        if self.protocol == "ISO9141":
            msg = bytes([0x68, 0x6A, 0xF1]) + data
            interbyte = 0.006
        else:
            msg = bytes([0xC0 | len(data), 0x33, 0xF1]) + data
            interbyte = 0.0
        msg += bytes([checksum(msg)])
        self._send_raw(msg, interbyte)
        resp = self._read_until_silence()
        self.last_comm = time.perf_counter() if resp else 0.0
        self.log(f"← {hexs(resp) if resp else '(тиша)'}", raw=True)
        if self.protocol == "ISO9141":
            payloads = parse_iso9141(resp) or parse_kwp(resp)
        else:
            payloads = parse_kwp(resp) or parse_iso9141(resp)
        result = []
        for p in payloads:
            if p and p[0] == expect_sid:
                result.append(p)
            elif len(p) >= 3 and p[0] == 0x7F:
                self.log(f"   Блок відмовив: сервіс {p[1]:02X}, причина {p[2]:02X}")
        return result

    # ── функції OBD-II ──
    def read_pid(self, pid):
        for p in self.request([0x01, pid], 0x41):
            if len(p) >= 3 and p[1] == pid:
                return p[2:]
        return None

    def supported_pids(self):
        d = self.read_pid(0x00)
        sup = set()
        if d and len(d) >= 4:
            for i in range(32):
                if d[i // 8] & (0x80 >> (i % 8)):
                    sup.add(i + 1)
        self.supported = sup
        return sup

    def read_dtcs(self, mode):
        payloads = self.request([mode], 0x40 + mode)
        codes = []
        for p in payloads:
            data = p[1:]
            if len(data) % 2:          # деякі блоки додають байт кількості
                data = data[1:]
            for j in range(0, len(data) - 1, 2):
                a, b = data[j], data[j + 1]
                if a == 0 and b == 0:
                    continue
                code = decode_dtc(a, b)
                if code not in codes:
                    codes.append(code)
        return codes, bool(payloads)

    def clear_dtcs(self):
        return bool(self.request([0x04], 0x44))


# ─────────────────────────── Інтерфейс ───────────────────────────

class App:
    def __init__(self, root):
        self.root = root
        root.title("Lancer OBD — діагностика через KKL")
        root.geometry("920x700")
        root.minsize(700, 500)
        self.q = queue.Queue()
        self.kline = None
        self.busy = False
        self.live = False

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Порт:").pack(side="left")
        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(top, textvariable=self.port_var, width=10, state="readonly")
        self.port_box.pack(side="left", padx=4)
        ttk.Button(top, text="⟳", width=3, command=self.refresh_ports).pack(side="left")
        self.btn_connect = ttk.Button(top, text="Підключитися", command=self.on_connect)
        self.btn_connect.pack(side="left", padx=8)
        self.status_var = tk.StringVar(value="Не підключено")
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=8)

        bar = ttk.Frame(root, padding=(8, 0, 8, 8))
        bar.pack(fill="x")
        self.btn_dtc = ttk.Button(bar, text="Зчитати помилки", command=self.on_read_dtc)
        self.btn_ready = ttk.Button(bar, text="Check Engine і готовність", command=self.on_readiness)
        self.btn_live = ttk.Button(bar, text="▶ Дані наживо", command=self.on_live)
        self.btn_clear = ttk.Button(bar, text="Стерти помилки", command=self.on_clear)
        for b in (self.btn_dtc, self.btn_ready, self.btn_live, self.btn_clear):
            b.pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Зберегти журнал", command=self.on_save_log).pack(side="right")

        paned = ttk.PanedWindow(root, orient="vertical")
        paned.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        res_frame = ttk.LabelFrame(paned, text="Результат", padding=4)
        self.result = tk.Text(res_frame, wrap="word", font=("Segoe UI", 11), height=14)
        rs = ttk.Scrollbar(res_frame, command=self.result.yview)
        self.result.configure(yscrollcommand=rs.set)
        rs.pack(side="right", fill="y")
        self.result.pack(fill="both", expand=True)

        log_frame = ttk.LabelFrame(paned, text="Технічний журнал (надішліть його, якщо щось не працює)",
                                   padding=4)
        self.logbox = tk.Text(log_frame, wrap="none", font=("Consolas", 9), height=10)
        ls = ttk.Scrollbar(log_frame, command=self.logbox.yview)
        self.logbox.configure(yscrollcommand=ls.set)
        ls.pack(side="right", fill="y")
        self.logbox.pack(fill="both", expand=True)

        paned.add(res_frame, weight=3)
        paned.add(log_frame, weight=2)

        self.show_result("1. Підключіть кабель до машини й ноутбука.\n"
                         "2. Увімкніть запалювання (двигун можна не заводити).\n"
                         "3. Закрийте VCDS-Lite, якщо вона відкрита.\n"
                         "4. Виберіть порт і натисніть «Підключитися».")
        self.refresh_ports()
        self.set_buttons()
        root.after(100, self.poll_queue)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ── службове ──
    def refresh_ports(self):
        ports = list(serial.tools.list_ports.comports())
        names = [p.device for p in ports]
        self.port_box["values"] = names
        preferred = next((p.device for p in ports
                          if "FTDI" in (p.manufacturer or "") or "USB Serial" in (p.description or "")),
                         None)
        if self.port_var.get() not in names:
            self.port_var.set(preferred or ("COM3" if "COM3" in names else (names[0] if names else "")))

    def connected(self):
        return self.kline is not None and self.kline.protocol is not None

    def set_buttons(self):
        idle = not self.busy
        conn = self.connected()
        self.btn_connect.state(["!disabled"] if idle else ["disabled"])
        for b in (self.btn_dtc, self.btn_ready, self.btn_clear):
            b.state(["!disabled"] if idle and conn else ["disabled"])
        self.btn_live.state(["!disabled"] if conn and (idle or self.live) else ["disabled"])
        self.btn_live.configure(text="■ Зупинити" if self.live else "▶ Дані наживо")

    def log_from_thread(self, text):
        self.q.put(("log", text))

    def append_log(self, text):
        stamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.logbox.insert("end", f"{stamp}  {text}\n")
        self.logbox.see("end")

    def show_result(self, text):
        self.result.delete("1.0", "end")
        self.result.insert("1.0", text)

    def poll_queue(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log":
                    self.append_log(val)
                elif kind == "result":
                    self.show_result(val)
                elif kind == "status":
                    self.status_var.set(val)
                elif kind == "done":
                    self.busy = False
                    self.live = False
                    if not self.connected():
                        self.status_var.set("Не підключено")
                    self.set_buttons()
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    def run_task(self, func):
        if self.busy:
            return
        self.busy = True
        self.set_buttons()

        def worker():
            try:
                func()
            except ObdError as e:
                self.q.put(("result", f"⚠ {e}"))
                self.q.put(("log", f"ПОМИЛКА: {e}"))
            except Exception as e:
                self.q.put(("result", f"⚠ Неочікувана помилка: {e}\n\nЗбережіть журнал і надішліть його."))
                self.q.put(("log", traceback.format_exc()))
            finally:
                if self.kline:
                    self.kline.quiet = False
                self.q.put(("done", None))

        threading.Thread(target=worker, daemon=True).start()

    # ── кнопки ──
    def on_connect(self):
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("Порт", "Не знайдено жодного COM-порту. Підключіть кабель і натисніть ⟳.")
            return

        def task():
            if self.kline:
                self.kline.close()
            self.kline = KLine(port, self.log_from_thread)
            self.q.put(("status", "Підключення…"))
            self.q.put(("result", "Підключаюся до машини. Це може тривати до 20 секунд…"))
            try:
                desc = self.kline.connect()
            except ObdError:
                self.kline.close()
                raise
            self.q.put(("status", f"Підключено: {desc}"))
            sup = self.kline.supported_pids()
            extra = (f"Блок підтримує {len(sup)} стандартних параметрів."
                     if sup else "Блок не повідомив список параметрів, але з’єднання є.")
            self.q.put(("result", f"✅ З’єднання встановлено!\n\nПротокол: {desc}\n{extra}\n\n"
                                  "Тепер можна зчитати помилки або переглянути дані наживо."))

        self.run_task(task)

    def on_read_dtc(self):
        def task():
            stored, ok = self.kline.read_dtcs(0x03)
            if not ok:
                raise ObdError("Блок не відповів на запит помилок. Спробуйте ще раз.")
            lines = []
            if stored:
                lines.append(f"Збережені помилки ({len(stored)}):")
                lines += [f"  {c} — {describe_dtc(c)}" for c in stored]
            else:
                lines.append("✅ Збережених помилок немає.")
            lines.append("")
            pending, ok2 = self.kline.read_dtcs(0x07)
            if not ok2:
                lines.append("(Блок не підтримує запит помилок, що очікують підтвердження.)")
            elif pending:
                lines.append(f"Помилки, що очікують підтвердження ({len(pending)}):")
                lines += [f"  {c} — {describe_dtc(c)}" for c in pending]
            else:
                lines.append("Помилок, що очікують підтвердження, немає.")
            self.q.put(("result", "\n".join(lines)))

        self.run_task(task)

    def on_readiness(self):
        def task():
            d = self.kline.read_pid(0x01)
            if not d or len(d) < 4:
                raise ObdError("Блок не відповів на запит стану систем.")
            self.q.put(("result", decode_readiness(d)))

        self.run_task(task)

    def on_clear(self):
        if not messagebox.askyesno(
                "Стерти помилки?",
                "Перед стиранням заглушіть двигун, запалювання залиште увімкненим.\n\n"
                "Зважте: стирання не усуває несправність. Якщо вона є, помилка повернеться. "
                "Також скинуться статуси готовності систем самодіагностики.\n\n"
                "Стерти коди помилок?"):
            return

        def task():
            if self.kline.clear_dtcs():
                self.q.put(("result", "✅ Коди помилок стерто.\n\n"
                                      "Вимкніть і знову увімкніть запалювання, потім можна "
                                      "зчитати помилки ще раз для перевірки."))
            else:
                raise ObdError("Блок не підтвердив стирання. Переконайтеся, що двигун заглушено.")

        self.run_task(task)

    def on_live(self):
        if self.live:
            self.live = False
            self.btn_live.state(["disabled"])
            return
        self.live = True

        def task():
            sup = self.kline.supported or self.kline.supported_pids()
            pids = [p for p in LIVE_PIDS if p[0] in sup] if sup else LIVE_PIDS
            first = True
            while self.live:
                rows = []
                for pid, name, unit, fn, dec in pids:
                    if not self.live:
                        break
                    d = self.kline.read_pid(pid)
                    try:
                        val = f"{fn(d):.{dec}f} {unit}" if d is not None else "—"
                    except (IndexError, TypeError):
                        val = "—"
                    rows.append(f"{name}:  {val}")
                if rows:
                    self.q.put(("result", "Дані наживо (оновлюються автоматично):\n\n" + "\n".join(rows)))
                if first:
                    self.kline.quiet = True   # після першого кола не засмічуємо журнал
                    self.q.put(("log", "(дані наживо: подальший обмін у журнал не пишеться)"))
                    first = False

        self.run_task(task)
        self.set_buttons()

    def on_save_log(self):
        name = datetime.datetime.now().strftime("lancer_obd_%Y-%m-%d_%H-%M.txt")
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=name,
                                            filetypes=[("Текстовий файл", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write("=== Результат ===\n")
            f.write(self.result.get("1.0", "end"))
            f.write("\n=== Журнал ===\n")
            f.write(self.logbox.get("1.0", "end"))
        messagebox.showinfo("Збережено", f"Журнал збережено:\n{path}")

    def on_close(self):
        self.live = False
        if self.kline:
            self.kline.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    if serial is None:
        root.withdraw()
        messagebox.showerror("Бракує бібліотеки",
                             "Не встановлено бібліотеку pyserial.\n\n"
                             "Відкрийте командний рядок і виконайте:\n\n"
                             "pip install pyserial")
        return
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
