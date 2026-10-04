#!/usr/bin/env bash
# title: Браузеры: русский интерфейс и проверка орфографии
# group: apps
# default: on
# desc: Chromium/Chrome/Brave: --lang=ru и предпочитаемые языки в флагах запуска; Firefox: языковой пакет; уже запущенные браузеры нужно перезапустить
set -euo pipefail
MARK="# omarchy-rus: language"
changed=0

# Chromium-семейство читает флаги из ~/.config/<браузер>-flags.conf (по одному на строку).
# Флаги не трогают профиль, поэтому безопасны при запущенном браузере (действуют после перезапуска).
for flags in chromium brave chrome; do
  bin="$flags"; [ "$flags" = chrome ] && bin="google-chrome-stable"
  command -v "$bin" >/dev/null || continue
  f="$HOME/.config/$flags-flags.conf"
  if [ -f "$f" ] && grep -qF -- "$MARK" "$f"; then
    echo "$flags: язык уже настроен, пропускаю"; continue
  fi
  [ -f "$f" ] && cp "$f" "$f.bak.$(date +%s)"
  {
    [ -f "$f" ] && [ -n "$(tail -c1 "$f")" ] && echo
    echo "$MARK"
    echo "--lang=ru"
    echo "--accept-lang=ru-RU,ru,en-US,en"
  } >> "$f"
  echo "$flags: добавлены --lang=ru и --accept-lang в $f"
  changed=1
done

# Firefox: интерфейс берётся из языкового пакета и системной локали.
if pacman -Q firefox >/dev/null 2>&1; then
  omarchy pkg add firefox-i18n-ru
  changed=1
fi

[ "$changed" = 1 ] && echo "Перезапустите браузер, чтобы язык применился." || echo "Подходящих браузеров не найдено."
exit 0
