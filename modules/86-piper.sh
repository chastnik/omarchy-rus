#!/usr/bin/env bash
# title: Русский голос Piper (нейросетевая озвучка, офлайн)
# group: apps
# default: off
# sudo: yes
# desc: piper-tts (AUR) + голос Irina (~63 МБ), команда say-ru и модуль speech-dispatcher; заметно естественнее espeak-ng
set -euo pipefail
VOICE=ru_RU-irina-medium
BASE=https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium
SHA_ONNX=8ff38212d23da300bbe3705c645e6e5b9475f0bfde01558eb17813e22acaaaaa
SHA_JSON=c2ec28bb38e2b59e93b959b3e40348c1afebbd272f30fed5d41205d08e98a9d7
DIR="$HOME/.local/share/piper/voices"
mkdir -p "$DIR" "$HOME/.local/bin"

# Пакет piper-tts-bin ставит бинарь под именем piper-tts (в других сборках — piper)
piper_bin() { command -v piper-tts || command -v piper; }
if ! piper_bin >/dev/null; then
  if ! omarchy pkg aur add piper-tts-bin; then
    # AUR бывает недоступен: тогда ставим пакет, собранный раньше (кэш yay), если он есть.
    cached=""
    for f in "$HOME"/.cache/yay/piper-tts-bin/piper-tts-bin-[0-9]*.pkg.tar.*; do
      [ -e "$f" ] && [ "${f#*-debug-}" = "$f" ] && cached=$f
    done
    if [ -n "$cached" ]; then
      echo "piper: AUR недоступен, ставлю собранный ранее пакет $cached"
      sudo pacman -U --noconfirm --needed "$cached"
    else
      echo "piper: AUR недоступен и готового пакета нет. Повторите позже: ./install.sh --only piper" >&2
      exit 1
    fi
  fi
fi

fetch() { # файл, sha256
  local f="$DIR/$1"
  if [ -f "$f" ] && echo "$2  $f" | sha256sum -c --status; then return 0; fi
  curl -fsSL -C - --retry 5 --retry-delay 3 -o "$f.part" "$BASE/$1" && mv "$f.part" "$f"
  echo "$2  $f" | sha256sum -c --status || { echo "piper: контрольная сумма $1 не совпала" >&2; rm -f "$f"; return 1; }
}
fetch "$VOICE.onnx" "$SHA_ONNX"
fetch "$VOICE.onnx.json" "$SHA_JSON"

# say-ru [текст…] | say-ru < файл — озвучить по-русски; say-ru --check — самопроверка без звука
cat > "$HOME/.local/bin/say-ru" <<'SAY'
#!/usr/bin/env bash
# Установлено omarchy-rus (модуль piper). Голос: PIPER_VOICE (по умолчанию Irina).
set -euo pipefail
MODEL="${PIPER_VOICE:-$HOME/.local/share/piper/voices/ru_RU-irina-medium.onnx}"
PIPER=$(command -v piper-tts || command -v piper) || { echo "say-ru: piper не установлен" >&2; exit 1; }
# piper 1.2 принимает --output_raw, более новые сборки — --output-raw
if "$PIPER" --help 2>&1 | grep -q -- '--output-raw'; then RAW=--output-raw; else RAW=--output_raw; fi
if [ "${1:-}" = "--check" ]; then
  set +o pipefail  # head закрывает канал раньше, чем piper закончит
  bytes=$(echo "проверка" | "$PIPER" --model "$MODEL" "$RAW" 2>/dev/null | head -c 4096 | wc -c)
  [ "$bytes" -gt 0 ]
  exit
fi
if [ $# -gt 0 ]; then text="$*"; else text=$(cat); fi
[ -n "$text" ] || exit 0
rate=$(sed -n 's/.*"sample_rate": *\([0-9]*\).*/\1/p' "$MODEL.json" | head -1)
printf '%s\n' "$text" | "$PIPER" --model "$MODEL" "$RAW" 2>/dev/null \
  | aplay -q -r "${rate:-22050}" -f S16_LE -t raw -
SAY
chmod +x "$HOME/.local/bin/say-ru"

# Подключаем к speech-dispatcher только если голос реально работает: иначе остаётся espeak-ng.
if "$HOME/.local/bin/say-ru" --check; then
  MODDIR="$HOME/.config/speech-dispatcher/modules"
  CONF="$HOME/.config/speech-dispatcher/speechd.conf"
  mkdir -p "$MODDIR"
  cat > "$MODDIR/piper-generic.conf" <<CFG
# omarchy-rus
GenericExecuteSynth "printf '%s' \"\$DATA\" | $HOME/.local/bin/say-ru"
GenericCmdDependency "aplay"
GenericLanguage "ru" "ru" "utf-8"
AddVoice "ru" "FEMALE1" "irina"
CFG
  if [ -f "$CONF" ] && ! grep -qF -- 'piper-generic' "$CONF"; then
    cp "$CONF" "$CONF.bak.$(date +%s)"
    if grep -q '^DefaultModule ' "$CONF"; then sed -i 's/^DefaultModule .*/DefaultModule piper-generic/' "$CONF"
    else echo 'DefaultModule piper-generic' >> "$CONF"; fi
    echo 'AddModule "piper-generic" "sd_generic" "piper-generic.conf"' >> "$CONF"
  fi
  systemctl --user restart speech-dispatcher 2>/dev/null || pkill -x speech-dispatcher 2>/dev/null || true
  echo "Готово. Проверка: say-ru 'Привет, мир' или spd-say -l ru 'Привет, мир'"
else
  echo "piper: голос не заработал, speech-dispatcher оставлен на espeak-ng." >&2
fi
exit 0
