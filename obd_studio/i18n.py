"""Мови програми: українська (основна, рядки в коді) та англійська (словники в locales/).

Правила:
- кожен видимий користувачеві рядок обгортається в tr("український текст");
- змінні частини — лише через format: tr("Знайдено кодів: {n}").format(n=3);
- рядки з таблиць даних (назви параметрів, марок тощо) лишаються українськими
  в таблицях і перекладаються там, де показуються: tr(pid.name);
- англійський переклад — у словниках obd_studio/locales/en_*.py: {"укр": "eng"}.
Якщо перекладу немає, показується український текст (тест test_i18n це ловить).
"""

import locale

LANGUAGES = {"uk": "Українська", "en": "English"}

_lang = "uk"
_en = None


def _english():
    global _en
    if _en is None:
        table = {}
        from .locales import en_core, en_data, en_ui
        for mod in (en_core, en_data, en_ui):
            table.update(mod.EN)
        _en = table
    return _en


def set_language(code):
    global _lang
    _lang = code if code in LANGUAGES else "uk"


def language():
    return _lang


def tr(text):
    if _lang == "uk" or not text:
        return text
    return _english().get(text, text)


def system_language():
    """Мова Windows: українська → "uk", будь-яка інша → "en"."""
    try:
        name = (locale.getlocale()[0] or locale.getdefaultlocale()[0] or "").lower()
    except (ValueError, TypeError):
        name = ""
    return "uk" if name.startswith(("uk", "ukrainian")) else "en"
