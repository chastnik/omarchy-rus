#!/usr/bin/env bash
# title: ЭЦП и смарт-карты (PC/SC: Рутокен/JaCarta и др.)
# group: work
# default: off
# sudo: yes
# desc: pcsclite, ccid, opensc, pcsc-tools и служба pcscd; КриптоПро ставится вручную
set -euo pipefail
omarchy pkg add pcsclite ccid opensc pcsc-tools
sudo systemctl enable --now pcscd.socket
cat <<'TXT'
Готово: смарт-карты и токены видны через PC/SC (проверка: pcsc_scan).
Вручную (проприетарное, требует регистрации на сайтах производителей):
  - КриптоПро CSP для Linux: cryptopro.ru/products/cryptopro-csp/downloads
  - плагин КриптоПро ЭЦП Browser plug-in, драйверы Рутокен / JaCarta (rutoken.ru, aladdin-rd.ru)
  - Госуслуги: плагин и сертификаты — отдельный пункт «Сертификаты Минцифры».
TXT
