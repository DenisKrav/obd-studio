# Changelog / Історія змін

[English](#english) | [Українська](#українська)

## English

All notable changes to OBD Studio. Versions follow `X.Y.Z`: `X` — major changes,
`Y` — new features, `Z` — fixes. Downloads: [Releases](https://github.com/DenisKrav/obd-studio/releases).

### 1.1.0 — upcoming

**New**

- English interface. Switch the language in **Settings → Appearance → Language**. On first
  start the app picks the language from Windows: Ukrainian Windows → Ukrainian, any other →
  English.
- Documentation in English and Ukrainian: README and a step-by-step
  [user guide](docs/user-guide.en.md).

### 1.0.0 — first release

- Diagnostics over standard OBD-II for any make, with three adapter types: KKL cable (K-line:
  ISO 9141-2, KWP2000), ELM327 USB / Bluetooth and ELM327 Wi-Fi (all OBD-II protocols,
  including CAN).
- **Overview**: make and year from the VIN, Check Engine light, number of codes, readiness,
  battery voltage (ELM327), gauges, scan history.
- **Full Scan** in one click: readiness, stored, pending and permanent (CAN) codes, freeze frame.
- **Trouble Codes** with descriptions (over 250 codes), type and estimated severity; hints for
  manufacturer codes that take the car make into account. Clearing codes (mode 04) only after
  confirmation.
- **Live Data**: over 50 parameters, chart, mini-charts, parameter picker, CSV recording.
- **Freeze Frame** (mode 02) and **Vehicle Info** (mode 09): VIN, calibration ID, CVN,
  control unit name; make, region and model year decoded from the VIN.
- HTML report for printing or PDF, technical log for troubleshooting.
- K-line timing settings, dark and light themes.
- Only standard read-only OBD-II requests (modes 01, 02, 03, 07, 09, 0A); no manufacturer commands.
- Single-file `OBDStudio.exe`, no installation; settings and history are stored next to it.
- K-line (KKL cable): the session is kept alive while the app is idle — a harmless `01 00`
  read request is sent every 2 s. The interval is configurable in
  **Settings → KKL cable — timing → Communication**; 0 turns it off.
- K-line: the app waits up to 1 s for replies to trouble-code requests. If the control unit
  stays silent on mode 03 but itself reported 0 confirmed codes via PID 01, this is treated as
  "no stored codes" instead of an error.
- Dropdowns and number fields don't change their value when you scroll the page with the
  mouse wheel.
- Dropdowns show an arrow.

---

## Українська

Усі помітні зміни OBD Studio. Номер версії `X.Y.Z`: `X` — великі зміни, `Y` — нові функції,
`Z` — виправлення. Завантаження: [сторінка випусків](https://github.com/DenisKrav/obd-studio/releases).

### 1.1.0 — готується

**Нове**

- Англійський інтерфейс. Мову можна змінити в **«Налаштування» → «Вигляд» → «Мова»**. Під час
  першого запуску програма бере мову Windows: українська Windows — українська мова, будь-яка
  інша — англійська.
- Документація українською та англійською: README і покроковий
  [посібник користувача](docs/user-guide.uk.md).

### 1.0.0 — перший випуск

- Діагностика через стандартний OBD-II для будь-якої марки з трьома типами адаптерів: кабель
  KKL (K-лінія: ISO 9141-2, KWP2000), ELM327 USB / Bluetooth і ELM327 Wi-Fi (усі протоколи
  OBD-II, зокрема CAN).
- **Огляд**: марка й рік за VIN, лампа Check Engine, кількість помилок, готовність систем,
  напруга мережі (ELM327), стрілочні прилади, історія сканувань.
- **Повне сканування** одним натисканням: готовність, збережені коди, коди, що очікують
  підтвердження, постійні (CAN), стоп-кадр.
- **Коди помилок** з описом (понад 250 кодів), типом і орієнтовною серйозністю; підказки для
  кодів виробника з урахуванням марки. Стирання кодів (режим 04) — лише після підтвердження.
- **Дані наживо**: понад 50 параметрів, графік, міні-графіки, вибір параметрів, запис у CSV.
- **Стоп-кадр** (режим 02) і **Про авто** (режим 09): VIN, ID калібрування, CVN, назва блока;
  марка, регіон і модельний рік за VIN.
- Звіт HTML для друку або PDF, технічний журнал для пошуку проблем.
- Часові параметри K-лінії, темна й світла теми.
- Лише стандартні запити OBD-II на читання (режими 01, 02, 03, 07, 09, 0A); заводських команд
  немає.
- Один файл `OBDStudio.exe` без встановлення; налаштування та історія зберігаються поруч із ним.
- K-лінія (кабель KKL): поки програма простоює, сесія підтримується — кожні 2 с надсилається
  безпечний запит на читання `01 00`. Інтервал змінюється в **«Налаштування» → «Кабель KKL —
  часові параметри» → «Обмін»**; 0 вимикає підтримку.
- K-лінія: відповіді на запит кодів помилок програма чекає до 1 с. Якщо блок мовчить на запит
  режиму 03, але сам повідомив через PID 01, що підтверджених помилок 0, це вважається
  «збережених кодів немає», а не помилкою.
- Випадні списки й числові поля не змінюють значення, коли прокручуєте сторінку
  коліщатком миші.
- Випадні списки мають стрілку.