# Print3D Platform — TODO & Roadmap

> Status: 🟢 Fases 1, 2 e 3 concluídas — próxima: Fase 4 (Validação avançada + Designer)
> Última atualização: Sprint 3 (Geração 3D + Preview React Three Fiber)

---

## Como usar este arquivo

- `[ ]` — Pendente
- `[x]` — Concluído
- `[~]` — Em progresso
- `[!]` — Bloqueado / requer decisão

---

## 🚀 FASE 1 — Fundação e CRUD

**Objetivo:** Projeto rodando com auth, banco, criação de pedidos e upload.

### Setup
- [x] Estrutura de pastas e arquivos base
- [x] `pyproject.toml` com todas as dependências
- [x] `docker-compose.yml` com PostgreSQL e Redis
- [x] `alembic.ini` + primeira migration
- [x] `package.json` do frontend com dependências
- [x] `.gitignore` completo
- [x] Scripts de setup (`scripts/setup.sh`)

### Backend — Core
- [x] `app/core/config.py` — Settings com Pydantic
- [x] `app/core/database.py` — Conexão async PostgreSQL
- [x] `app/core/security.py` — JWT, hash de senha
- [x] `app/core/dependencies.py` — Injeção de dependências
- [x] `app/main.py` — App FastAPI com middlewares

### Backend — Models
- [x] `User` model
- [x] `Order` model
- [x] `ProjectAsset` model
- [x] `AIGenerationJob` model
- [x] `DesignerTask` model
- [x] `CustomerApproval` model
- [x] `PrintJob` model

### Backend — Auth
- [x] `POST /api/v1/auth/register`
- [x] `POST /api/v1/auth/login`
- [x] `POST /api/v1/auth/refresh`
- [x] `GET /api/v1/auth/me`
- [x] Middleware de autenticação JWT
- [x] Decorador de roles (customer, admin, designer)

### Backend — Orders
- [x] `POST /api/v1/orders` — Criar pedido
- [x] `GET /api/v1/orders` — Listar (filtros por role)
- [x] `GET /api/v1/orders/{id}` — Detalhes
- [x] `PATCH /api/v1/orders/{id}` — Atualizar
- [x] `DELETE /api/v1/orders/{id}` — Cancelar (soft delete)
- [x] Validação de payload com Pydantic
- [x] Ações de ciclo de vida: `generate-3d`, `validate-mesh`, `upload-final-model`, `approve-final`

### Backend — Upload
- [x] `POST /api/v1/orders/{id}/assets` — Upload de arquivo
- [x] `GET /api/v1/orders/{id}/assets` — Listar assets
- [x] Validação de tipo e tamanho de arquivo
- [x] `StorageService` — local na Fase 1 (S3/R2 na Fase 2)
- [x] Modo mock de storage para dev

### Frontend — Setup
- [x] `next.config.mjs` configurado (Next 14)
- [x] `tailwind.config.ts` com tema customizado
- [x] shadcn/ui configurado (componentes base + `cn`)
- [x] `lib/api.ts` — cliente HTTP com interceptors (refresh automático)
- [x] `lib/auth.ts` — gerenciamento de token
- [x] `types/index.ts` — tipos TypeScript

### Frontend — Auth
- [x] Página `/login`
- [x] Página `/register`
- [x] Contexto de autenticação (`useAuth`)
- [x] Proteção de rotas autenticadas (`ProtectedRoute`)
- [x] Redirect após login

### Frontend — Páginas
- [x] `/` — Landing page
- [x] `/dashboard` — Lista de pedidos do cliente
- [x] `/create` — Formulário de criação de pedido
- [x] `/dashboard/orders/[id]` — Detalhes do pedido

### Testes — Fase 1
- [x] Testes unitários de `security.py` (JWT, hash) — 8 testes
- [x] Testes de integração das rotas de auth
- [x] Testes de integração do CRUD de pedidos
- [x] Testes de upload de arquivo
- [x] **22 testes passando** (`uv run pytest`), 68% de cobertura

---

## 🧠 FASE 2 — IA: Briefing + Imagens Conceituais

**Objetivo:** Claude gera briefing, GPT Image 2 gera imagens, cliente aprova.

### Backend — Claude Service
- [x] `services/ai/claude_service.py` — `generate_production_brief(order) → ProductionBrief`
- [x] Prompt de geração de Production Brief (system prompt JSON-only)
- [x] Parser do response para campos estruturados (tolera code fences)
- [x] Modo mock (briefing fake que varia por categoria)
- [x] `POST /api/v1/orders/{id}/generate-brief`
- [x] Persistência: `order.ai_brief_json` + `order.complexity` (migration nova)

### Backend — GPT Image Service
- [x] `services/ai/openai_image_service.py`
- [x] Geração de 6 ângulos com consistência visual
- [x] Upload automático das imagens para storage (modo real)
- [x] Salvamento como `ProjectAsset` (type: concept_image)
- [x] Modo mock (placeholders picsum.photos determinísticos)
- [x] `POST /api/v1/orders/{id}/generate-concept`
- [x] Tolerância a falha parcial (salva as que deram certo)

### Backend — Aprovação
- [x] `POST /api/v1/orders/{id}/approve-concept`
- [x] Model `CustomerApproval` com stage/status
- [x] Atualização de status do pedido (aprovar → generating_3d; rejeitar → generating_concept)
- [~] Limite de revisões — `ai_attempts` incrementa; teto rígido fica p/ Fase 4 (fallback designer)

### Backend — Celery Tasks
- [~] Geração é **síncrona** na Fase 2 (await direto, jobs rápidos com mock). Celery fica p/ Fase 3, onde TRELLIS.2 demora.
- [x] Logging das operações de IA (loguru) sem expor chaves

### Frontend — Componentes
- [x] `ConceptGallery` — galeria 3x2 + modal + aprovação
- [x] `AIBriefCard` — exibe briefing gerado pela IA (complexidade, riscos, alertas, preço)
- [x] Aprovação (aprovar/rejeitar/comentar) integrada na `ConceptGallery`
- [x] `OrderStatusTimeline` — timeline de status (Fase 1)
- [x] Loading states para operações de IA

### Testes — Fase 2
- [x] Testes do `ClaudeService` com mock (3 testes)
- [x] Testes do `OpenAIImageService` com mock (2 testes)
- [x] Testes das rotas de aprovação
- [x] Teste de fluxo completo Fase 1→2 (`test_brief_flow.py`, 6 testes)
- [x] **33 testes passando** no total, 66% cobertura

---

## 🎨 FASE 3 — Geração 3D + Preview

**Objetivo:** TRELLIS.2 gera o modelo, cliente vê preview 3D.

### Backend — RunPod/TRELLIS.2
- [x] `services/ai/runpod_trellis_service.py`
- [x] Interface abstrata `ThreeDGenerationProvider`
- [x] `RunpodTrellisProvider` — provider real (runsync + tratamento de timeout)
- [x] `MockThreeDProvider` — dev (Duck.glb; falha na tentativa 2; sucesso na 3)
- [~] `ManualUploadProvider` — fallback é via status `designer_required` + `DesignerTask` (upload manual do designer fica p/ Fase 4)
- [x] Controle de timeout e retry (3 tentativas → `designer_required`)
- [~] Webhook de callback do RunPod — geração é **síncrona** (`runsync`); webhook fica p/ quando usar Celery/`run` assíncrono
- [x] `POST /api/v1/orders/{id}/generate-3d` (com controle de tentativas + validação)
- [ ] `POST /api/v1/webhooks/runpod` (não necessário no modo síncrono)

### Backend — Storage de Modelos
- [x] Upload do GLB gerado (`LocalStorageService` → `/static`; `S3StorageService` p/ prod)
- [x] Versionamento: cada tentativa cria um novo `ProjectAsset` (mais recente por `created_at`)
- [~] URL pré-assinada — local serve via `/static`; pré-assinada S3 fica p/ produção
- [x] Nunca deletar arquivo antigo (só adiciona novos)

### Frontend — 3D Viewer
- [x] Instalar `@react-three/fiber` + `@react-three/drei` + `three`
- [x] Componente `ThreeDViewer` — carrega GLB (OBJ/STL = TODO)
- [x] Controles de câmera (orbit, zoom, pan)
- [x] Loading state (Suspense + spinner)
- [x] Fallback (ErrorBoundary) se o modelo não carregar
- [x] `MeshReportCard` + polling de status + botões por status

### Testes — Fase 3
- [x] Testes do `MockThreeDProvider` (padrão de tentativas)
- [x] Testes do `MeshValidator` (box válido, bytes inválidos)
- [x] Testes de geração 3D (sucesso, job+asset, 3 falhas→designer, approve-final)
- [x] **45 testes passando** no total, 65% cobertura
- [ ] Teste do webhook RunPod (não aplicável no modo síncrono)

---

## 🔧 FASE 4 — Validação de Mesh + Fallback Designer

**Objetivo:** Validar modelo automaticamente, fallback humano após 3 falhas.

### Backend — Validação de Mesh
- [ ] `services/mesh/mesh_validator.py`
- [ ] Verificar se é manifold (Trimesh)
- [ ] Verificar faces abertas
- [ ] Verificar escala e unidades
- [ ] Verificar espessura mínima
- [ ] Verificar presença de base plana
- [ ] Estimar necessidade de suportes
- [ ] Gerar relatório técnico JSON

### Backend — Reparo Automático
- [ ] `services/mesh/mesh_repair.py`
- [ ] Tentativa de fechamento de faces abertas
- [ ] Correção de normais invertidas
- [ ] Remoção de geometria duplicada
- [ ] Contagem de tentativas por pedido (`aiAttempts`)

### Backend — Fallback Designer
- [ ] Lógica de 3 tentativas antes de `designer_required`
- [ ] `POST /api/v1/orders/{id}/request-designer`
- [ ] Criação de `DesignerTask`
- [ ] Geração de pacote para designer (PDF/ZIP com briefing + imagens)
- [ ] Notificação por email (SMTP)
- [ ] `POST /api/v1/orders/{id}/upload-final-model` (admin/designer)

### Frontend — Admin
- [ ] `/admin` — dashboard admin
- [ ] `/admin/orders` — lista com filtros de status
- [ ] `/admin/orders/[id]` — gestão completa do pedido
- [ ] `AdminActionPanel` — ações manuais admin
- [ ] `DesignerTaskPanel` — painel do designer
- [ ] Upload manual de modelo final

### Testes — Fase 4
- [ ] Testes de validação de mesh (com arquivos reais de teste)
- [ ] Testes de contagem de tentativas
- [ ] Testes de transição para `designer_required`
- [ ] Testes de upload do designer

---

## 🖨️ FASE 5 — Print Workflow

**Objetivo:** Fila de impressão, aprovação final, status de produção.

### Backend
- [ ] `POST /api/v1/orders/{id}/approve-final`
- [ ] `POST /api/v1/orders/{id}/prepare-print`
- [ ] `PrintJob` model com configurações de impressão
- [ ] Fila de impressão (Redis-based)
- [ ] API de status de produção para admin
- [ ] Atualização manual de status (printing → shipped)

### Frontend — Print Queue
- [ ] `/admin/print-jobs` — fila de impressão
- [ ] `PrintJobCard` — card com configs e status
- [ ] Botões de atualização manual de status

### Futuro (não nesta fase)
- [ ] Integração OrcaSlicer CLI para G-code automático
- [ ] API Moonraker para controle da Creality Hi Combo
- [ ] Rede de impressores parceiros
- [ ] Precificação automática por volume de material

---

## 💳 FASE 6 — Pagamentos + Finalização

- [ ] Integração Stripe (pagamento na criação ou na aprovação final)
- [ ] Stripe webhook para confirmação
- [ ] Histórico de pagamentos
- [ ] Nota fiscal / recibo

---

## 🔒 SEGURANÇA — Itens contínuos

- [ ] Rate limiting nas rotas de IA (evitar custo acidental)
- [ ] Validação de arquivo no upload (magic bytes, não só extensão)
- [ ] CORS configurado corretamente por ambiente
- [ ] Headers de segurança (Helmet equivalente)
- [ ] Sanitização de inputs
- [ ] Webhook secrets validados (HMAC)
- [ ] Logs sem dados sensíveis
- [ ] Revisão de permissões por role
- [ ] Designer não vê dados pessoais do cliente

---

## 📊 OBSERVABILIDADE — Itens contínuos

- [ ] Structured logging com loguru
- [ ] Sentry no backend e frontend
- [ ] Health check endpoint `/health`
- [ ] Métricas de jobs de IA (tempo, taxa de sucesso)
- [ ] Alertas de jobs travados

---

## 🐛 BUGS CONHECIDOS

_Nenhum aberto._

### Correções aplicadas na Fase 1 (na fundação pré-existente)
1. **`models.py` — relacionamentos SQLModel não inicializavam.** O `from __future__
   import annotations` transformava `list["Order"]` em string totalmente
   stringificada e o SQLAlchemy 2.0.x rejeitava. Removido o import; anotações
   reais restauradas.
2. **`models.py` — timezone vs. Postgres.** `utcnow()` retornava datetime *aware*,
   mas as colunas são `TIMESTAMP WITHOUT TIME ZONE`; o asyncpg rejeitava no insert.
   Agora `utcnow()` retorna UTC *naive* (consistente em Postgres e SQLite).
3. **`config.py` — `.env` da raiz não era carregado.** O backend roda a partir de
   `backend/`, mas o `.env` está na raiz; só os defaults eram usados (CORS quebrava
   na porta 3001). Agora resolve o `.env` da raiz por caminho absoluto.
4. **`scripts/seed.py` — `ModuleNotFoundError: app`.** Rodando como script, só
   `scripts/` entrava no `sys.path`. Adicionado o root do backend ao path.

### Nota de ambiente (local do Henrique)
- A porta **8000 está ocupada por outro projeto** seu (`smarttap-backend`) e a **3000**
  por outro frontend. Para usar as portas padrão do Print3D, pare esses serviços
  antes. Em testes este projeto subiu em 8001 (backend) e 3001 (frontend).

---

## 📝 DECISÕES TÉCNICAS

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Gerenciador Python | uv | Mais rápido que pip/poetry, lockfile determinístico |
| ORM | SQLModel | Integra nativamente com FastAPI + Pydantic |
| Filas | Celery + Redis | Maturidade, retry fácil, monitoring |
| Storage | Cloudflare R2 | Sem egress fees, compatível com S3 SDK |
| 3D Viewer | React Three Fiber | Mais idiomático para React que Three.js puro |
| Auth | JWT próprio | Controle total, sem dependência de terceiros |

---

## 🗓️ Sprint atual

**Sprint 1 — Setup + Auth + Orders CRUD**
- Prazo: 5 dias
- Objetivo: projeto rodando localmente do backend ao frontend
