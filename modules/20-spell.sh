#!/usr/bin/env bash
# title: Словари орфографии и man-страницы
# group: base
# default: on
# desc: hunspell-ru, aspell-ru, man-pages-ru
set -euo pipefail
omarchy pkg add hunspell-ru aspell-ru man-pages-ru
# Для Firefox (по желанию): omarchy pkg add firefox-i18n-ru
