#!/usr/bin/env python3
"""Русификация панелей бара Omarchy (календарь, сеть/Wi-Fi, Bluetooth, звук, питание, экран, Wi-Fi QR).

Встроенные плагины лежат в /usr/share/omarchy/ и правке не подлежат, поэтому скрипт:
  1. клонирует плагин (`omarchy plugin clone omarchy.<имя>`), если клона ещё нет;
  2. заменяет в QML/JS клона точные строковые литералы "English" -> "Русский".

Литералы, стоящие в сравнениях (===, !==, indexOf(, case ...), не трогаются, чтобы не сломать логику.
Внутренние ключи (DHCP/Cloudflare/Google/Custom и т.п.) в словарях нет намеренно.
Скрипт идемпотентен. ВАЖНО: клон не получает обновления оригинального плагина; после
`omarchy update` можно удалить ~/.config/omarchy/plugins/<user>.<имя> и запустить скрипт заново.
"""
import getpass
import json
import re
import subprocess
import sys
from pathlib import Path

PLUGINS_DIR = Path.home() / ".config/omarchy/plugins"
USER = getpass.getuser()

TRANSLATIONS = {
    "clock": {
        "Back to today": "Сегодня", "Next month": "Следующий месяц", "next month": "Следующий месяц",
        "Previous month": "Предыдущий месяц", "not set": "не задано",
        "Start weeks on ": "Неделя начинается с ",
        "BORN": "РОДИЛСЯ", "LIVE TO": "ДОЖИТЬ ДО", "LIFE": "ЖИЗНЬ", "Memento Mori": "Memento Mori",
        "year": "год",
    },
    "network": {
        "Auto": "Авто", "Automatic": "Автоматически", "AUTOMATIC": "АВТОМАТИЧЕСКИ",
        "Connect": "Подключить", "Connected": "Подключено",
        "Connecting...": "Подключение...", "Connecting…": "Подключение…",
        "Connection failed": "Ошибка подключения", "Copy gateway": "Копировать шлюз",
        "Copy IP": "Копировать IP", "Copy to clipboard": "Копировать в буфер",
        "Disconnected": "Отключено", "Disconnecting…": "Отключение…", "DNS PROVIDER": "DNS-СЕРВЕР",
        "Downloaded": "Загружено", "Failed": "Ошибка", "Failed to connect": "Не удалось подключиться",
        "Forget network": "Забыть сеть", "Forgetting…": "Удаление…", "Gateway": "Шлюз",
        "Hidden": "Скрытая сеть", "Identity (user@domain)": "Логин (user@domain)",
        "IP Address": "IP-адрес", "KNOWN NETWORKS": "ИЗВЕСТНЫЕ СЕТИ",
        "Let Wi-Fi pick the band": "Wi-Fi сам выберет диапазон", "Network lost": "Сеть потеряна",
        "No connection": "Нет подключения", "NOT CONNECTED": "НЕ ПОДКЛЮЧЕНО",
        "OTHER NETWORKS": "ДРУГИЕ СЕТИ", "Packet Loss": "Потеря пакетов", "Passphrase": "Пароль",
        "Passphrase required": "Нужен пароль", "Receiving": "Приём", "Sending": "Отправка",
        "Run a speed test": "Проверить скорость", "SCANNING WI-FI…": "ПОИСК СЕТЕЙ WI-FI…",
        "Set custom DNS servers": "Свои DNS-серверы", "Set DNS to Cloudflare": "DNS: Cloudflare",
        "Set DNS to Google": "DNS: Google", "Show QR code": "Показать QR-код",
        "Stay on ": "Оставаться на ", "Timed out connecting": "Время подключения истекло",
        "Timed out disconnecting": "Время отключения истекло", "Timed out forgetting": "Время удаления истекло",
        "Timeout": "Таймаут", "Turn Wi-Fi off": "Выключить Wi-Fi", "Turn Wi-Fi on": "Включить Wi-Fi",
        "Uploaded": "Отдано", "Use DNS from DHCP": "DNS от DHCP", "WI-FI BAND": "ДИАПАЗОН WI-FI",
        "WI-FI BAND: ": "ДИАПАЗОН WI-FI: ", "Wrong password": "Неверный пароль",
        "Bending light": "Изгибаем свет", "Counting collisions": "Считаем коллизии",
        "Handling packets": "Обрабатываем пакеты", "Hauling bytes": "Таскаем байты",
        "Routing crumbs": "Маршрутизируем крошки", "Sorting frames": "Сортируем кадры",
        "Wiring bits": "Проводим биты",
    },
    "bluetooth": {
        "AVAILABLE": "ДОСТУПНЫЕ", "CONNECTED": "ПОДКЛЮЧЕНЫ", "PAIRED": "СОПРЯЖЕНЫ",
        "Connect": "Подключить", "Connected": "Подключено", "Connecting…": "Подключение…",
        "Device": "Устройство", "Disconnect": "Отключить", "Disconnecting…": "Отключение…",
        "Forget": "Забыть", "Forgetting…": "Удаление…", "No adapter": "Нет адаптера",
        "No Bluetooth adapter": "Нет адаптера Bluetooth", "Pair": "Сопрячь",
        "Scanning for devices…": "Поиск устройств…", "Turn Bluetooth off": "Выключить Bluetooth",
        "Turn Bluetooth on": "Включить Bluetooth", "Turn Bluetooth on to scan": "Включите Bluetooth для поиска",
        "Turned Off": "Выключен",
        "Herding headsets": "Пасём гарнитуры", "Pairing mysteries": "Разгадываем сопряжение",
        "Polishing packets": "Полируем пакеты", "Streaming vikings": "Стримим викингов",
        "Summoning speakers": "Призываем колонки", "Taming radios": "Приручаем радио",
        "Untangling wires": "Распутываем провода", "Wrangling codecs": "Укрощаем кодеки",
    },
    "audio": {
        "Concert hall": "Концертный зал", "Cranked up": "На полную", "Easy listening": "Лёгкая музыка",
        "INPUT": "ВХОД", "OUTPUT": "ВЫХОД", "SOURCES": "ИСТОЧНИКИ", "Microphone": "Микрофон",
        "Murmur": "Бормотание", "Mute": "Выключить звук", "Unmute": "Включить звук",
        "Muted": "Без звука", "Party mode": "Вечеринка", "Silenced": "Тишина",
        "Steady groove": "Ровный ритм", "Unknown": "Неизвестно", "Stream": "Поток", "Whisper": "Шёпот",
    },
    "power": {
        "Battery": "Батарея", "Battery size": "Ёмкость батареи", "Battery state": "Состояние батареи",
        "Charge cycles": "Циклы зарядки", "Charge limit": "Лимит заряда", "Charging": "Зарядка",
        "Discharging": "Разрядка", "Fully charged": "Полностью заряжена",
        "FULLY CHARGED": "ПОЛНОСТЬЮ ЗАРЯЖЕНА", "Holding": "Удержание", "On battery": "От батареи",
        "POWER PROFILE": "ПРОФИЛЬ ПИТАНИЯ", "Threshold": "Порог", "Time left": "Осталось",
        "Time to full": "До полной",
        "Amassing watts": "Копим ватты", "Bleeding amps": "Теряем амперы",
        "Burning electrons": "Жжём электроны", "Draining watts": "Сливаем ватты",
        "Guzzling volts": "Глотаем вольты", "Hoarding joules": "Копим джоули",
        "Inhaling kilowatts": "Вдыхаем киловатты", "Injecting electrons": "Вводим электроны",
        "Munching reserves": "Хрустим запасами", "Pouring juice": "Льём сок",
        "Pumping power": "Качаем энергию", "Sipping juice": "Потягиваем сок",
        "Slurping power": "Хлебаем энергию", "Soaking amps": "Впитываем амперы",
        "Spending coulombs": "Тратим кулоны", "Spending joules": "Тратим джоули",
        "Sucking volts": "Всасываем вольты", "Topping reserves": "Пополняем запасы",
    },
    "monitor": {
        "BRIGHTNESS": "ЯРКОСТЬ", "Candlelit": "При свечах", "Display": "Экран", "DISPLAYS": "ЭКРАНЫ",
        "Even day": "Ровный день", "FIXED BRIGHTNESS": "ФИКСИРОВАННАЯ ЯРКОСТЬ",
        " · focused": " · в фокусе", "Golden hour": "Золотой час", "Lamp light": "Свет лампы",
        "Night owl": "Сова", "SCALE": "МАСШТАБ", "Soft glow": "Мягкое свечение",
        "Solar flare": "Солнечная вспышка", "Sun blast": "Солнечный удар", "TEXT SIZE": "РАЗМЕР ТЕКСТА",
    },
    "weather": {
        "FEELS": "ОЩУЩАЕТСЯ", "HUMID": "ВЛАЖН.", "WIND": "ВЕТЕР",
        "Fetching forecast…": "Загрузка прогноза…", "Search city": "Поиск города",
    },
    "speedtest": {
        "DOWNLOAD": "ЗАГРУЗКА", "UPLOAD": "ОТДАЧА", "Measure again via fast.com": "Измерить снова через fast.com",
    },
    "disk-speedtest": {"READ": "ЧТЕНИЕ", "WRITE": "ЗАПИСЬ", "Measure again": "Измерить снова"},
    "tailscale": {
        "Account": "Аккаунт", "Allow this user to operate this Tailscale profile": "Разрешить этому пользователю управлять профилем Tailscale",
        "Authorize Tailscale operator": "Авторизовать оператора Tailscale", "Authorize this device": "Авторизовать это устройство",
        "Checking…": "Проверка…", "Choose Mullvad region": "Выберите регион Mullvad", "Connect": "Подключить",
        "CONNECTIONS": "ПОДКЛЮЧЕНИЯ", "Disconnect": "Отключить", "Disconnected": "Отключено", "EXIT NODES": "ВЫХОДНЫЕ УЗЛЫ",
        "Failed to parse tailscale status": "Не удалось разобрать статус tailscale", "MACHINES": "УСТРОЙСТВА",
        "No machines found on this tailnet.": "В этой сети устройств не найдено.", "No Mullvad regions found.": "Регионы Mullvad не найдены.",
        "Search regions": "Поиск регионов", "Send files": "Отправить файлы", "Status error": "Ошибка статуса",
        "Tailscale CLI is not installed or not on PATH.": "Tailscale CLI не установлен или не найден в PATH.",
        "Tailscale is disconnected": "Tailscale отключён", "Turn Tailscale off": "Выключить Tailscale",
        "Turn Tailscale on": "Включить Tailscale", "Unknown": "Неизвестно", "Unknown account": "Неизвестный аккаунт",
    },
    "notifications": {"No recent notifications": "Нет недавних уведомлений"},
    "reminders": {"Reminder message": "Текст напоминания", "Remind in minutes": "Напомнить через (мин)"},
    "clipboard": {
        "Clipboard is empty": "Буфер обмена пуст", "Delete": "Удалить",
        "Delete entire clipboard history?": "Удалить всю историю буфера обмена?", "Image": "Изображение",
        "Screenshot": "Снимок экрана", "No matches for “": "Нет совпадений для “",
    },
    "emojis": {"No matches for “": "Нет совпадений для “"},
    "image-picker": {"No matches": "Нет совпадений"},
    "wifiqr": {
        "Could not read the Wi-Fi password": "Не удалось прочитать пароль Wi-Fi",
        "Generating QR code…": "Создание QR-кода…",
        "Scan to join this network": "Сканируйте, чтобы подключиться к сети",
        "Show password": "Показать пароль",
    },
    "dropbox": {
        "Filing files": "Раскладываем файлы", "Distributing data": "Раздаём данные",
        "Shuffling folders": "Тасуем папки", "Boxing bytes": "Пакуем байты", "Sorting stuff": "Разбираем вещи",
        "Syncing secrets": "Синхронизируем секреты", "Packing packets": "Упаковываем пакеты",
        "Moving memories": "Переносим воспоминания", "Wrangling revisions": "Укрощаем версии",
        "Cataloging chaos": "Каталогизируем хаос",
        "Pause syncing": "Приостановить синхронизацию", "Resume syncing": "Возобновить синхронизацию",
        "Syncing paused": "Синхронизация приостановлена", "Stored": "Занято", "RECENT FILES": "НЕДАВНИЕ ФАЙЛЫ",
        "No synced files found.": "Синхронизированных файлов нет.", "Login to Dropbox": "Войти в Dropbox",
        "Dropbox CLI is not installed": "Dropbox CLI не установлен",
        "Install Dropbox from the service menu": "Установите Dropbox через меню «Установка → Сервис»",
        "Start the authentication flow": "Начать авторизацию", "Untitled": "Без названия",
        "Checking…": "Проверка…", "Stopped": "Остановлен", "Not installed": "Не установлен",
        "Starting Dropbox login…": "Запуск входа в Dropbox…", "Opened Dropbox login": "Страница входа в Dropbox открыта",
        "Failed to read Dropbox status": "Не удалось прочитать статус Dropbox",
        "Could not read Dropbox status": "Не удалось прочитать статус Dropbox",
        "Dropbox login failed": "Не удалось войти в Dropbox", "Dropbox command failed": "Ошибка команды Dropbox",
        "Failed to parse Dropbox status": "Не удалось разобрать статус Dropbox", "Unavailable": "Недоступно",
        "Unknown time": "Время неизвестно", "Just now": "Только что",
    },
    "agents": {
        "Agents": "Агенты", "Starting…": "Запуск…", "Checking the code…": "Проверка кода…",
        "The sign-in didn't finish.": "Вход не завершён.",
        "Back to the limits": "К лимитам", "Add a subscription": "Добавить подписку",
        "Start the default agent": "Запустить агента по умолчанию", "MAKE SOMETHING COOL": "СОЗДАЙТЕ ЧТО-НИБУДЬ КРУТОЕ",
        "Sign in to an AI coding subscription, and this panel keeps track of how much of it you have left.":
            "Войдите в подписку на ИИ-ассистента для кода, и эта панель покажет, сколько лимита осталось.",
        "Name this account. It signs in through a private window, so your browser's current account isn't picked up.":
            "Назовите этот аккаунт. Вход идёт через приватное окно, поэтому текущий аккаунт браузера не подхватывается.",
        "Work": "Работа", "Confirm this code in your browser": "Подтвердите этот код в браузере",
        "If the page shows a code instead of finishing, paste it here.":
            "Если страница показала код вместо завершения входа, вставьте его сюда.",
        "Code": "Код", "Open the sign-in page again": "Открыть страницу входа снова",
        "Sign-in required": "Нужен вход", "Sign in to this account again": "Войти в этот аккаунт заново",
        "Balance": "Баланс", "ACTIVE": "АКТИВЕН", "Autoswitch": "Автопереключение", "Autoswitch ⏎": "Автопереключение ⏎",
        "Use": "Выбрать", "Use ⏎": "Выбрать ⏎", "Stop switching automatically": "Не переключаться автоматически",
        "Last known": "Последние данные", "Subscriptions": "Подписки", "now": "сейчас",
        "Theme": "Тема", "Plugin": "Плагин", "App": "Приложение",
        "Make me a new Omarchy theme. Ask me what look or inspiration I have in mind, then build it following the Omarchy skill's theming guide and switch to it.":
            "Сделай мне новую тему Omarchy. Спроси, какой вид или вдохновение я имею в виду, затем создай её по руководству по темам из навыка Omarchy и переключись на неё. Общайся со мной по-русски.",
        "Make me a new Omarchy shell plugin. Ask me what I'd like it to do, then build it following the Omarchy skill's plugin guide and enable it.":
            "Сделай мне новый плагин шелла Omarchy. Спроси, что он должен делать, затем создай его по руководству по плагинам из навыка Omarchy и включи. Общайся со мной по-русски.",
        "Make me a new app for my Omarchy desktop. Ask me what it should do, then build it following the omarchy-app skill and install it so it shows up in the app launcher.":
            "Сделай мне новое приложение для рабочего стола Omarchy. Спроси, что оно должно делать, затем создай его по навыку omarchy-app и установи, чтобы оно появилось в лаунчере. Общайся со мной по-русски.",
    },
    "indicators": {
        "Day Light": "Дневной свет", "Night Light": "Ночной свет", "Dictate": "Диктовка",
        "Allow Notifications": "Включить уведомления", "Silence Notifications": "Отключить уведомления",
        "Stop recording": "Остановить запись", "Screen Recording": "Запись экрана",
        "Allow Idle Lock & Screensaver": "Разрешить блокировку и заставку", "Stay Awake": "Не засыпать",
    },
    "microphone": {
        "Microphone muted": "Микрофон выключен", "Microphone in use": "Микрофон используется",
        "Microphone live": "Микрофон включён",
    },
    "system-update": {"Pending Omarchy Updates": "Доступны обновления Omarchy"},
    "tray": {
        "Tray icons": "Значки трея", "Pinned icons stay visible. Hidden icons never show.":
            "Закреплённые значки всегда видны. Скрытые не показываются.",
        "No tray items reporting.": "Нет значков в трее.", "Unknown": "Неизвестно",
        "Unpin": "Открепить", "Pin": "Закрепить", "Show": "Показать", "Hide": "Скрыть",
    },
}

# Точечные правки кода (там, где текст не литерал): (плагин, файл, старое, новое, ожидаемое число вхождений).
# Даты форматируем русской локалью явно, т.к. процесс шелла может работать с en_US.
PATCHES = [
    ("clock", "Panel.qml", 'Qt.locale("en_US")', 'Qt.locale("ru_RU")', 1),
    ("clock", "Panel.qml", 'Qt.formatDate(root.today, "MMMM d")', 'Qt.locale("ru_RU").toString(root.today, "d MMMM")', 1),
    ("clock", "Panel.qml", 'Qt.formatDate(root.viewDate, "MMMM yyyy")', 'Qt.locale("ru_RU").toString(root.viewDate, "MMMM yyyy")', 1),
    ("clock", "BarWidget.qml", 'Qt.formatDateTime(date, ', 'Qt.locale("ru_RU").toString(date, ', 1),
    ("weather", "Panel.qml", "&language=en&", "&language=ru&", 1),
    ("power", "Panel.qml",
     'text: String(modelData).charAt(0).toUpperCase() + String(modelData).slice(1)',
     'text: ({"power-saver": "Экономия", "balanced": "Баланс", "performance": "Мощность"})[String(modelData)]'
     ' || (String(modelData).charAt(0).toUpperCase() + String(modelData).slice(1))', 1),
    # Dropbox: единицы, «из» и относительное время собираются из кусков.
    ("dropbox", "Model.js", 'var units = ["B", "KB", "MB", "GB", "TB"]', 'var units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]', 1),
    ("dropbox", "Model.js", '"0 B"', '"0 Б"', 1),
    ("dropbox", "Model.js", '" of " + formatBytes(quotaBytes)', '" из " + formatBytes(quotaBytes)', 1),
    ("dropbox", "Model.js", 'minutes + "m ago"', 'minutes + " мин назад"', 1),
    ("dropbox", "Model.js", 'hours + "h ago"', 'hours + " ч назад"', 1),
    ("dropbox", "Model.js", 'days + "d ago"', 'days + " дн назад"', 1),
    ("dropbox", "Model.js", 'months + "mo ago"', 'months + " мес назад"', 1),
    ("dropbox", "Model.js", 'Math.floor(days / 365) + "y ago"', 'Math.floor(days / 365) + " г назад"', 1),
    # Agents: длительности и сводка в шапке. Названия окон лимитов (Session/Weekly/Monthly) не трогаем:
    # по ним панель сопоставляет лимиты моделей с основным окном.
    ("agents", "Panel.qml", 'days + "d " + (hours % 24) + "h"', 'days + " д " + (hours % 24) + " ч"', 1),
    ("agents", "Panel.qml", 'hours + "h " + (minutes % 60) + "m"', 'hours + " ч " + (minutes % 60) + " мин"', 1),
    ("agents", "Panel.qml", 'Math.max(1, minutes) + "m"', 'Math.max(1, minutes) + " мин"', 1),
    ("agents", "Panel.qml", '" tokens this week"', '" токенов за неделю"', 1),
    ("agents", "Panel.qml", '" tokens today"', '" токенов сегодня"', 1),
    ("agents", "Panel.qml", '"Mostly " + topModel', '"Чаще всего " + topModel', 1),
    ("agents", "Panel.qml", '"Busiest day: " + dayName(busiest)', '"Самый активный день: " + dayName(busiest)', 1),
    ("agents", "Panel.qml", '["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]',
     '["воскресенье", "понедельник", "вторник", "среда", "четверг", "пятница", "суббота"]', 1),
    ("agents", "Panel.qml", '" · resets in "', '" · сброс через "', 1),
    ("agents", "Panel.qml", '"% used"', '"% использовано"', 1),
    ("agents", "Panel.qml", '"Start your default agent on a new " + tile.title.toLowerCase()',
     '"Запустить агента по умолчанию: " + tile.title.toLowerCase()', 1),
]

# Литерал не трогаем, если перед ним стоит оператор сравнения или поиск по значению.
COMPARE_BEFORE = ("===", "!==", "==", "!=", "indexOf(", "includes(", "startsWith(", "endsWith(", "case")
STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


def translate_text(text: str, table: dict, hits: set) -> str:
    def repl(m):
        src = m.group(1)
        if src not in table:
            return m.group(0)
        before = text[: m.start()].rstrip()
        if before.endswith(COMPARE_BEFORE):
            return m.group(0)
        after = text[m.end():].lstrip()
        if after.startswith(("===", "!==", "==", "!=")):
            return m.group(0)
        hits.add(src)
        return '"' + table[src] + '"'

    return STRING.sub(repl, text)


def merge_emoji_keywords(target: Path) -> int:
    """Дописывает русские названия в поле поиска `k` клона emojis.json (данные CLDR: data/emojis-ru.json)."""
    f = target / "emojis.json"
    ru_file = Path(__file__).resolve().parent / "data/emojis-ru.json"
    if not f.exists() or not ru_file.exists():
        return 0
    ru = json.loads(ru_file.read_text())
    items = json.loads(f.read_text())
    added = 0
    for item in items:
        name = ru.get(item.get("e", ""))
        if name and name not in item.get("k", ""):
            item["k"] = (item.get("k", "") + " " + name).strip()
            added += 1
    if added:
        f.write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")))
    return added


def ensure_clone(name: str) -> Path | None:
    target = PLUGINS_DIR / f"{USER}.{name}"
    if target.exists():
        return target
    r = subprocess.run(["omarchy", "plugin", "clone", f"omarchy.{name}"], capture_output=True, text=True)
    if r.returncode != 0 or not target.exists():
        print(f"translate-plugins: не удалось клонировать {name}: {r.stderr.strip()}", file=sys.stderr)
        return None
    print(f"translate-plugins: склонирован omarchy.{name}")
    return target


def main() -> int:
    import os
    failed = 0
    # Использование: translate-plugins.py [имя ...] [--except имя ...]; без аргументов — все плагины.
    args = sys.argv[1:]
    excluded = set()
    if "--except" in args:
        i = args.index("--except")
        excluded, args = set(args[i + 1:]), args[:i]
    selected = args or list(TRANSLATIONS)
    unknown = [n for n in selected if n not in TRANSLATIONS]
    if unknown:
        print(f"translate-plugins: неизвестные плагины: {', '.join(unknown)}", file=sys.stderr)
        return 2
    for name in [n for n in selected if n not in excluded]:
        table = TRANSLATIONS[name]
        target = ensure_clone(name)
        if not target:
            failed += 1
            continue
        hits: set = set()
        for f in sorted(list(target.rglob("*.qml")) + list(target.rglob("*.js"))):
            old = f.read_text()
            new = translate_text(old, table, hits)
            if new != old:
                f.write_text(new)
        for pname, fname, old, new, count in PATCHES:
            if pname != name:
                continue
            f = target / fname
            text = f.read_text()
            if old in text:
                if text.count(old) != count:
                    print(f"translate-plugins: {name}/{fname}: ожидалось {count} вхождений, найдено {text.count(old)}", file=sys.stderr)
                    continue
                f.write_text(text.replace(old, new))
            elif new not in text:
                print(f"translate-plugins: {name}/{fname}: не найден фрагмент для правки: {old[:50]}", file=sys.stderr)
        if name == "emojis":
            print(f"translate-plugins: emojis: добавлены русские названия к {merge_emoji_keywords(target)} эмодзи")
        print(f"translate-plugins: {name}: переведено строк {len(hits)}/{len(table)}")
    # Горячая перезагрузка не обновляет уже открытые панели — перезапускаем шелл целиком.
    # RUS_NO_RESTART=1 выставляет install.sh: он перезапустит шелл один раз в конце.
    if not os.environ.get("RUS_NO_RESTART"):
        subprocess.run(["omarchy", "restart", "shell"], capture_output=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
