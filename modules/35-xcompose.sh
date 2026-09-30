#!/usr/bin/env bash
# title: Типографика через Compose (₽ № «» —)
# group: safe
# default: on
# desc: добавляет в ~/.XCompose блок с русской типографикой (Compose = Caps Lock)
set -euo pipefail
F="$HOME/.XCompose"
BEGIN="# >>> omarchy-rus"
END="# <<< omarchy-rus"
touch "$F"
# Блок пересобираем целиком, остальное содержимое файла не трогаем.
sed -i "/^$BEGIN/,/^$END/d" "$F"
cat >> "$F" <<BLOCK
$BEGIN
# Compose + r + u + b = ₽, Compose + N + o = №, Compose + < + < = «, Compose + > + > = »
<Multi_key> <r> <u> <b> : "₽"
<Multi_key> <N> <o> : "№"
<Multi_key> <less> <less> : "«"
<Multi_key> <greater> <greater> : "»"
<Multi_key> <minus> <minus> <minus> : "—"
<Multi_key> <minus> <period> : "–"
<Multi_key> <period> <period> <period> : "…"
$END
BLOCK
command -v omarchy-restart-xcompose >/dev/null && omarchy-restart-xcompose || true
