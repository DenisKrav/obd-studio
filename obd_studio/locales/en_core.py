"""Англійський переклад (див. obd_studio/i18n.py)."""

EN = {
    "так": "yes",
    "ні": "no",
    "мс": "ms",
    # ── kline.py: кабель KKL ──
    "Параметри ініціалізації:": "Initialization parameters:",
    "Машина не відповіла жодним способом.\n\n"
    "Перевірте, що запалювання увімкнене, кабель щільно сидить у роз’ємі, "
    "і спробуйте ще раз. Якщо не вийде — збережіть журнал і надішліть його.":
        "The car did not respond to any connection method.\n\n"
        "Make sure the ignition is on and the cable is firmly seated in the connector, "
        "then try again. If it still fails, save the log and send it to us.",
    " — кабель не повертає надіслане: чи є живлення 12 В на роз’ємі (увімкнене запалювання)?":
        " — the cable does not echo what was sent: is there 12 V at the connector (ignition on)?",
    "← немає байта синхронізації 0x55": "← no 0x55 sync byte",
    "У налаштуваннях вимкнено всі способи підключення.":
        "All connection methods are disabled in Settings.",
    "Спершу натисніть «Підключитися».": "Press “Connect” first.",
    "Сесія могла завершитися — перепідключаюся…": "Session may have expired — reconnecting…",
    "   (виміряно на ПК: нуль {low:.1f} мс, від початку імпульсу до запиту {req:.1f} мс)":
        "   (measured on PC: low {low:.1f} ms, pulse start to request {req:.1f} ms)",
    "   (виміряно на ПК: луна 0x00 {echo} через {echo_ms:.1f} мс, від початку імпульсу до запиту "
    "{req:.1f} мс)":
        "   (measured on PC: 0x00 echo {echo} after {echo_ms:.1f} ms, pulse start to request "
        "{req:.1f} ms)",
    "   (0x55 прийшов через {ms:.0f} мс після адреси)": "   (0x55 arrived {ms:.0f} ms after address)",
    "← 55 {kb}  (синхронізація OK, ключові байти {kb})": "← 55 {kb}  (sync OK, key bytes {kb})",
    "KWP2000, швидкий старт": "KWP2000, fast init",
    "KWP2000, швидкий старт (спосіб 2)": "KWP2000, fast init (method 2)",
    "повільний старт 5 бод": "5-baud slow init",
    "Зв’язок із машиною втрачено. Натисніть «Підключитися» ще раз.":
        "Connection to the car was lost. Press “Connect” again.",
    "Порт {port} відкрито, {baud} бод": "Port {port} opened, {baud} baud",
    "(тиша)": "(silence)",
    "немає": "none",
    "← 55 {kb} (ключові байти неповні)": "← 55 {kb} (key bytes incomplete)",
    "── Спроба {n}/{total}: {name}": "── Attempt {n}/{total}: {name}",
    "   (луна не збіглася: {echo})": "   (echo mismatch: {echo})",
    "Блок відповів! Ключові байти: {kb}": "ECU responded! Key bytes: {kb}",
    "   (сторонній байт {byte})": "   (unexpected byte {byte})",
    "Пауза {pause:g} с перед наступною спробою…": "Waiting {pause:g} s before next attempt…",
    "Не вдалося відкрити {port}: {error}\n"
    "Можливо, порт зайнятий іншою програмою (наприклад, VCDS-Lite).":
        "Could not open {port}: {error}\n"
        "The port may be in use by another program (e.g. VCDS-Lite).",
    "Помилка порту: {error}": "Port error: {error}",
    "   Блок відмовив: сервіс {sid:02X}, причина {nrc:02X}":
        "   ECU rejected request: service {sid:02X}, reason {nrc:02X}",

    # ── elm327.py ──
    "Пошук протоколу і зв’язок із блоком керування…": "Searching for protocol and contacting the ECU…",
    "Блок керування не відповів.": "The ECU did not respond.",
    "Адаптер ELM327 не відповідає. Перевірте підключення.":
        "The ELM327 adapter is not responding. Check the connection.",
    "Адаптер ELM327 не відповідає.\n\n"
    "Перевірте, що вибрано правильний порт (для Bluetooth — вихідний COM-порт "
    "спареного адаптера) і що адаптер вставлено в роз’єм авто.":
        "The ELM327 adapter is not responding.\n\n"
        "Make sure the correct port is selected (for Bluetooth, the outgoing COM port "
        "of the paired adapter) and that the adapter is plugged into the car's connector.",
    "Адаптер не зміг підключитися до блока керування (UNABLE TO CONNECT).":
        "The adapter could not connect to the ECU (UNABLE TO CONNECT).",
    "{name} через {version}": "{name} via {version}",
    "Не вдалося відкрити адаптера Wi-Fi: {error}\n"
    "Перевірте, що ноутбук підключено до Wi-Fi мережі адаптера.":
        "Could not open the Wi-Fi adapter: {error}\n"
        "Make sure the laptop is connected to the adapter's Wi-Fi network.",
    "Не вдалося відкрити порту {port}: {error}\n"
    "Можливо, порт зайнятий іншою програмою або адаптер не спарено.":
        "Could not open port {port}: {error}\n"
        "The port may be in use by another program, or the adapter is not paired.",
    "Адаптер: {version}": "Adapter: {version}",
    "Блок керування не відповів на запит (NO DATA).": "The ECU did not answer the request (NO DATA).",
    "Увімкніть запалювання, перевірте контакт у роз’ємі й спробуйте ще раз. "
    "Якщо авто не підтримує OBD-II, зв’язку не буде.":
        "Turn the ignition on, check the connector contact and try again. "
        "If the car does not support OBD-II, it cannot connect.",
    "Відкрито {url}": "Opened {url}",
    "Відкрито {url}, {baud} бод": "Opened {url}, {baud} baud",
    "Немає відповіді ELM327 на {baud} бод": "No ELM327 response at {baud} baud",
    "   Адаптер повідомив про помилку: {text}": "   Adapter reported an error: {text}",
    "Зв’язок з адаптером втрачено: {error}": "Connection to the adapter was lost: {error}",
    "невідомий протокол": "unknown protocol",

    # ── obd.py: готовність ──
    "Готовність систем самодіагностики:": "Self-test monitor readiness:",
    "«НЕ готово» буває після стирання помилок або відключення акумулятора: "
    "система ще не завершила самоперевірку. Після кількох днів звичайної їзди "
    "статус зазвичай змінюється на «готово».":
        "“NOT ready” is normal after clearing codes or disconnecting the battery: "
        "the system has not finished its self-test yet. After a few days of normal driving "
        "the status usually changes to “ready”.",
    "Лампа Check Engine: {state}": "Check Engine light: {state}",
    "Кількість підтверджених помилок: {n}": "Confirmed trouble codes: {n}",
    "УВІМКНЕНА": "ON",
    "вимкнена": "off",
    "готово": "ready",
    "НЕ готово": "NOT ready",
    "не готово": "not ready",

    # ── report.py ──
    "Звіт діагностики": "Diagnostic Report",
    "Авто": "Vehicle",
    "авто": "vehicle",
    "Протокол": "Protocol",
    "Адаптер": "Adapter",
    "не повідомлено блоком": "not reported by the ECU",
    "ID калібрування": "Calibration ID",
    "Автомобіль і з’єднання": "Vehicle and Connection",
    "Коди помилок": "Trouble Codes",
    "Серйозність — орієнтовна оцінка за типом коду. Остаточний діагноз ставить фахівець.":
        "Severity is a rough estimate based on the code type. "
        "A final diagnosis should be made by a mechanic.",
    "Код": "Code",
    "Тип": "Type",
    "Опис": "Description",
    "Серйозність": "Severity",
    "Check Engine і готовність систем": "Check Engine and Readiness",
    "Система": "System",
    "Стан": "Status",
    "Параметр": "Parameter",
    "Значення": "Value",
    "Останні дані наживо": "Latest Live Data",
    "Помилок не знайдено": "No trouble codes found",
    "Коди помилок не зчитувалися.": "Trouble codes were not read.",
    "Лампа Check Engine: {state} · підтверджених помилок: {n}":
        "Check Engine light: {state} · confirmed codes: {n}",
    "Стоп-кадр (код {code})": "Freeze Frame (code {code})",
    "Збережена": "Stored",
    "Очікує підтвердження": "Pending",
    "Постійна": "Permanent",
    "висока": "High",
    "середня": "Medium",
    "низька": "Low",

    # ── ui/controller.py ──
    "Кабель KKL (K-лінія)": "KKL cable (K-line)",
    "Авто не визначено": "Vehicle not identified",
    "Підключення…": "Connecting…",
    "Відключення…": "Disconnecting…",
    "Зчитування кодів помилок…": "Reading trouble codes…",
    "Зчитування готовності систем…": "Reading readiness…",
    "Зчитування стоп-кадру…": "Reading freeze frame…",
    "Зчитування даних авто…": "Reading vehicle info…",
    "Стирання кодів помилок…": "Clearing codes…",
    "Повне сканування…": "Full scan…",
    "Дані наживо": "Live Data",
    "Немає з’єднання з авто. Спершу підключіться на сторінці «Підключення».":
        "Not connected to the car. Connect first on the “Connection” page.",
    "Блок не відповів на запит 03, але за PID 01 підтверджених помилок 0 — "
    "вважаю, що збережених кодів немає":
        "ECU did not answer mode 03, but PID 01 reports 0 confirmed codes — "
        "assuming no stored codes",
    "Коди помилок стерто": "Trouble codes cleared",
    "Відключено": "Disconnected",
    "Блок не відповів на запит помилок. Спробуйте ще раз.":
        "The ECU did not answer the trouble code request. Please try again.",
    "Блок не відповів на запит стану систем.": "The ECU did not answer the readiness request.",
    "Блок не підтвердив стирання. Переконайтеся, що двигун заглушено.":
        "The ECU did not confirm clearing. Make sure the engine is off.",
    "Виберіть COM-порт кабелю KKL.": "Select the COM port of the KKL cable.",
    "Виберіть COM-порт адаптера ELM327.": "Select the COM port of the ELM327 adapter.",
    "Підключення: {adapter}": "Connecting: {adapter}",
    "З’єднання встановлено: {protocol}": "Connected: {protocol}",
    "Блок підтримує {n} параметрів режиму 01": "ECU supports {n} mode 01 parameters",
    "Підтримка сесії не вдалася: {error}": "Session keep-alive failed: {error}",
    "ПОМИЛКА: {error}": "ERROR: {error}",
    "Неочікувана помилка: {error}\n\nЗбережіть журнал і надішліть його.":
        "Unexpected error: {error}\n\nPlease save the log and send it to us.",
    "(дані наживо: подальший обмін у журнал не пишеться)":
        "(live data: further traffic is not written to the log)",
    "Зв’язок із машиною втрачено.": "Connection to the car was lost.",
}
