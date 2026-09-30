#!/usr/bin/env bash
# title: Сертификаты Минцифры + автопроверка срока
# group: work
# default: off
# sudo: yes
# desc: корневой и подчинённый сертификаты (сверка SHA-256), недельный таймер проверки
set -euo pipefail
"$RUS_DIR/install-mincifry-ca.sh"
"$RUS_DIR/install-mincifry-ca.sh" --enable-timer
