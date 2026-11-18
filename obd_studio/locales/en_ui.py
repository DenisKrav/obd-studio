"""Англійський переклад (див. obd_studio/i18n.py)."""

EN = {
    # ── бокове меню, рядок стану, вікно ──
    "Діагностика OBD-II": "OBD-II Diagnostics",
    "Діагностика": "Diagnostics",
    "Авто": "Vehicle",
    "Система": "System",
    "Огляд": "Overview",
    "Коди помилок": "Trouble Codes",
    "Дані наживо": "Live Data",
    "Готовність систем": "Readiness",
    "Стоп-кадр": "Freeze Frame",
    "Про авто": "Vehicle Info",
    "Підключення": "Connection",
    "Журнал": "Log",
    "Налаштування": "Settings",
    "Готово": "Ready",
    "Не готово": "Not ready",
    "Підключено": "Connected",
    "Не підключено": "Not connected",
    "Підключення…": "Connecting…",
    "Адаптер не вибрано": "No adapter selected",
    "Помилка": "Error",
    "Помилка: {text}": "Error: {text}",
    "Гаразд": "OK",
    "Відкрити журнал": "Open Log",
    "Скасувати": "Cancel",
    "Коди помилок стерто. Вимкніть і знову увімкніть запалювання.":
        "Trouble codes cleared. Turn the ignition off and on again.",
    "Сканування завершено: помилок не знайдено": "Scan complete: no trouble codes found",
    "Сканування завершено: знайдено кодів: {n}": "Scan complete: codes found: {n}",
    "Параметри збережено. Вони діятимуть з наступного підключення.":
        "Settings saved. They take effect from the next connection.",
    "Звіт збережено: {path}": "Report saved: {path}",
    "Журнал збережено: {path}": "Log saved: {path}",
    "Файл налаштувань: {path}": "Settings file: {path}",
    "Порт {port}: {desc}": "Port {port}: {desc}",
    "Не вдалося зберегти історію: {error}": "Could not save history: {error}",
    "Не вдалося зберегти налаштування: {error}": "Could not save settings: {error}",
    "Нові параметри K-лінії (діють з наступного підключення):":
        "New K-line timing (takes effect from the next connection):",
    "Запис CSV зупинено": "CSV recording stopped",
    "Запис CSV: {path}": "Recording CSV: {path}",
    "Записувати дані у файл": "Record Data to File",
    "Зберегти звіт": "Save Report",
    "Текстовий файл": "Text file",
    "Час": "Time",
    "Коди": "Codes",
    "Налаштування: {settings}\nІсторія: {history}": "Settings: {settings}\nHistory: {history}",
    "{app} {version} — універсальна діагностика OBD-II для кабелю KKL і адаптерів ELM327. Програма "
    "надсилає лише стандартні запити OBD-II на читання; єдина команда, що змінює стан блока, — "
    "стирання кодів помилок (режим 04), і лише за вашим підтвердженням.":
        "{app} {version} is universal OBD-II diagnostics for KKL cables and ELM327 adapters. The app "
        "sends only standard read-only OBD-II requests; the only command that changes the control "
        "unit's state is clearing trouble codes (mode 04), and only after you confirm it.",

    # ── спільне ──
    "Підключитися": "Connect",
    "Відключитися": "Disconnect",
    "Повне сканування": "Full Scan",
    "Зчитати": "Read",
    "Стерти коди": "Clear Codes",
    "Звіт": "Report",
    "Запустити": "Start",
    "Зупинити": "Stop",
    "Параметри": "Parameters",
    "Запис CSV": "Record CSV",
    "Зберегти журнал": "Save Log",
    "Оновити": "Refresh",
    "Стандартні значення": "Restore Defaults",
    "Зберегти": "Save",
    "Копіювати": "Copy",
    "Очистити": "Clear",
    "н/д": "n/a",
    "або": "or",
    "с": "s",
    "мс": "ms",

    # ── Огляд ──
    "Стан авто та основні показники одним поглядом": "Vehicle status and key readings at a glance",
    "Готовність систем, усі коди помилок і стоп-кадр": "Readiness, all trouble codes and freeze frame",
    "Авто не підключено": "No vehicle connected",
    "Підключіть адаптер до роз’єму OBD-II і натисніть «Підключитися»":
        "Plug the adapter into the OBD-II port and click “Connect”",
    "Підключіть адаптер до роз’єму OBD-II, увімкніть запалювання й натисніть «Підключитися»":
        "Plug the adapter into the OBD-II port, turn the ignition on and click “Connect”",
    "Напруга мережі": "Battery voltage",
    "Прилади": "Gauges",
    "Оновлюються, коли запущено дані наживо": "Updated while live data is running",
    "Останні сканування": "Recent Scans",
    "Зберігаються у файлі obd_studio_history.json": "Stored in obd_studio_history.json",
    "помилок немає": "no trouble codes",
    "Ще не було жодного сканування": "No scans yet",
    "Горить": "On",
    "Не горить": "Off",
    "Підтверджених помилок: {n}": "Confirmed faults: {n}",
    "систем завершили самоперевірку": "monitors have completed self-tests",
    "Дані з’являться після підключення": "Data appears after connecting",
    "немає помилок": "no trouble codes",
    "збережених {stored}, очікують {pending}": "{stored} stored, {pending} pending",
    "Натисніть «Повне сканування»": "Click “Full Scan”",
    "Адаптер KKL напругу не міряє": "The KKL adapter can't measure voltage",
    "двигун працює, зарядка є": "engine running, charging",
    "норма без зарядки": "normal, not charging",
    "акумулятор розряджений": "battery low",
    "{v} В": "{v} V",

    # ── Підключення ──
    "Виберіть адаптер, порт і марку авто": "Choose the adapter, port and vehicle make",
    "Адаптер": "Adapter",
    "Чим ноутбук підключено до діагностичного роз’єму авто":
        "How your laptop is connected to the vehicle's diagnostic port",
    "Кабель KKL": "KKL cable",
    "VAG KKL 409.1 та подібні\nK-лінія: ISO 9141-2, KWP2000": "VAG KKL 409.1 and similar\nK-line: ISO 9141-2, KWP2000",
    "Усі протоколи OBD-II,\nзокрема CAN (авто після 2008)": "All OBD-II protocols,\nincluding CAN (cars after 2008)",
    "Усі протоколи OBD-II\nчерез Wi-Fi мережу адаптера": "All OBD-II protocols\nover the adapter's Wi-Fi network",
    "Оновити список портів": "Refresh port list",
    "COM-порт": "COM port",
    "Адреса адаптера": "Adapter address",
    "Протокол": "Protocol",
    "Марка авто": "Vehicle make",
    "Програма працює зі стандартним OBD-II для будь-якої марки. Профіль марки підказує, який "
    "адаптер потрібен, і уточнює описи кодів.":
        "The app works with standard OBD-II on any make. The make profile suggests which adapter "
        "you need and refines code descriptions.",
    "Автовизначення за VIN": "Detect from VIN",
    "Перед підключенням": "Before Connecting",
    "1.  Вставте адаптер у роз’єм OBD-II (зазвичай під кермом зліва).\n"
    "2.  Увімкніть запалювання. Двигун можна не заводити.\n"
    "3.  Закрийте інші діагностичні програми (VCDS-Lite, Torque тощо) — вони займають порт.\n"
    "4.  Для Bluetooth спершу спарте адаптер у Windows (PIN зазвичай 1234 або 0000).\n"
    "5.  Кабелю KKL потрібні 12 В від авто: без запалювання він мовчить.":
        "1.  Plug the adapter into the OBD-II port (usually under the dashboard, driver's side).\n"
        "2.  Turn the ignition on. You don't need to start the engine.\n"
        "3.  Close other diagnostic apps (VCDS-Lite, Torque, etc.): they keep the port busy.\n"
        "4.  For Bluetooth, pair the adapter in Windows first (PIN is usually 1234 or 0000).\n"
        "5.  The KKL cable needs 12 V from the car: with the ignition off it stays silent.",
    "Портів не знайдено — підключіть адаптер": "No ports found. Plug in the adapter",
    "Кабель KKL працює лише з K-лінією (переважно авто до 2008 р.). Програма сама по черзі пробує "
    "швидкий і повільний старт. Часові параметри — у «Налаштуваннях».":
        "The KKL cable works only with the K-line (mostly cars before 2008). The app tries fast and "
        "slow init in turn. Timing parameters are in Settings.",
    "Для USB-адаптера виберіть його COM-порт. Для Bluetooth — вихідний (Outgoing) COM-порт "
    "спареного адаптера. Швидкість підбирається автоматично.":
        "For a USB adapter, choose its COM port. For Bluetooth, choose the Outgoing COM port of the "
        "paired adapter. The baud rate is detected automatically.",
    "Підключіть ноутбук до Wi-Fi мережі адаптера (часто «WiFi_OBDII»). Типова адреса — "
    "192.168.0.10, порт 35000.":
        "Connect your laptop to the adapter's Wi-Fi network (often “WiFi_OBDII”). The usual address is "
        "192.168.0.10, port 35000.",
    "Марку буде визначено за VIN, якщо блок керування його повідомить (зазвичай авто після ~2005 р.). "
    "Інакше виберіть марку вручну.":
        "The make will be detected from the VIN if the control unit reports it (usually cars after "
        "~2005). Otherwise, choose the make manually.",
    "Підключено: {protocol}": "Connected: {protocol}",
    "Підключення може тривати до 20 секунд…": "Connecting can take up to 20 seconds…",

    # ── Коди помилок ──
    "Збережені, ті, що очікують підтвердження, і постійні (лише CAN)":
        "Stored, pending confirmation, and permanent (CAN only)",
    "Збережені": "Stored",
    "Очікують підтвердження": "Pending",
    "Постійні": "Permanent",
    "Збережена": "Stored",
    "Очікує": "Pending",
    "Постійна": "Permanent",
    "Висока": "High",
    "Середня": "Medium",
    "Низька": "Low",
    "Зберегти HTML-звіт": "Save an HTML report",
    "Код": "Code",
    "Тип": "Type",
    "Опис": "Description",
    "Серйозність": "Severity",
    "Коди ще не зчитано": "Codes not read yet",
    "Підключіться до авто й натисніть «Зчитати». Програма покаже коди з описом українською та "
    "орієнтовною серйозністю.":
        "Connect to the vehicle and click “Read”. The app will show the codes with a plain-language "
        "description and an estimated severity.",
    "Стирання кодів не усуває несправність: якщо вона є, код повернеться. Також скинуться статуси "
    "готовності систем самодіагностики (це важливо перед техоглядом).":
        "Clearing codes doesn't fix the fault: if it's still there, the code will come back. It also "
        "resets the readiness monitors (this matters before an emissions inspection).",
    "Стерти коди помилок?": "Clear Trouble Codes?",
    "Стерти всі коди помилок і стоп-кадр?": "Clear all trouble codes and the freeze frame?",
    "Перед стиранням заглушіть двигун, запалювання залиште увімкненим.\n\nСтирання не усуває "
    "несправність. Також скинуться статуси готовності систем самодіагностики.":
        "Before clearing, switch the engine off and leave the ignition on.\n\nClearing doesn't fix the "
        "fault. It also resets the readiness monitors.",
    "Стерти": "Clear",
    "за даними PID 01 (блок не відповів на запит кодів)": "from PID 01 (the unit didn't answer the code request)",
    "підтверджені, запалюють Check Engine": "confirmed, turn on Check Engine",
    "виявлені в поточному циклі поїздки": "detected during the current drive cycle",
    "блок не підтримує цей запит": "the unit doesn't support this request",
    "не стираються вручну, зникають самі": "can't be cleared manually, go away on their own",
    "лише для авто з CAN": "CAN vehicles only",
    "Помилок не знайдено": "No Trouble Codes Found",
    "Блок керування не повідомив жодного коду помилки.": "The control unit reported no trouble codes.",
    "код виробника": "manufacturer code",

    # ── Дані наживо ──
    "Параметри для відображення": "Parameters to Display",
    "Виберіть параметри. Що менше параметрів, то частіше вони оновлюються (особливо на K-лінії).":
        "Choose parameters. The fewer you pick, the faster they update (especially on the K-line).",
    "Блок не повідомив, що підтримує, тож показано всі параметри.":
        "The unit didn't report what it supports, so all parameters are shown.",
    "Пошук…": "Search…",
    "Усі": "All",
    "Жодного": "None",
    "Застосувати": "Apply",
    "Параметри двигуна в реальному часі. Клацніть плитку, щоб показати її на графіку":
        "Engine parameters in real time. Click a tile to show it on the chart",
    "Записувати значення у файл CSV": "Record values to a CSV file",
    "{rate} оновл./с": "{rate} updates/s",
    "Графік": "Chart",
    "зараз": "now",
    "-{sec} с": "-{sec} s",
    "Запустіть дані наживо — тут з’явиться графік": "Start live data and the chart will appear here",

    # ── Готовність ──
    "Лампа Check Engine і статус самоперевірок (монітори OBD-II)":
        "Check Engine light and self-test status (OBD-II monitors)",
    "Підтверджених помилок": "Confirmed faults",
    "Готово систем": "Monitors ready",
    "Монітори самодіагностики": "Readiness Monitors",
    "Стан": "Status",
    "Дані ще не зчитано": "No data read yet",
    "Підключіться до авто — стан систем зчитується автоматично.":
        "Connect to the vehicle: readiness is read automatically.",
    "«Не готово» буває після стирання помилок або відключення акумулятора: система ще не завершила "
    "самоперевірку. Після кількох днів звичайної їзди статус зазвичай змінюється на «готово». Для "
    "техогляду зазвичай потрібно, щоб були готові всі системи (або всі, крім однієї).":
        "“Not ready” is normal after clearing codes or disconnecting the battery: the monitor hasn't "
        "finished its self-test yet. After a few days of normal driving it usually changes to “ready”. "
        "An emissions inspection usually requires all monitors (or all but one) to be ready.",
    "дизельний двигун": "diesel engine",
    "бензиновий двигун": "petrol engine",

    # ── Стоп-кадр ──
    "Значення датчиків у момент, коли блок зафіксував помилку (режим 02)":
        "Sensor values at the moment the unit logged a fault (mode 02)",
    "Параметр": "Parameter",
    "Значення": "Value",
    "Стоп-кадр ще не зчитано": "Freeze frame not read yet",
    "Стоп-кадр зберігається разом із першою підтвердженою помилкою. Він допомагає зрозуміти умови, "
    "за яких виникла несправність.":
        "A freeze frame is stored with the first confirmed fault. It helps you understand the "
        "conditions in which the fault occurred.",
    "Стоп-кадру немає": "No Freeze Frame",
    "Блок керування не зберігав стоп-кадр — зазвичай це означає, що підтверджених помилок немає.":
        "The control unit hasn't stored a freeze frame, which usually means there are no confirmed faults.",
    "Код {code}": "Code {code}",

    # ── Про авто ──
    "VIN, ідентифікатори прошивки та дані блока керування (режим 09)":
        "VIN, software IDs and control unit data (mode 09)",
    "Ідентифікація": "Identification",
    "Марка (за VIN)": "Make (from VIN)",
    "Модельний рік": "Model year",
    "Регіон виробництва": "Region of manufacture",
    "Код виробника (WMI)": "Manufacturer code (WMI)",
    "ID калібрування": "Calibration ID",
    "Блок керування": "Control unit",
    "Підтримуваних параметрів": "Supported parameters",
    "Порада щодо адаптера": "Adapter Tip",
    "Порада щодо адаптера — {brand}": "Adapter Tip: {brand}",
    "VIN невідомий": "VIN unknown",
    "Блок керування не підтримує режим 09 — так буває в авто, вироблених до ~2005 р. для "
    "європейського ринку. Марку можна вибрати вручну на сторінці «Підключення».":
        "The control unit doesn't support mode 09. This is common on cars built for the European "
        "market before ~2005. You can choose the make manually on the Connection page.",
    "Натисніть «Зчитати», щоб отримати VIN і дані блока керування.":
        "Click “Read” to get the VIN and control unit data.",

    # ── Журнал ──
    "Технічний журнал": "Technical Log",
    "Кожен надісланий і отриманий байт. Надішліть цей журнал, якщо щось не працює":
        "Every byte sent and received. Send this log if something doesn't work",

    # ── Налаштування ──
    "Вигляд програми, мова та часові параметри зв’язку": "Appearance, language and communication timing",
    "Вигляд": "Appearance",
    "Тема": "Theme",
    "Темна": "Dark",
    "Світла": "Light",
    "Мова": "Language",
    "Параметри для адаптерів ELM327": "Settings for ELM327 adapters",
    "Очікування відповіді": "Response timeout",
    "Початкова швидкість порту": "Initial baud rate",
    "{baud} бод": "{baud} baud",
    "Якщо адаптер не відповідає на вибраній швидкості, програма по черзі пробує інші.":
        "If the adapter doesn't answer at the selected rate, the app tries the others in turn.",
    "Кабель KKL — часові параметри": "KKL cable — timing",
    "Змінюйте, лише якщо машина не відповідає. Нові значення діють з наступного підключення. Усі "
    "тривалості — у мілісекундах.":
        "Change these only if the car doesn't respond. New values take effect from the next "
        "connection. All durations are in milliseconds.",
    "Способи підключення": "Connection methods",
    "Швидкий старт": "Fast init",
    "Повільний старт": "Slow init",
    "Обмін": "Communication",
    "Загальне": "General",
    "{unit}   (стандартно {default})": "{unit}   (default {default})",
    "Некоректне значення: {field}": "Invalid value: {field}",
    "Про програму": "About",
}
