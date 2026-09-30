#!/usr/bin/env bash
# title: Тачпад: жест тремя пальцами для смены рабочих столов
# group: safe
# default: off
# desc: hl.gesture (3 пальца влево/вправо) в ~/.config/hypr/input.lua (с резервной копией) и перезагрузка Hyprland
set -euo pipefail
INPUT_LUA="$HOME/.config/hypr/input.lua"
MARK="-- omarchy-rus: touchpad gestures"
if grep -qF "$MARK" "$INPUT_LUA" || grep -q '^[[:space:]]*hl\.gesture(.*"workspace"' "$INPUT_LUA"; then
  echo "жест смены рабочих столов уже настроен, пропускаю"; exit 0
fi
cp "$INPUT_LUA" "$INPUT_LUA.bak.$(date +%s)"
cat >> "$INPUT_LUA" <<BLOCK

$MARK
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
BLOCK
hyprctl reload
hyprctl configerrors
