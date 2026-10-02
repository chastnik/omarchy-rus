#!/usr/bin/env bash
# title: Раскладка US/RU в Hyprland
# group: base
# default: on
# desc: добавляет us,ru в ~/.config/hypr/input.lua (с резервной копией) и перезагружает Hyprland
set -euo pipefail
INPUT_LUA="$HOME/.config/hypr/input.lua"
MARK="-- omarchy-rus: layouts"
if ! grep -qF -- "$MARK" "$INPUT_LUA"; then
  cp "$INPUT_LUA" "$INPUT_LUA.bak.$(date +%s)"
  { echo; echo "$MARK"; cat "$RUS_DIR/input.lua.snippet"; } >> "$INPUT_LUA"
  hyprctl reload
  hyprctl configerrors
fi
