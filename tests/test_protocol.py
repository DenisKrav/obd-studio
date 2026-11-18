"""Розбір кадрів KWP2000 / ISO 9141-2."""

import random
import time

from obd_studio.protocol import busy_wait, checksum, hexs, parse_iso9141, parse_kwp

from fakes import iso_frame, kwp_frame


def test_checksum_and_hexs():
    assert checksum([0xC1, 0x33, 0xF1, 0x81]) == 0x66
    assert checksum([0xFF, 0x02]) == 0x01
    assert hexs(b"\x00\x0a\xff") == "00 0A FF"
    assert hexs(b"") == ""


def test_kwp_with_addresses():
    assert parse_kwp(kwp_frame([0x41, 0x0C, 0x0B, 0xB8])) == [bytes([0x41, 0x0C, 0x0B, 0xB8])]


def test_kwp_start_communication_response():
    # реальна форма позитивної відповіді на StartCommunication
    buf = bytes([0x83, 0xF1, 0x10, 0xC1, 0xE9, 0x8F])
    buf += bytes([checksum(buf)])
    assert parse_kwp(buf) == [bytes([0xC1, 0xE9, 0x8F])]


def test_kwp_without_addresses():
    frame = bytes([0x02, 0x41, 0x0D])
    frame += bytes([checksum(frame)])
    assert parse_kwp(frame) == [bytes([0x41, 0x0D])]


def test_kwp_separate_length_byte():
    payload = bytes([0x43] + [0x01, 0x33] * 40)       # 81 байт — довжина окремим байтом
    frame = bytes([0x80, 0xF1, 0x10, len(payload)]) + payload
    frame += bytes([checksum(frame)])
    assert parse_kwp(frame) == [payload]


def test_kwp_several_frames_and_garbage():
    a = kwp_frame([0x43, 0x01, 0x33, 0x00, 0x00, 0x00, 0x00])
    b = kwp_frame([0x43, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00])
    out = parse_kwp(b"\x00\xFF" + a + b)
    assert bytes([0x43, 0x01, 0x33, 0, 0, 0, 0]) in out
    assert bytes([0x43, 0x03, 0x00, 0, 0, 0, 0]) in out


def test_kwp_bad_checksum_is_dropped():
    frame = bytearray(kwp_frame([0x41, 0x0C, 0x0B, 0xB8]))
    frame[-1] ^= 0xFF
    assert parse_kwp(bytes(frame)) == []


def test_kwp_truncated_and_empty():
    assert parse_kwp(kwp_frame([0x41, 0x0C, 0x0B, 0xB8])[:-1]) == []
    assert parse_kwp(b"") == []
    assert parse_kwp(b"\x80") == []


def test_kwp_negative_response():
    assert parse_kwp(kwp_frame([0x7F, 0x04, 0x22])) == [bytes([0x7F, 0x04, 0x22])]


def test_iso9141_single_and_multiple():
    a = iso_frame([0x41, 0x0C, 0x0B, 0xB8])
    b = iso_frame([0x43, 0x01, 0x33, 0x00, 0x00, 0x00, 0x00], src=0x1A)
    assert parse_iso9141(a) == [bytes([0x41, 0x0C, 0x0B, 0xB8])]
    assert parse_iso9141(a + b) == [bytes([0x41, 0x0C, 0x0B, 0xB8]),
                                    bytes([0x43, 0x01, 0x33, 0, 0, 0, 0])]


def test_iso9141_bad_checksum_and_short():
    frame = bytearray(iso_frame([0x41, 0x0C, 0x0B, 0xB8]))
    frame[-1] ^= 0x01
    assert parse_iso9141(bytes(frame)) == []
    assert parse_iso9141(b"\x48\x6B\x10\xC3") == []
    assert parse_iso9141(b"") == []


def test_parsers_do_not_crash_on_random_data():
    rnd = random.Random(1)
    for _ in range(2000):
        buf = bytes(rnd.randrange(256) for _ in range(rnd.randrange(30)))
        parse_kwp(buf)
        parse_iso9141(buf)


def test_parsers_match_original_draft(draft):
    """Перенесений код розбирає довільні дані так само, як чернетка."""
    rnd = random.Random(2)
    samples = [kwp_frame([0x41, 0x0C, 1, 2]), iso_frame([0x41, 0x0C, 1, 2])]
    samples += [bytes(rnd.randrange(256) for _ in range(rnd.randrange(40))) for _ in range(3000)]
    for buf in samples:
        assert parse_kwp(buf) == draft.parse_kwp(buf)
        assert parse_iso9141(buf) == draft.parse_iso9141(buf)


def test_busy_wait_is_accurate_enough():
    t0 = time.perf_counter()
    busy_wait(0.025)
    elapsed = time.perf_counter() - t0
    assert 0.025 <= elapsed < 0.035
