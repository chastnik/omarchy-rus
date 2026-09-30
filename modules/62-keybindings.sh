#!/usr/bin/env bash
# title: Русское меню горячих клавиш (Super+K)
# group: ui
# default: on
# desc: копия omarchy-menu-keybindings с переводом описаний; SUPER+K и пункт меню «Обучение» ведут на неё
set -euo pipefail
"$RUS_DIR/keybindings-ru.py" wrapper
"$RUS_DIR/keybindings-ru.py" bindings
# пункт меню «Обучение → Горячие клавиши» тоже должен открывать русскую версию
"$RUS_DIR/translate-menu.py"
