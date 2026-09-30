#!/usr/bin/env bash
# Установка корневого и подчинённого сертификатов Минцифры (Russian Trusted Root/Sub CA).
# Нужны для госсайтов и части банков. Ставит в:
#   - системное хранилище (update-ca-trust; curl, git, Python, Electron и т.п.)   [sudo]
#   - NSS-базу ~/.pki/nssdb (Chromium/Chrome/Brave/Edge)
#   - профили Firefox (security.enterprise_roots.enabled -> берёт системное хранилище)
# Сертификаты скачиваются с gu-st.ru (Госуслуги) и сверяются с зафиксированными SHA-256.
# Удаление: ./install-mincifry-ca.sh --remove
# Проверка срока и отпечатков (без sudo, без установки): ./install-mincifry-ca.sh --check
# Еженедельная автопроверка (systemd user timer): ./install-mincifry-ca.sh --enable-timer | --disable-timer
#   Автоустановки новых сертификатов нет намеренно: при изменении отпечатка или сроке < 90 дней
#   приходит уведомление, а обновление отпечатков в скрипте и установка — осознанное решение.
set -euo pipefail

BASE="https://gu-st.ru/content/lending"
ANCHORS="/etc/ca-certificates/trust-source/anchors"
NSS_DB="sql:$HOME/.pki/nssdb"

declare -A FILES=(
  [russian_trusted_root_ca]="russian_trusted_root_ca_pem.crt"
  [russian_trusted_sub_ca]="russian_trusted_sub_ca_pem.crt"
)
declare -A SHA256=(
  [russian_trusted_root_ca]="D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31"
  [russian_trusted_sub_ca]="BB:BD:E2:10:3E:79:0B:99:9E:C6:2B:D0:3C:F6:25:A5:A2:E7:C3:16:E1:0A:FE:6A:49:0E:ED:EA:D8:B3:FD:9B"
)
declare -A NICK=(
  [russian_trusted_root_ca]="Russian Trusted Root CA"
  [russian_trusted_sub_ca]="Russian Trusted Sub CA"
)

nss_db_ready() {
  mkdir -p "$HOME/.pki/nssdb"
  [ -f "$HOME/.pki/nssdb/cert9.db" ] || certutil -d "$NSS_DB" -N --empty-password
}

firefox_profiles() {
  local d
  for d in "$HOME"/.mozilla/firefox/*.default* "$HOME"/.mozilla/firefox/*.*/; do
    [ -f "$d/prefs.js" ] && echo "${d%/}"
  done | sort -u
}

notify() {
  echo "$1: $2"
  if command -v omarchy-notification-send >/dev/null; then
    omarchy-notification-send -g 󰄬 "$1" "$2" 2>/dev/null || true
  elif command -v notify-send >/dev/null; then
    notify-send "$1" "$2" || true
  fi
}

if [ "${1:-}" = "--check" ]; then
  tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
  rc=0
  for k in "${!FILES[@]}"; do
    if ! curl -fsSL --retry 3 -m 60 -o "$tmp/$k.crt" "$BASE/${FILES[$k]}"; then
      echo "check: не удалось скачать ${NICK[$k]} (нет сети?)" >&2; continue
    fi
    got=$(openssl x509 -in "$tmp/$k.crt" -noout -fingerprint -sha256 | cut -d= -f2)
    if [ "$got" != "${SHA256[$k]}" ]; then
      notify "Сертификат Минцифры изменился" "${NICK[$k]}: новый отпечаток $got. Проверьте на gosuslugi.ru/crt, обновите SHA256 в install-mincifry-ca.sh и запустите его."
      rc=1
    fi
    # Срок: берём установленный сертификат, а если его нет — скачанный.
    src="$ANCHORS/$k.crt"; [ -r "$src" ] || src="$tmp/$k.crt"
    if ! openssl x509 -in "$src" -noout -checkend $((90*86400)) >/dev/null; then
      end=$(openssl x509 -in "$src" -noout -enddate | cut -d= -f2)
      notify "Сертификат Минцифры скоро истекает" "${NICK[$k]}: действует до $end. Проверьте, выпущен ли новый, и обновите скрипт."
      rc=1
    fi
  done
  [ "$rc" = 0 ] && echo "check: отпечатки совпадают, срок действия > 90 дней."
  exit $rc
fi

UNIT_DIR="$HOME/.config/systemd/user"
if [ "${1:-}" = "--enable-timer" ]; then
  self=$(readlink -f "$0")
  mkdir -p "$UNIT_DIR"
  cat > "$UNIT_DIR/mincifry-ca-check.service" <<EOF
[Unit]
Description=Проверка сертификатов Минцифры

[Service]
Type=oneshot
ExecStart=$self --check
EOF
  cat > "$UNIT_DIR/mincifry-ca-check.timer" <<EOF
[Unit]
Description=Еженедельная проверка сертификатов Минцифры

[Timer]
OnCalendar=weekly
Persistent=true
RandomizedDelaySec=1h

[Install]
WantedBy=timers.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now mincifry-ca-check.timer
  echo "Таймер включён: $(systemctl --user list-timers mincifry-ca-check.timer --no-legend | head -1)"
  exit 0
fi
if [ "${1:-}" = "--disable-timer" ]; then
  systemctl --user disable --now mincifry-ca-check.timer 2>/dev/null || true
  rm -f "$UNIT_DIR/mincifry-ca-check.service" "$UNIT_DIR/mincifry-ca-check.timer"
  systemctl --user daemon-reload
  echo "Таймер выключен."
  exit 0
fi

if [ "${1:-}" = "--remove" ]; then
  for k in "${!FILES[@]}"; do
    sudo rm -f "$ANCHORS/$k.crt"
    certutil -d "$NSS_DB" -D -n "${NICK[$k]}" 2>/dev/null || true
  done
  sudo update-ca-trust
  for p in $(firefox_profiles); do sed -i '/security.enterprise_roots.enabled/d' "$p/user.js" 2>/dev/null || true; done
  echo "Сертификаты Минцифры удалены."
  exit 0
fi

for c in curl openssl certutil update-ca-trust; do
  command -v "$c" >/dev/null || { echo "Нужна утилита: $c (certutil — пакет nss)" >&2; exit 1; }
done

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

for k in "${!FILES[@]}"; do
  curl -fsSL --retry 3 -m 60 -o "$tmp/$k.crt" "$BASE/${FILES[$k]}"
  got=$(openssl x509 -in "$tmp/$k.crt" -noout -fingerprint -sha256 | cut -d= -f2)
  if [ "$got" != "${SHA256[$k]}" ]; then
    echo "ОШИБКА: отпечаток $k не совпал (получен $got). Установка прервана." >&2
    exit 1
  fi
  echo "OK: ${NICK[$k]} ($got)"
done

# 1. Системное хранилище
for k in "${!FILES[@]}"; do sudo install -Dm644 "$tmp/$k.crt" "$ANCHORS/$k.crt"; done
sudo update-ca-trust
echo "Системное хранилище обновлено."

# 2. Chromium-семейство (NSS)
nss_db_ready
for k in "${!FILES[@]}"; do
  certutil -d "$NSS_DB" -D -n "${NICK[$k]}" 2>/dev/null || true
  certutil -d "$NSS_DB" -A -t "C,," -n "${NICK[$k]}" -i "$tmp/$k.crt"
done
echo "NSS-база Chromium обновлена (перезапустите браузер)."

# 3. Firefox: использовать системное хранилище
for p in $(firefox_profiles); do
  grep -qs 'security.enterprise_roots.enabled' "$p/user.js" 2>/dev/null \
    || echo 'user_pref("security.enterprise_roots.enabled", true);' >> "$p/user.js"
  echo "Firefox: $p"
done

if [ -t 0 ] && ! systemctl --user is-enabled mincifry-ca-check.timer >/dev/null 2>&1; then
  echo "Совет: ./install-mincifry-ca.sh --enable-timer — еженедельная проверка срока и отпечатков."
fi
echo "Готово. Проверка: curl -sI https://www.gosuslugi.ru | head -1"
