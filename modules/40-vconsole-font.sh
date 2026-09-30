#!/usr/bin/env bash
# title: Кириллический шрифт консоли (TTY)
# group: safe
# default: on
# sudo: yes
# desc: FONT=LatArCyrHeb-16 в /etc/vconsole.conf (применится после перезагрузки)
set -euo pipefail
FONT_NAME="LatArCyrHeb-16"
ls /usr/share/kbd/consolefonts/"$FONT_NAME".psfu* >/dev/null 2>&1 || { echo "шрифт $FONT_NAME не найден" >&2; exit 1; }
if grep -q '^FONT=' /etc/vconsole.conf; then
  sudo sed -i "s/^FONT=.*/FONT=$FONT_NAME/" /etc/vconsole.conf
else
  echo "FONT=$FONT_NAME" | sudo tee -a /etc/vconsole.conf >/dev/null
fi
