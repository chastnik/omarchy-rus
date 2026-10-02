#!/usr/bin/env python3
"""Русское меню горячих клавиш (Super+K).

Описания привязок берутся из Lua-конфигов Hyprland в /usr/share/omarchy/ (править нельзя), а
`omarchy-menu-keybindings` показывает их как есть. Поэтому:

  keybindings-ru.py wrapper    собирает ~/.local/bin/omarchy-menu-keybindings-ru — копию стокового
                               скрипта с шагом перевода записей меню (после сортировки, чтобы не
                               ломать приоритеты); ключ кеша включает хеш словаря
  keybindings-ru.py bindings   переназначает SUPER+K на этот скрипт в ~/.config/hypr/bindings.lua
  keybindings-ru.py tmux       то же для меню Tmux (SUPER+ALT+K): omarchy-menu-tmux-keybindings-ru
  keybindings-ru.py herdr      то же для меню Herdr (SUPER+CTRL+K): omarchy-menu-herdr-keybindings-ru

Непереведённые описания остаются английскими. Словарь — TRANSLATIONS/PREFIX_RULES ниже.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

STOCK = Path("/usr/share/omarchy/bin/omarchy-menu-keybindings")
OUT = Path.home() / ".local/bin/omarchy-menu-keybindings-ru"
BINDINGS = Path.home() / ".config/hypr/bindings.lua"
BIN = Path.home() / ".local/bin"
STOCK_DIR = Path("/usr/share/omarchy/bin")
MARK_BEGIN, MARK_END = "-- >>> omarchy-rus: keybindings", "-- <<< omarchy-rus: keybindings"

TRANSLATIONS = {
    "Activity": "Монитор активности", "Agent": "ИИ-агент", "Apps menu": "Меню приложений", "Audio": "Звук",
    "Background switcher": "Смена фона", "Brightness down": "Уменьшить яркость",
    "Brightness down precise": "Уменьшить яркость (точно)", "Brightness maximum": "Максимальная яркость",
    "Brightness minimum": "Минимальная яркость", "Brightness up": "Увеличить яркость",
    "Brightness up precise": "Увеличить яркость (точно)", "Browser": "Браузер",
    "Browser (private)": "Браузер (приватный)", "Calculator": "Калькулятор", "Calendar": "Календарь",
    "Capture menu": "Меню захвата", "Clear reminders": "Удалить напоминания",
    "Clipboard manager": "История буфера обмена", "Close all windows": "Закрыть все окна",
    "Close window": "Закрыть окно", "Color picker": "Пипетка",
    "Copy URL from Web App": "Копировать URL из веб-приложения", "Disable touchpad": "Отключить тачпад",
    "Dismiss all notifications": "Скрыть все уведомления", "Dismiss last notification": "Скрыть последнее уведомление",
    "Display": "Экран", "Download Video from Web App": "Скачать видео из веб-приложения", "Editor": "Редактор",
    "Eject media": "Извлечь носитель", "Email": "Почта", "Emojis": "Эмодзи", "Enable touchpad": "Включить тачпад",
    "Extract text (OCR) from screenshot": "Распознать текст (OCR) со снимка", "File manager": "Файловый менеджер",
    "File manager (cwd)": "Файловый менеджер (текущая папка)",
    "Focus on above window": "Фокус на окно выше", "Focus on below window": "Фокус на окно ниже",
    "Focus on left window": "Фокус на окно слева", "Focus on right window": "Фокус на окно справа",
    "Focus on next monitor": "Фокус на следующий монитор", "Focus on next window": "Фокус на следующее окно",
    "Focus on previous monitor": "Фокус на предыдущий монитор", "Focus on previous window": "Фокус на предыдущее окно",
    "Former workspace": "Прежний рабочий стол", "Full screen": "Полный экран", "Full width": "Во всю ширину",
    "Hardware menu": "Меню оборудования", "Herdr keybindings": "Горячие клавиши Herdr",
    "Invoke last notification": "Открыть последнее уведомление", "Keybindings": "Горячие клавиши",
    "Keyboard backlight cycle": "Подсветка клавиатуры: переключить",
    "Keyboard brightness down": "Уменьшить яркость подсветки клавиатуры",
    "Keyboard brightness up": "Увеличить яркость подсветки клавиатуры", "Lock system": "Заблокировать систему",
    "Make webcam overlay larger": "Увеличить оверлей веб-камеры", "Make webcam overlay smaller": "Уменьшить оверлей веб-камеры",
    "Monitor scaling down": "Уменьшить масштаб монитора", "Monitor scaling up": "Увеличить масштаб монитора",
    "Move active window out of group": "Вынуть окно из группы",
    "Move grouped window focus left": "Фокус в группе влево", "Move grouped window focus right": "Фокус в группе вправо",
    "Move window": "Переместить окно", "Move window to group on bottom": "Переместить окно в группу снизу",
    "Move window to group on left": "Переместить окно в группу слева", "Move window to group on right": "Переместить окно в группу справа",
    "Move window to group on top": "Переместить окно в группу сверху", "Move window to scratchpad": "Убрать окно в scratchpad",
    "Move workspace to down monitor": "Рабочий стол на монитор снизу", "Move workspace to left monitor": "Рабочий стол на монитор слева",
    "Move workspace to right monitor": "Рабочий стол на монитор справа", "Move workspace to up monitor": "Рабочий стол на монитор сверху",
    "Music": "Музыка", "Music TUI": "Музыка (TUI)", "Mute": "Выключить звук", "Mute microphone": "Выключить микрофон",
    "Network": "Сеть", "New email": "Новое письмо", "Next track": "Следующий трек",
    "Next window in group": "Следующее окно в группе", "Next workspace": "Следующий рабочий стол",
    "Omarchy menu": "Меню Omarchy", "Open notification history": "История уведомлений", "Passwords": "Пароли",
    "Pause": "Пауза", "Play": "Воспроизвести", "Pop window out (float & pin)": "Вынести окно (плавающее и закреплённое)",
    "Power": "Питание", "Power menu": "Меню питания", "Previous track": "Предыдущий трек",
    "Previous window in group": "Предыдущее окно в группе", "Previous workspace": "Предыдущий рабочий стол",
    "Pseudo window": "Псевдо-окно", "Reset zoom": "Сбросить масштаб", "Resize window": "Изменить размер окна",
    "Restore window width": "Восстановить ширину окна", "Reveal active window on top": "Показать активное окно поверх",
    "Save window width": "Запомнить ширину окна", "Screenrecording": "Запись экрана", "Screenshot": "Снимок экрана",
    "Scroll active workspace backward": "Прокрутить рабочий стол назад", "Scroll active workspace forward": "Прокрутить рабочий стол вперёд",
    "Set reminder": "Создать напоминание", "Share": "Поделиться", "Show battery remaining": "Показать заряд батареи",
    "Show reminders": "Показать напоминания", "Show time": "Показать время",
    "Start dictation (push-to-talk)": "Начать диктовку (push-to-talk)", "Stop dictation (push-to-talk)": "Остановить диктовку (push-to-talk)",
    "Swap window down": "Поменять с окном снизу", "Swap window to the left": "Поменять с окном слева",
    "Swap window to the right": "Поменять с окном справа", "Swap window up": "Поменять с окном сверху",
    "Switch audio output": "Переключить вывод звука", "Switch media source": "Переключить источник медиа",
    "System menu": "Системное меню", "Terminal": "Терминал", "Theme menu": "Меню тем",
    "Tiled full screen": "Полный экран (тайлинг)", "Tmux keybindings": "Горячие клавиши Tmux",
    "Toggle dictation": "Диктовка вкл/выкл", "Toggle laptop display": "Экран ноутбука вкл/выкл",
    "Toggle laptop display mirroring": "Дублирование экрана ноутбука вкл/выкл",
    "Toggle locking on idle": "Блокировка при простое вкл/выкл", "Toggle menu": "Меню переключателей",
    "Toggle nightlight": "Ночной свет вкл/выкл", "Toggle scratchpad": "Показать/скрыть scratchpad",
    "Toggle silencing notifications": "Режим без уведомлений вкл/выкл",
    "Toggle single-window square aspect": "Квадратные пропорции одного окна вкл/выкл",
    "Toggle top bar": "Верхняя панель вкл/выкл", "Toggle touchpad": "Тачпад вкл/выкл", "Toggle weather": "Погода вкл/выкл",
    "Toggle window floating/tiling": "Окно: плавающее/тайловое", "Toggle window gaps": "Отступы окон вкл/выкл",
    "Toggle window grouping": "Группировка окон вкл/выкл", "Toggle window split": "Сменить направление разделения",
    "Toggle window transparency": "Прозрачность окна вкл/выкл", "Toggle workspace layout": "Сменить раскладку рабочего стола",
    "Transcode": "Перекодирование", "Universal copy": "Универсальное копирование", "Universal cut": "Универсальное вырезание",
    "Universal paste": "Универсальная вставка", "Volume down": "Тише", "Volume down precise": "Тише (точно)",
    "Volume up": "Громче", "Volume up precise": "Громче (точно)", "X Post": "Пост в X", "Zoom in": "Приблизить",
}
# "Expand/Shrink window <направление> [a little|a lot]"
DIRS = {"up": "вверх", "down": "вниз", "left": "влево", "right": "вправо"}
AMOUNT = {"": "", " a little": " (чуть-чуть)", " a lot": " (сильно)"}
for verb, ru in (("Expand", "Расширить"), ("Shrink", "Сузить")):
    for d, ru_d in DIRS.items():
        for a, ru_a in AMOUNT.items():
            TRANSLATIONS[f"{verb} window {d}{a}"] = f"{ru} окно {ru_d}{ru_a}"
# Правила «префикс + число»
PREFIX_RULES = [
    ("Switch to workspace ", "Перейти на рабочий стол "),
    ("Move window to workspace ", "Переместить окно на рабочий стол "),
    ("Move window silently to workspace ", "Переместить окно на рабочий стол (без перехода) "),
    ("Switch to group window ", "Перейти к окну группы № "),
    ("Bar panel ", "Панель бара "),
]


# Меню Tmux и Herdr: переводятся только описания (правая часть после « → »), чтобы не ломать выравнивание клавиш.
TMUX = {
    "Begin selection": "Начать выделение", "Copy selection": "Копировать выделенное",
    "Create session": "Создать сессию", "Create window": "Создать окно",
    "Focus pane down": "Фокус на панель ниже", "Focus pane left": "Фокус на панель слева",
    "Focus pane right": "Фокус на панель справа", "Focus pane up": "Фокус на панель выше",
    "Kill pane": "Закрыть панель", "Kill session": "Закрыть сессию", "Kill window": "Закрыть окно",
    "Move window left": "Сдвинуть окно влево", "Move window right": "Сдвинуть окно вправо",
    "Next session": "Следующая сессия", "Next window": "Следующее окно",
    "Previous session": "Предыдущая сессия", "Previous window": "Предыдущее окно",
    "Reload configuration": "Перечитать конфигурацию", "Rename session": "Переименовать сессию",
    "Rename window": "Переименовать окно", "Resize pane down": "Изменить размер панели вниз",
    "Resize pane left": "Изменить размер панели влево", "Resize pane right": "Изменить размер панели вправо",
    "Resize pane up": "Изменить размер панели вверх", "Send prefix": "Отправить префикс",
    "Show Tmux keybindings": "Показать горячие клавиши Tmux",
    "Split pane horizontally": "Разделить панель горизонтально", "Split pane vertically": "Разделить панель вертикально",
}
TMUX_RULES = [("Switch to window ", "Перейти к окну ")]
HERDR = {
    "Reload config": "Перечитать конфигурацию", "Help": "Справка", "Detach": "Отсоединиться",
    "Copy mode": "Режим копирования", "Split horizontal": "Разделить горизонтально",
    "Split vertical": "Разделить вертикально", "Close pane": "Закрыть панель", "Zoom": "Развернуть панель",
    "Last pane": "Предыдущая панель", "Focus pane left": "Фокус на панель слева",
    "Focus pane down": "Фокус на панель ниже", "Focus pane up": "Фокус на панель выше",
    "Focus pane right": "Фокус на панель справа", "Resize mode": "Режим изменения размера",
    "Resize pane left": "Изменить размер панели влево", "Resize pane down": "Изменить размер панели вниз",
    "Resize pane up": "Изменить размер панели вверх", "Resize pane right": "Изменить размер панели вправо",
    "Rename pane": "Переименовать панель", "New tab": "Новая вкладка", "Rename tab": "Переименовать вкладку",
    "Close tab": "Закрыть вкладку", "Switch tab": "Переключить вкладку", "Previous tab": "Предыдущая вкладка",
    "Next tab": "Следующая вкладка", "Move tab previous": "Сдвинуть вкладку влево",
    "Move tab next": "Сдвинуть вкладку вправо", "New workspace": "Новое рабочее пространство",
    "Rename workspace": "Переименовать рабочее пространство", "Close workspace": "Закрыть рабочее пространство",
    "Previous workspace": "Предыдущее рабочее пространство", "Next workspace": "Следующее рабочее пространство",
}
MENUS = {
    "tmux": ("omarchy-menu-tmux-keybindings", "Tmux keybindings", "Горячие клавиши Tmux", TMUX, TMUX_RULES, "SUPER + ALT + K"),
    "herdr": ("omarchy-menu-herdr-keybindings", "Herdr keybindings", "Горячие клавиши Herdr", HERDR, [], "SUPER + CTRL + K"),
}


def records_translator(table: dict, rules: list) -> str:
    """awk-функция translate_records: переводит описание в строках вида «КЛАВИШИ → описание»."""
    lines = ["translate_records() {", "  awk 'BEGIN {"]
    for k, v in sorted(table.items()):
        lines.append(f'    T["{k}"] = "{v}"')
    for i, (p, r) in enumerate(rules, 1):
        lines.append(f'    P[{i}] = "{p}"; R[{i}] = "{r}"')
    lines.append(f"    np = {len(rules)}")
    lines.append('    sep = " → "')
    lines.append("  }")
    lines.append("  {")
    lines.append("    i = index($0, sep)")
    lines.append("    if (i > 0) {")
    lines.append("      head = substr($0, 1, i - 1); action = substr($0, i + length(sep))")
    lines.append("      if (action in T) action = T[action]")
    lines.append("      else for (j = 1; j <= np; j++) {")
    lines.append("        if (index(action, P[j]) == 1 && substr(action, length(P[j]) + 1) ~ /^[0-9]+$/) {")
    lines.append("          action = R[j] substr(action, length(P[j]) + 1); break")
    lines.append("        }")
    lines.append("      }")
    lines.append("      $0 = head sep action")
    lines.append("    }")
    lines.append("    print")
    lines.append("  }'")
    lines.append("}")
    lines.append("")
    return "\n".join(lines) + "\n"


def awk_translator() -> str:
    lines = ["translate_entries() {", "  awk -F '\\t' 'BEGIN { OFS = \"\\t\""]
    for k, v in sorted(TRANSLATIONS.items()):
        lines.append(f'    T["{k}"] = "{v}"')
    for i, (p, r) in enumerate(PREFIX_RULES, 1):
        lines.append(f'    P[{i}] = "{p}"; R[{i}] = "{r}"')
    lines.append(f"    np = {len(PREFIX_RULES)}")
    lines.append('    sep = " → "')
    lines.append("  }")
    lines.append("  {")
    lines.append("    i = index($1, sep)")
    lines.append("    if (i > 0) {")
    lines.append("      head = substr($1, 1, i - 1); action = substr($1, i + length(sep))")
    lines.append("      if (action in T) action = T[action]")
    lines.append("      else for (j = 1; j <= np; j++) {")
    lines.append("        if (index(action, P[j]) == 1 && substr(action, length(P[j]) + 1) ~ /^[0-9]+$/) {")
    lines.append("          action = R[j] substr(action, length(P[j]) + 1); break")
    lines.append("        }")
    lines.append("      }")
    lines.append("      $1 = head sep action")
    lines.append("    }")
    lines.append("    print")
    lines.append("  }'")
    lines.append("}")
    lines.append("")
    return "\n".join(lines) + "\n"


def die(msg: str) -> None:
    print(f"keybindings-ru: {msg}", file=sys.stderr)
    sys.exit(1)


def replace_once(text: str, old: str, new: str, what: str) -> str:
    if text.count(old) != 1:
        die(f"не найден якорь «{what}» в стоковом omarchy-menu-keybindings (он изменился?) — ничего не изменено")
    return text.replace(old, new)


def build_wrapper() -> None:
    if not STOCK.exists():
        die(f"{STOCK} не найден")
    t = STOCK.read_text()
    translator = awk_translator()
    digest = hashlib.sha256(translator.encode()).hexdigest()[:10]

    t = replace_once(t, "prioritize_entries() {", translator + "prioritize_entries() {", "prioritize_entries()")
    t = replace_once(t, "    parse_binding_records |\n    prioritize_entries\n",
                     "    parse_binding_records |\n    prioritize_entries |\n    translate_entries\n", "конвейер записей")
    t = replace_once(t, "printf 'v11\\n'", f"printf 'v11-ru-{digest}\\n'", "ключ кеша")
    t = replace_once(t, "omarchy-menu-select 'Keybindings'", "omarchy-menu-select 'Горячие клавиши'", "заголовок меню")
    lines = t.split("\n", 1)
    t = lines[0] + "\n# Generated by omarchy-rus/keybindings-ru.py from " + str(STOCK) + ". Do not edit.\n" + lines[1]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(t)
    OUT.chmod(0o755)
    print(f"keybindings-ru: {OUT} ({len(TRANSLATIONS)} переводов + {len(PREFIX_RULES)} правил)")


def build_menu(name: str) -> None:
    stock_name, title, ru_title, table, rules, _ = MENUS[name]
    stock = STOCK_DIR / stock_name
    if not stock.exists():
        die(f"{stock} не найден")
    t = stock.read_text()
    translator = records_translator(table, rules)
    anchor = 'if [[ $print_only == "true" ]]; then\n  output_keybindings\n  exit 0\nfi\n'
    t = replace_once(t, anchor, translator + anchor.replace("  output_keybindings\n", "  output_keybindings | translate_records\n"),
                     "вывод --print")
    t = replace_once(t, "records=$(output_keybindings)", "records=$(output_keybindings | translate_records)", "records=")
    t = replace_once(t, f"omarchy-menu-select '{title}'", f"omarchy-menu-select '{ru_title}'", "заголовок меню")
    lines = t.split("\n", 1)
    t = lines[0] + "\n# Generated by omarchy-rus/keybindings-ru.py from " + str(stock) + ". Do not edit.\n" + lines[1]
    out = BIN / f"{stock_name}-ru"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(t)
    out.chmod(0o755)
    print(f"keybindings-ru: {out} ({len(table)} переводов)")


def patch_bindings() -> None:
    # Описание привязки оставляем английским: приоритет в списке считается по английским словам,
    # а перевод применяется уже после сортировки.
    block = (f'{MARK_BEGIN}\n'
             f'hl.unbind("SUPER + K")\n'
             f'o.bind("SUPER + K", "Keybindings", "{OUT}")\n')
    # Меню Tmux/Herdr, если их обёртки уже собраны.
    for _, (stock_name, en_title, _, _, _, combo) in MENUS.items():
        wrapper = BIN / f"{stock_name}-ru"
        if wrapper.exists():
            block += f'hl.unbind("{combo}")\no.bind("{combo}", "{en_title}", "{wrapper}")\n'
    block += f'{MARK_END}\n'
    text = BINDINGS.read_text() if BINDINGS.exists() else ""
    if MARK_BEGIN in text:
        start, end = text.index(MARK_BEGIN), text.index(MARK_END) + len(MARK_END) + 1
        text = text[:start] + block + text[end:]
    else:
        text = text.rstrip("\n") + "\n\n" + block
    BINDINGS.parent.mkdir(parents=True, exist_ok=True)
    BINDINGS.write_text(text)
    subprocess.run(["hyprctl", "reload"], capture_output=True)
    r = subprocess.run(["hyprctl", "configerrors"], capture_output=True, text=True)
    if r.stdout.strip():
        print("keybindings-ru: hyprctl configerrors:\n" + r.stdout, file=sys.stderr)
        sys.exit(1)
    print("keybindings-ru: SUPER+K -> omarchy-menu-keybindings-ru")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "wrapper":
        build_wrapper()
    elif cmd in MENUS:
        build_menu(cmd)
    elif cmd == "bindings":
        patch_bindings()
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
