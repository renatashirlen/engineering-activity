#!/usr/bin/env bash
# Aviso mensal: compara os números atuais com os publicados. NÃO grava, NÃO faz commit nem push.
set -u
AQUI="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${RSC_REPO:-$HOME/desenvolvimento/rsc-tae}"
CONF="${ATIVIDADE_CONF:-$HOME/.config/engineering-activity.env}"  # fora do repositório; define ATIVIDADE_AUTOR
[ -f "$CONF" ] && . "$CONF"
AUTOR="${ATIVIDADE_AUTOR:?defina ATIVIDADE_AUTOR em $CONF}"
AVISO="$HOME/engineering-activity-aviso.txt"

PRIV="${ATIVIDADE_PRIVADO:-$AQUI/../engineering-activity-privado}"  # exportador e dados privados (fora do repositório)
ISS=()
if [ -f "$PRIV/export_issues.py" ]; then
  python3 "$PRIV/export_issues.py" >/dev/null 2>&1 && ISS=(--issues-json "$PRIV/issues-export.json")
fi
python3 "$AQUI/scripts/aggregate_activity.py" --repo "$REPO" --author "$AUTOR" --out "$AQUI" "${ISS[@]}" --check >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 10 ]; then
  msg="engineering-activity: há números novos. Rode scripts/aggregate_activity.py --write, revise o diff, faça commit e push."
  echo "$(date -Iseconds) $msg" > "$AVISO"
  /mnt/c/Windows/System32/msg.exe '*' "$msg" >/dev/null 2>&1 || true
elif [ "$rc" -ne 0 ]; then
  echo "$(date -Iseconds) engineering-activity: falha ao checar (código $rc)" > "$AVISO"
fi
exit 0
