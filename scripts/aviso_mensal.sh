#!/usr/bin/env bash
# Aviso mensal: compara os números atuais com os publicados. NÃO grava, NÃO faz commit nem push.
set -u
AQUI="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${RSC_REPO:-$HOME/desenvolvimento/rsc-tae}"
AUTOR="${ATIVIDADE_AUTOR:-}"
AVISO="$HOME/engineering-activity-aviso.txt"

python3 "$AQUI/scripts/aggregate_activity.py" --repo "$REPO" --author "$AUTOR" --out "$AQUI" --check >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 10 ]; then
  msg="engineering-activity: há números novos. Rode scripts/aggregate_activity.py --write, revise o diff, faça commit e push."
  echo "$(date -Iseconds) $msg" > "$AVISO"
  /mnt/c/Windows/System32/msg.exe '*' "$msg" >/dev/null 2>&1 || true
elif [ "$rc" -ne 0 ]; then
  echo "$(date -Iseconds) engineering-activity: falha ao checar (código $rc)" > "$AVISO"
fi
exit 0
