#!/usr/bin/env bash
# title: Перевод панелей и оверлеев (календарь/сеть/звук/питание и др.)
# group: ui
# default: on
# desc: клонирует плагины Omarchy и переводит их; погоду переводит отдельный пункт
set -euo pipefail
"$RUS_DIR/translate-plugins.py" --except weather
