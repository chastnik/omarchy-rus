#!/usr/bin/env bash
# title: Русская озвучка текста (speech-dispatcher + espeak-ng)
# group: ui
# default: on
# desc: экранный чтец/озвучка; язык по умолчанию — русский (RHVoice можно добавить из AUR)
set -euo pipefail
omarchy pkg add speech-dispatcher espeak-ng
CONF="$HOME/.config/speech-dispatcher/speechd.conf"
mkdir -p "$(dirname "$CONF")"
MARK="# omarchy-rus"
if ! grep -qF "$MARK" "$CONF" 2>/dev/null; then
  [ -f "$CONF" ] && cp "$CONF" "$CONF.bak.$(date +%s)"
  cat >> "$CONF" <<CFG
$MARK
DefaultLanguage "ru"
DefaultModule espeak-ng
CFG
fi
echo "Проверка: spd-say -l ru 'Привет, мир'"
