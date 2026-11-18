"""KLine і ObdClient з фальшивим портом: ініціалізація, луна, відповіді та відмови блока."""

import time

import pytest

from obd_studio.kline import KLine, ObdError
from obd_studio.obd import ObdClient
from obd_studio.protocol import checksum, parse_kwp

from fakes import FakeSerial, fast_timing, iso_frame, kwp_frame, slow_init_bits

START_COMM = bytes([0xC1, 0x33, 0xF1, 0x81, 0x66])
START_COMM_OK = kwp_frame([0xC1, 0xE9, 0x8F])      # позитивна відповідь, ключові байти E9 8F

PID00 = [0x41, 0x00, 0xBE, 0x3E, 0xB8, 0x11]        # PID 01..20, які підтримує блок
DEFAULT_ANSWERS = {
    b"\x01\x00": [PID00],
    b"\x01\x0C": [[0x41, 0x0C, 0x0B, 0xB8]],         # 750 об/хв
    b"\x03": [[0x43, 0x01, 0x33, 0x03, 0x00, 0x00, 0x00]],
    b"\x07": [[0x47, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]],
    b"\x04": [[0x44]],
}


def kwp_ecu(answers=None, accept=lambda fake: True):
    """Блок KWP2000 зі швидким стартом. accept(fake) вирішує, чи вдався імпульс."""
    answers = DEFAULT_ANSWERS if answers is None else answers

    def responder(fake, tx):
        if tx == START_COMM:
            fake.tx.clear()
            return START_COMM_OK if accept(fake) else b""
        frames = parse_kwp(tx)
        if not frames:
            return b""
        fake.tx.clear()
        return b"".join(kwp_frame(r) for r in answers.get(frames[0], []))

    return responder


def make_kline(fake, timing=None):
    logs = []
    k = KLine("COM_TEST", logs.append, timing or fast_timing())
    k.ser = fake
    return k, logs


def written_requests(fake):
    """Усі запити після ініціалізації, розібрані як KWP: [(sid, ...), ...]."""
    return [frame for w in fake.written for frame in parse_kwp(w)]


# ───────────── швидкий старт ─────────────

def test_fast_init_break_success():
    fake = FakeSerial(kwp_ecu(accept=lambda f: True in f.breaks))
    k, logs = make_kline(fake)

    desc = k.connect()

    assert k.protocol == "KWP"
    assert "KWP2000" in desc and "швидкий старт" in desc
    assert k.method_name == "KWP2000, швидкий старт"
    assert fake.written[0] == START_COMM
    # імпульс: лінія в 0, потім знову в 1
    assert fake.breaks[:3] == [False, True, False]
    assert any("Ключові байти: E9 8F" in line for line in logs)
    assert any("виміряно на ПК" in line for line in logs)
    # луну відкинуто, тож розбіжностей немає
    assert not any("луна не збіглася" in line for line in logs)


def test_connect_logs_all_timing_parameters():
    fake = FakeSerial(kwp_ecu())
    k, logs = make_kline(fake)
    k.connect()
    assert "Параметри ініціалізації:" in logs
    assert any(line.strip().startswith("fast_low =") for line in logs)
    assert any(line.strip().startswith("iso_interbyte =") for line in logs)


def test_fast_init_method_2_when_break_fails():
    # блок «чує» лише імпульс, зроблений байтом 0x00 на 360 бод
    fake = FakeSerial(kwp_ecu(accept=lambda f: 360 in f.baud_history))
    k, logs = make_kline(fake)

    desc = k.connect()

    assert "спосіб 2" in desc
    assert k.protocol == "KWP"
    assert b"\x00" in fake.written
    assert fake.baudrate == 10400                  # швидкість повернуто
    assert any("Спроба 1/3" in line for line in logs)
    assert any("Спроба 2/3" in line for line in logs)
    assert not any("Спроба 3/3" in line for line in logs)


def test_silence_raises_after_all_attempts():
    fake = FakeSerial(responder=None)
    k, logs = make_kline(fake)

    with pytest.raises(ObdError, match="не відповіла жодним способом"):
        k.connect()

    assert k.protocol is None
    assert any("Спроба 3/3: повільний старт 5 бод" in line for line in logs)
    assert any("немає байта синхронізації 0x55" in line for line in logs)
    assert fake.break_condition is False            # лінію не залишено в нулі
    assert fake.baudrate == 10400


def test_disabled_methods_are_skipped():
    fake = FakeSerial(responder=None)
    k, logs = make_kline(fake, fast_timing(try_fast_break=False, try_slow=False))
    with pytest.raises(ObdError):
        k.connect()
    assert any("Спроба 1/1: KWP2000, швидкий старт (спосіб 2)" in line for line in logs)
    assert True not in fake.breaks


def test_all_methods_disabled():
    k, _ = make_kline(FakeSerial(), fast_timing(try_fast_break=False, try_fast_360=False,
                                                try_slow=False))
    with pytest.raises(ObdError, match="вимкнено всі способи"):
        k.connect()


def test_echo_mismatch_is_logged():
    fake = FakeSerial(responder=None, echo=False)
    k, logs = make_kline(fake, fast_timing(try_fast_360=False, try_slow=False))
    with pytest.raises(ObdError):
        k.connect()
    assert any("луна не збіглася" in line for line in logs)


# ───────────── запити після підключення ─────────────

def connected_kwp(answers=None):
    fake = FakeSerial(kwp_ecu(answers))
    k, logs = make_kline(fake)
    k.connect()
    return fake, k, ObdClient(k), logs


def test_request_frame_format_and_supported_pids():
    fake, k, obd, _ = connected_kwp()

    sup = obd.supported_pids()

    req = fake.written[-2]
    assert req[:3] == bytes([0xC2, 0x33, 0xF1])
    assert req[3:5] == b"\x01\x00"
    assert req[-1] == checksum(req[:-1])
    # блок повідомив про PID 20, тож запитано й наступний діапазон (тут блок мовчить)
    assert fake.written[-1][3:5] == b"\x01\x20"
    assert {0x01, 0x05, 0x0C, 0x0D, 0x20} <= sup
    assert obd.supported == sup


def test_supported_pids_second_range():
    answers = dict(DEFAULT_ANSWERS)
    answers[b"\x01\x20"] = [[0x41, 0x20, 0x80, 0x00, 0x00, 0x00]]
    _, _, obd, _ = connected_kwp(answers)
    assert 0x21 in obd.supported_pids()


def test_read_pid_and_dtcs():
    _, _, obd, _ = connected_kwp()
    assert obd.read_pid(0x0C) == bytes([0x0B, 0xB8])
    assert obd.read_pid(0x0D) is None              # блок мовчить про цей PID
    codes, ok = obd.read_dtcs(0x03)
    assert ok and codes == ["P0133", "P0300"]
    codes, ok = obd.read_dtcs(0x07)
    assert ok and codes == []


def test_clear_dtcs_positive():
    _, _, obd, _ = connected_kwp()
    assert obd.clear_dtcs() is True


def test_negative_response_7f():
    answers = dict(DEFAULT_ANSWERS)
    answers[b"\x04"] = [[0x7F, 0x04, 0x22]]        # conditionsNotCorrect (двигун працює)
    _, _, obd, logs = connected_kwp(answers)

    assert obd.clear_dtcs() is False
    assert any("Блок відмовив: сервіс 04, причина 22" in line for line in logs)


def test_dtc_mode_not_supported_7f():
    answers = dict(DEFAULT_ANSWERS)
    answers[b"\x07"] = [[0x7F, 0x07, 0x11]]
    _, _, obd, logs = connected_kwp(answers)
    codes, ok = obd.read_dtcs(0x07)
    assert (codes, ok) == ([], False)
    assert any("сервіс 07, причина 11" in line for line in logs)


def test_silence_after_connect_drops_session_timer():
    fake, k, obd, logs = connected_kwp(answers={})
    assert obd.read_pid(0x0C) is None
    assert k.last_comm == 0.0                       # наступний запит спершу перепідключиться
    assert any("(тиша)" in line for line in logs)


def test_reconnect_after_session_timeout():
    fake, k, obd, logs = connected_kwp()
    k.last_comm = time.perf_counter() - 10
    assert obd.read_pid(0x0C) == bytes([0x0B, 0xB8])
    assert any("перепідключаюся" in line for line in logs)
    assert fake.written.count(START_COMM) == 2


def test_lost_session_raises():
    fake, k, obd, _ = connected_kwp()
    fake.responder = None                           # машину вимкнули
    k.last_comm = time.perf_counter() - 10
    with pytest.raises(ObdError, match="Зв’язок із машиною втрачено"):
        obd.read_pid(0x0C)
    assert k.protocol is None


def test_request_without_connect():
    k, _ = make_kline(FakeSerial())
    with pytest.raises(ObdError, match="Підключитися"):
        ObdClient(k).read_pid(0x0C)


def test_quiet_mode_hides_raw_exchange():
    _, k, obd, logs = connected_kwp()
    k.quiet = True
    before = len(logs)
    obd.read_pid(0x0C)
    assert len(logs) == before


def test_only_standard_obd_services_are_sent():
    fake, k, obd, _ = connected_kwp()
    obd.supported_pids()
    obd.read_pid(0x0C)
    obd.read_dtcs(0x03)
    obd.read_dtcs(0x07)
    obd.clear_dtcs()
    sids = {frame[0] for frame in written_requests(fake)}
    # 81 — StartCommunication; решта — лише стандартні режими OBD-II
    assert sids <= {0x81, 0x01, 0x03, 0x07, 0x04}


# ───────────── повільний старт 5 бод ─────────────

def slow_ecu(keybytes, answers=None, iso=True):
    answers = DEFAULT_ANSWERS if answers is None else answers
    inverted_kb2 = (~keybytes[1]) & 0xFF

    def on_reset(fake):
        if fake.breaks[-10:] == slow_init_bits(0x33):
            fake.breaks.clear()
            return bytes([0x55]) + bytes(keybytes)
        return b""

    def responder(fake, tx):
        if tx == bytes([inverted_kb2]):
            fake.tx.clear()
            return b"\xCC"
        if iso:
            if len(tx) >= 5 and tx[:3] == bytes([0x68, 0x6A, 0xF1]) \
                    and tx[-1] == checksum(tx[:-1]) and bytes(tx[3:-1]) in answers:
                fake.tx.clear()
                return b"".join(iso_frame(r) for r in answers[bytes(tx[3:-1])])
            return b""
        frames = parse_kwp(tx)
        if frames:
            fake.tx.clear()
            return b"".join(kwp_frame(r) for r in answers.get(frames[0], []))
        return b""

    return responder, on_reset


def test_slow_init_iso9141():
    responder, on_reset = slow_ecu([0x08, 0x08])
    fake = FakeSerial(responder, on_reset)
    k, logs = make_kline(fake)

    desc = k.connect()

    assert k.protocol == "ISO9141"
    assert desc.startswith("ISO 9141-2")
    assert bytes([0xF7]) in fake.written            # інвертований KB2
    assert any("синхронізація OK, ключові байти 08 08" in line for line in logs)

    obd = ObdClient(k)
    assert obd.read_pid(0x0C) == bytes([0x0B, 0xB8])
    # ISO 9141: заголовок 68 6A F1, байти йдуть по одному (пауза між байтами)
    sent = b"".join(fake.written[-6:])
    assert sent == bytes([0x68, 0x6A, 0xF1, 0x01, 0x0C, checksum(sent[:-1])])
    assert all(len(w) == 1 for w in fake.written[-6:])
    assert obd.read_dtcs(0x03) == (["P0133", "P0300"], True)


def test_slow_init_kwp_keybytes():
    responder, on_reset = slow_ecu([0xE9, 0x8F], iso=False)
    fake = FakeSerial(responder, on_reset)
    k, _ = make_kline(fake, fast_timing(try_fast_break=False, try_fast_360=False))

    desc = k.connect()

    assert k.protocol == "KWP"
    assert desc == "ISO 14230-4 (KWP2000), повільний старт 5 бод"
    assert bytes([0x70]) in fake.written            # ~0x8F
    assert ObdClient(k).read_pid(0x0C) == bytes([0x0B, 0xB8])


def test_slow_init_without_ack_fails():
    responder, on_reset = slow_ecu([0x08, 0x08])
    fake = FakeSerial(lambda f, tx: b"", on_reset)   # 0x55 і ключові байти є, а 0xCC немає
    k, logs = make_kline(fake, fast_timing(try_fast_break=False, try_fast_360=False))
    with pytest.raises(ObdError):
        k.connect()
    assert any("ключові байти 08 08" in line for line in logs)


def test_slow_init_address_bits():
    """Адреса 0x33 передається як старт-біт + 8 біт LSB-first + стоп-біт."""
    assert slow_init_bits(0x33) == [True, False, False, True, True, False, False, True, True, False]


# ───────────── підтримка сесії та повільні відповіді на запит кодів ─────────────

def test_keepalive_sends_pid00_after_pause():
    fake, k, obd, logs = connected_kwp()
    k.t.session_keepalive = 0.05
    assert not k.keepalive()                      # ще рано
    time.sleep(0.06)
    before = len(fake.written)
    assert k.keepalive()
    assert parse_kwp(fake.written[before]) == [b"\x01\x00"]
    assert time.perf_counter() - k.last_comm < 0.05   # сесію продовжено
    assert not k.quiet


def test_keepalive_disabled_or_session_lost():
    fake, k, obd, _ = connected_kwp()
    k.t.session_keepalive = 0.0
    time.sleep(0.01)
    assert not k.keepalive()
    k.t.session_keepalive = 0.001
    k.last_comm = 0.0                             # сесію вже втрачено — не втручаємося
    assert not k.keepalive()


def test_dtc_request_waits_longer():
    fake, k, obd, _ = connected_kwp()
    k.t.response_first_timeout = 0.02
    k.t.response_dtc_timeout = 0.4
    real = fake.responder

    def slow(f, tx):          # відповідь на 03 «приходить» пізніше за P2 параметрів
        resp = real(f, tx)
        if resp and parse_kwp(tx) and parse_kwp(tx)[0] == b"\x03":
            f.later = resp
            return b""
        return resp
    fake.responder = slow
    orig_read = fake.read
    t0 = {}

    def read(n=1):
        if getattr(fake, "later", None):
            t0.setdefault("t", time.perf_counter())
            if time.perf_counter() - t0["t"] > 0.1:
                fake.rx += fake.later
                fake.later = None
        return orig_read(n)
    fake.read = read
    codes, ok = obd.read_dtcs(0x03)
    assert ok and codes == ["P0133", "P0300"]
