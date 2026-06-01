# CLAUDE CODE — PROMPT DE EXECUÇÃO
# Print3D Platform — Fase 1: Fundação

## Contexto
Você está num repositório já estruturado para uma plataforma de impressão 3D personalizada com IA.
A fundação (modelos, config, segurança, estrutura) já foi criada.
Seu trabalho agora é completar a Fase 1 e garantir que tudo roda.

## Stack
- Backend: Python 3.11 + FastAPI + SQLModel + Alembic + Celery + Redis
- Frontend: Next.js 14 + TypeScript + TailwindCSS + shadcn/ui
- Banco: PostgreSQL
- Gerenciador Python: uv
- Package manager frontend: npm

## O que JÁ EXISTE (não recriar)
- `/backend/app/core/config.py` — settings com pydantic-settings
- `/backend/app/core/database.py` — engine async PostgreSQL
- `/backend/app/core/security.py` — JWT e hashing de senha
- `/backend/app/models/models.py` — todos os SQLModel models
- `/backend/app/main.py` — app FastAPI com CORS e lifespan
- `/backend/app/api/v1/endpoints/auth.py` — register, login, refresh
- `/backend/app/api/v1/endpoints/orders.py` — CRUD básico de pedidos
- `/backend/app/services/ai/claude_service.py` — Claude com mock mode
- `/backend/app/services/ai/runpod_trellis_service.py` — TRELLIS.2 com mock mode
- `/backend/app/services/mesh/mesh_validator.py` — validação Trimesh
- `/backend/app/tasks/celery_app.py` — Celery configurado
- `/backend/tests/unit/test_security.py` — testes de JWT e senha
- `/backend/tests/integration/test_orders_api.py` — testes de API
- `/backend/scripts/seed.py` — seed do banco
- `/frontend/src/types/index.ts` — tipos TypeScript
- `/frontend/src/lib/api.ts` — cliente HTTP Axios
- `docker-compose.yml` — PostgreSQL + Redis
- `.env.example` — todas as variáveis
- `README.md`, `TODO.md`

## TAREFA 1 — Instalar dependências e subir o projeto

```bash
# 1. Subir infraestrutura
docker-compose up -d

# 2. Backend
cd backend
uv sync
cp ../.env.example ../.env
# Deixar AI_MOCK_MODE=true e RUNPOD_MOCK_MODE=true no .env

# 3. Rodar migrations
uv run alembic upgrade head

# 4. Seed
uv run python scripts/seed.py

# 5. Subir servidor
uv run uvicorn app.main:app --reload --port 8000

# 6. Verificar se está rodando
curl http://localhost:8000/health
```

## TAREFA 2 — Completar endpoint GET /auth/me

O arquivo `/backend/app/api/v1/endpoints/auth.py` tem um TODO no endpoint `/auth/me`.

Implemente a dependency `get_current_user` em `/backend/app/core/dependencies.py`:

```python
# Deve:
# 1. Extrair o token do header Authorization: Bearer {token}
# 2. Decodificar o JWT
# 3. Buscar o User no banco pelo ID do subject
# 4. Retornar o User ou lançar 401
```

Depois conecte essa dependency no endpoint `/auth/me`.

## TAREFA 3 — Completar upload de assets

O arquivo `/backend/app/api/v1/endpoints/assets.py` está incompleto.

Implemente:
- `POST /orders/{order_id}/assets` — recebe arquivo via multipart/form-data
- Valida tipo e tamanho (use `settings.upload_allowed_extensions` e `settings.upload_max_bytes`)
- Por agora, salva localmente em `/tmp/print3d_uploads/` (storage real vem na Fase 2)
- Cria `ProjectAsset` no banco com `storage_url` como path local
- `GET /orders/{order_id}/assets` — lista assets do pedido

## TAREFA 4 — Completar rotas faltando em orders.py

Adicione em `/backend/app/api/v1/endpoints/orders.py`:

- `POST /orders/{id}/generate-3d` — inicia geração 3D, muda status para `generating_3d`
- `POST /orders/{id}/validate-mesh` — simula validação, muda status para `validating_mesh`
- `POST /orders/{id}/upload-final-model` — admin faz upload do STL final
- `POST /orders/{id}/approve-final` — cliente aprova modelo final

## TAREFA 5 — Rodar os testes e garantir que passam

```bash
cd backend
uv run pytest tests/ -v

# Deve ter:
# - tests/unit/test_security.py — todos passando
# - tests/integration/test_orders_api.py — todos passando

# Se algum falhar, CORRIJA antes de continuar
```

Atenção: os testes de integração precisam do SQLite com aiosqlite.
Adicione `aiosqlite` nas dependências se não estiver.

## TAREFA 6 — Frontend básico

Instale shadcn/ui e configure o projeto:

```bash
cd frontend
npm install
npx shadcn-ui@latest init
# Escolha: TypeScript, Default style, Slate color, no CSS variables is fine
```

Crie as seguintes páginas mínimas:

### `/app/page.tsx` — Landing page simples
- Nome do produto: Print3D
- Tagline: "Peças 3D personalizadas com IA"
- Botão: "Criar pedido" → /create
- Botão: "Entrar" → /login

### `/app/login/page.tsx` — Login
- Formulário: email + senha
- Botão de submit
- Chama `authApi.login()` do `src/lib/api.ts`
- Redireciona para `/dashboard` após sucesso
- Mostra erro em caso de falha

### `/app/dashboard/page.tsx` — Dashboard
- Lista de pedidos do usuário (chama `ordersApi.list()`)
- Para cada pedido: título, status, data
- Botão "Criar novo pedido"

### `/app/create/page.tsx` — Criar pedido
- Formulário com: título, descrição, categoria, tamanho, cores, material, prazo, notas
- Validação com react-hook-form + zod
- Chama `ordersApi.create()` ao submeter
- Redireciona para `/dashboard/orders/{id}` após sucesso

### `/app/dashboard/orders/[id]/page.tsx` — Detalhe do pedido
- Título e status do pedido
- Timeline de status (componente `OrderStatusTimeline`)
- Lista de assets do pedido
- Botão "Gerar Briefing" (se status === "draft")

## TAREFA 7 — Componentes base

Crie em `/frontend/src/components/orders/`:

### `OrderStatusTimeline.tsx`
- Mostra o ciclo de vida do pedido
- Status atual destacado
- Usa `ORDER_STATUS_LABELS` de `src/types/index.ts`

### `StatusBadge.tsx`
- Badge colorido para cada status
- Usa `ORDER_STATUS_COLORS` de `src/types/index.ts`

## TAREFA 8 — Validar tudo junto

1. Backend rodando em `localhost:8000`
2. Frontend rodando em `localhost:3000`
3. Fluxo básico funcionando:
   - Registrar → Login → Dashboard → Criar pedido → Ver pedido
4. Health check: `curl http://localhost:8000/health` retorna `{"status": "ok"}`
5. Swagger abre em `http://localhost:8000/docs`

## REGRAS IMPORTANTES

1. Não quebre o que já está funcionando
2. Mantenha `AI_MOCK_MODE=true` e `RUNPOD_MOCK_MODE=true` para não gastar créditos
3. Antes de criar qualquer arquivo, verifique se ele já existe
4. Se encontrar um bug, corrija e documente
5. Mantenha os testes passando em todo momento
6. Não simplifique removendo features — apenas implemente o que está faltando
7. Se uma library não estiver no pyproject.toml, adicione antes de usar
8. Nunca exponha segredos nos logs ou no relatório

## APÓS COMPLETAR

Execute e relate:
- `uv run pytest --cov=app tests/ -v` — cobertura dos testes
- `npm run build` — build do frontend sem erros
- `npm run type-check` — zero erros TypeScript
- Curl nos endpoints principais mostrando respostas corretas

---
Comece pela TAREFA 1 (subir o projeto) e avance sequencialmente.
Relate o que foi feito e qualquer problema encontrado.
