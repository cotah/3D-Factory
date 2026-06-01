#!/usr/bin/env bash
# One-shot local setup for the Print3D Platform (Phase 1).
# Brings up infra, installs deps, runs migrations and seeds the admin user.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> 1/6 Creating .env from example (if missing)"
[ -f .env ] || cp .env.example .env

echo "==> 2/6 Starting Postgres + Redis (docker compose)"
docker compose up -d

echo "==> 3/6 Installing backend dependencies (uv sync)"
cd backend
uv sync

echo "==> 4/6 Running database migrations"
uv run alembic upgrade head

echo "==> 5/6 Seeding admin user"
uv run python scripts/seed.py

echo "==> 6/6 Installing frontend dependencies"
cd ../frontend
npm install

cat <<'EOF'

Setup complete.

Start the backend:
  cd backend && uv run uvicorn app.main:app --reload --port 8000

Start the frontend:
  cd frontend && npm run dev

URLs:
  Frontend  http://localhost:3000
  API       http://localhost:8000
  Swagger   http://localhost:8000/docs
EOF
