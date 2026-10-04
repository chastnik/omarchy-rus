#!/usr/bin/env python3
"""Русификация панелей бара Omarchy (календарь, сеть/Wi-Fi, Bluetooth, звук, питание, экран, Wi-Fi QR).

Встроенные плагины лежат в /usr/share/omarchy/ и правке не подлежат, поэтому скрипт:
  1. клонирует плагин (`omarchy plugin clone omarchy.<имя>`), если клона ещё нет;
  2. заменяет в QML/JS клона точные строковые литералы "English" -> "Русский".

Литералы, стоящие в сравнениях (===, !==, indexOf(, case ...), не трогаются, чтобы не сломать логику.
Внутренние ключи (DHCP/Cloudflare/Google/Custom и т.п.) в словарях нет намеренно.
Скрипт идемпотентен. ВАЖНО: клон не получает обновления оригинального плагина; после
`omarchy update` можно удалить ~/.config/omarchy/plugins/<user>.<имя> и запустить скрипт заново.

Использование:
  translate-plugins.py [имя ...] [--except имя ...]   перевести плагины (без аргументов — все)
  translate-plugins.py --check [--notify]             найти клоны, чей оригинал изменился после «omarchy update»
  translate-plugins.py --refresh [имя ...]            пересоздать устаревшие (или указанные) клоны и перевести заново
"""
import getpass
import hashlib
import json
import os
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
        "Ping": "Пинг",
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
        "Audio": "Звук",
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
        "Prepaid credits": "Предоплаченные кредиты", "Resets in ": "Сброс через ", "Limit": "Лимит",
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

PLUGINS_SRC = Path("/usr/share/omarchy/shell/plugins")
STATE_FILE = Path.home() / ".local/share/omarchy-rus/clones.json"
NOTIFICATIONS_DATA = Path(__file__).resolve().parent / "data" / "notifications-ru.json"


def plural_js(n: str, one: str, few: str, many: str) -> str:
    """JS-выражение с русским склонением по числу n: 1 напоминание, 2 напоминания, 5 напоминаний."""
    return (f'({n} % 10 === 1 && {n} % 100 !== 11 ? "{one}" : ({n} % 10 >= 2 && {n} % 10 <= 4 '
            f'&& ({n} % 100 < 12 || {n} % 100 > 14) ? "{few}" : "{many}"))')


def notifications_js() -> str:
    """Функция ruText для NotificationLogic.js: словарь data/notifications-ru.json встраивается литералом."""
    d = json.loads(NOTIFICATIONS_DATA.read_text())
    lit = lambda x: json.dumps(x, ensure_ascii=False)
    return f"""// omarchy-rus: русский текст уведомлений. Строки приходят из скриптов Omarchy готовыми английскими.
var RU_EXACT = {lit(d["exact"])}
var RU_PATTERNS = {lit(d["patterns"])}
var RU_LOOSE = {lit(d["loose"])}
var RU_LOOSE_GATE = new RegExp({lit(d["loose_gate"])})

function ruLine(line) {{
  var exact = RU_EXACT[line]
  if (exact !== undefined) return exact
  for (var i = 0; i < RU_PATTERNS.length; i++) {{
    var re = new RegExp(RU_PATTERNS[i][0])
    if (re.test(line)) return line.replace(re, RU_PATTERNS[i][1])
  }}
  if (RU_LOOSE_GATE.test(line)) {{
    for (var j = 0; j < RU_LOOSE.length; j++) line = line.replace(new RegExp(RU_LOOSE[j][0], "g"), RU_LOOSE[j][1])
  }}
  return line
}}

function ruText(text) {{
  return String(text || "").split("\\n").map(ruLine).join("\\n")
}}

"""


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
    # Подсказка Reminder приходит из omarchy-reminder готовой английской строкой ("Set Reminder", "N reminders").
    ("indicators", "indicators/Reminder.qml", 'tooltip = String(data.tooltip || "")',
     'tooltip = reminderCount === 0 ? "Создать напоминание" : reminderCount + " " + '
     + plural_js("reminderCount", "напоминание", "напоминания", "напоминаний"), 1),
    ("clipboard", "ClipboardHistory.js", 'paths.length + " files"',
     'paths.length + " " + ' + plural_js("paths.length", "файл", "файла", "файлов"), 1),
    ("agents", "Panel.qml", '"Merged from " + provider.syncDeviceCount + " device" + (provider.syncDeviceCount === 1 ? "" : "s")',
     '"Объединено с " + provider.syncDeviceCount + " " + ' + plural_js("provider.syncDeviceCount", "устройства", "устройств", "устройств"), 1),
    # Уведомления: переводим на показе (карточка и история), словарь — data/notifications-ru.json.
    ("notifications", "NotificationLogic.js", "function isChromiumDerived(app, appIcon) {",
     notifications_js() + "function isChromiumDerived(app, appIcon) {", 1),
    ("notifications", "components/NotificationCard.qml", "text: root.summary",
     "text: NotificationLogic.ruText(root.summary)", 1),
    ("notifications", "components/NotificationCard.qml", "NotificationLogic.styledBody(body, app, appIcon)",
     "NotificationLogic.styledBody(NotificationLogic.ruText(body), app, appIcon)", 1),
    # Dropbox: единицы, «из» и относительное время собираются из кусков.
    ("dropbox", "Model.js", 'var units = ["B", "KB", "MB", "GB", "TB"]', 'var units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]', 1),
    ("dropbox", "Model.js", '"0 B"', '"0 Б"', 1),
    ("dropbox", "Model.js", '" of " + formatBytes(quotaBytes)', '" из " + formatBytes(quotaBytes)', 1),
    ("dropbox", "Model.js", 'minutes + "m ago"', 'minutes + " мин назад"', 1),
    ("dropbox", "Model.js", 'hours + "h ago"', 'hours + " ч назад"', 1),
    ("dropbox", "Model.js", 'days + "d ago"', 'days + " дн назад"', 1),
    ("dropbox", "Model.js", 'months + "mo ago"', 'months + " мес назад"', 1),
    ("dropbox", "Model.js", 'Math.floor(days / 365) + "y ago"', 'Math.floor(days / 365) + " г назад"', 1),
    # Agents: длительности. Названия окон лимитов (Session/Weekly/Monthly) не трогаем:
    # по ним панель сопоставляет лимиты моделей с основным окном.
    ("agents", "Panel.qml", 'days + "d " + (hours % 24) + "h"', 'days + " д " + (hours % 24) + " ч"', 1),
    ("agents", "Panel.qml", 'hours + "h " + (minutes % 60) + "m"', 'hours + " ч " + (minutes % 60) + " мин"', 1),
    ("agents", "Panel.qml", 'Math.max(1, minutes) + "m"', 'Math.max(1, minutes) + " мин"', 1),
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


def omarchy_version() -> str:
    try:
        return Path("/usr/share/omarchy/version").read_text().strip()
    except OSError:
        return "?"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def related_originals(name: str, target: Path) -> dict:
    """Файлы оригинала, из которых сделан клон: {путь относительно plugins/: sha256}.

    Соответствие эвристическое: у клона нет ссылки на источник, поэтому ищем в оригинале файлы,
    чей путь оканчивается путём файла клона и у которых в пути есть имя плагина (или имя файла = имя плагина).
    """
    mine = [f.relative_to(target).as_posix() for f in target.rglob("*")
            if f.is_file() and f.suffix in (".qml", ".js") and not f.name.startswith(".")]
    out = {}
    for f in PLUGINS_SRC.rglob("*"):
        if not f.is_file() or f.suffix not in (".qml", ".js") or "dev-gallery" in f.parts:
            continue
        rel = f.relative_to(PLUGINS_SRC).as_posix()
        if any(rel.endswith("/" + m) or rel == m for m in mine) and (name in f.parts or f.stem.lower() == name):
            out[rel] = sha(f)
    return out


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {"plugins": {}}


def save_state(state: dict) -> None:
    state["omarchy"] = omarchy_version()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True))


def process(name: str) -> bool:
    table = TRANSLATIONS[name]
    target = ensure_clone(name)
    if not target:
        return False
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
        if new in text:
            continue
        if old in text:
            if text.count(old) != count:
                print(f"translate-plugins: {name}/{fname}: ожидалось {count} вхождений, найдено {text.count(old)}", file=sys.stderr)
                continue
            f.write_text(text.replace(old, new))
        else:
            print(f"translate-plugins: {name}/{fname}: не найден фрагмент для правки: {old[:50]}", file=sys.stderr)
    if name == "emojis":
        print(f"translate-plugins: emojis: добавлены русские названия к {merge_emoji_keywords(target)} эмодзи")
    print(f"translate-plugins: {name}: переведено строк {len(hits)}/{len(table)}")
    return True


def record_baseline(names) -> None:
    """Запоминает, с какой версией оригинала сделан клон (для --check)."""
    state = load_state()
    for n in names:
        target = PLUGINS_DIR / f"{USER}.{n}"
        if target.exists():
            state.setdefault("plugins", {})[n] = related_originals(n, target)
    save_state(state)


def stale_clones() -> tuple:
    """(устаревшие, без базовой точки): клоны, чей оригинал изменился после «omarchy update»."""
    state = load_state().get("plugins", {})
    stale, unknown = [], []
    for n in TRANSLATIONS:
        target = PLUGINS_DIR / f"{USER}.{n}"
        if not target.exists():
            continue
        if n not in state:
            unknown.append(n)
        elif state[n] != related_originals(n, target):
            stale.append(n)
    return stale, unknown


def cmd_check(notify: bool) -> int:
    stale, unknown = stale_clones()
    if unknown:
        record_baseline(unknown)
        print(f"translate-plugins: запомнил текущее состояние оригиналов для: {', '.join(unknown)}")
    if not stale:
        print("translate-plugins: все клоны актуальны")
        return 0
    print(f"translate-plugins: оригиналы изменились после обновления Omarchy: {', '.join(stale)}")
    print("Пересоздать клоны и перевести заново: translate-plugins.py --refresh")
    if notify:
        subprocess.run(["omarchy-notification-send", "-g", "", "Русификация: плагины обновились",
                        f"Изменились оригиналы: {', '.join(stale)}. Выполните: translate-plugins.py --refresh"],
                       capture_output=True)
    return 3


def cmd_refresh(names) -> int:
    import shutil
    stale = names or stale_clones()[0]
    if not stale:
        print("translate-plugins: обновлять нечего")
        return 0
    bad = [n for n in stale if n not in TRANSLATIONS]
    if bad:
        print(f"translate-plugins: неизвестные плагины: {', '.join(bad)}", file=sys.stderr)
        return 2
    failed = 0
    for n in stale:
        target = PLUGINS_DIR / f"{USER}.{n}"
        if target.exists():
            shutil.rmtree(target)
        if not process(n):
            failed += 1
    record_baseline([n for n in stale])
    here = Path(__file__).resolve().parent
    if "network" in stale and Path("/usr/local/bin/omarchy-dns-ru").exists() and (here / "dns-ru.py").exists():
        subprocess.run([sys.executable, str(here / "dns-ru.py"), "panel"])
    if not os.environ.get("RUS_NO_RESTART"):
        subprocess.run(["omarchy", "restart", "shell"], capture_output=True)
    return 1 if failed else 0


def main() -> int:
    # Использование: translate-plugins.py [имя ...] [--except имя ...]; без аргументов — все плагины.
    args = sys.argv[1:]
    if "--check" in args:
        return cmd_check("--notify" in args)
    if "--refresh" in args:
        return cmd_refresh([a for a in args if a != "--refresh"])
    failed = 0
    excluded = set()
    if "--except" in args:
        i = args.index("--except")
        excluded, args = set(args[i + 1:]), args[:i]
    selected = args or list(TRANSLATIONS)
    unknown = [n for n in selected if n not in TRANSLATIONS]
    if unknown:
        print(f"translate-plugins: неизвестные плагины: {', '.join(unknown)}", file=sys.stderr)
        return 2
    done = []
    for name in [n for n in selected if n not in excluded]:
        if process(name):
            done.append(name)
        else:
            failed += 1
    record_baseline(done)
    # Горячая перезагрузка не обновляет уже открытые панели — перезапускаем шелл целиком.
    # RUS_NO_RESTART=1 выставляет install.sh: он перезапустит шелл один раз в конце.
    if not os.environ.get("RUS_NO_RESTART"):
        subprocess.run(["omarchy", "restart", "shell"], capture_output=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
