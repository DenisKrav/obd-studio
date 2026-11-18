"""Звіт про діагностику у форматі HTML (відкривається в будь-якому браузері, друкується в PDF)."""

import html

from . import APP_NAME, __version__
from .dtc import describe_dtc, dtc_severity
from .i18n import language, tr
from .pids import PIDS, format_value

KIND_LABEL = {"stored": "Збережена", "pending": "Очікує підтвердження", "permanent": "Постійна"}
SEVERITY_LABEL = {"high": "висока", "medium": "середня", "low": "низька"}

_CSS = """
body{font-family:'Segoe UI',system-ui,sans-serif;color:#1b1f27;background:#f4f6fa;margin:0;padding:32px}
.wrap{max-width:880px;margin:0 auto;background:#fff;border-radius:14px;padding:32px 40px;
box-shadow:0 4px 24px rgba(20,30,60,.08)}
h1{margin:0 0 4px;font-size:26px}h2{font-size:17px;margin:28px 0 10px;color:#2a3242;
border-bottom:1px solid #e3e7ef;padding-bottom:6px}
.muted{color:#6b7385}.grid{display:grid;grid-template-columns:180px 1fr;gap:6px 16px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:7px 8px;
border-bottom:1px solid #edf0f5}th{color:#6b7385;font-weight:600}
.pill{display:inline-block;padding:2px 9px;border-radius:99px;font-size:12px;font-weight:600}
.high{background:#fde2e1;color:#b42318}.medium{background:#fef0c7;color:#93370d}
.low{background:#e0f2fe;color:#075985}.ok{background:#dcfae6;color:#067647}
.code{font-family:Consolas,monospace;font-weight:700}
"""


def _row(label, value):
    return f"<div class='muted'>{html.escape(label)}</div><div>{html.escape(str(value))}</div>"


def build_html(data):
    """data: dict з ключами date, vehicle, vin_info, protocol, adapter, dtcs{kind: [codes]},
    readiness (dict або None), freeze (code, {pid: value}) або None, live {pid: value}, brand."""
    e = html.escape
    brand = data.get("brand")
    title = tr("Звіт діагностики")
    out = [f"<!doctype html><html lang='{language()}'><meta charset='utf-8'>"
           f"<title>{e(title)} — {e(data.get('vehicle') or tr('авто'))}</title>"
           f"<style>{_CSS}</style><body><div class='wrap'>",
           f"<h1>{e(title)}</h1><div class='muted'>{e(data.get('date', ''))} · "
           f"{APP_NAME} {__version__}</div>",
           f"<h2>{e(tr('Автомобіль і з’єднання'))}</h2><div class='grid'>"]
    out.append(_row(tr("Авто"), data.get("vehicle") or "—"))
    info = data.get("vin_info") or {}
    out.append(_row("VIN", info.get("vin") or tr("не повідомлено блоком")))
    if info.get("calibration_ids"):
        out.append(_row(tr("ID калібрування"), ", ".join(info["calibration_ids"])))
    out.append(_row(tr("Протокол"), data.get("protocol") or "—"))
    out.append(_row(tr("Адаптер"), data.get("adapter") or "—"))
    out.append("</div>")

    out.append(f"<h2>{e(tr('Коди помилок'))}</h2>")
    rows = [(kind, c) for kind in ("stored", "pending", "permanent")
            for c in (data.get("dtcs") or {}).get(kind, [])]
    if rows:
        out.append(f"<table><tr><th>{e(tr('Код'))}</th><th>{e(tr('Тип'))}</th><th>{e(tr('Опис'))}</th>"
                   f"<th>{e(tr('Серйозність'))}</th></tr>")
        for kind, c in rows:
            sev = dtc_severity(c)
            out.append(f"<tr><td class='code'>{e(c)}</td><td>{e(tr(KIND_LABEL[kind]))}</td>"
                       f"<td>{e(describe_dtc(c, brand))}</td>"
                       f"<td><span class='pill {sev}'>{e(tr(SEVERITY_LABEL[sev]))}</span></td></tr>")
        out.append("</table>")
    elif data.get("dtcs") is not None:
        out.append(f"<p><span class='pill ok'>{e(tr('Помилок не знайдено'))}</span></p>")
    else:
        out.append(f"<p class='muted'>{e(tr('Коди помилок не зчитувалися.'))}</p>")

    rd = data.get("readiness")
    if rd:
        out.append(f"<h2>{e(tr('Check Engine і готовність систем'))}</h2>")
        mil = f"<span class='pill high'>{e(tr('УВІМКНЕНА'))}</span>" if rd["mil"] else \
            f"<span class='pill ok'>{e(tr('вимкнена'))}</span>"
        out.append("<p>" + e(tr("Лампа Check Engine: {state} · підтверджених помилок: {n}"))
                   .format(state=mil, n=rd["dtc_count"]) + "</p>")
        out.append(f"<table><tr><th>{e(tr('Система'))}</th><th>{e(tr('Стан'))}</th></tr>")
        for name, ok in rd["monitors"]:
            pill = f"<span class='pill ok'>{e(tr('готово'))}</span>" if ok else \
                f"<span class='pill medium'>{e(tr('не готово'))}</span>"
            out.append(f"<tr><td>{e(tr(name))}</td><td>{pill}</td></tr>")
        out.append("</table>")

    fr = data.get("freeze")
    if fr:
        code, values = fr
        out.append(f"<h2>{e(tr('Стоп-кадр (код {code})').format(code=code))}</h2>"
                   f"<table><tr><th>{e(tr('Параметр'))}</th><th>{e(tr('Значення'))}</th></tr>")
        for pid, v in values.items():
            out.append(f"<tr><td>{e(tr(PIDS[pid].name))}</td><td>{e(format_value(pid, v))}</td></tr>")
        out.append("</table>")

    live = data.get("live")
    if live:
        out.append(f"<h2>{e(tr('Останні дані наживо'))}</h2>"
                   f"<table><tr><th>{e(tr('Параметр'))}</th><th>{e(tr('Значення'))}</th></tr>")
        for pid, v in live.items():
            out.append(f"<tr><td>{e(tr(PIDS[pid].name))}</td><td>{e(format_value(pid, v))}</td></tr>")
        out.append("</table>")

    out.append("<p class='muted' style='margin-top:28px;font-size:12px'>"
               + e(tr("Серйозність — орієнтовна оцінка за типом коду. "
                      "Остаточний діагноз ставить фахівець."))
               + "</p></div></body></html>")
    return "\n".join(out)
