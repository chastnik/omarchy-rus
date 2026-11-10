#!/usr/bin/env bash
# title: Русский язык Omarchy и локаль ru_RU.UTF-8 + раскладка US/RU
# group: base
# default: on
# sudo: yes
# desc: omarchy language ru (встроенный перевод меню, бара, панелей, Super+K, уведомлений), системная LANG=ru_RU.UTF-8, раскладка us,ru (Left Alt + Right Alt)
set -euo pipefail
sudo sed -i 's/^#ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen
sudo locale-gen
sudo localectl set-locale LANG=ru_RU.UTF-8
sudo localectl set-x11-keymap us,ru pc105 "" grp:alts_toggle
# Язык интерфейса Omarchy (с 4.5): ~/.config/omarchy/language и LANG сессии через uwsm.
omarchy language ru
