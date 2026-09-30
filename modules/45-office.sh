#!/usr/bin/env bash
# title: LibreOffice: русский язык + переносы + тезаурус
# group: safe
# default: on
# desc: libreoffice-*-ru, hyphen-ru, mythes-ru (если LibreOffice установлен)
set -euo pipefail
if pacman -Q libreoffice-fresh >/dev/null 2>&1; then lo=fresh
elif pacman -Q libreoffice-still >/dev/null 2>&1; then lo=still
else echo "LibreOffice не установлен — пропускаю."; exit 0; fi
pkgs=()
for p in "libreoffice-$lo-ru" hyphen-ru mythes-ru; do
  if pacman -Si "$p" >/dev/null 2>&1; then pkgs+=("$p"); else echo "пакета $p нет в репозиториях, пропускаю"; fi
done
[ ${#pkgs[@]} -gt 0 ] && omarchy pkg add "${pkgs[@]}"
exit 0
