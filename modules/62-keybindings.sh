#!/usr/bin/env bash
# title: Русское меню горячих клавиш (Super+K)
# group: ui
# default: on
# desc: копии меню горячих клавиш (Hyprland, Tmux, Herdr) с переводом; SUPER+K, SUPER+ALT+K, SUPER+CTRL+K и меню «Обучение» ведут на них
set -euo pipefail
"$RUS_DIR/keybindings-ru.py" wrapper
"$RUS_DIR/keybindings-ru.py" tmux || echo "keybindings: меню Tmux пропущено"
"$RUS_DIR/keybindings-ru.py" herdr || echo "keybindings: меню Herdr пропущено"
"$RUS_DIR/keybindings-ru.py" bindings
# пункты меню «Обучение → Горячие клавиши / Tmux / Herdr» тоже должен открывать русскую версию
"$RUS_DIR/translate-menu.py"
