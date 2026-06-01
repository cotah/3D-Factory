# 🖨️ Print3D Platform — AI-Powered Custom 3D Printing

> Uma plataforma onde o cliente descreve uma peça, IA gera o conceito visual e o modelo 3D, com fallback para designer humano quando necessário.

---

## Visão Geral

O Print3D Platform é um MVP de e-commerce de impressão 3D personalizada com IA. O cliente descreve o que quer, aprova imagens conceituais geradas por GPT Image 2, e o sistema gera automaticamente um modelo 3D via TRELLIS.2 na RunPod. Se a IA falhar 3 vezes, o pedido é encaminhado para um designer humano.

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Next.js 14 + TypeScript + TailwindCSS + shadcn/ui |
| Backend | Python 3.11 + FastAPI + SQLModel + Alembic |
| Banco | PostgreSQL |
| Filas | Celery + Redis |
| IA Orquestrador | Claude API (Anthropic) |
| Geração de Imagens | OpenAI GPT Image 2 |
| Geração 3D | RunPod Serverless + TRELLIS.2 |
| Validação de Mesh | Trimesh + Open3D |
| Storage | S3-compatible (Cloudflare R2 ou AWS S3) |
| Auth | JWT + bcrypt |
| Deploy | Railway (backend) + Vercel (frontend) |

---

## Fluxo do Produto

```
Cliente cria pedido
       ↓
Claude gera Production Brief
       ↓
GPT Image 2 gera imagens conceituais (6 ângulos)
       ↓
Cliente aprova/rejeita imagens
       ↓
TRELLIS.2 (RunPod) gera modelo 3D
       ↓
Validação automática de mesh (Trimesh/Open3D)
       ↓ (até 3 tentativas)
       ├── Sucesso → Cliente aprova modelo final
       └── 3 falhas → Designer humano
               ↓
       Admin/Designer faz upload manual
               ↓
       Cliente aprova modelo final
               ↓
       Preparação para impressão (admin)
               ↓
       Produção → Envio → Completo
```

---

## Status do Pedido

| Status | Descrição |
|--------|-----------|
| `draft` | Pedido criado, briefing pendente |
| `waiting_brief` | Aguardando geração do briefing pela IA |
| `generating_concept` | Gerando imagens conceituais |
| `waiting_concept_approval` | Aguardando aprovação do cliente |
| `generating_3d` | Gerando modelo 3D via TRELLIS.2 |
| `validating_mesh` | Validando/corrigindo o modelo |
| `ai_revision_required` | Tentativa falhou, tentando novamente |
| `designer_required` | 3 falhas — designer humano necessário |
| `waiting_final_approval` | Aguardando aprovação final do cliente |
| `ready_for_slicing` | Pronto para fatiamento |
| `slicing` | Gerando G-code |
| `ready_to_print` | Na fila de impressão |
| `printing` | Imprimindo |
| `post_processing` | Pós-processamento |
| `shipped` | Enviado |
| `completed` | Concluído |
| `cancelled` | Cancelado |

---

## Estrutura do Projeto

```
print3d-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # Rotas FastAPI
│   │   ├── core/                 # Config, segurança, DB
│   │   ├── models/               # SQLModel models
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── services/
│   │   │   ├── ai/               # Claude, GPT Image, TRELLIS
│   │   │   ├── storage/          # S3/R2
│   │   │   └── mesh/             # Validação e reparo de mesh
│   │   ├── tasks/                # Celery tasks
│   │   └── webhooks/             # RunPod, Stripe
│   ├── alembic/                  # Migrations
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router
│   │   ├── components/
│   │   │   ├── ui/               # shadcn/ui
│   │   │   ├── orders/           # Componentes de pedido
│   │   │   ├── admin/            # Componentes admin
│   │   │   └── 3d/               # Three.js / R3F viewer
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   └── package.json
├── docs/
│   ├── api.md
│   ├── deployment.md
│   └── architecture.md
├── scripts/
│   ├── setup.sh
│   └── seed.py
├── docker-compose.yml
├── .env.example
└── TODO.md
```

---

## Setup Local

### Pré-requisitos

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose
- uv (gerenciador Python recomendado)

### 1. Clone e configure o ambiente

```bash
git clone <repo-url>
cd print3d-platform
cp .env.example .env
# Edite o .env com suas chaves
```

### 2. Suba os serviços de infraestrutura

```bash
docker-compose up -d
# Isso sobe PostgreSQL e Redis
```

### 3. Backend

```bash
cd backend

# Instalar dependências com uv
uv sync

# Rodar migrations
uv run alembic upgrade head

# Seed inicial (admin user)
uv run python scripts/seed.py

# Iniciar servidor de desenvolvimento
uv run uvicorn app.main:app --reload --port 8000
```

### 4. Celery Worker (para jobs assíncronos de IA)

```bash
cd backend

# Em outro terminal
uv run celery -A app.tasks.celery_app worker --loglevel=info
```

### 5. Frontend

```bash
cd frontend

npm install
npm run dev
# Abre em http://localhost:3000
```

### 6. Acessar

| Interface | URL |
|-----------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Docs API (Swagger) | http://localhost:8000/docs |
| Docs API (ReDoc) | http://localhost:8000/redoc |

---

## Variáveis de Ambiente

Veja `.env.example` para a lista completa. As principais:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/print3d
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
RUNPOD_API_KEY=...
RUNPOD_TRELLIS_ENDPOINT_ID=...
```

---

## Rodar Testes

```bash
cd backend

# Todos os testes
uv run pytest

# Com coverage
uv run pytest --cov=app --cov-report=html

# Apenas unitários
uv run pytest tests/unit/

# Apenas integração
uv run pytest tests/integration/
```

---

## API — Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/orders` | Criar pedido |
| GET | `/api/v1/orders` | Listar pedidos |
| GET | `/api/v1/orders/{id}` | Detalhes do pedido |
| POST | `/api/v1/orders/{id}/generate-brief` | Gerar briefing com Claude |
| POST | `/api/v1/orders/{id}/generate-concept` | Gerar imagens com GPT Image 2 |
| POST | `/api/v1/orders/{id}/approve-concept` | Cliente aprova/rejeita imagens |
| POST | `/api/v1/orders/{id}/generate-3d` | Iniciar geração 3D (RunPod) |
| POST | `/api/v1/orders/{id}/validate-mesh` | Validar modelo recebido |
| POST | `/api/v1/orders/{id}/upload-final-model` | Admin/designer faz upload |
| POST | `/api/v1/orders/{id}/approve-final` | Cliente aprova modelo final |
| POST | `/api/v1/webhooks/runpod` | Webhook de callback do RunPod |

Documentação completa em `/docs/api.md` e no Swagger em `/docs`.

---

## Papéis de Usuário

| Role | Acesso |
|------|--------|
| `customer` | Cria pedidos, aprova conceitos e modelos, acompanha status |
| `admin` | Acesso total, gerencia fila de impressão |
| `designer` | Recebe briefing técnico, faz upload do modelo final |
| `print_partner` | Acessa fila de impressão (futuro) |

---

## Providers de Geração 3D

O sistema usa uma interface abstrata que permite trocar o provider:

```python
class ThreeDGenerationProvider(ABC):
    async def generate_model(self, input: GenerateModelInput) -> GenerateModelOutput:
        ...
```

Providers implementados:
- `RunpodTrellisProvider` — produção (TRELLIS.2 via RunPod)
- `MockThreeDProvider` — desenvolvimento local (retorna um cubo de teste)
- `ManualUploadProvider` — fallback humano

---

## Desenvolvimento — Modo Mock

Para desenvolvimento sem gastar créditos de API, use o modo mock:

```env
AI_MOCK_MODE=true
RUNPOD_MOCK_MODE=true
```

Isso ativa providers simulados que retornam dados realistas sem chamar APIs externas.

---

## Deploy

### Railway (Backend)

```bash
# O projeto está configurado para Railway via Procfile
# Variáveis de ambiente configuradas no painel Railway
railway up
```

### Vercel (Frontend)

```bash
cd frontend
vercel deploy
```

Documentação detalhada em `/docs/deployment.md`.

---

## Roadmap

Veja `TODO.md` para o roadmap completo por fases.

### Fase atual: MVP — Fase 1

- [x] Estrutura do projeto
- [x] Auth (JWT) — register, login, refresh, me
- [x] CRUD de pedidos + ações de ciclo de vida
- [x] Upload de arquivos de referência (storage local)
- [x] Dashboard básico do cliente
- [x] 22 testes passando

---

## Licença

Proprietário — todos os direitos reservados.
