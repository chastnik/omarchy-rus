#!/usr/bin/env bash
# title: Проверка клонов после «omarchy update»
# group: ui
# default: off
# desc: хук post-update.d: после обновления Omarchy сообщает, если оригиналы клонов (сеть, погода, эмодзи) изменились
set -euo pipefail
D="$HOME/.local/share/omarchy-rus"
HOOK_DIR="$HOME/.config/omarchy/hooks/post-update.d"
# Скрипты копируются в постоянное место: папка с распакованным архивом может быть удалена.
mkdir -p "$D" "$HOOK_DIR"
# Остатки 1.x: этих скриптов больше нет.
rm -f "$D/translate-menu.py" "$D/keybindings-ru.py" "$D/check-i18n.py"
install -m 755 "$RUS_DIR/translate-plugins.py" "$RUS_DIR/dns-ru.py" "$D/"
rm -rf "$D/data" && cp -r "$RUS_DIR/data" "$D/data"
cat > "$HOOK_DIR/omarchy-rus.hook" <<'HOOK'
#!/bin/bash
# Установлен omarchy-rus (модуль post-update-hook). Клоны плагинов не обновляются сами:
# сообщаем, если оригинал изменился (пересоздать: translate-plugins.py --refresh).
D="$HOME/.local/share/omarchy-rus"
python3 "$D/translate-plugins.py" --check --notify || true
exit 0
HOOK
chmod +x "$HOOK_DIR/omarchy-rus.hook"
