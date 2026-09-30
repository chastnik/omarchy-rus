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
        print(f"translate-plugins: {name}: переведено строк {len(hits)}/{len(table)}")
    # Горячая перезагрузка не обновляет уже открытые панели — перезапускаем шелл целиком.
    # RUS_NO_RESTART=1 выставляет install.sh: он перезапустит шелл один раз в конце.
    if not os.environ.get("RUS_NO_RESTART"):
        subprocess.run(["omarchy", "restart", "shell"], capture_output=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
