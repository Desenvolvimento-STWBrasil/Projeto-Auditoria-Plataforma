# infra/ — o que roda na VM (ADR-001)

A VM **não guarda código-fonte**: só os arquivos desta pasta, copiados para
`/srv/auditoria/`, e as imagens publicadas no GHCR pelo `release.yml`.
Nada aqui tem IP, senha ou token. Os segredos ficam só na VM, em
`/srv/auditoria/<ambiente>/.env` (root, 600).

| Arquivo | Na VM | Card |
|---|---|---|
| `scripts/deploy.sh` | `/srv/auditoria/bin/deploy.sh` | INFRA-05 |
| `systemd/auditoria-deploy@.service` / `.timer` | `/etc/systemd/system/` | INFRA-05 |
| `ssh/10-auditoria.conf` | `/etc/ssh/sshd_config.d/` | INFRA-05 |
| `compose.app.yml` | `/srv/auditoria/staging/compose.yml` e `/srv/auditoria/prod/compose.yml` | INFRA-06 / INFRA-07 |
| `compose.edge.yml` | `/srv/auditoria/edge/compose.yml` | INFRA-06 |
| `edge/conf.d/*.conf` | `/srv/auditoria/edge/conf.d/` | INFRA-06 (`prod.conf` no INFRA-07) |
| `env/staging.env.example` | modelo de `/srv/auditoria/staging/.env` | INFRA-06 |


## Como o deploy funciona

1. O merge na `develop` publica `:staging`; a aprovação na `main` reaponta `:prod` para o mesmo digest.
2. A cada 2 min, `auditoria-deploy@<ambiente>.timer` roda o `deploy.sh <ambiente>`.
3. O script baixa as imagens da tag `IMAGE_TAG` do `.env`. Se forem as mesmas que estão rodando, sai sem fazer nada.
4. Se mudaram: na produção faz `mysqldump` antes, depois `docker compose up --wait` e grava a troca em `deploy-history.log`.

## Contrato com o compose de cada ambiente

- Serviços `mysql`, `backend` e `frontend`. O `mysql` tem healthcheck, e o container define `MYSQL_ROOT_PASSWORD` e `MYSQL_DATABASE` (o backup usa os dois).
- Imagens `${IMAGE_REPO}/backend:${IMAGE_TAG}` e `${IMAGE_REPO}/frontend:${IMAGE_TAG}`.
- Projeto Compose `auditoria-<ambiente>`.

## Staging

Só por túnel SSH, do PC:

```bash
ssh -N -L 8081:localhost:8081 auditoria-vm      # deixe aberto
```

No navegador: `http://localhost:8081` (Swagger em `/docs`). O edge tem que estar no ar antes do 1º deploy de um ambiente, porque é ele que cria as redes `auditoria-<ambiente>-edge`

```bash
sudo docker compose -f /srv/auditoria/edge/compose.yml up -d --wait
sudo docker compose -f /srv/auditoria/edge/compose.yml exec edge nginx -t   # depois de editar um .conf
sudo docker compose -f /srv/auditoria/edge/compose.yml exec edge nginx -s reload
```

## Operação

```bash
sudo journalctl -u auditoria-deploy@staging -n 50          # o que o timer fez
sudo /srv/auditoria/bin/deploy.sh staging --force     # reaplica (ex.: depois de editar o .env)
sudo cat /srv/auditoria/prod/deploy-history.log       # trocas de versão
```

**Rollback:** no `.env` do ambiente, troque `IMAGE_TAG` para `sha-<7>` da versão anterior (a revisão está no `deploy-history.log`) e rode `deploy.sh <ambiente> --force`. A tag `sha-<7>` vale também na produção, porque o `:prod` é a mesma imagem publicada pela `develop`. Enquanto a tag fixa estiver no `.env`, o timer não aplica versões novas. Para retomar, volte o valor para `staging` ou `prod`.
