#!/usr/bin/env bash
# title: Перевод меню Omarchy
# group: ui
# default: on
# desc: переопределения label/title в ~/.config/omarchy/extensions/omarchy-menu.jsonc
set -euo pipefail
"$RUS_DIR/translate-menu.py"
