#!/usr/bin/env python3
"""Клоны встроенных плагинов Omarchy для того, чего нет во встроенной локализации.

С Omarchy 4.5 интерфейс переведён самим Omarchy (`omarchy language ru`, каталоги
/usr/share/omarchy/default/i18n/ru/), поэтому строки плагинов больше не переводятся. Клоны нужны только для:
  network  пилюли российских DNS-провайдеров (правку делает dns-ru.py panel);
  weather  поиск городов на языке интерфейса (стоковый геокодер всегда запрашивает английский);
  emojis   поиск эмодзи по русским названиям (data/emojis-ru.json, CLDR).

Встроенные плагины лежат в /usr/share/omarchy/ и правке не подлежат, поэтому скрипт клонирует плагин
(`omarchy plugin clone omarchy.<имя>`), если клона ещё нет, и применяет PATCHES. Скрипт идемпотентен.
Клон не получает обновлений оригинала: после `omarchy update` смотрите `--check`.

Использование:
  translate-plugins.py [имя ...] [--except имя ...]   создать клоны и применить правки (без аргументов — все)
  translate-plugins.py --check [--notify]             найти клоны, чей оригинал изменился после «omarchy update»
  translate-plugins.py --refresh [имя ...]            пересоздать устаревшие (или указанные) клоны
"""
import getpass
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PLUGINS_DIR = Path.home() / ".config/omarchy/plugins"
USER = getpass.getuser()
CLONES = ("network", "weather", "emojis")
PLUGINS_SRC = Path("/usr/share/omarchy/shell/plugins")
STATE_FILE = Path.home() / ".local/share/omarchy-rus/clones.json"

# Точечные правки кода: (плагин, файл, старое, новое, ожидаемое число вхождений).
PATCHES = [
    ("weather", "Panel.qml", '&language=en&format=json"',
     '&language=" + Commons.I18n.language.split("-")[0] + "&format=json"', 1),
]


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


def wait_shell(seconds: int = 20) -> None:
    """omarchy plugin clone/remove перезагружают шелл; следующая команда сразу после этого получает
    «omarchy-shell is not responding». Ждём, пока шелл снова ответит."""
    for _ in range(seconds):
        if subprocess.run(["omarchy-shell", "shell", "ping"], capture_output=True).returncode == 0:
            return
        time.sleep(1)


def plugin_cmd(args: list, done) -> subprocess.CompletedProcess:
    """omarchy plugin … с повтором, пока не выполнится условие done() (шелл мог не ответить)."""
    for _ in range(3):
        wait_shell()
        r = subprocess.run(["omarchy", "plugin", *args], capture_output=True, text=True)
        if done():
            return r
    return r


def made_by_v1(name: str) -> bool:
    """Клон сделан omarchy-rus 1.x (переведённые строки, код Omarchy до 4.5): его нужно пересоздать."""
    return (PLUGINS_DIR / f"{USER}.{name}").exists() and name not in load_state().get("v2", [])


def remove_clone(name: str) -> bool:
    """Удаляет клон; Omarchy возвращает оригинал на его место в баре."""
    target = PLUGINS_DIR / f"{USER}.{name}"
    plugin_cmd(["remove", f"{USER}.{name}", "--yes"], lambda: not target.exists())
    return not target.exists()


def ensure_clone(name: str) -> Path | None:
    target = PLUGINS_DIR / f"{USER}.{name}"
    if made_by_v1(name):
        if not remove_clone(name):
            print(f"translate-plugins: не удалось убрать старый клон {name}: omarchy plugin remove {USER}.{name} --yes",
                  file=sys.stderr)
            return None
        print(f"translate-plugins: старый клон {name} (omarchy-rus 1.x) удалён, создаю заново")
    if target.exists():
        return target
    r = plugin_cmd(["clone", f"omarchy.{name}"], target.exists)
    if not target.exists():
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
    target = ensure_clone(name)
    if not target:
        return False
    ok = True
    for pname, fname, old, new, count in PATCHES:
        if pname != name:
            continue
        f = target / fname
        text = f.read_text()
        if new in text:
            continue
        if text.count(old) != count:
            print(f"translate-plugins: {name}/{fname}: ожидалось {count} вхождений фрагмента, найдено {text.count(old)}: {old[:50]}",
                  file=sys.stderr)
            ok = False
            continue
        f.write_text(text.replace(old, new))
    if name == "emojis":
        print(f"translate-plugins: emojis: добавлены русские названия к {merge_emoji_keywords(target)} эмодзи")
    print(f"translate-plugins: {name}: готово")
    return ok


def record_baseline(names) -> None:
    """Запоминает, с какой версией оригинала сделан клон (для --check)."""
    state = load_state()
    for n in names:
        target = PLUGINS_DIR / f"{USER}.{n}"
        if target.exists():
            state.setdefault("plugins", {})[n] = related_originals(n, target)
            if n not in state.setdefault("v2", []):
                state["v2"].append(n)
    save_state(state)


def stale_clones() -> tuple:
    """(устаревшие, без базовой точки): клоны, чей оригинал изменился после «omarchy update»."""
    state = load_state().get("plugins", {})
    stale, unknown = [], []
    for n in CLONES:
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
    print("Пересоздать клоны: translate-plugins.py --refresh")
    if notify:
        subprocess.run(["omarchy-notification-send", "-g", "", "Русификация: плагины обновились",
                        f"Изменились оригиналы: {', '.join(stale)}. Выполните: translate-plugins.py --refresh"],
                       capture_output=True)
    return 3


def cmd_refresh(names) -> int:
    stale = names or stale_clones()[0]
    if not stale:
        print("translate-plugins: обновлять нечего")
        return 0
    bad = [n for n in stale if n not in CLONES]
    if bad:
        print(f"translate-plugins: неизвестные плагины: {', '.join(bad)}", file=sys.stderr)
        return 2
    failed = 0
    for n in stale:
        # Через omarchy plugin remove, а не rmtree: иначе бар до нового клона ссылается на пустое место.
        if (PLUGINS_DIR / f"{USER}.{n}").exists() and not remove_clone(n):
            print(f"translate-plugins: не удалось убрать клон {n}", file=sys.stderr)
            failed += 1
            continue
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
    selected = args or list(CLONES)
    unknown = [n for n in selected if n not in CLONES]
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
