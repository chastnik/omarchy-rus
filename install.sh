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
#   ./install.sh --version       версия (из файла VERSION в релизном архиве)
set -uo pipefail

RUS_DIR=$(dirname "$(readlink -f "$0")")
export RUS_DIR
MODULES_DIR="$RUS_DIR/modules"

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

usage() { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; }

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
mode=""; only=""; skip=""; dry=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --list) print_catalog; exit 0 ;;
    --version) cat "$RUS_DIR/VERSION" 2>/dev/null || echo "dev"; exit 0 ;;
    --all) mode=all ;;
    --defaults|-y|--yes) mode=defaults ;;
    --only) only="${2:-}"; mode=only; shift ;;
    --dry-run) dry=1 ;;
    --skip) skip="${2:-}"; mode=defaults; shift ;;
    *) echo "Неизвестный параметр: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

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

echo; echo "Будет выполнено:"
for i in "${selected[@]}"; do echo "  • $(label_of "$i")"; done
[ "$dry" = 1 ] && exit 0
if [ -t 0 ] && [ -t 1 ] && [ -z "$mode" ]; then
  if command -v gum >/dev/null; then gum confirm "Продолжить?" || exit 0
  else read -rp "Продолжить? [Y/n] " a; [[ "${a:-y}" =~ ^[YyДд] ]] || exit 0; fi
fi

# sudo: спрашиваем пароль один раз и поддерживаем сессию
need_sudo=0
for i in "${selected[@]}"; do [ "${sudos[$i]}" = yes ] && need_sudo=1; done
if [ "$need_sudo" = 1 ]; then
  sudo -v || { echo "Нужен sudo" >&2; exit 1; }
  ( while true; do sudo -n true 2>/dev/null; sleep 50; kill -0 "$$" 2>/dev/null || exit; done ) &
  trap 'kill $! 2>/dev/null' EXIT
fi

export RUS_NO_RESTART=1   # шелл перезапускаем один раз в конце
need_restart=0
declare -A result
for i in "${selected[@]}"; do
  echo; echo "▶ ${titles[$i]}"
  if bash "${files[$i]}"; then result[$i]="ok"; else result[$i]="FAIL"; fi
  case "${ids[$i]}" in panels|weather|dns) need_restart=1 ;; esac
done

if [ "$need_restart" = 1 ]; then
  echo; echo "Перезапуск шелла Omarchy (бар на пару секунд пропадёт)…"
  omarchy restart shell >/dev/null 2>&1 || true
fi

echo; echo "Итоги:"
failed=0
for i in "${selected[@]}"; do
  if [ "${result[$i]}" = ok ]; then echo "  ✓ ${titles[$i]}"; else echo "  ✗ ${titles[$i]}"; failed=1; fi
done
echo; echo "Готово. Перезайдите в сессию, чтобы применить язык интерфейса."
exit $failed
