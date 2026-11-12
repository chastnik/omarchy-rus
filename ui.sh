# shellcheck shell=bash
# Оформление установщика: баннер, спиннер с живым выводом, прогресс, итоги.
# Подключается из install.sh (source). Без TTY или с --plain / RUS_PLAIN=1 всё выводится по-старому, без анимаций.
#   RUS_NO_ANIM=1  — оставить цвета и спиннер, но без баннерной анимации
#   NO_COLOR=1     — без цветов

ESC=$'\e'
UI_FANCY=0; UI_ANIM=1; UI_TTY_STATE=""; UI_CHILD=""
UI_SPIN=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
UI_EXPANDED=0     # «v» во время шага — показать больше строк вывода
UI_TAIL_LINES=8

ui_init() {   # $1 — 1, если запрошен простой вывод
  if [ "${1:-0}" != 1 ] && [ -z "${RUS_PLAIN:-}" ] && [ -t 1 ] && [ "${TERM:-dumb}" != dumb ]; then UI_FANCY=1; fi
  case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in *[Uu][Tt][Ff]-8*|*[Uu][Tt][Ff]8*) ;; *) UI_ANIM=0 ;; esac
  [ -n "${RUS_NO_ANIM:-}" ] && UI_ANIM=0
  if [ "$UI_FANCY" = 1 ] && [ -z "${NO_COLOR:-}" ]; then
    C0="${ESC}[0m" CB="${ESC}[1m" CD="${ESC}[2m"
    CW="${ESC}[38;5;255m" CBl="${ESC}[38;5;33m" CR="${ESC}[38;5;196m"   # триколор
    CA="${ESC}[38;5;39m" CG="${ESC}[38;5;42m" CF="${ESC}[38;5;203m" CY="${ESC}[38;5;221m"
  else
    C0="" CB="" CD="" CW="" CBl="" CR="" CA="" CG="" CF="" CY=""
  fi
}

ui_cols() { local c; c=$(tput cols 2>/dev/null) || c=80; [ "$c" -gt 100 ] && c=100; UI_COLS=$c; }

ui_now() { local t=${EPOCHREALTIME:-}; if [ -n "$t" ]; then t=${t/[.,]/}; UI_NOW=$((10#$t / 1000)); else UI_NOW=$((SECONDS * 1000)); fi; }

ui_dur() {   # мс → «4.2 с» / «1 мин 03 с»
  local ms=$1
  if [ "$ms" -lt 60000 ]; then printf '%d.%d с' $((ms / 1000)) $((ms % 1000 / 100))
  else printf '%d мин %02d с' $((ms / 60000)) $((ms % 60000 / 1000)); fi
}

ui_fit() {   # обрезать строку до $2 символов, с многоточием
  local s=$1 w=$2
  if [ "${#s}" -gt "$w" ]; then UI_FIT="${s:0:w-1}…"; else UI_FIT=$s; fi
}

ui_row() {   # значок, цвет заголовка, заголовок, правая колонка — заголовок обрезается, правая выравнивается
  local icon=$1 color=$2 title=$3 right=$4 w pad
  w=$((UI_COLS - 6 - ${#right})); [ "$w" -lt 10 ] && w=10
  ui_fit "$title" "$w"
  printf -v pad '%*s' $((w - ${#UI_FIT})) ''
  printf '  %s %s%s%s%s %s%s%s\n' "$icon" "$color" "$UI_FIT" "$C0" "$pad" "$CD" "$right" "$C0"
}

ui_cursor_hide() { [ "$UI_FANCY" = 1 ] && printf '%s[?25l' "$ESC"; return 0; }
ui_cursor_show() { [ "$UI_FANCY" = 1 ] && printf '%s[?25h' "$ESC"; return 0; }

ui_tty_quiet() {   # не эхоить нажатия во время анимации
  [ "$UI_FANCY" = 1 ] && [ -t 0 ] || return 0
  UI_TTY_STATE=$(stty -g 2>/dev/null) && stty -echo -icanon min 0 time 0 2>/dev/null
  return 0
}
ui_tty_restore() { [ -n "$UI_TTY_STATE" ] && stty "$UI_TTY_STATE" 2>/dev/null; UI_TTY_STATE=""; return 0; }

ui_cleanup() { [ -n "$UI_CHILD" ] && kill "$UI_CHILD" 2>/dev/null; ui_tty_restore; ui_cursor_show; }

banner() {
  [ "$UI_FANCY" = 1 ] || return 0
  local -a art=(
    '██████╗ ██╗   ██╗ ██████╗'
    '██╔══██╗╚██╗ ██╔╝██╔════╝'
    '██████╔╝ ╚████╔╝ ██║     '
    '██╔═══╝   ██╔╝   ██║     '
    '██║      ██╔╝    ╚██████╗'
    '╚═╝      ╚═╝      ╚═════╝'
  )
  local -a col=("$CW" "$CW" "$CBl" "$CBl" "$CR" "$CR")
  local n=${#art[@]} w=${#art[0]} x i ver sub
  ver=$(cat "$RUS_DIR/VERSION" 2>/dev/null || echo dev)
  sub="Русификация Omarchy"
  echo
  if [ "$UI_ANIM" = 1 ]; then
    ui_cursor_hide
    for ((x = 2; x < w + 2; x += 2)); do
      for ((i = 0; i < n; i++)); do printf '  %s%s%s%s[K\n' "$CB${col[i]}" "${art[i]:0:x}" "$C0" "$ESC"; done
      printf '%s[%dA' "$ESC" "$n"; sleep 0.015
    done
  fi
  for ((i = 0; i < n; i++)); do printf '  %s%s%s%s[K\n' "$CB${col[i]}" "${art[i]}" "$C0" "$ESC"; done
  printf '  '
  if [ "$UI_ANIM" = 1 ]; then
    for ((i = 0; i < ${#sub}; i++)); do printf '%s%s%s' "$CB" "${sub:i:1}" "$C0"; sleep 0.012; done
  else printf '%s%s%s' "$CB" "$sub" "$C0"; fi
  printf '  %s%s%s\n\n' "$CD" "$ver" "$C0"
  ui_cursor_show
}

ui_heading() {   # «── Текст» акцентным цветом
  if [ "$UI_FANCY" = 1 ]; then printf '\n%s%s──%s %s%s%s\n' "$CA" "$CB" "$C0" "$CB" "$1" "$C0"
  else printf '\n%s\n' "$1"; fi
}

ui_bar() {   # заполненность $1 из $2, ширина $3
  local done=$1 total=$2 w=$3 f s1 s2
  f=$((total > 0 ? done * w / total : w))
  printf -v s1 '%*s' "$f" ''; printf -v s2 '%*s' $((w - f)) ''
  UI_BAR="$CA${s1// /━}$C0$CD${s2// /─}$C0"
}

ui_tail() {   # последние $2 непустых строк файла $1, без управляющих последовательностей
  tail -c 8192 "$1" 2>/dev/null | tr '\r' '\n' | sed "s/$ESC\[[0-9;?]*[A-Za-z]//g; s/${ESC}[()][A-Za-z0-9]//g" \
    | grep -v '^[[:space:]]*$' | tail -n "$2"
}

# ui_step <номер> <всего> <заголовок> <лог шага> <команда…>
# Запускает команду в фоне, рисует спиннер, прогресс и хвост вывода. Код возврата — код команды.
UI_LAST_DUR=0
ui_step() {
  local num=$1 total=$2 title=$3 log=$4; shift 4
  local start rc f=0 drawn=0 key="" line hint frame tw
  local -a tail_buf=()
  ui_now; start=$UI_NOW
  : > "$log"
  "$@" >"$log" 2>&1 </dev/null &
  UI_CHILD=$!
  ui_cursor_hide; ui_tty_quiet; ui_cols
  while kill -0 "$UI_CHILD" 2>/dev/null; do
    if [ $((f % 3)) = 0 ]; then
      mapfile -t tail_buf < <(ui_tail "$log" $((UI_EXPANDED ? UI_TAIL_LINES : 1)))
    fi
    [ $((f % 25)) = 0 ] && ui_cols
    frame=${UI_SPIN[f % ${#UI_SPIN[@]}]}
    ui_now
    [ "$drawn" -gt 0 ] && printf '\r%s[%dA' "$ESC" "$drawn"
    printf '\r%s[J' "$ESC"
    ui_row "$CA$frame$C0" "$CB" "$title" "$(ui_dur $((UI_NOW - start)))"
    drawn=1
    tw=$((UI_COLS - 8))
    for line in "${tail_buf[@]}"; do
      ui_fit "$line" "$tw"; printf '    %s│ %s%s\n' "$CD" "$UI_FIT" "$C0"; drawn=$((drawn + 1))
    done
    if [ "$UI_COLS" -lt 56 ] || [ ! -t 0 ]; then hint=""
    elif [ "$UI_EXPANDED" = 1 ]; then hint="v — свернуть"; else hint="v — показать вывод"; fi
    ui_bar $((num - 1)) "$total" 24
    printf '\n  %s %s%d/%d%s  %s%s%s' "$UI_BAR" "$CB" "$num" "$total" "$C0" "$CD" "$hint" "$C0"
    drawn=$((drawn + 1))
    key=""
    if [ -t 0 ]; then read -rs -n1 -t 0.08 key 2>/dev/null || true; else sleep 0.08; fi
    case "$key" in v|V|м|М) UI_EXPANDED=$((1 - UI_EXPANDED)) ;; esac
    f=$((f + 1))
  done
  wait "$UI_CHILD"; rc=$?; UI_CHILD=""
  ui_tty_restore
  printf '\r%s[%dA\r%s[J' "$ESC" "$drawn" "$ESC"
  ui_now; UI_LAST_DUR=$((UI_NOW - start))
  if [ "$rc" = 0 ]; then ui_row "$CG✓$C0" "" "$title" "$(ui_dur "$UI_LAST_DUR")"
  else
    ui_row "$CF✗$C0" "$CF" "$title" "$(ui_dur "$UI_LAST_DUR") · код $rc"
    tw=$((UI_COLS - 8))
    while IFS= read -r line; do ui_fit "$line" "$tw"; printf '    %s│%s %s\n' "$CF" "$C0" "$UI_FIT"; done < <(ui_tail "$log" 6)
  fi
  ui_cursor_show
  return "$rc"
}

ui_shimmer() {   # блик пробегает по строке слева направо, затем строка остаётся зелёной
  local s=$1 p i c d out
  if [ "$UI_FANCY" != 1 ] || [ "$UI_ANIM" != 1 ] || [ -z "$C0" ]; then printf '  %s%s%s\n' "$CB$CG" "$s" "$C0"; return; fi
  ui_cursor_hide
  for ((p = -2; p < ${#s} + 3; p++)); do
    out=""
    for ((i = 0; i < ${#s}; i++)); do
      c=${s:i:1}; d=$((i - p)); [ "$d" -lt 0 ] && d=$((-d))
      case $d in
        0) out+="$CB$CW$c" ;;
        1) out+="$CB$CY$c" ;;
        *) if [ "$i" -lt "$p" ]; then out+="$C0$CB$CG$c"; else out+="$C0$CD$c"; fi ;;
      esac
    done
    printf '\r  %s%s' "$out" "$C0"; sleep 0.018
  done
  printf '\r  %s%s%s%s[K\n' "$CB$CG" "$s" "$C0" "$ESC"
  ui_cursor_show
}
