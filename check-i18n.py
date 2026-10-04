#!/usr/bin/env python3
"""Проверка полноты русификации: что в Omarchy осталось по-английски.

Сравнивает словари проекта с тем, что есть в системе сейчас (после «omarchy update» там могут быть новые строки):
  menu           подписи и заголовки меню Omarchy, которых нет в translate-menu.py (LABELS/TITLES);
  notifications  тексты уведомлений из скриптов /usr/share/omarchy/bin, которых нет в data/notifications-ru.json;
  plugins        английские литералы в клонах плагинов (~/.config/omarchy/plugins/<user>.*) после перевода;
  patches        правки PATCHES из translate-plugins.py, для которых в клоне нет ни старого, ни нового текста.

Использование:
  check-i18n.py [menu|notifications|plugins|patches ...]   отчёт в терминал (без аргументов — всё)
  check-i18n.py --strict                                  код возврата 1, если что-то найдено (для CI и скриптов)
  check-i18n.py --notify                                  при находках отправить уведомление (для post-update хука)

Что считать брендом или техническим именем и не показывать — в data/i18n-ignore.txt (по строке на запись).
Для plugins проверка эвристическая: берутся литералы у text/label/title/placeholderText/description/tooltip и т.п.
"""
import getpass
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGINS_DIR = Path.home() / ".config/omarchy/plugins"
USER = getpass.getuser()
BIN_DIR = Path("/usr/share/omarchy/bin")
IGNORE_FILE = HERE / "data" / "i18n-ignore.txt"

UI_KEYS = ("text", "label", "title", "placeholderText", "description", "subtitle", "tooltip", "tooltipText",
           "displayName", "hint", "headline", "message", "emptyText", "activeTooltipText", "inactiveTooltipText")
KEY_LITERAL = re.compile(r'\b(' + "|".join(UI_KEYS) + r')\s*:\s*"((?:[^"\\\n]|\\.)*)"')
TERNARY_LITERAL = re.compile(r'[?:]\s*"((?:[^"\\\n]|\\.)*)"')
PHRASE = re.compile(r"^[A-Z][A-Za-z0-9'’ ,.\-&/()…!?:%+]*[a-z][A-Za-z0-9'’ ,.\-&/()…!?:%+]*$")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ignored() -> set:
    try:
        return {l.strip() for l in IGNORE_FILE.read_text().splitlines() if l.strip() and not l.startswith("#")}
    except OSError:
        return set()


def check_menu(skip: set) -> list:
    mod = load_module(HERE / "translate-menu.py", "translate_menu")
    if not mod.DEFAULT.exists():
        return [("menu", f"не найден {mod.DEFAULT}")]
    raw = mod.DEFAULT.read_text()
    raw = re.sub(r"^\s*//[^\n]*(\n|$)", "", raw, flags=re.M)
    raw = re.sub(r",(\s*[}\]])", r"\1", raw)
    data = json.loads(raw)
    data = data.get("items", data)
    out, seen = [], set()
    for key, entry in data.items():
        for field, table in (("label", mod.LABELS), ("title", mod.TITLES)):
            v = entry.get(field)
            if not v or v in table or v in skip or v in seen or not re.search(r"[A-Za-z]{2}", v):
                continue
            # title без перевода допустим, если label этого же пункта переведён тем же словом
            if field == "title" and v in mod.LABELS:
                continue
            seen.add(v)
            out.append(("menu", f'{key}: {field} "{v}"'))
    return out


def notification_strings() -> dict:
    found = {}
    for f in BIN_DIR.glob("*"):
        try:
            text = f.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        for m in re.finditer(r"omarchy-notification-send([^\n]*(?:\\\n[^\n]*)*)", text):
            for q in re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1)):
                if re.search(r"[A-Za-z]{3}", q) and not q.startswith("$") and "/" not in q.split()[0:1]:
                    found.setdefault(q, f.name)
    return found


def check_notifications(skip: set) -> list:
    d = json.loads((HERE / "data" / "notifications-ru.json").read_text())
    exact = set(d["exact"])
    patterns = [re.compile(p) for p, _ in d["patterns"]]
    out = []
    for s, src in sorted(notification_strings().items()):
        if s in exact or s in skip or any(p.search(re.sub(r"\$\{?\w+\}?", "1", s)) for p in patterns):
            continue
        # строки, целиком собранные из переменных и путей, не переводим
        if not re.search(r"[A-Za-z]{3}", re.sub(r"\$\{?\w+\}?", "", s)):
            continue
        out.append(("notifications", f'{src}: "{s}"'))
    return out


def check_plugins(skip: set) -> list:
    mod = load_module(HERE / "translate-plugins.py", "translate_plugins")
    out, seen = [], set()
    for name, table in mod.TRANSLATIONS.items():
        target = PLUGINS_DIR / f"{USER}.{name}"
        if not target.exists():
            continue
        for f in sorted(list(target.rglob("*.qml")) + list(target.rglob("*.js"))):
            for n, line in enumerate(f.read_text().splitlines(), 1):
                if line.lstrip().startswith("//"):
                    continue
                cands = [m.group(2) for m in KEY_LITERAL.finditer(line)]
                cands += [m.group(1) for m in TERNARY_LITERAL.finditer(line)]
                for s in cands:
                    if s in table or s in skip or not PHRASE.match(s) or len(s) < 3:
                        continue
                    if (name, s) in seen:
                        continue
                    seen.add((name, s))
                    out.append(("plugins", f'{name}/{f.relative_to(target)}:{n}: "{s}"'))
    return out


def check_patches(_skip: set) -> list:
    mod = load_module(HERE / "translate-plugins.py", "translate_plugins")
    out = []
    for pname, fname, old, new, _count in mod.PATCHES:
        f = PLUGINS_DIR / f"{USER}.{pname}" / fname
        if not f.exists():
            continue
        text = f.read_text()
        if old not in text and new not in text:
            out.append(("patches", f"{pname}/{fname}: фрагмент не найден (плагин изменился?): {old[:60]}"))
    return out


CHECKS = {"menu": check_menu, "notifications": check_notifications, "plugins": check_plugins, "patches": check_patches}
TITLES = {"menu": "Меню Omarchy", "notifications": "Уведомления", "plugins": "Плагины бара", "patches": "Правки PATCHES"}


def main() -> int:
    args = sys.argv[1:]
    strict, notify = "--strict" in args, "--notify" in args
    names = [a for a in args if not a.startswith("--")] or list(CHECKS)
    bad = [n for n in names if n not in CHECKS]
    if bad:
        print(f"check-i18n: неизвестные проверки: {', '.join(bad)}", file=sys.stderr)
        return 2
    skip = ignored()
    total = 0
    for n in names:
        items = CHECKS[n](skip)
        total += len(items)
        print(f"\n== {TITLES[n]}: {'всё переведено' if not items else f'не переведено {len(items)}'}")
        for _, msg in items:
            print(f"  {msg}")
    print(f"\ncheck-i18n: найдено {total}")
    if total and notify:
        subprocess.run(["omarchy-notification-send", "-g", "", "Русификация: есть непереведённое",
                        f"Найдено строк: {total}. Подробности: check-i18n.py"], capture_output=True)
    return 1 if (total and strict) else 0


if __name__ == "__main__":
    sys.exit(main())
