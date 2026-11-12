#!/usr/bin/env python3
"""Проверки модулей, которые не ловит shellcheck.

- метаданные по смыслу: имя файла NN-id.sh, поля title/group/default/desc, допустимые значения, уникальные id;
- set -euo pipefail в каждом модуле;
- модуль, который вызывает sudo (сам или через скрипт из репозитория), помечен «# sudo: yes»:
  иначе установщик не спросит пароль заранее, и запрос sudo спрячется за спиннером;
- модуль не ждёт ввода (read -p, gum, /dev/tty): в анимированном режиме у модулей нет stdin;
- таблицы модулей в README.md и README.en.md совпадают с кодом: тот же набор id, группа и отметка «по умолчанию».

Запуск: python3 tests/check-modules.py (из корня репозитория). Код возврата 1 — есть ошибки.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES = os.path.join(ROOT, "modules")

# Как группы называются в таблицах README (README.md берёт первое слово заголовка группы из install.sh)
README_GROUPS_EN = {"base": "Base", "safe": "Simple", "apps": "Apps", "ui": "UI", "work": "Work"}

NEEDS_SUDO = re.compile(
    r"\bsudo\b|omarchy[ -]pkg[ -]add|\bpacman\s+-S(?![ilsgp])|\btee\s+(-a\s+)?/etc/|\binstall\b.*\s/usr/|\bupdate-ca-trust\b"
)
WAITS_INPUT = re.compile(r"\bread\s+(-\w*p|-p)|\bgum\s+(choose|confirm|input|write|filter|file)\b|/dev/tty|\bselect\s+\w+\s+in\b")
RUS_REF = re.compile(r"\$\{?RUS_DIR\}?/([A-Za-z0-9._/-]+)")

errors = []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def code_lines(text):
    """Строки без комментариев (шебанг и метаданные — тоже комментарии)."""
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        yield n, line


def meta(text, key):
    m = re.search(rf"^# {key}:[ \t]*(.*)$", text, re.M)
    return m.group(1).strip() if m else None


def install_groups():
    src = open(os.path.join(ROOT, "install.sh"), encoding="utf-8").read()
    order = re.search(r"^GROUP_ORDER=\(([^)]*)\)", src, re.M).group(1).split()
    titles = dict(re.findall(r"^\s*\[(\w+)\]=\"([^\"]+)\"", src, re.M))
    return order, titles


def helper_uses_sudo(rel, seen=None):
    """Скрипт из репозитория, вызываемый модулем, сам вызывает sudo?"""
    seen = seen or set()
    path = os.path.join(ROOT, rel)
    if rel in seen or not os.path.isfile(path):
        return False
    seen.add(rel)
    text = open(path, encoding="utf-8", errors="replace").read()
    if path.endswith(".py"):
        return bool(re.search(r"['\"]sudo['\"]", text))
    return any(NEEDS_SUDO.search(line) for _, line in code_lines(text))


def readme_table(path):
    """{id: (группа, отметка)} из таблицы модулей README (строки вида | `id` | Группа | ✓ | …)."""
    rows = {}
    for line in open(path, encoding="utf-8"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and re.fullmatch(r"`[a-z0-9-]+`", cells[0]) and cells[2] in ("✓", "—"):
            mid = cells[0].strip("`")
            if mid in rows:
                err(os.path.basename(path), f"модуль {mid} дважды в таблице")
            rows[mid] = (cells[1], cells[2])
    return rows


def main():
    order, titles = install_groups()
    modules = {}
    for name in sorted(os.listdir(MODULES)):
        if not name.endswith(".sh"):
            continue
        where = f"modules/{name}"
        path = os.path.join(MODULES, name)
        m = re.fullmatch(r"(\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)\.sh", name)
        if not m:
            err(where, "имя должно быть вида NN-id.sh (id — строчные латинские буквы, цифры и дефисы)")
            continue
        mid = m.group(2)
        if mid in modules:
            err(where, f"id {mid} уже занят модулем {modules[mid]['file']}")
        text = open(path, encoding="utf-8").read()
        info = {"file": name, **{k: meta(text, k) for k in ("title", "group", "default", "desc", "sudo")}}
        modules[mid] = info

        if not text.startswith("#!/usr/bin/env bash\n"):
            err(where, "первая строка должна быть #!/usr/bin/env bash")
        if not os.access(path, os.X_OK):
            err(where, "файл не исполняемый")
        for k in ("title", "group", "default", "desc"):
            if not info[k]:
                err(where, f"нет поля «# {k}:» или оно пустое")
        if info["group"] and info["group"] not in order:
            err(where, f"group: {info['group']} — нет такой группы (есть: {', '.join(order)})")
        if info["default"] and info["default"] not in ("on", "off"):
            err(where, f"default: {info['default']} — допустимо on или off")
        if info["sudo"] is not None and info["sudo"] != "yes":
            err(where, f"sudo: {info['sudo']} — допустимо только yes (или не указывать поле)")
        if not re.search(r"^set -euo pipefail$", text, re.M):
            err(where, "нет строки set -euo pipefail")

        # sudo: сам модуль или вызываемые им скрипты репозитория
        reason = None
        for n, line in code_lines(text):
            if NEEDS_SUDO.search(line):
                reason = f"строка {n}: {line.strip()[:70]}"
                break
            for ref in RUS_REF.findall(line):
                if helper_uses_sudo(ref):
                    reason = f"строка {n} вызывает {ref}, а он использует sudo"
                    break
            if reason:
                break
        if reason and info["sudo"] != "yes":
            err(where, f"нужен sudo, но нет «# sudo: yes» ({reason})")

        for n, line in code_lines(text):
            if WAITS_INPUT.search(line):
                err(where, f"строка {n} ждёт ввода — в анимированном режиме у модулей нет stdin: {line.strip()[:70]}")

    for readme, groups in (
        ("README.md", {g: titles[g].split()[0] for g in order}),
        ("README.en.md", README_GROUPS_EN),
    ):
        rows = readme_table(os.path.join(ROOT, readme))
        for mid in sorted(set(modules) - set(rows)):
            err(readme, f"нет модуля {mid} в таблице модулей")
        for mid in sorted(set(rows) - set(modules)):
            err(readme, f"в таблице есть {mid}, а модуля modules/NN-{mid}.sh нет")
        for mid in sorted(set(rows) & set(modules)):
            group, mark = rows[mid]
            info = modules[mid]
            want_mark = "✓" if info["default"] == "on" else "—"
            if mark != want_mark:
                err(readme, f"{mid}: в таблице «{mark}», а в модуле default: {info['default']}")
            want_group = groups.get(info["group"])
            if want_group and group != want_group:
                err(readme, f"{mid}: в таблице группа «{group}», а в модуле {info['group']} («{want_group}»)")

    if errors:
        print("\n".join(errors))
        print(f"\nОшибок: {len(errors)}")
        return 1
    print(f"Модулей: {len(modules)}, ошибок нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
