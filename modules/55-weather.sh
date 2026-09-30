#!/usr/bin/env bash
# title: Виджет погоды: °C и русский интерфейс
# group: apps
# default: on
# desc: unit=metric в shell.json, перевод панели погоды (клон плагина), геокодинг на русском
set -euo pipefail
CFG="$HOME/.config/omarchy/shell.json"
if [ -f "$CFG" ]; then
  cp "$CFG" "$CFG.bak.$(date +%s)"
  tmp=$(mktemp)
  # Явно metric для любого виджета погоды в раскладке бара (и оригинал, и клон).
  jq '.bar.layout |= with_entries(.value |= map(
        if ((.id // "") | test("weather$")) then . + {unit: "metric"} else . end))' "$CFG" > "$tmp" \
    && mv "$tmp" "$CFG" || rm -f "$tmp"
fi
"$RUS_DIR/translate-plugins.py" weather
