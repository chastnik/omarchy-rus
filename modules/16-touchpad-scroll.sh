#!/usr/bin/env bash
# title: Тачпад: натуральная прокрутка (как на MacBook)
# group: safe
# default: off
# desc: natural_scroll для тачпада в ~/.config/hypr/input.lua (с резервной копией) и перезагрузка Hyprland
set -euo pipefail
INPUT_LUA="$HOME/.config/hypr/input.lua"
MARK="-- omarchy-rus: touchpad scroll"
if grep -qF "$MARK" "$INPUT_LUA" || grep -q '^[[:space:]]*natural_scroll' "$INPUT_LUA"; then
  echo "natural_scroll уже настроен, пропускаю"; exit 0
fi
cp "$INPUT_LUA" "$INPUT_LUA.bak.$(date +%s)"
cat >> "$INPUT_LUA" <<BLOCK

$MARK
hl.config({
  input = {
    touchpad = {
      natural_scroll = true,
    },
  },
})
BLOCK
hyprctl reload
hyprctl configerrors
