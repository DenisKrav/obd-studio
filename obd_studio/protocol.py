"""Розбір кадрів KWP2000 / ISO 9141-2 і допоміжні функції (без роботи з портом)."""

import time


class ObdError(Exception):
    """Помилка зв’язку або відповіді блока, яку треба показати користувачеві."""


def wait_until(t):
    """Точне очікування до моменту t (time.perf_counter).

    time.sleep на Windows неточний, тому останні ~20 мс чекаємо активно.
    """
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
