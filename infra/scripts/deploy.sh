#!/usr/bin/env bash
# /infra/scripts/deploy.sh — deploy por pull de um ambiente (ADR-001 D3, D4, D9)
#
# Chamado a cada 2 min pelo timer auditoria-deploy@<ambiente>, como root.
# Baixa as imagens das tags definidas no .env do ambiente e só recria os
# containers se a imagem mudou. Na produção faz um mysqldump ANTES, porque
# as migrations rodam no start do backend.
# Na VM fica em /srv/auditoria/bin/deploy.sh (a VM não guarda código-fonte).
#
# Uso: deploy.sh staging|prod [--force]
#   --force  reaplica mesmo sem imagem nova (ex.: depois de editar o .env)
set -euo pipefail
umask 077

ENV_NAME="${1:-}"
FORCE="${2:-}"
case "$ENV_NAME" in
  staging|prod) ;;
  *) echo "uso: deploy.sh staging|prod [--force]" >&2; exit 2 ;;
esac
case "$FORCE" in
  ""|--force) ;;
  *) echo "opção desconhecida: $FORCE" >&2; exit 2 ;;
esac

# AUDITORIA_BASE só existe para testar o script fora da VM.
BASE="${AUDITORIA_BASE:-/srv/auditoria}"
DIR="$BASE/$ENV_NAME"
PROJECT="auditoria-$ENV_NAME"
APP_SERVICES=(backend frontend)
KEEP_BACKUPS=14
REVISION_LABEL='{{index .Config.Labels "org.opencontainers.image.revision"}}'

log() { echo "[$ENV_NAME] $*"; }

# Timer ligado antes do INFRA-06/07: ainda não há o que aplicar.
if [ ! -f "$DIR/compose.yml" ] || [ ! -f "$DIR/.env" ]; then
  log "compose.yml ou .env ausente em $DIR: ambiente não instalado, nada a fazer."
  exit 0
fi

# Um deploy por ambiente de cada vez (timer + execução manual).
exec 9>"/run/lock/auditoria-deploy-$ENV_NAME.lock"
if ! flock --nonblock 9; then
  log "outro deploy em andamento, pulando esta volta."
  exit 0
fi

compose() {
  docker compose --project-name "$PROJECT" --project-directory "$DIR" \
    --file "$DIR/compose.yml" --env-file "$DIR/.env" "$@"
}

# 1. Baixa as tags. Falha de rede ou de credencial para aqui: o que está
#    no ar não é tocado. A saída só aparece no erro (a cada 2 min, ela
#    encheria o journal).
if ! pull_out="$(compose pull --quiet "${APP_SERVICES[@]}" 2>&1)"; then
  echo "$pull_out" >&2
  log "ERRO: não consegui baixar as imagens (rede ou token do GHCR?). Nada foi alterado."
  exit 1
fi

# 2. Compara a imagem baixada com a que cada container usa. "--all" conta
#    também container parado: se você parou um serviço de propósito, o timer
#    não o religa sozinho (só religa se a imagem mudar).
#    ("config --images <serviço>" inclui as dependências, por isso a lista
#    inteira filtrada por "/<serviço>:".)
declare -A REF OLD_REV
changed=()
all_images="$(compose config --images)"
for svc in "${APP_SERVICES[@]}"; do
  REF[$svc]="$(grep -F "/$svc:" <<< "$all_images" || true)"
  if [ -z "${REF[$svc]}" ] || [ "$(wc -l <<< "${REF[$svc]}")" -ne 1 ]; then
    log "ERRO: imagem do serviço $svc ausente ou ambígua no compose.yml."
    exit 1
  fi
  wanted="$(docker image inspect --format '{{.Id}}' "${REF[$svc]}")"
  cid="$(compose ps --all --quiet "$svc")"
  running=""
  OLD_REV[$svc]=""
  if [ -n "$cid" ]; then
    running="$(docker inspect --format '{{.Image}}' "$cid")"
    OLD_REV[$svc]="$(docker inspect --format "$REVISION_LABEL" "$cid")"
  fi
  if [ "$wanted" != "$running" ]; then
    changed+=("$svc")
  fi
done

if [ "${#changed[@]}" -eq 0 ] && [ "$FORCE" != "--force" ]; then
  exit 0   # nada novo: silêncio no journal
fi
log "aplicando (imagem nova: ${changed[*]:-nenhuma, --force})"

# 3. Produção: backup antes de subir (D9). Sem MySQL rodando = 1º deploy.
if [ "$ENV_NAME" = prod ]; then
  if [ -n "$(compose ps --status running --quiet mysql)" ]; then
    mkdir -p "$DIR/backups"
    file="$DIR/backups/pre-deploy-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
    trap 'rm -f "$file.tmp"' EXIT
    # MYSQL_PWD em vez de -p: a senha não aparece na lista de processos.
    # Aspas simples de propósito: as variáveis são as do container do MySQL.
    # shellcheck disable=SC2016
    if ! compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --single-transaction --routines --triggers --events --databases "$MYSQL_DATABASE"' \
        | gzip > "$file.tmp" \
      || ! zcat "$file.tmp" | tail -n 1 | grep -q 'Dump completed'; then
      log "ERRO: backup incompleto, deploy cancelado (nada foi alterado)."
      exit 1
    fi
    mv "$file.tmp" "$file"
    log "backup: $file"
    # Mantém só os últimos $KEEP_BACKUPS (nomes gerados aqui, sem espaço).
    # shellcheck disable=SC2012
    ls -1t "$DIR"/backups/pre-deploy-*.sql.gz | tail -n +"$((KEEP_BACKUPS + 1))" | xargs -r rm --
  else
    log "MySQL não está rodando (1º deploy): sem backup."
  fi
fi

# 4. Sobe e espera todos os serviços ficarem healthy.
if ! compose up --detach --remove-orphans --wait --wait-timeout 300; then
  log "ERRO: serviços não ficaram healthy. Veja: sudo docker compose -p $PROJECT ps / logs"
  exit 1
fi

# 5. Histórico (o journal gira; este arquivo fica). A revisão anterior é o
#    alvo de um rollback: IMAGE_TAG=sha-<7> no .env + deploy.sh --force.
for svc in "${APP_SERVICES[@]}"; do
  new_rev="$(docker image inspect --format "$REVISION_LABEL" "${REF[$svc]}")"
  old="${OLD_REV[$svc]:0:7}"
  line="$(date -u +%FT%TZ) $svc ${old:-nenhuma} -> ${new_rev:0:7} ${REF[$svc]}"
  echo "$line" >> "$DIR/deploy-history.log"
  log "$svc: ${old:-nenhuma} -> ${new_rev:0:7}"
done

# Remove só imagens sem tag (as antigas continuam no GHCR para rollback).
docker image prune --force > /dev/null
log "deploy concluído."
