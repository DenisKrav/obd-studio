"""Транспорт для адаптерів ELM327 (USB, Bluetooth як COM-порт, Wi-Fi як TCP).

ELM327 сам ініціалізує шину й підтримує всі протоколи OBD-II, зокрема CAN
(ISO 15765-4), який стоїть на більшості авто після 2008 року. Програма
надсилає адаптеру лише AT-команди налаштування та стандартні запити OBD-II.
Відповіді читаються із заголовками (ATH1), щоб розрізняти блоки керування
й самостійно збирати багатокадрові повідомлення CAN (ISO-TP).
"""

import time

try:
    import serial
except ImportError:
    serial = None

from .i18n import tr
from .protocol import ObdError, hexs

PROTOCOLS = {
    "0": "Автовизначення",
    "1": "SAE J1850 PWM (41.6 кбіт/с)",
    "2": "SAE J1850 VPW (10.4 кбіт/с)",
    "3": "ISO 9141-2 (5 бод)",
    "4": "ISO 14230-4 KWP (5 бод)",
    "5": "ISO 14230-4 KWP (швидкий старт)",
    "6": "ISO 15765-4 CAN (11 біт, 500 кбіт/с)",
    "7": "ISO 15765-4 CAN (29 біт, 500 кбіт/с)",
    "8": "ISO 15765-4 CAN (11 біт, 250 кбіт/с)",
    "9": "ISO 15765-4 CAN (29 біт, 250 кбіт/с)",
}
CAN11 = {"6", "8"}
CAN29 = {"7", "9"}

ERROR_WORDS = ("UNABLE TO CONNECT", "BUS ERROR", "CAN ERROR", "BUS BUSY", "FB ERROR",
               "DATA ERROR", "LV RESET", "ERR", "STOPPED", "ACT ALERT")
NO_DATA = "NO DATA"
BAUD_CANDIDATES = (38400, 9600, 115200, 57600, 230400, 500000)


def wifi_url(host, port):
    return f"socket://{host}:{port}"


def parse_frames(lines, protocol):
    """Рядки відповіді ELM327 (із заголовками) → [(адреса блока, корисні дані), ...].

    Для CAN збирає багатокадрові повідомлення ISO-TP, для K-лінії та J1850
    відкидає заголовок (3 байти) і контрольну суму.
    """
    can = protocol in CAN11 or protocol in CAN29
    hdr_len = 4 if protocol in CAN29 else 3
    out, partial = [], {}
    for line in lines:
        tokens = line.split()
        if not tokens or any(len(t) not in (2, 3) for t in tokens):
            continue
        try:
            if can and protocol in CAN11:
                header, data = tokens[0], bytes(int(t, 16) for t in tokens[1:])
            else:
                values = [int(t, 16) for t in tokens]
                header = " ".join(tokens[:hdr_len])
                data = bytes(values[hdr_len:])
        except ValueError:
            continue
        if not can:
            if len(data) >= 2:
                out.append((header, data[:-1]))
            continue
        if not data:
            continue
        pci = data[0] >> 4
        if pci == 0:
            n = data[0] & 0x0F
            if n:
                out.append((header, data[1:1 + n]))
        elif pci == 1 and len(data) >= 2:
            size = ((data[0] & 0x0F) << 8) | data[1]
            partial[header] = [size, bytearray(data[2:])]
        elif pci == 2 and header in partial:
            size, buf = partial[header]
            buf += data[1:]
            if len(buf) >= size:
                out.append((header, bytes(buf[:size])))
                del partial[header]
    for header, (size, buf) in partial.items():   # неповне повідомлення — віддаємо що є
        out.append((header, bytes(buf)))
    return out


class Elm327:
    kind = "ELM327"
    reset_timeout = 2.0     # очікування відповіді на ATZ (секунди)
    settle = 0.1            # пауза після «пробудження» адаптера
    search_timeout = 20.0   # перший запит: ELM327 шукає протокол (SEARCHING...)

    def __init__(self, url, log, baud=38400, protocol="0", timeout=5.0):
        self.url = url
        self._log = log
        self.baud = baud
        self.want_protocol = protocol
        self.timeout = timeout
        self.ser = None
        self.protocol = None          # номер протоколу за ATDPN, наприклад "6"
        self.version = ""
        self.quiet = False
        self.is_wifi = url.startswith("socket://")

    @property
    def is_connected(self):
        return self.ser is not None and self.protocol is not None

    def log(self, text, raw=False):
        if raw and self.quiet:
            return
        self._log(text)

    # ── порт ──
    def open(self, baud=None):
        if self.ser is not None:
            return
        try:
            self.ser = serial.serial_for_url(self.url, baudrate=baud or self.baud,
                                             timeout=0.05, write_timeout=2)
        except (serial.SerialException, ValueError, OSError) as e:
            if self.is_wifi:
                msg = tr("Не вдалося відкрити адаптера Wi-Fi: {error}\n"
                         "Перевірте, що ноутбук підключено до Wi-Fi мережі адаптера.")
            else:
                msg = tr("Не вдалося відкрити порту {port}: {error}\n"
                         "Можливо, порт зайнятий іншою програмою або адаптер не спарено.")
            raise ObdError(msg.format(port=self.url, error=e))
        if self.is_wifi:
            self.log(tr("Відкрито {url}").format(url=self.url))
        else:
            self.log(tr("Відкрито {url}, {baud} бод").format(url=self.url, baud=baud or self.baud))

    def close(self):
        if self.ser:
            try:
                self.ser.write(b"ATPC\r")    # закрити сесію з блоком (не обов’язково)
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.protocol = None

    # ── обмін ──
    def command(self, cmd, timeout=None, raw=False):
        """Надсилає команду й повертає рядки відповіді до запрошення «>»."""
        timeout = self.timeout if timeout is None else timeout
        self.ser.reset_input_buffer()
        self.ser.write(cmd.encode("ascii") + b"\r")
        buf = bytearray()
        end = time.perf_counter() + timeout
        while time.perf_counter() < end:
            chunk = self.ser.read(256)
            if chunk:
                buf += chunk
                if b">" in chunk:
                    break
        text = buf.decode("ascii", "replace").replace("\x00", "")
        lines = [ln.strip() for ln in text.replace("\n", "\r").split("\r")]
        lines = [ln for ln in lines if ln and ln != ">" and ln != cmd]
        lines = [ln.rstrip(">").strip() for ln in lines]
        self.log(f"→ {cmd}", raw=raw)
        self.log(f"← {' | '.join(lines) if lines else tr('(тиша)')}", raw=raw)
        if not buf:
            raise ObdError(tr("Адаптер ELM327 не відповідає. Перевірте підключення."))
        return [ln for ln in lines if ln]

    def _reset(self, attempts=1):
        for _ in range(attempts):
            try:
                self.ser.write(b"\r")
                time.sleep(self.settle)
                lines = self.command("ATZ", timeout=self.reset_timeout)
            except ObdError:
                continue
            for ln in lines:
                if "ELM" in ln.upper():
                    return ln
        return None

    def connect(self):
        bauds = [self.baud] if self.is_wifi else \
            [self.baud] + [b for b in BAUD_CANDIDATES if b != self.baud]
        version = None
        for i, baud in enumerate(bauds):
            self.open(baud)
            version = self._reset(attempts=2 if i == 0 else 1)
            if version:
                self.baud = baud
                break
            self.log(tr("Немає відповіді ELM327 на {baud} бод").format(baud=baud))
            if self.ser:
                self.ser.close()
            self.ser = None
        if not version:
            raise ObdError(tr("Адаптер ELM327 не відповідає.\n\n"
                              "Перевірте, що вибрано правильний порт (для Bluetooth — вихідний COM-порт "
                              "спареного адаптера) і що адаптер вставлено в роз’єм авто."))
        self.version = version
        self.log(tr("Адаптер: {version}").format(version=version))
        for cmd in ("ATE0", "ATL0", "ATS1", "ATH1", "ATAT1", f"ATSP{self.want_protocol}"):
            self.command(cmd, timeout=2)
        self.log(tr("Пошук протоколу і зв’язок із блоком керування…"))
        lines = self.command("0100", timeout=max(self.timeout, self.search_timeout))
        joined = " ".join(lines).upper()
        if not any(ln.replace(" ", "").upper().find("4100") >= 0 for ln in lines):
            reason = tr("Блок керування не відповів.")
            if "UNABLE TO CONNECT" in joined:
                reason = tr("Адаптер не зміг підключитися до блока керування (UNABLE TO CONNECT).")
            elif NO_DATA in joined:
                reason = tr("Блок керування не відповів на запит (NO DATA).")
            raise ObdError(reason + "\n\n" + tr(
                "Увімкніть запалювання, перевірте контакт у роз’ємі "
                "й спробуйте ще раз. Якщо авто не підтримує OBD-II, зв’язку не буде."))
        dpn = self.command("ATDPN", timeout=2)
        num = (dpn[0] if dpn else "0").upper().lstrip("A")[:1] or "0"
        self.protocol = num if num in PROTOCOLS else "6"
        name = tr(PROTOCOLS.get(self.protocol, "невідомий протокол"))
        return tr("{name} через {version}").format(name=name, version=version)

    def request(self, data, expect_sid):
        if not self.is_connected:
            raise ObdError(tr("Спершу натисніть «Підключитися»."))
        cmd = hexs(data).replace(" ", "")
        try:
            lines = self.command(cmd, raw=True)
        except serial.SerialException as e:
            self.protocol = None
            raise ObdError(tr("Зв’язок з адаптером втрачено: {error}").format(error=e))
        upper = " ".join(lines).upper()
        if NO_DATA in upper or upper.strip() == "?":
            return []
        if any(w in upper for w in ERROR_WORDS) and not any(
                ln[:1] in "0123456789ABCDEF" and len(ln.split()) > 2 for ln in lines):
            self.log(tr("   Адаптер повідомив про помилку: {text}").format(text=upper), raw=True)
            return []
        result = []
        for _header, p in parse_frames(lines, self.protocol):
            if p and p[0] == expect_sid:
                result.append(p)
            elif len(p) >= 3 and p[0] == 0x7F:
                self.log(tr("   Блок відмовив: сервіс {sid:02X}, причина {nrc:02X}").format(sid=p[1], nrc=p[2]),
                         raw=True)
        return result

    def keepalive(self):
        """ELM327 сам підтримує сесію з блоком."""
        return False

    def read_voltage(self):
        """Напруга бортової мережі, яку міряє сам адаптер (ATRV)."""
        try:
            lines = self.command("ATRV", timeout=2, raw=True)
        except (ObdError, serial.SerialException):
            return None
        for ln in lines:
            try:
                return float(ln.upper().replace("V", "").strip())
            except ValueError:
                continue
        return None
