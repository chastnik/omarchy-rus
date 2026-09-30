#!/usr/bin/env bash
# title: DNS для России в виджете сети (Yandex/DNS4EU/NextDNS вместо Cloudflare/Google)
# group: apps
# default: on
# sudo: yes
# desc: пилюли DNS в панели сети + root-helper /usr/local/bin/omarchy-dns-ru (смена DNS — через polkit-диалог)
set -euo pipefail
# 1. клон виджета сети (стоковый править нельзя)
"$RUS_DIR/translate-plugins.py" network
# 2. helper: копия стокового omarchy-dns с новыми провайдерами; ставится от root, чтобы его
#    нельзя было подменить без пароля (он исполняется от root после подтверждения)
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
"$RUS_DIR/dns-ru.py" helper "$tmp"
sudo install -m 0755 -o root -g root "$tmp" /usr/local/bin/omarchy-dns-ru
# 3. пилюли и вызов helper в клоне виджета
"$RUS_DIR/dns-ru.py" panel
echo "Готово: пилюли DNS — DHCP, Yandex, DNS4EU, NextDNS, Custom. Смена DNS запрашивает подтверждение (polkit)."
