"""Профілі марок авто й розбір VIN.

Профіль не змінює запити (програма завжди працює лише зі стандартним OBD-II),
а підказує, який адаптер підійде, і уточнює описи кодів виробника.
"""

from collections import namedtuple

Brand = namedtuple("Brand", "key name wmi adapter_hint")

_K_OLD = ("До ~2008 р. більшість моделей мають K-лінію (підійде кабель KKL або ELM327), "
          "новіші — CAN (потрібен ELM327).")
_CAN = "Майже всі моделі після 2008 р. мають CAN — потрібен адаптер ELM327."
_US = ("Моделі для ринку США до 2008 р. часто мають J1850 або CAN — потрібен ELM327; "
       "європейські — K-лінію або CAN.")

BRANDS = [
    Brand("mitsubishi", "Mitsubishi", ("JMB", "JMY", "JMA", "JA3", "JA4", "JA7", "4A3", "4A4",
                                         "XMC", "MMB", "MMC", "MMT", "Z8T"),
          "Lancer IX, Outlander, Pajero до ~2007 р. — K-лінія (ISO 9141-2): підходить кабель KKL. "
          "Lancer X, ASX, Outlander XL і новіші — CAN, потрібен ELM327."),
    Brand("toyota", "Toyota / Lexus", ("JT", "4T", "5T", "SB1", "NMT", "VNK", "MR0", "TW1", "AHT"), _K_OLD),
    Brand("honda", "Honda / Acura", ("JH", "1HG", "2HG", "5FN", "5J6", "SHH", "SHS", "19X"), _K_OLD),
    Brand("nissan", "Nissan / Infiniti", ("JN", "1N4", "1N6", "3N1", "5N1", "SJN", "VSK", "VWA", "Z8N"), _K_OLD),
    Brand("mazda", "Mazda", ("JM1", "JM3", "JMZ", "4F2"), _K_OLD),
    Brand("subaru", "Subaru", ("JF1", "JF2", "4S3", "4S4"), _K_OLD),
    Brand("suzuki", "Suzuki", ("JS", "TSM", "MA3", "VSE"), _K_OLD),
    Brand("hyundai", "Hyundai", ("KMH", "KM8", "TMA", "5NP", "NLH", "MAL", "Z94"), _K_OLD),
    Brand("kia", "Kia", ("KNA", "KND", "KNE", "U5Y", "U6Y", "XWE", "5XY"), _K_OLD),
    Brand("vag", "Volkswagen / Audi / Škoda / SEAT", ("WVW", "WV1", "WV2", "WVG", "WAU", "WA1", "WUA",
                                                       "TRU", "TMB", "VSS", "XW8", "1VW", "3VW"),
          "До ~2005 р. — K-лінія (кабель KKL), 2005–2008 — K-лінія або CAN, далі — CAN (ELM327). "
          "Стандартний OBD-II бачить лише блок двигуна; інші блоки VAG потребують VCDS."),
    Brand("bmw", "BMW / MINI", ("WBA", "WBS", "WBY", "WBX", "4US", "5UX", "5YM", "WMW", "X4X"),
          "До ~2007 р. — K-лінія або D-CAN, далі — CAN (ELM327)."),
    Brand("mercedes", "Mercedes-Benz", ("WDB", "WDD", "WDC", "WDF", "W1K", "W1N", "W1V", "4JG", "55S"),
          "До ~2004 р. бензинові — K-лінія, далі — CAN (ELM327)."),
    Brand("opel", "Opel / Vauxhall", ("W0L", "W0V", "VXK", "XWF"), _K_OLD),
    Brand("ford", "Ford", ("WF0", "1FA", "1FM", "1FT", "1FD", "2FM", "3FA", "MAJ", "X9F", "NM0"), _US),
    Brand("chevrolet", "Chevrolet / GM / Daewoo", ("1G", "2G", "3G", "KL", "XUU"), _US),
    Brand("renault", "Renault / Dacia", ("VF1", "VF6", "UU1", "X7L", "VF2"), _K_OLD),
    Brand("psa", "Peugeot / Citroën / DS", ("VF3", "VF7", "VR3", "VR7", "VXE", "VF8"), _K_OLD),
    Brand("fiat", "Fiat / Alfa Romeo / Jeep", ("ZFA", "ZAR", "ZFC", "1C4", "1J4", "1J8", "ZAC"), _K_OLD),
    Brand("volvo", "Volvo", ("YV1", "YV4", "YV2"), "До ~2005 р. — K-лінія, далі — CAN (ELM327)."),
    Brand("lada", "Lada (ВАЗ)", ("XTA", "XTT"), "Моделі з інжектором Bosch/Январь — K-лінія (KKL або ELM327)."),
    Brand("zaz", "ЗАЗ", ("Y6D",), "Sens, Lanos, Vida — K-лінія (KKL або ELM327)."),
    Brand("chinese", "Chery / Geely / BYD / Great Wall", ("LVV", "L6T", "LGX", "LGW", "LC0", "LS5"), _CAN),
    Brand("tesla", "Tesla", ("5YJ", "7SA", "LRW", "XP7"), "Електромобіль: стандартний OBD-II майже нічого не показує."),
]

BRANDS_BY_KEY = {b.key: b for b in BRANDS}

REGIONS = [
    ("ABCDEFGH", "Африка"), ("J", "Японія"), ("KL", "Південна Корея"), ("MN", "Південна Азія"),
    ("PR", "Азія"), ("S", "Велика Британія / Німеччина / Польща"), ("T", "Центральна Європа"),
    ("U", "Європа"), ("VW", "Франція / Іспанія / Європа"), ("X", "Східна Європа"),
    ("Y", "Північна Європа / Україна"), ("Z", "Італія / Європа"), ("12345", "Північна Америка"),
    ("67", "Океанія"), ("89", "Південна Америка"),
]

_YEAR_CODES = "ABCDEFGHJKLMNPRSTVWXY123456789"
_TRANSLIT = {**{str(i): i for i in range(10)},
             **dict(zip("ABCDEFGH", range(1, 9))), **dict(zip("JKLMN", range(1, 6))),
             "P": 7, "R": 9, **dict(zip("STUVWXYZ", range(2, 10)))}
_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def brand_for_wmi(vin):
    vin = (vin or "").upper()
    best, best_len = None, 0
    for b in BRANDS:
        for w in b.wmi:
            if vin.startswith(w) and len(w) > best_len:
                best, best_len = b, len(w)
    return best


def region_of(vin):
    if not vin:
        return ""
    for letters, name in REGIONS:
        if vin[0] in letters:
            return name
    return ""


def model_years(vin, current_year):
    """Можливі модельні роки за 10-м символом (цикл 30 років), не пізніше наступного року."""
    if len(vin) < 10 or vin[9] not in _YEAR_CODES:
        return []
    base = 1980 + _YEAR_CODES.index(vin[9])
    return [y for y in (base, base + 30) if y <= current_year + 1]


def vin_check_digit_ok(vin):
    """Контрольна цифра (9-й символ) — обов’язкова лише для Північної Америки."""
    if len(vin) != 17:
        return False
    try:
        total = sum(_TRANSLIT[c] * w for c, w in zip(vin, _WEIGHTS))
    except KeyError:
        return False
    check = total % 11
    return vin[8] == ("X" if check == 10 else str(check))


def decode_vin(vin, current_year):
    """Короткий розбір VIN для показу користувачеві."""
    vin = (vin or "").strip().upper()
    brand = brand_for_wmi(vin)
    years = model_years(vin, current_year)
    return {
        "vin": vin,
        "valid": len(vin) == 17 and not any(c in "IOQ" for c in vin),
        "brand": brand,
        "region": region_of(vin),
        "wmi": vin[:3],
        "year": years[-1] if years else None,
        "years": years,
        "check_digit_ok": vin_check_digit_ok(vin),
    }
