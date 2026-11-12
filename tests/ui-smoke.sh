#!/usr/bin/env bash
# Смоук-тест установщика на фейковых модулях: анимированный режим в псевдотерминале (script),
# простой режим через пайп, журнал, код возврата, восстановление курсора.
# Запуск из корня репозитория: tests/ui-smoke.sh   (нужен bash 4+ и script из util-linux или BSD)
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
mkdir -p "$W/modules" "$W/bin" "$W/i18n" "$W/state"
fails=0
ok()   { printf '  ✓ %s\n' "$1"; }
fail() { printf '  ✗ %s\n' "$1"; fails=$((fails + 1)); }
ESC=$'\e'
plain_text() { sed "s/$ESC\[[0-9;?]*[A-Za-z]//g" "$1"; }   # текст без цветов и движений курсора
has()  { plain_text "$1" | grep -qF -- "$2" && ok "$3" || fail "$3 (нет «$2»)"; }
hasnt(){ if grep -qF -- "$2" "$1"; then fail "$3 (есть «$2»)"; else ok "$3"; fi; }

mod() {   # mod <файл> <заголовок> <тело>
  printf '#!/usr/bin/env bash\n# title: %s\n# group: base\n# default: on\n# desc: тест\nset -euo pipefail\n%s\n' "$2" "$3" > "$W/modules/$1.sh"
  chmod +x "$W/modules/$1.sh"
}
mod 10-alpha "Фейк: обычный вывод"     'for i in 1 2 3; do echo "шаг $i"; sleep 0.2; done'
mod 20-bravo "Фейк: прогресс через CR" 'for k in 25 50 75 100; do printf "\r:: загрузка %d%%" $k; sleep 0.1; done; echo'
mod 30-charlie "Фейк: ошибка"          'echo "что-то пошло не так" >&2; exit 3'
mod 40-delta "Фейк: после ошибки"      'echo "дошли до конца"'

printf '#!/bin/sh\nexit 0\n' > "$W/bin/omarchy"; cp "$W/bin/omarchy" "$W/bin/omarchy-language"; chmod +x "$W/bin/"*

export PATH="$W/bin:$PATH" RUS_MODULES_DIR="$W/modules" RUS_I18N_DIR="$W/i18n" XDG_STATE_HOME="$W/state"
export TERM=xterm-256color LANG=C.UTF-8 LC_ALL=C.UTF-8 RUS_NO_ANIM=1

in_pty() {   # in_pty <файл вывода> <команда…> — запуск в псевдотерминале, код возврата команды
  local out=$1; shift
  local cmd; printf -v cmd '%q ' "$@"
  if script --version 2>/dev/null | grep -q util-linux; then
    script -qec "$cmd" /dev/null > "$out" 2>&1 < /dev/null
  else
    script -q /dev/null bash -c "$cmd" > "$out" 2>&1 < /dev/null
  fi
}

echo "Анимированный режим (pty), один модуль падает:"
rc=0; in_pty "$W/fancy.out" "$ROOT/install.sh" -y || rc=$?
[ "$rc" = 1 ] && ok "код возврата 1" || fail "код возврата $rc, ожидался 1"
has "$W/fancy.out" "✓ Фейк: обычный вывод" "успешный шаг отмечен ✓"
has "$W/fancy.out" "✗ Фейк: ошибка" "упавший шаг отмечен ✗"
has "$W/fancy.out" "код 3" "показан код выхода модуля"
has "$W/fancy.out" "что-то пошло не так" "показан хвост вывода упавшего шага"
has "$W/fancy.out" "✓ Фейк: после ошибки" "сбой не останавливает остальные шаги"
has "$W/fancy.out" "3/4" "в итогах 3 из 4"
has "$W/fancy.out" "./install.sh --only charlie" "подсказка для повтора"
has "$W/fancy.out" "Русификация Omarchy" "баннер"
tail -c 400 "$W/fancy.out" | grep -qF $'\e[?25h' && ok "курсор возвращён" || fail "курсор не возвращён"
log=$(ls "$W/state/omarchy-rus/"install-*.log 2>/dev/null | head -1)
if [ -n "$log" ]; then
  ok "журнал создан"
  has "$log" "дошли до конца" "в журнале вывод модулей"
  has "$log" "charlie) — FAIL" "в журнале отмечен сбой"
else fail "журнал не создан"; fi
[ ! -e "$W/state/omarchy-rus/.step.log" ] && ok "временный файл шага удалён" || fail "остался .step.log"

echo "Анимированный режим, всё успешно:"
rc=0; in_pty "$W/ok.out" "$ROOT/install.sh" --skip charlie || rc=$?
[ "$rc" = 0 ] && ok "код возврата 0" || fail "код возврата $rc, ожидался 0"
has "$W/ok.out" "Готово!" "финальное сообщение"
has "$W/ok.out" "3/3" "в итогах 3 из 3"

echo "Простой режим (пайп, без TTY):"
rc=0; "$ROOT/install.sh" -y > "$W/plain.out" 2>&1 < /dev/null || rc=$?
[ "$rc" = 1 ] && ok "код возврата 1" || fail "код возврата $rc, ожидался 1"
has "$W/plain.out" "▶ [1/4] Фейк: обычный вывод" "шаги с номерами"
has "$W/plain.out" "шаг 3" "вывод модулей идёт напрямую"
hasnt "$W/plain.out" $'\e[' "без управляющих последовательностей"

echo "--plain в псевдотерминале:"
rc=0; in_pty "$W/forced.out" "$ROOT/install.sh" --plain -y || rc=$?
has "$W/forced.out" "▶ [1/4]" "--plain отключает анимацию"
hasnt "$W/forced.out" "⠋" "спиннера нет"

echo "Нет Omarchy 4.5:"
rc=0; RUS_I18N_DIR="$W/nope" "$ROOT/install.sh" -y > "$W/old.out" 2>&1 < /dev/null || rc=$?
[ "$rc" = 1 ] && ok "код возврата 1" || fail "код возврата $rc, ожидался 1"
has "$W/old.out" "Нужен Omarchy 4.5" "понятное сообщение"
hasnt "$W/old.out" "шаг 1" "модули не запускались"

echo
if [ "$fails" = 0 ]; then echo "ui-smoke: всё в порядке"; else echo "ui-smoke: ошибок — $fails"; exit 1; fi
