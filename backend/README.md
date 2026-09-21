# Auditoria API — Backend

API REST construída com **FastAPI + SQLAlchemy + MySQL (Docker)**.

---

## Pré-requisitos

- Python 3.11+
- Docker Desktop rodando
- Git Bash ou PowerShell

---

## Configuração inicial (primeira vez)

### 1. Subir o banco de dados (MySQL via Docker)

```bash
cd backend
docker compose up -d
```

Verifique se o container está rodando:

```bash
docker ps
```

O container `auditoria-mysql` deve aparecer na lista.

---

### 2. Configurar o arquivo `.env`

Copie o exemplo e ajuste se necessário:

```bash
cp .env.example .env
```

O `.env` deve conter (já configurado):

```
DATABASE_URL=mysql+pymysql://auditoria_app:SUA_SENHA_AQUI@127.0.0.1:3307/auditoria
PROJECT_NAME=Auditoria API
API_PREFIX_V1=/api/v1
IS_DEBUG=false
CORS_ALLOWED_ORIGINS=http://localhost:3000
JWT_SECRET=<gere-uma-chave-forte-de-64-caracteres-hex>
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=60
```

---

### 3. Criar ambiente virtual e instalar dependências

```bash
python -m venv venv
source venv/Scripts/activate    # Git Bash
# ou: venv\Scripts\activate     # PowerShell/CMD

pip install -r requirements.txt
```

---

### 4. Rodar as migrations (criar tabelas no banco)

```bash
alembic upgrade head
```

---

### 5. Popular dados iniciais (opcional)

Cria o usuário admin:

```bash
ADMIN_EMAIL=admin@auditoria.local ADMIN_PASSWORD=senha_forte python -m scripts.seed_admin
```

Popula o catálogo de controles:

```bash
python -m scripts.seed_catalog
```

---

### 6. Subir a API

```bash
uvicorn app.main:app --reload
```

---

## Acessar a documentação (Swagger)

Com a API rodando:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health check:** http://localhost:8000/api/v1/Monitoring

---

## Consultar o banco em modo interativo (MySQL)

Se você quer aprender SQL e consultar tudo manualmente, use o terminal interativo do MySQL.

### 1. Entrar no MySQL interativo (dentro do container)

```bash
docker exec -it auditoria-mysql mysql -uauditoria_app -p -D auditoria
```

### 2. Comandos básicos (executar dentro do prompt `mysql>`)

```sql
SHOW TABLES;
DESCRIBE users;
DESCRIBE control_catalog;
DESCRIBE checklist_items;

SELECT * FROM users;
SELECT id, email, role, created_at FROM users ORDER BY id DESC;
SELECT * FROM control_catalog ORDER BY id;
SELECT * FROM checklist_items ORDER BY control_id, sort_order;

SELECT COUNT(*) AS total FROM users;
SELECT COUNT(*) AS total FROM control_catalog;
SELECT COUNT(*) AS total FROM checklist_items;
```

### 3. Contagem de registros em todas as tabelas

```sql
SELECT 'alembic_version' AS tabela, COUNT(*) AS total FROM alembic_version
UNION ALL SELECT 'audit_controls', COUNT(*) FROM audit_controls
UNION ALL SELECT 'audits', COUNT(*) FROM audits
UNION ALL SELECT 'checklist_item_state', COUNT(*) FROM checklist_item_state
UNION ALL SELECT 'checklist_items', COUNT(*) FROM checklist_items
UNION ALL SELECT 'control_catalog', COUNT(*) FROM control_catalog
UNION ALL SELECT 'evidences', COUNT(*) FROM evidences
UNION ALL SELECT 'messagens', COUNT(*) FROM messagens
UNION ALL SELECT 'users', COUNT(*) FROM users;
```

### 4. Sair do MySQL interativo

```sql
exit
```

### 5. Apagar dados da tabela `users` (quando realmente necessário)

> Atenção: isso remove os usuários cadastrados. Faça apenas quando souber o impacto.

```sql
DELETE FROM users;
```

Se quiser reiniciar o contador de IDs após apagar:

```sql
ALTER TABLE users AUTO_INCREMENT = 1;
```

---

## Para rodar novamente (próximas vezes)

Basta executar na ordem:

```bash
# 1. Garantir que o banco está rodando
docker compose up -d

# 2. Ativar o ambiente virtual
source venv/Scripts/activate    # Git Bash
# ou: venv\Scripts\activate     # PowerShell/CMD

# 3. Subir a API
uvicorn app.main:app --reload
```

---

## Parar o banco

```bash
docker compose down
```

Para remover também os dados (reset completo):

```bash
docker compose down -v
```

---

## Estrutura do projeto

```
backend/
├── app/
│   ├── api/v1/         # Rotas (auth, users, client, admin)
│   ├── core/           # Config, JWT, segurança
│   ├── db/             # Session e Base do SQLAlchemy
│   ├── models/         # Modelos ORM
│   ├── schemas/        # Schemas Pydantic
│   └── services/       # Lógica de negócio
├── alembic/            # Migrations do banco
├── scripts/            # Seeds (admin, catálogo)
├── docker-compose.yml  # MySQL via Docker
├── requirements.txt    # Dependências Python
└── .env.example        # Exemplo de variáveis de ambiente
```
