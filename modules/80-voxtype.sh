#!/usr/bin/env bash
# title: voxtype: русское распознавание речи (Parakeet)
# group: apps
# default: on
# sudo: yes
# desc: ONNX-сборка, модель parakeet-tdt-0.6b-v3-int8 (~650 МБ), настройка микрофона
set -euo pipefail
command -v voxtype >/dev/null || { echo "voxtype не установлен — пропускаю."; exit 0; }
MODEL=parakeet-tdt-0.6b-v3-int8
# ONNX-сборка voxtype нужна для Parakeet (в Whisper-сборке движка нет)
voxtype setup onnx --status 2>/dev/null | grep -q "Active engine: Whisper" && sudo voxtype setup onnx --enable
# Усиление встроенного микрофона по умолчанию максимальное (+30 дБ ×2) и клиппит звук —
# модель тогда выдаёт пустую строку или английский мусор ("Thank you."). Снижаем.
amixer -c 0 sset 'Internal Mic Boost' 1 >/dev/null 2>&1 || true
amixer -c 0 sset Capture 60% >/dev/null 2>&1 || true
# Основной хост (models.voxtype.io) иногда отдаёт данные очень медленно;
# тогда качаем те же файлы с зеркала Hugging Face и сверяем sha256 с манифестом.
MODEL_DIR="$HOME/.local/share/voxtype/models/$MODEL"
MIRROR="https://huggingface.co/istupakov/parakeet-tdt-0.6b-v3-onnx/resolve/main"
declare -A SHA=(
  [encoder-model.int8.onnx]=6139d2fa7e1b086097b277c7149725edbab89cc7c7ae64b23c741be4055aff09
  [decoder_joint-model.int8.onnx]=eea7483ee3d1a30375daedc8ed83e3960c91b098812127a0d99d1c8977667a70
  [vocab.txt]=d58544679ea4bc6ac563d1f545eb7d474bd6cfa467f0a6e2c1dc1c7d37e3c35d
  [config.json]=666903c76b9798caf2c210afd4f6cd60b08a8dbf9800ec8d7a3bc0d2148ac466
)
model_complete() {
  local f
  for f in "${!SHA[@]}"; do
    [ -f "$MODEL_DIR/$f" ] && echo "${SHA[$f]}  $MODEL_DIR/$f" | sha256sum -c --status || return 1
  done
}
mirror_download() {
  mkdir -p "$MODEL_DIR"
  local f
  for f in "${!SHA[@]}"; do
    if [ -f "$MODEL_DIR/$f" ] && echo "${SHA[$f]}  $MODEL_DIR/$f" | sha256sum -c --status; then continue; fi
    curl -fL -C - --retry 5 --retry-delay 3 -o "$MODEL_DIR/$f.part" "$MIRROR/$f" \
      && mv "$MODEL_DIR/$f.part" "$MODEL_DIR/$f" || return 1
  done
  model_complete
}

ok=0
model_complete && ok=1
if [ "$ok" != 1 ]; then
  # Быстрая проверка основного хоста: 1-2 попытки, затем зеркало
  for i in 1 2; do
    if timeout 300 voxtype setup --download --model "$MODEL" --quiet && model_complete; then ok=1; break; fi
    echo "voxtype: основной хост не отдал модель (попытка $i/2)"
  done
fi
if [ "$ok" != 1 ]; then
  echo "voxtype: качаю с зеркала Hugging Face..."
  mirror_download && ok=1
fi
if [ "$ok" = 1 ]; then
  voxtype config set engine parakeet
  voxtype config set parakeet.model "$MODEL"
  voxtype config set whisper.language auto
  systemctl --user restart voxtype 2>/dev/null || true
else
  echo "voxtype: модель не скачалась, конфигурация не изменена. Запустите скрипт позже." >&2
fi
