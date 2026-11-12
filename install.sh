#!/usr/bin/env bash
# Русификация Omarchy. Запускать в терминале от обычного пользователя (sudo спросит пароль).
# Каждый пункт — отдельный скрипт в modules/; перед установкой можно выбрать нужные («корзина»).
#   ./install.sh                 интерактивный выбор (gum, либо текстовое меню)
#   ./install.sh --list          показать все пункты
#   ./install.sh --all           поставить всё (включая необязательное)
#   ./install.sh --defaults|-y   только пункты, отмеченные по умолчанию, без вопросов
#   ./install.sh --only a,b      только указанные пункты (id из --list)
#   ./install.sh --skip a,b      пункты по умолчанию, кроме указанных
#   ./install.sh --dry-run ...   только показать, что будет выполнено
#   ./install.sh --plain ...     без анимаций: полный вывод модулей прямо в терминал
#   ./install.sh --version       версия (из файла VERSION в релизном архиве)
set -uo pipefail

RUS_DIR=$(dirname "$(readlink -f "$0")")
export RUS_DIR
# RUS_MODULES_DIR и RUS_I18N_DIR — только для тестов (tests/ui-smoke.sh)
MODULES_DIR="${RUS_MODULES_DIR:-$RUS_DIR/modules}"
I18N_DIR="${RUS_I18N_DIR:-/usr/share/omarchy/default/i18n/ru}"
# shellcheck source=ui.sh
. "$RUS_DIR/ui.sh"

declare -A GROUP_TITLE=(
  [base]="Базовая русификация"
  [safe]="Простое и безопасное"
  [apps]="Приложения"
  [work]="Работа и госуслуги"
  [ui]="Интерфейс"
)
GROUP_ORDER=(base safe apps ui work)

ids=(); files=(); titles=(); groups=(); defaults=(); sudos=(); descs=()

meta() { sed -n "s/^# $2: *//p" "$1" | head -1; }

load_modules() {
  local f id
  for f in "$MODULES_DIR"/*.sh; do
    id=${f##*/}; id=${id%.sh}; id=${id#*-}
    ids+=("$id"); files+=("$f")
    titles+=("$(meta "$f" title | tr ',' ';')")
    groups+=("$(meta "$f" group)")
    defaults+=("$(meta "$f" default)")
    sudos+=("$(meta "$f" sudo)")
    descs+=("$(meta "$f" desc)")
  done
}

idx_of() { local i; for i in "${!ids[@]}"; do [ "${ids[$i]}" = "$1" ] && { echo "$i"; return 0; }; done; return 1; }

label_of() { echo "${GROUP_TITLE[${groups[$1]}]} · ${titles[$1]}"; }

print_catalog() {
  local g i
  for g in "${GROUP_ORDER[@]}"; do
    echo; echo "── ${GROUP_TITLE[$g]}"
    for i in "${!ids[@]}"; do
      [ "${groups[$i]}" = "$g" ] || continue
      printf '  %-14s %s [%s]\n      %s\n' "${ids[$i]}" "${titles[$i]}" \
        "$([ "${defaults[$i]}" = on ] && echo 'по умолчанию' || echo 'необязательно')" "${descs[$i]}"
    done
  done
}

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; }

selected=()   # индексы
set_defaults() { local i; selected=(); for i in "${!ids[@]}"; do [ "${defaults[$i]}" = on ] && selected+=("$i"); done; }
set_all() { local i; selected=(); for i in "${!ids[@]}"; do selected+=("$i"); done; }

choose_gum() {
  local preset label i sel="" out
  preset=$(gum choose --header "Что установить?" \
    "Рекомендуемое (по умолчанию)" "Всё, включая необязательное" "Выбрать вручную" "Отмена") || exit 1
  case "$preset" in
    Рекоменд*) set_defaults; return ;;
    Всё*)      set_all; return ;;
    Отмена)    exit 0 ;;
  esac
  local -a labels=()
  for i in "${!ids[@]}"; do
    label=$(label_of "$i"); labels+=("$label")
    [ "${defaults[$i]}" = on ] && sel+="${sel:+,}$label"
  done
  out=$(gum choose --no-limit --height 24 --selected "$sel" \
    --header "Пробел — отметить, Ctrl+A — выбрать всё, Enter — продолжить" "${labels[@]}") || exit 1
  selected=()
  while IFS= read -r label; do
    [ -n "$label" ] || continue
    for i in "${!labels[@]}"; do [ "${labels[$i]}" = "$label" ] && selected+=("$i"); done
  done <<< "$out"
}

choose_text() {
  local i ans n
  print_catalog
  echo
  echo "Пункты по умолчанию:"
  for i in "${!ids[@]}"; do [ "${defaults[$i]}" = on ] && printf '  %s' "${ids[$i]}"; done; echo
  read -rp $'\nEnter — по умолчанию, a — всё, n — отмена, либо id через пробел: ' ans
  case "$ans" in
    ""|d) set_defaults ;;
    a)    set_all ;;
    n)    exit 0 ;;
    *)    selected=()
          for n in $ans; do
            i=$(idx_of "$n") || { echo "Неизвестный пункт: $n" >&2; exit 2; }
            selected+=("$i")
          done ;;
  esac
}

load_modules
mode=""; only=""; skip=""; dry=0; plain=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --list) print_catalog; exit 0 ;;
    --version) cat "$RUS_DIR/VERSION" 2>/dev/null || echo "dev"; exit 0 ;;
    --all) mode=all ;;
    --defaults|-y|--yes) mode=defaults ;;
    --only) only="${2:-}"; mode=only; shift ;;
    --dry-run) dry=1 ;;
    --plain|--verbose) plain=1 ;;
    --skip) skip="${2:-}"; mode=defaults; shift ;;
    *) echo "Неизвестный параметр: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

ui_init "$plain"
trap 'ui_cleanup; echo; echo "Прервано."; exit 130' INT TERM
banner

case "$mode" in
  all) set_all ;;
  defaults) set_defaults ;;
  only)
    selected=()
    for n in ${only//,/ }; do
      i=$(idx_of "$n") || { echo "Неизвестный пункт: $n" >&2; exit 2; }
      selected+=("$i")
    done ;;
  *)
    if [ -t 0 ] && [ -t 1 ]; then
      if command -v gum >/dev/null; then choose_gum; else choose_text; fi
    else
      set_defaults
    fi ;;
esac

if [ -n "$skip" ]; then
  keep=()
  for i in "${selected[@]}"; do
    drop=0; for n in ${skip//,/ }; do [ "${ids[$i]}" = "$n" ] && drop=1; done
    [ "$drop" = 1 ] || keep+=("$i")
  done
  selected=("${keep[@]}")
fi

if [ ${#selected[@]} -eq 0 ]; then echo "Ничего не выбрано."; exit 0; fi

# Выполняем в порядке номеров модулей, а не порядка выбора.
mapfile -t selected < <(printf '%s\n' "${selected[@]}" | sort -un)

ui_heading "Будет выполнено (${#selected[@]}):"
for i in "${selected[@]}"; do
  printf '  %s•%s %s' "$CA" "$C0" "$(label_of "$i")"
  [ "${sudos[$i]}" = yes ] && printf ' %s(sudo)%s' "$CD" "$C0"
  echo
done
[ "$dry" = 1 ] && exit 0
# С 2.0 интерфейс переводит сам Omarchy (4.5+); на старых версиях модули убрали бы перевод, ничего не дав взамен.
if [ ! -d "$I18N_DIR" ] || ! command -v omarchy-language >/dev/null; then
  printf '\n  %s✗ Нужен Omarchy 4.5 или новее%s (встроенная локализация): сначала выполните «omarchy update».\n' "$CB$CF" "$C0" >&2
  printf '  %sДля старых версий Omarchy: omarchy-rus 1.5.0 (https://github.com/chastnik/omarchy-rus/releases/tag/v1.5.0).%s\n' "$CD" "$C0" >&2
  exit 1
fi
if [ -t 0 ] && [ -t 1 ] && [ -z "$mode" ]; then
  echo
  if command -v gum >/dev/null; then gum confirm "Продолжить?" || exit 0
  else read -rp "Продолжить? [Y/n] " a; [[ "${a:-y}" =~ ^[YyДд] ]] || exit 0; fi
fi

# sudo: спрашиваем пароль один раз и поддерживаем сессию
need_sudo=0
for i in "${selected[@]}"; do [ "${sudos[$i]}" = yes ] && need_sudo=1; done
keepalive=""
trap 'ui_cleanup; [ -n "$keepalive" ] && kill "$keepalive" 2>/dev/null' EXIT
if [ "$need_sudo" = 1 ]; then
  echo
  sudo -v || { echo "Нужен sudo" >&2; exit 1; }
  ( while true; do sudo -n true 2>/dev/null; sleep 50; kill -0 "$$" 2>/dev/null || exit; done ) &
  keepalive=$!
fi

# Журнал: вывод всех модулей, на случай ошибок
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-rus"
mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR=$(mktemp -d)
LOG="$LOG_DIR/install-$(date +%Y%m%d-%H%M%S).log"
STEP_LOG="$LOG_DIR/.step.log"
: > "$LOG"

export RUS_NO_RESTART=1   # шелл перезапускаем один раз в конце
need_restart=0
declare -A result
total=${#selected[@]}; n=0; ok_count=0
ui_now; t_start=$UI_NOW
[ "$UI_FANCY" = 1 ] && ui_heading "Установка"
for i in "${selected[@]}"; do
  n=$((n + 1))
  if [ "$UI_FANCY" = 1 ]; then
    if ui_step "$n" "$total" "${titles[$i]}" "$STEP_LOG" bash "${files[$i]}"; then result[$i]=ok; else result[$i]=FAIL; fi
    { printf '\n===== [%d/%d] %s (%s) — %s =====\n' "$n" "$total" "${titles[$i]}" "${ids[$i]}" "${result[$i]}"; cat "$STEP_LOG"; } >> "$LOG"
  else
    echo; echo "▶ [$n/$total] ${titles[$i]}"
    if bash "${files[$i]}"; then result[$i]=ok; else result[$i]=FAIL; fi
  fi
  [ "${result[$i]}" = ok ] && ok_count=$((ok_count + 1))
  case "${ids[$i]}" in migrate|emojis|weather|dns) need_restart=1 ;; esac
done

if [ "$need_restart" = 1 ]; then
  if [ "$UI_FANCY" = 1 ]; then
    ui_step "$total" "$total" "Перезапуск шелла Omarchy (бар на пару секунд пропадёт)" "$STEP_LOG" \
      omarchy restart shell || true
  else
    echo; echo "Перезапуск шелла Omarchy (бар на пару секунд пропадёт)…"
    omarchy restart shell >/dev/null 2>&1 || true
  fi
fi
rm -f "$STEP_LOG"
ui_now; t_total=$((UI_NOW - t_start))

failed=0; [ "$ok_count" = "$total" ] || failed=1
if [ "$UI_FANCY" = 1 ]; then
  ui_bar "$ok_count" "$total" 24
  printf '\n  %s %s%d/%d%s успешно  %s· %s%s\n' "$UI_BAR" "$CB" "$ok_count" "$total" "$C0" "$CD" "$(ui_dur "$t_total")" "$C0"
  if [ "$failed" = 1 ]; then
    printf '\n  %s%sНе получилось:%s\n' "$CB" "$CF" "$C0"
    for i in "${selected[@]}"; do
      [ "${result[$i]}" = ok ] || printf '    %s✗%s %s  %s./install.sh --only %s%s\n' "$CF" "$C0" "${titles[$i]}" "$CD" "${ids[$i]}" "$C0"
    done
    printf '\n  %sПодробный вывод: %s%s\n' "$CD" "$LOG" "$C0"
  else
    echo; ui_shimmer "Готово! Omarchy говорит по-русски."
  fi
  printf '  %sПерезайдите в сессию, чтобы применить язык интерфейса.%s\n\n' "$CD" "$C0"
else
  echo; echo "Итоги:"
  for i in "${selected[@]}"; do
    if [ "${result[$i]}" = ok ]; then echo "  ✓ ${titles[$i]}"; else echo "  ✗ ${titles[$i]}"; fi
  done
  echo; echo "Готово. Перезайдите в сессию, чтобы применить язык интерфейса."
fi
exit $failed
