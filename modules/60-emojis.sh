#!/usr/bin/env bash
# title: Поиск эмодзи по-русски
# group: ui
# default: on
# desc: клон плагина эмодзи с русскими названиями из CLDR в поиске (Super+Ctrl+E): «сердце», «огонь», «кот»
set -euo pipefail
"$RUS_DIR/translate-plugins.py" emojis
