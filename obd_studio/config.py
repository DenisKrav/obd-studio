"""
Усі часові параметри K-лінії в одному місці.

Значення за замовчуванням збігаються з першою (чернетковою) версією програми.
Їх можна змінити на сторінці «Налаштування» — тоді вони зберігаються у файл
obd_studio_settings.json поруч із програмою і діють з наступного «Підключитися».
Там само зберігаються загальні налаштування програми (AppSettings).

Усі тривалості — у секундах (у вікні налаштувань показуються в мілісекундах).
"""

import dataclasses
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .i18n import tr

SETTINGS_FILE = "obd_studio_settings.json"
LEGACY_SETTINGS_FILE = "lancer_obd_settings.json"   # версії 0.x зберігали лише Timing

# Адреси (стандарт ISO 14230-4 / ISO 9141-2). Це не часові параметри,
# тому вони не виносяться у вікно налаштувань.
ECU_ADDRESS = 0x33        # функціональна адреса «усі блоки OBD-II»
TESTER_ADDRESS = 0xF1     # адреса діагностичного приладу


def _ms(default, label):
    return field(default=default, metadata={"label": label, "kind": "ms"})


def _num(default, label, unit=""):
    return field(default=default, metadata={"label": label, "kind": "num", "unit": unit})


def _flag(default, label):
    return field(default=default, metadata={"label": label, "kind": "bool"})


@dataclass
class Timing:
    # ── загальне ──
    baud: int = _num(10400, "Швидкість K-лінії", "бод")
    serial_read_timeout: float = _ms(0.010, "Таймаут одного читання з порту")
    echo_timeout: float = _ms(0.300, "Очікування «луни» надісланих байтів")

    # ── які способи ініціалізації пробувати ──
    try_fast_break: bool = _flag(True, "Пробувати швидкий старт (break)")
    try_fast_360: bool = _flag(True, "Пробувати швидкий старт (спосіб 2, 360 бод)")
    try_slow: bool = _flag(True, "Пробувати повільний старт 5 бод")
    retry_pause: float = _ms(3.000, "Пауза між спробами ініціалізації")

    # ── швидкий старт (ISO 14230-2) ──
    fast_idle: float = _ms(0.400, "Швидкий старт: тиша на лінії перед імпульсом")
    fast_low: float = _ms(0.025, "Швидкий старт: тривалість нуля (Tinil)")
    fast_high: float = _ms(0.025, "Швидкий старт: тривалість одиниці після нуля")
    fast_360_baud: int = _num(360, "Спосіб 2: швидкість для байта 0x00", "бод")
    fast_360_echo_timeout: float = _ms(0.200, "Спосіб 2: очікування луни байта 0x00")
    fast_360_total: float = _ms(0.050, "Спосіб 2: від початку імпульсу до запиту (Twup)")
    start_comm_timeout: float = _ms(0.300, "Очікування відповіді на StartCommunication")

    # ── повільний старт 5 бод (ISO 9141-2 / ISO 14230-2) ──
    slow_idle: float = _ms(2.600, "Повільний старт: тиша на лінії перед адресою")
    slow_bit: float = _ms(0.200, "Повільний старт: тривалість біта (5 бод = 200 мс)")
    slow_sync_timeout: float = _ms(0.800, "Повільний старт: очікування байта 0x55 (W1)")
    slow_kb_timeout: float = _ms(0.100, "Повільний старт: очікування ключових байтів")
    slow_kb2_delay: float = _ms(0.030, "Повільний старт: пауза перед інвертованим KB2 (W4)")
    slow_ack_timeout: float = _ms(0.200, "Повільний старт: очікування підтвердження 0xCC")

    # ── обмін повідомленнями ──
    response_first_timeout: float = _ms(0.350, "Очікування першого байта відповіді (P2)")
    response_gap: float = _ms(0.080, "Тиша, після якої відповідь вважається завершеною")
    response_max_total: float = _ms(2.000, "Максимальна тривалість прийому відповіді")
    p3_min: float = _ms(0.060, "Мінімальна пауза між повідомленнями (P3min)")
    iso_interbyte: float = _ms(0.006, "ISO 9141: пауза між байтами запиту (P4)")
    response_dtc_timeout: float = _ms(1.000, "Очікування відповіді на запит кодів помилок")
    session_timeout: float = _ms(4.000, "Тиша, після якої сесія вважається втраченою")
    session_keepalive: float = _ms(2.000, "Підтримка сесії: запит 01 00 після такої паузи (0 — вимкнено)")

    # ── службове ──
    @classmethod
    def fields(cls):
        return dataclasses.fields(cls)

    def as_dict(self):
        return dataclasses.asdict(self)

    def describe(self):
        """Рядки для технічного журналу: усі параметри з поточними значеннями."""
        lines = []
        for f in self.fields():
            v = getattr(self, f.name)
            kind = f.metadata["kind"]
            if kind == "ms":
                shown = f"{v * 1000:g} {tr('мс')}"
            elif kind == "bool":
                shown = tr("так") if v else tr("ні")
            else:
                shown = f"{v} {tr(f.metadata.get('unit', ''))}".strip()
            lines.append(f"  {f.name} = {shown}")
        return lines

    @classmethod
    def from_dict(cls, data):
        """Створює Timing зі словника, ігноруючи невідомі ключі й помилкові значення."""
        t = cls()
        for f in cls.fields():
            if f.name not in data:
                continue
            raw = data[f.name]
            try:
                if f.type in (bool, "bool"):
                    value = bool(raw)
                elif f.type in (int, "int"):
                    value = int(raw)
                else:
                    value = float(raw)
            except (TypeError, ValueError):
                continue
            setattr(t, f.name, value)
        return t


@dataclass
class AppSettings:
    """Загальні налаштування: адаптер, порт, марка авто, тема, вибрані параметри."""
    adapter: str = "kkl"              # "kkl" | "elm_serial" | "elm_wifi"
    port: str = ""
    wifi_host: str = "192.168.0.10"
    wifi_port: int = 35000
    elm_baud: int = 38400
    elm_protocol: str = "0"           # 0 — автовизначення ELM327
    elm_timeout: float = 5.0          # секунди очікування відповіді ELM327
    brand: str = "auto"               # ключ профілю марки або "auto" (за VIN)
    theme: str = "dark"               # "dark" | "light"
    language: str = ""                # "uk" | "en"; порожньо — за мовою Windows
    live_pids: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        s = cls()
        for f in dataclasses.fields(cls):
            if f.name not in data:
                continue
            raw, default = data[f.name], getattr(s, f.name)
            try:
                if isinstance(default, list):
                    value = [int(x) for x in raw] if isinstance(raw, list) else default
                elif isinstance(default, int):
                    value = int(raw)
                elif isinstance(default, float):
                    value = float(raw)
                else:
                    value = str(raw)
            except (TypeError, ValueError):
                continue
            setattr(s, f.name, value)
        return s


def base_dir():
    """Файли програми лежать поруч із .exe або в корені проєкту."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def settings_path():
    return base_dir() / SETTINGS_FILE


def _read_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def load_all(path=None):
    """Повертає (Timing, AppSettings). Розуміє й старий файл lancer_obd_settings.json."""
    path = Path(path) if path else settings_path()
    data = _read_json(path)
    if data is None and not path.exists():
        legacy = _read_json(path.with_name(LEGACY_SETTINGS_FILE))
        if legacy is not None:
            return Timing.from_dict(legacy), AppSettings()
    if data is None:
        return Timing(), AppSettings()
    if "timing" in data or "app" in data:
        timing = data.get("timing") if isinstance(data.get("timing"), dict) else {}
        app = data.get("app") if isinstance(data.get("app"), dict) else {}
        return Timing.from_dict(timing), AppSettings.from_dict(app)
    return Timing.from_dict(data), AppSettings()


def save_all(timing, app, path=None):
    path = Path(path) if path else settings_path()
    data = {"timing": timing.as_dict(), "app": dataclasses.asdict(app)}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_timing(path=None):
    return load_all(path)[0]


def save_timing(timing, path=None):
    path = Path(path) if path else settings_path()
    app = load_all(path)[1] if path.exists() else AppSettings()
    return save_all(timing, app, path)
