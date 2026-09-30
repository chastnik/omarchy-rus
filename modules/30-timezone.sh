#!/usr/bin/env bash
# title: Часовой пояс и российские NTP-серверы
# group: safe
# default: on
# sudo: yes
# desc: Europe/Moscow (переменная RUS_TZ) и ru.pool.ntp.org для systemd-timesyncd
set -euo pipefail
TZ_NAME="${RUS_TZ:-Europe/Moscow}"
if [ "$(timedatectl show -p Timezone --value)" != "$TZ_NAME" ]; then
  sudo timedatectl set-timezone "$TZ_NAME"
fi
sudo install -d /etc/systemd/timesyncd.conf.d
printf '[Time]\nNTP=0.ru.pool.ntp.org 1.ru.pool.ntp.org 2.ru.pool.ntp.org 3.ru.pool.ntp.org\nFallbackNTP=pool.ntp.org time.cloudflare.com\n' \
  | sudo tee /etc/systemd/timesyncd.conf.d/10-omarchy-rus.conf >/dev/null
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd
