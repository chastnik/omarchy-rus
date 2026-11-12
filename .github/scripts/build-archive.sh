#!/usr/bin/env bash
# Сборка релизного архива: ./.github/scripts/build-archive.sh <версия> [каталог=dist]
# Используется в release.yml и в CI (проверка упаковки до тега).
set -euo pipefail
ver=${1:?версия}; out=${2:-dist}
build=$(mktemp -d)
mkdir -p "$out"
git archive --prefix=omarchy-rus/ HEAD | tar -x -C "$build"
rm -rf "$build/omarchy-rus/.github" "$build/omarchy-rus/.gitignore" "$build/omarchy-rus/tests"
echo "$ver" > "$build/omarchy-rus/VERSION"
tar --sort=name --owner=0 --group=0 --numeric-owner -C "$build" -czf "$out/omarchy-rus.tar.gz" omarchy-rus
(cd "$out" && sha256sum omarchy-rus.tar.gz > omarchy-rus.tar.gz.sha256)

# Проверка: архив распаковывается, скрипты исполняемые, версия на месте, всё, на что ссылаются модули, упаковано
tmp=$(mktemp -d) && tar -xzf "$out/omarchy-rus.tar.gz" -C "$tmp"
r="$tmp/omarchy-rus"
test -x "$r/install.sh"
test -f "$r/ui.sh"
test "$("$r/install.sh" --version)" = "$ver"
"$r/install.sh" --dry-run -y >/dev/null
for f in "$r"/modules/*.sh; do
  [ -x "$f" ] || { echo "в архиве не исполняемый: ${f#"$r"/}"; exit 1; }
  for ref in $(grep -oE '\$RUS_DIR/[A-Za-z0-9._/-]+' "$f" | sed 's/^\$RUS_DIR\///' | sort -u); do
    [ -e "$r/$ref" ] || { echo "${f#"$r"/} ссылается на $ref, а его нет в архиве"; exit 1; }
  done
done
rm -rf "$build" "$tmp"
cat "$out/omarchy-rus.tar.gz.sha256"
