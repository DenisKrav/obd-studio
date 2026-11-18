"""Фальшивий serial-порт, що імітує кабель KKL (луна) і блок керування."""

import time

from obd_studio.config import Timing
from obd_studio.protocol import checksum


def kwp_frame(payload, src=0x10, dst=0xF1):
    """Відповідь блока у форматі KWP2000 з адресами: 80|len F1 10 <дані> CS."""
    frame = bytes([0x80 | len(payload), dst, src]) + bytes(payload)
    return frame + bytes([checksum(frame)])


def iso_frame(payload, src=0x10):
    """Відповідь блока у форматі ISO 9141-2: 48 6B 10 <дані> CS."""
    frame = bytes([0x48, 0x6B, src]) + bytes(payload)
    return frame + bytes([checksum(frame)])


def fast_timing(**overrides):
    """Дуже короткі паузи, щоб тести не чекали секундами."""
    t = Timing(
        serial_read_timeout=0.001, echo_timeout=0.05, retry_pause=0.0,
        fast_idle=0.0, fast_low=0.001, fast_high=0.001, fast_360_echo_timeout=0.02,
        fast_360_total=0.002, start_comm_timeout=0.03,
        slow_idle=0.0, slow_bit=0.001, slow_sync_timeout=0.03, slow_kb_timeout=0.03,
        slow_kb2_delay=0.0, slow_ack_timeout=0.03,
        response_first_timeout=0.03, response_gap=0.01, response_max_total=0.5,
        p3_min=0.0, iso_interbyte=0.0005, session_timeout=4.0,
    )
    for k, v in overrides.items():
        setattr(t, k, v)
    return t


class FakeSerial:
    """
    Імітує pyserial.Serial.

    responder(fake, tx) викликається після кожного запису й отримує всі байти,
    надіслані після останнього reset_input_buffer; повертає байти відповіді
    (або b"") і може очистити fake.tx, коли повідомлення оброблене.
    on_reset(fake) викликається під час reset_input_buffer (для 5-бодового старту).
    """

    def __init__(self, responder=None, on_reset=None, echo=True):
        self.responder = responder
        self.on_reset = on_reset
        self.echo = echo
        self.rx = bytearray()
        self.tx = bytearray()
        self.written = []           # усі виклики write
        self.breaks = []            # послідовність значень break_condition
        self.baudrate = 10400
        self.baud_history = []
        self._break = False
        self.closed = False

    @property
    def break_condition(self):
        return self._break

    @break_condition.setter
    def break_condition(self, value):
        self._break = value
        self.breaks.append(value)

    def __setattr__(self, name, value):
        if name == "baudrate" and "baud_history" in self.__dict__:
            self.baud_history.append(value)
        object.__setattr__(self, name, value)

    def write(self, data):
        data = bytes(data)
        self.written.append(data)
        if self.echo:
            self.rx += data
        self.tx += data
        if self.responder:
            resp = self.responder(self, bytes(self.tx))
            if resp:
                self.rx += resp
        return len(data)

    def read(self, n=1):
        if not self.rx:
            time.sleep(0.0005)
            return b""
        out = bytes(self.rx[:n])
        del self.rx[:n]
        return out

    def reset_input_buffer(self):
        self.rx.clear()
        self.tx.clear()
        if self.on_reset:
            resp = self.on_reset(self)
            if resp:
                self.rx += resp

    def close(self):
        self.closed = True


def slow_init_bits(address):
    """Значення break_condition, які KLine виставляє для адреси на 5 бод (+ стоп-біт)."""
    bits = [0] + [(address >> i) & 1 for i in range(8)]
    return [bit == 0 for bit in bits] + [False]


# ───────────── фальшивий адаптер ELM327 ─────────────

def can_frames(payload, header="7E8"):
    """Повідомлення блока → рядки ELM327 із заголовками (ISO-TP для довгих)."""
    payload = bytes(payload)
    hx = lambda bs: " ".join(f"{b:02X}" for b in bs)
    if len(payload) <= 7:
        return [f"{header} {hx(bytes([len(payload)]) + payload)}"]
    lines = [f"{header} {hx(bytes([0x10 | (len(payload) >> 8), len(payload) & 0xFF]) + payload[:6])}"]
    rest, seq = payload[6:], 1
    while rest:
        lines.append(f"{header} {hx(bytes([0x20 | (seq & 0x0F)]) + rest[:7])}")
        rest, seq = rest[7:], seq + 1
    return lines


def kline_elm_frames(payload):
    """Відповідь ISO 9141 через ELM327 із заголовками: 48 6B 10 <дані> CS."""
    frame = bytes([0x48, 0x6B, 0x10]) + bytes(payload)
    frame += bytes([checksum(frame)])
    return [" ".join(f"{b:02X}" for b in frame)]


class FakeElm:
    """Імітує ELM327: AT-команди і відповіді блоків. answers: {bytes запиту: [payload, ...]}."""

    def __init__(self, answers, protocol="6", version="ELM327 v1.5", voltage="12.6V",
                 extra_ecus=None, silent=False):
        self.answers = answers
        self.extra_ecus = extra_ecus or {}
        self.protocol = protocol
        self.version = version
        self.voltage = voltage
        self.silent = silent
        self.rx = bytearray()
        self.buf = bytearray()
        self.commands = []
        self.baudrate = 38400
        self.closed = False

    def _frames(self, payload, header):
        if self.protocol in ("6", "8"):
            return can_frames(payload, header)
        return kline_elm_frames(payload)

    def _answer(self, cmd):
        if cmd.startswith("AT"):
            if cmd == "ATZ":
                return ["", self.version]
            if cmd == "ATDPN":
                return ["A" + self.protocol]
            if cmd == "ATRV":
                return [self.voltage]
            return ["OK"]
        try:
            req = bytes.fromhex(cmd)
        except ValueError:
            return ["?"]
        lines = []
        for p in self.answers.get(req, []):
            lines += self._frames(p, "7E8")
        for p in self.extra_ecus.get(req, []):
            lines += self._frames(p, "7E9")
        if not lines:
            return ["NO DATA"]
        if req == b"\x01\x00" and not self.commands_had_search:
            lines = ["SEARCHING..."] + lines
        return lines

    commands_had_search = False

    def write(self, data):
        if self.silent:
            return len(data)
        self.buf += data
        while b"\r" in self.buf:
            line, _, rest = bytes(self.buf).partition(b"\r")
            self.buf = bytearray(rest)
            cmd = line.decode().strip().upper()
            if not cmd:
                continue
            self.commands.append(cmd)
            out = self._answer(cmd)
            if cmd == "0100":
                self.commands_had_search = True
            self.rx += ("\r".join(out) + "\r\r>").encode()
        return len(data)

    def read(self, n=1):
        if not self.rx:
            time.sleep(0.0005)
            return b""
        out = bytes(self.rx[:n])
        del self.rx[:n]
        return out

    def reset_input_buffer(self):
        self.rx.clear()

    def close(self):
        self.closed = True
