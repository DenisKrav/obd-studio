"""Стандартні функції OBD-II (SAE J1979) поверх будь-якого транспорту (KLine або Elm327).

Читання: режими 01 (поточні дані), 02 (стоп-кадр), 03/07/0A (коди помилок),
09 (VIN, ідентифікатори калібрування, назва блока).
Єдиний запит, що змінює стан блока керування, — режим 04 (стирання помилок),
і він виконується лише за явною командою користувача. Заводських команд немає.
"""

from .dtc import decode_dtc
from .pids import PIDS

# Режими OBD-II, які програма взагалі може надіслати
ALLOWED_MODES = {0x01, 0x02, 0x03, 0x04, 0x07, 0x09, 0x0A}

DTC_MODES = {0x03: "stored", 0x07: "pending", 0x0A: "permanent"}


def parse_supported_pids(d, base=0x00):
    """Відповідь на PID base (4 байти бітової маски) → множина PID base+1..base+0x20."""
    sup = set()
    if d and len(d) >= 4:
        for i in range(32):
            if d[i // 8] & (0x80 >> (i % 8)):
                sup.add(base + i + 1)
    return sup


def extract_dtcs(payloads):
    """Корисні дані відповідей режимів 03/07/0A → список кодів без повторів."""
    codes = []
    for p in payloads:
        data = p[1:]
        if len(data) % 2:          # деякі блоки (і всі блоки CAN) додають байт кількості
            data = data[1:]
        for j in range(0, len(data) - 1, 2):
            a, b = data[j], data[j + 1]
            if a == 0 and b == 0:
                continue
            code = decode_dtc(a, b)
            if code not in codes:
                codes.append(code)
    return codes


SPARK_MONITORS = ["Каталізатор", "Підігрів каталізатора", "Система EVAP", "Вторинне повітря",
                  "Кондиціонер (холодоагент)", "Кисневі датчики", "Підігрів кисневих датчиків", "EGR"]
DIESEL_MONITORS = ["Каталізатор NMHC", "Нейтралізатор NOx / SCR", None, "Тиск наддуву",
                   None, "Датчик відпрацьованих газів", "Сажовий фільтр (DPF)", "EGR / VVT"]


def readiness_status(d):
    """PID 01 → dict: mil, dtc_count, diesel, monitors=[(назва, готово: bool)]."""
    a, b, c, dd = d[:4]
    diesel = bool(b & 0x08)
    monitors = []
    for sup_bit, inc_bit, name in ((0, 4, "Пропуски запалювання"),
                                   (1, 5, "Паливна система"),
                                   (2, 6, "Компоненти")):
        if b & (1 << sup_bit):
            monitors.append((name, not b & (1 << inc_bit)))
    names = DIESEL_MONITORS if diesel else SPARK_MONITORS
    for i, name in enumerate(names):
        if name and c & (1 << i):
            monitors.append((name, not dd & (1 << i)))
    return {"mil": bool(a & 0x80), "dtc_count": a & 0x7F, "diesel": diesel, "monitors": monitors}


def decode_readiness(d):
    """Текстовий опис готовності систем (для журналу й звіту)."""
    st = readiness_status(d)
    lines = [
        f"Лампа Check Engine: {'УВІМКНЕНА' if st['mil'] else 'вимкнена'}",
        f"Кількість підтверджених помилок: {st['dtc_count']}",
        "",
        "Готовність систем самодіагностики:",
    ]
    lines += [f"  {name}: {'готово' if ok else 'НЕ готово'}" for name, ok in st["monitors"]]
    lines += ["",
              "«НЕ готово» буває після стирання помилок або відключення акумулятора: "
              "система ще не завершила самоперевірку. Після кількох днів звичайної їзди "
              "статус зазвичай змінюється на «готово»."]
    return "\n".join(lines)


def assemble_mode9(payloads, pid):
    """Відповіді режиму 09 → байти даних.

    K-лінія: кілька повідомлень «49 pid N d1 d2 d3 d4» (N — номер); CAN: одне
    повідомлення «49 pid count дані…».
    """
    parts = [p for p in payloads if len(p) >= 3 and p[1] == pid]
    if not parts:
        return b""
    if len(parts) == 1:
        return bytes(parts[0][3:])
    parts.sort(key=lambda p: p[2])
    return b"".join(bytes(p[3:]) for p in parts)


def ascii_clean(data):
    return "".join(chr(b) for b in data if 0x20 <= b < 0x7F).strip()


def decode_vin(payloads):
    text = ascii_clean(assemble_mode9(payloads, 0x02)).replace(" ", "")
    return text[-17:] if len(text) >= 17 else text


class ObdClient:
    """Запити OBD-II поверх встановленого з’єднання (KLine або Elm327)."""

    def __init__(self, transport):
        self.kline = transport          # назва поля збережена з версії 0.x
        self.supported = set()

    @property
    def transport(self):
        return self.kline

    def _request(self, data, expect_sid):
        assert data[0] in ALLOWED_MODES, f"режим {data[0]:02X} заборонено"
        return self.kline.request(data, expect_sid)

    # ── режим 01 ──
    def read_pid(self, pid):
        for p in self._request([0x01, pid], 0x41):
            if len(p) >= 3 and p[1] == pid:
                return p[2:]
        return None

    def supported_pids(self):
        """Опитує PID 00, 20, 40… поки блок повідомляє про наступний діапазон."""
        sup = set()
        base = 0x00
        while base <= 0xC0:
            found = parse_supported_pids(self.read_pid(base), base)
            if not found:
                break
            sup |= found
            if base + 0x20 not in found:
                break
            base += 0x20
        self.supported = sup
        return sup

    def live_candidates(self):
        """PID із таблиці, які підтримує блок (або всі, якщо список невідомий)."""
        if not self.supported:
            return sorted(PIDS)
        return [p for p in sorted(PIDS) if p in self.supported]

    # ── коди помилок ──
    def read_dtcs(self, mode):
        payloads = self._request([mode], 0x40 + mode)
        return extract_dtcs(payloads), bool(payloads)

    def clear_dtcs(self):
        return bool(self._request([0x04], 0x44))

    def readiness(self):
        d = self.read_pid(0x01)
        return readiness_status(d) if d and len(d) >= 4 else None

    # ── режим 02: стоп-кадр ──
    def read_freeze_pid(self, pid, frame=0):
        for p in self._request([0x02, pid, frame], 0x42):
            if len(p) >= 4 and p[1] == pid:
                return p[3:]
        return None

    def freeze_frame(self):
        """→ (код, що спричинив кадр, {pid: байти}) або None, якщо кадру немає."""
        d = self.read_freeze_pid(0x02)
        if not d or len(d) < 2 or (d[0] == 0 and d[1] == 0):
            return None
        code = decode_dtc(d[0], d[1])
        sup = parse_supported_pids(self.read_freeze_pid(0x00), 0)
        pids = [p for p in sorted(PIDS) if p in sup] if sup else \
            [p for p in (0x04, 0x05, 0x06, 0x07, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x11) if p in PIDS]
        values = {}
        for pid in pids:
            raw = self.read_freeze_pid(pid)
            if raw is not None:
                values[pid] = raw
        return code, values

    # ── режим 09: інформація про авто ──
    def mode9_supported(self):
        """PID режиму 09, які підтримує блок. Порожньо — режим 09 не підтримується
        (типово для європейських авто до ~2005 р.)."""
        for p in self._request([0x09, 0x00], 0x49):
            if len(p) >= 6 and p[1] == 0x00:
                data = p[2:]
                return parse_supported_pids(data[1:] if len(data) == 5 else data, 0)
        return set()

    def vehicle_info(self):
        """VIN, ідентифікатори калібрування (CALID), CVN і назва блока (режим 09)."""
        info = {"supported": False, "vin": "", "calibration_ids": [], "cvn": [], "ecu_name": ""}
        sup = self.mode9_supported()
        if not sup:
            return info
        info["supported"] = True
        if 0x02 in sup:
            info["vin"] = decode_vin(self._request([0x09, 0x02], 0x49))
        if 0x04 in sup:
            cal = assemble_mode9(self._request([0x09, 0x04], 0x49), 0x04)
            info["calibration_ids"] = [ascii_clean(cal[i:i + 16]) for i in range(0, len(cal), 16)
                                       if ascii_clean(cal[i:i + 16])]
        if 0x06 in sup:
            cvn = assemble_mode9(self._request([0x09, 0x06], 0x49), 0x06)
            info["cvn"] = [cvn[i:i + 4].hex().upper() for i in range(0, len(cvn) - 3, 4)]
        if 0x0A in sup:
            name = assemble_mode9(self._request([0x09, 0x0A], 0x49), 0x0A)
            info["ecu_name"] = ascii_clean(name.replace(b"\x00-", b" - ").replace(b"\x00", b" "))
        return info
