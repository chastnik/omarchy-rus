#!/usr/bin/env bash
# title: Русский fastfetch («О системе»)
# group: ui
# default: on
# desc: ~/.config/fastfetch/config.jsonc на основе системного, с русскими заголовками
set -euo pipefail
SRC=/etc/fastfetch/config.jsonc
DST="$HOME/.config/fastfetch/config.jsonc"
MARK="// omarchy-rus: generated from $SRC"
[ -f "$SRC" ] || { echo "$SRC не найден — пропускаю."; exit 0; }
mkdir -p "$(dirname "$DST")"
if [ -f "$DST" ] && ! grep -qF "$MARK" "$DST"; then
  cp "$DST" "$DST.bak.$(date +%s)"
  echo "fastfetch: прежний конфиг сохранён в $DST.bak.*"
fi
python3 - "$SRC" "$DST" "$MARK" <<'PY'
import re, sys
src, dst, mark = sys.argv[1:4]
text = open(src, encoding="utf-8").read()
WIDTH = 52  # ширина рамки между углами

def header(old, new):
    # Заголовок рамки перестраиваем так, чтобы ширина осталась прежней.
    left = (WIDTH - len(new) + 1) // 2
    right = WIDTH - len(new) - left
    pat = re.compile(r"┌─+" + re.escape(old) + r"─+┐")
    return pat, "┌" + "─" * left + new + "─" * right + "┐"

for old, new in [("Hardware", "Железо"), ("Software", "Программы"),
                 ("Age / Uptime / Update", "Возраст / Аптайм / Обновление")]:
    pat, rep = header(old, new)
    text = pat.sub(rep, text)

# Подписи ключей и единицы: точные фрагменты, глифы Nerd Font сохраняются.
for old, new in [(" OS Age\"", " Возраст ОС\""), (" Uptime\"", " Аптайм\""),
                 (" Update\"", " Обновление\""), (" / 86400 )) days\"", " / 86400 )) дн.\"")]:
    text = text.replace(old, new)
open(dst, "w", encoding="utf-8").write(mark + "\n" + text)
PY
fastfetch --config "$DST" >/dev/null 2>&1 && echo "fastfetch: конфиг применён" || echo "fastfetch: проверьте $DST (запуск дал ошибку)" >&2
