# Print3D Platform — TODO & Roadmap

> Status: 🟢 Fases 1, 2, 3 e 4 concluídas (53 testes passando) — próxima: Fase 5 (Print Workflow)
> Em produção: backend (Railway) + frontend (Vercel) + storage R2. RunPod TRELLIS.2 em validação.
> Última atualização: Fase 4 (Validação de mesh + reparo + fallback designer + R2)

---

## Como usar este arquivo

- `[ ]` — Pendente
- `[x]` — Concluído
- `[~]` — Em progresso
- `[!]` — Bloqueado / requer decisão

---

## 🚀 FASE 1 — Fundação e CRUD ✅

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

## 🧠 FASE 2 — IA: Briefing + Imagens Conceituais ✅

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

## 🎨 FASE 3 — Geração 3D + Preview ✅

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

## 🔧 FASE 4 — Validação de Mesh + Fallback Designer ✅

**Objetivo:** Validar modelo automaticamente, fallback humano após 3 falhas.

### Backend — Validação de Mesh
- [x] `services/mesh/mesh_validator.py`
- [x] Verificar se é manifold/watertight (Trimesh)
- [x] Verificar faces abertas (buracos / arestas abertas)
- [x] Verificar escala e unidades (bounding box + volume)
- [ ] Verificar espessura mínima — não implementado (heurística de wall-thickness fica p/ depois)
- [x] Verificar presença de base plana (heurística de vértices no plano Z mínimo)
- [x] Estimar necessidade de suportes (heurística altura vs. footprint)
- [x] Gerar relatório técnico JSON (`MeshReport.to_dict`)

### Backend — Reparo Automático
- [x] Reparo implementado em `mesh_validator.attempt_repair()` (não num `mesh_repair.py` separado)
- [x] Tentativa de fechamento de faces abertas (`trimesh.repair.fill_holes`)
- [x] Correção de normais invertidas (`trimesh.repair.fix_normals`)
- [x] Remoção de geometria duplicada (`merge_vertices` + `unique_faces` + `nondegenerate_faces`)
- [x] Contagem de tentativas por pedido (`ai_attempts`, teto de 3 → `designer_required`)

### Backend — Fallback Designer
- [x] Lógica de 3 tentativas antes de `designer_required`
- [x] `POST /api/v1/orders/{id}/request-designer`
- [x] Criação de `DesignerTask`
- [ ] Geração de pacote para designer (PDF/ZIP) — não feito; o painel do designer exibe o briefing + assets direto
- [x] Notificação por email (SMTP) — `send_designer_notification`
- [x] `POST /api/v1/orders/{id}/upload-final-model` (admin/designer)

### Frontend — Painel do Designer
> Nota: em vez de um dashboard `/admin` genérico, a Fase 4 entregou um painel dedicado `/designer`.
- [x] `/designer` — lista de tarefas do designer (`GET /designer/tasks`)
- [x] `/designer/tasks/[id]` — detalhe da tarefa (briefing técnico, sem dados pessoais do cliente)
- [x] Upload manual do modelo final pelo designer/admin
- [ ] Dashboard `/admin` genérico com filtros de status — adiado (não necessário p/ o fluxo atual)

### Testes — Fase 4
- [x] Testes de validação/reparo de mesh (`test_mesh_validator.py`)
- [x] Testes de transição para `designer_required` e fluxo do designer (`test_designer_flow.py`)
- [x] Testes de storage R2 (`test_r2_storage.py`)
- [x] **53 testes passando no total**

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

**Próximo — Fase 5 (Print Workflow)**
- Objetivo: fila de impressão, aprovação final, status de produção (ver Fase 5 acima)
- Bloqueio atual: validar o endpoint RunPod TRELLIS.2 real (sair do mock) antes de avançar

### Fases concluídas
- ✅ Fase 1 — Setup + Auth + Orders CRUD
- ✅ Fase 2 — IA: Briefing (Claude) + Imagens conceituais (GPT Image 2)
- ✅ Fase 3 — Geração 3D (TRELLIS.2) + Preview React Three Fiber
- ✅ Fase 4 — Validação/reparo de mesh + fallback designer + storage R2
