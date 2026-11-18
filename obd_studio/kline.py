"""Транспорт K-лінії через «простий» кабель KKL (FTDI): ініціалізація, обмін, луна."""

import time

try:
    import serial
except ImportError:
    serial = None

from .config import ECU_ADDRESS, TESTER_ADDRESS, Timing
from .protocol import ObdError, busy_wait, checksum, hexs, parse_iso9141, parse_kwp, wait_until

__all__ = ["KLine", "ObdError"]

DTC_MODES = (0x03, 0x07, 0x0A)


class KLine:
    """Транспорт для кабелю KKL. Спільний інтерфейс з Elm327:
    connect() → опис протоколу, request(data, expect_sid), close(), is_connected, quiet."""

    kind = "KKL (K-лінія)"

    def __init__(self, port, log, timing=None):
        self.port = port
        self._log = log
        self.t = timing or Timing()
        self.ser = None
        self.protocol = None      # "KWP" або "ISO9141"
        self.method = None
        self.method_name = ""
        self.last_comm = 0.0
        self.quiet = False

    @property
    def is_connected(self):
        return self.ser is not None and self.protocol is not None

    def read_voltage(self):
        """Кабель KKL не вміє міряти напругу (на відміну від ELM327)."""
        return None

    def log(self, text, raw=False):
        if raw and self.quiet:
            return
        self._log(text)

    # ── порт ──
    def open(self):
        if self.ser is None:
            try:
                self.ser = serial.Serial(self.port, self.t.baud,
                                         timeout=self.t.serial_read_timeout, write_timeout=1)
            except serial.SerialException as e:
                raise ObdError(f"Не вдалося відкрити {self.port}: {e}\n"
                               "Можливо, порт зайнятий іншою програмою (наприклад, VCDS-Lite).")
            self.ser.break_condition = False
            self.log(f"Порт {self.port} відкрито, {self.t.baud} бод")

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
    def _read_exact(self, n, timeout=None):
        if timeout is None:
            timeout = self.t.echo_timeout
        buf = bytearray()
        end = time.perf_counter() + timeout
        while len(buf) < n and time.perf_counter() < end:
            buf += self.ser.read(n - len(buf))
        return bytes(buf)

    def _read_until_silence(self, first_timeout=None, gap=None, max_total=None):
        if first_timeout is None:
            first_timeout = self.t.response_first_timeout
        if gap is None:
            gap = self.t.response_gap
        if max_total is None:
            max_total = self.t.response_max_total
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
        mismatch = False
        if interbyte > 0:
            for b in data:
                self.ser.write(bytes([b]))
                echo = self._read_exact(1)
                if echo != bytes([b]):
                    odd += echo
                    mismatch = True
                busy_wait(interbyte)
        else:
            self.ser.write(data)
            echo = self._read_exact(len(data))
            if echo != data:
                odd += echo
                mismatch = True
        self.log(f"→ {hexs(data)}", raw=True)
        if mismatch:
            hint = ("" if odd else " — кабель не повертає надіслане: чи є живлення 12 В "
                                   "на роз’ємі (увімкнене запалювання)?")
            self.log(f"   (луна не збіглася: {hexs(odd) or 'немає'}){hint}", raw=True)

    # ── способи ініціалізації ──
    def _idle(self, seconds):
        self.ser.break_condition = False
        time.sleep(seconds)
        self.ser.reset_input_buffer()

    def _start_comm(self):
        req = bytes([0xC1, ECU_ADDRESS, TESTER_ADDRESS, 0x81])
        req += bytes([checksum(req)])
        self._send_raw(req)
        resp = self._read_until_silence(first_timeout=self.t.start_comm_timeout)
        self.log(f"← {hexs(resp) if resp else '(тиша)'}")
        for p in parse_kwp(resp):
            if p and p[0] == 0xC1:
                self.log(f"Блок відповів! Ключові байти: {hexs(p[1:3])}")
                return True
        return False

    def _fast_init_break(self):
        self._idle(self.t.fast_idle)
        t_low = time.perf_counter()
        self.ser.break_condition = True       # лінія в 0
        busy_wait(self.t.fast_low)
        t_high = time.perf_counter()
        self.ser.break_condition = False      # лінія в 1
        t = time.perf_counter() + self.t.fast_high
        self.ser.reset_input_buffer()
        wait_until(t)
        t_req = time.perf_counter()
        ok = self._start_comm()
        self.log(f"   (виміряно на ПК: нуль {(t_high - t_low) * 1000:.1f} мс, "
                 f"від початку імпульсу до запиту {(t_req - t_low) * 1000:.1f} мс)")
        return ok

    def _fast_init_360(self):
        self._idle(self.t.fast_idle)
        self.ser.baudrate = self.t.fast_360_baud   # байт 0x00 на 360 бод ≈ 25 мс нуля
        t0 = time.perf_counter()
        self.ser.write(b"\x00")
        echo = self._read_exact(1, timeout=self.t.fast_360_echo_timeout)
        t_echo = time.perf_counter()
        self.ser.baudrate = self.t.baud
        self.ser.reset_input_buffer()
        wait_until(t0 + self.t.fast_360_total)
        t_req = time.perf_counter()
        ok = self._start_comm()
        self.log(f"   (виміряно на ПК: луна 0x00 {hexs(echo) or 'немає'} через "
                 f"{(t_echo - t0) * 1000:.1f} мс, від початку імпульсу до запиту "
                 f"{(t_req - t0) * 1000:.1f} мс)")
        return ok

    def _slow_init(self):
        self._idle(self.t.slow_idle)
        bits = [0] + [(ECU_ADDRESS >> i) & 1 for i in range(8)]   # старт-біт + адреса
        t = time.perf_counter()
        for bit in bits:
            self.ser.break_condition = (bit == 0)
            t += self.t.slow_bit                                  # 5 бод = 200 мс на біт
            wait_until(t)
        self.ser.break_condition = False                          # стоп-біт
        self.ser.reset_input_buffer()
        sync = None
        t_addr_end = time.perf_counter()
        end = t_addr_end + self.t.slow_sync_timeout
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
        self.log(f"   (0x55 прийшов через {(time.perf_counter() - t_addr_end) * 1000:.0f} мс "
                 "після адреси)")
        kb = self._read_exact(2, timeout=self.t.slow_kb_timeout)
        if len(kb) < 2:
            self.log(f"← 55 {hexs(kb)} (ключові байти неповні)")
            return False
        self.log(f"← 55 {hexs(kb)}  (синхронізація OK, ключові байти {hexs(kb)})")
        busy_wait(self.t.slow_kb2_delay)
        self._send_raw([(~kb[1]) & 0xFF])
        ack = self._read_exact(1, timeout=self.t.slow_ack_timeout)
        self.log(f"← {hexs(ack) if ack else '(тиша)'}")
        if ack != bytes([(~ECU_ADDRESS) & 0xFF]):
            return False
        if kb[0] == kb[1] and kb[0] in (0x08, 0x94):
            self.protocol = "ISO9141"
        else:
            self.protocol = "KWP"
        return True

    # ── сесія ──
    def init_attempts(self):
        attempts = []
        if self.t.try_fast_break:
            attempts.append(("KWP2000, швидкий старт", self._fast_init_break, "KWP"))
        if self.t.try_fast_360:
            attempts.append(("KWP2000, швидкий старт (спосіб 2)", self._fast_init_360, "KWP"))
        if self.t.try_slow:
            attempts.append(("повільний старт 5 бод", self._slow_init, None))
        return attempts

    def connect(self):
        attempts = self.init_attempts()
        if not attempts:
            raise ObdError("У налаштуваннях вимкнено всі способи підключення.")
        self.open()
        self.log("Параметри ініціалізації:")
        for line in self.t.describe():
            self.log(line)
        total = len(attempts)
        for i, (name, func, proto) in enumerate(attempts):
            if i:
                self.log(f"Пауза {self.t.retry_pause:g} с перед наступною спробою…")
                time.sleep(self.t.retry_pause)
            self.log(f"── Спроба {i + 1}/{total}: {name}")
            try:
                ok = func()
            except serial.SerialException as e:
                raise ObdError(f"Помилка порту: {e}")
            finally:
                if self.ser:
                    self.ser.break_condition = False
                    if self.ser.baudrate != self.t.baud:
                        self.ser.baudrate = self.t.baud
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

    def keepalive(self):
        """Не дає сесії K-лінії згаснути, поки програма простоює (блок тримає її ~5 с).

        Надсилає той самий запит на читання, що й під час підключення (01 00).
        Повертає True, якщо запит надіслано.
        """
        if not self.is_connected or self.t.session_keepalive <= 0:
            return False
        idle = time.perf_counter() - self.last_comm
        if idle < self.t.session_keepalive or idle > self.t.session_timeout:
            return False      # ще рано, або сесію вже втрачено — тоді перепідключить ensure_session
        quiet, self.quiet = self.quiet, True
        try:
            self.request([0x01, 0x00], 0x41)
        finally:
            self.quiet = quiet
        return True

    def ensure_session(self):
        if self.protocol is None:
            raise ObdError("Спершу натисніть «Підключитися».")
        if time.perf_counter() - self.last_comm > self.t.session_timeout:
            self.log("Сесія могла завершитися — перепідключаюся…")
            ok = self.method()
            if not ok:
                time.sleep(self.t.retry_pause)
                ok = self.method()
            if not ok:
                self.protocol = None
                raise ObdError("Зв’язок із машиною втрачено. Натисніть «Підключитися» ще раз.")
            self.last_comm = time.perf_counter()
        wait_until(self.last_comm + self.t.p3_min)

    def request(self, data, expect_sid):
        """Надсилає запит OBD-II і повертає список відповідей із потрібним SID."""
        self.ensure_session()
        self.ser.reset_input_buffer()
        data = bytes(data)
        if self.protocol == "ISO9141":
            msg = bytes([0x68, 0x6A, TESTER_ADDRESS]) + data
            interbyte = self.t.iso_interbyte
        else:
            msg = bytes([0xC0 | len(data), ECU_ADDRESS, TESTER_ADDRESS]) + data
            interbyte = 0.0
        msg += bytes([checksum(msg)])
        self._send_raw(msg, interbyte)
        # блоки ISO 9141 відповідають на запит кодів повільніше, ніж на запит параметрів
        first = self.t.response_first_timeout
        if data[0] in DTC_MODES:
            first = max(first, self.t.response_dtc_timeout)
        resp = self._read_until_silence(first_timeout=first)
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
