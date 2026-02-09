# Infrastructure Reference Specifications

> 이 문서는 인프라/설정 파일의 **참조 구현 코드**를 모아둔 것입니다.
> 아키텍처 설계는 [ARCHITECTURE.md](./ARCHITECTURE.md), 컨벤션은 [CONVENTIONS.md](./CONVENTIONS.md)를 참조하세요.

---

## 1. 환경변수 (.env.example)

> 환경변수 설명은 [ARCHITECTURE.md §6](./ARCHITECTURE.md#6-개발-환경)을 참조하세요.
> `LOG_JSON`의 코드 기본값은 `True`(운영 환경 대비)이며, `.env.example`에서는 `false`(개발 환경 콘솔 출력용)로 설정합니다.

```bash
# === Backend ===
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/app
REDIS_URL=redis://redis:6379/0
SECRET_KEY=change-me-to-random-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
ALLOWED_ORIGINS=http://localhost:3000,http://frontend:3000
LOG_LEVEL=INFO
LOG_JSON=false

# === Frontend ===
BACKEND_URL=http://backend:8000
NEXT_PUBLIC_APP_NAME=App

# === Database ===
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=app
```

---

## 2. Docker

### 2.1 docker-compose.yml (개발 환경)

> 서비스 구성은 [ARCHITECTURE.md §6](./ARCHITECTURE.md#6-개발-환경)을 참조하세요.

```yaml
services:
  frontend:
    build:
      context: .
      dockerfile: docker/frontend/Dockerfile
      target: development
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
    environment:
      - BACKEND_URL=http://backend:8000
      - NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME:-App}
    depends_on:
      backend:
        condition: service_healthy

  backend:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
      target: development
    ports:
      - "8000:8000"
    volumes:
      - ./backend/app:/app/app
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  db:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-app}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

### 2.2 docker-compose.prod.yml (운영 환경)

> 개발 환경과의 차이점은 [ARCHITECTURE.md §7](./ARCHITECTURE.md#7-배포)를 참조하세요.

```yaml
services:
  frontend:
    build:
      context: .
      dockerfile: docker/frontend/Dockerfile
      target: production
    ports:
      - "3000:3000"
    environment:
      - BACKEND_URL=${BACKEND_URL}
      - NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME}
    depends_on:
      backend:
        condition: service_healthy

  backend:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
      target: production
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - LOG_JSON=true
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

**개발 환경과의 주요 차이:**
- `target: production` — Multi-stage 빌드의 운영 스테이지 사용
- 소스 마운트 없음 — 이미지에 코드 포함
- 환경변수를 외부에서 주입 (`${DATABASE_URL}` 등)
- 디버그 포트 미노출 (DB, Redis 포트 바인딩 없음)
- `LOG_JSON=true` — 운영 환경에서는 JSON 포맷 로깅

### 2.3 docker/backend/Dockerfile

> Multi-stage 전략은 [ARCHITECTURE.md §7](./ARCHITECTURE.md#7-배포)를 참조하세요.

```dockerfile
# === Base ===
FROM python:3.12-slim AS base
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

# === Development ===
FROM base AS development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# === Production ===
FROM base AS production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2.4 docker/frontend/Dockerfile

```dockerfile
# === Base ===
FROM node:20-alpine AS base
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .

# === Development ===
FROM base AS development
CMD ["npm", "run", "dev"]

# === Build ===
FROM base AS build
RUN npm run build

# === Production ===
FROM node:20-alpine AS production
WORKDIR /app
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
CMD ["node", "server.js"]
```

**주의:** Frontend 운영 빌드는 `next.config.ts`에서 `output: "standalone"` 설정이 필요합니다.

---

## 3. CI/CD

### 3.1 .github/workflows/ci.yml

> CI/CD 구성은 [ARCHITECTURE.md §7](./ARCHITECTURE.md#7-배포)를 참조하세요.

```yaml
name: CI

on:
  pull_request:
    branches: [main, develop]

jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - run: npm run lint
        working-directory: frontend
      - run: npx tsc --noEmit
        working-directory: frontend
      - run: npm test -- --coverage
        working-directory: frontend

  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test
      REDIS_URL: redis://localhost:6379/0
      SECRET_KEY: test-secret-key
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: backend/requirements.txt
      - run: pip install -r requirements.txt
        working-directory: backend
      - run: ruff check .
        working-directory: backend
      - run: mypy --strict .
        working-directory: backend
      - run: pytest --cov --cov-report=xml
        working-directory: backend

  e2e:
    runs-on: ubuntu-latest
    needs: [frontend, backend]
    steps:
      - uses: actions/checkout@v4
      - run: docker compose up -d
      - run: docker compose exec backend alembic upgrade head
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npx playwright install --with-deps
        working-directory: frontend
      - run: npx playwright test
        working-directory: frontend
      - run: docker compose down
```

---

## 4. DB 마이그레이션

### 4.1 alembic/env.py (async 설정)

> 마이그레이션 워크플로우는 [ARCHITECTURE.md §4.4](./ARCHITECTURE.md#44-db-마이그레이션)를 참조하세요.

```python
# backend/alembic/env.py
import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.models.base import Base

# Alembic Config
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = create_async_engine(settings.DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

---

## 5. Git Hooks

### 5.1 .pre-commit-config.yaml

> Hook 구성은 [CONVENTIONS.md §4](./CONVENTIONS.md#4-pre-commit-hooks)를 참조하세요.

```yaml
repos:
  - repo: local
    hooks:
      # --- Frontend ---
      - id: frontend-lint
        name: Frontend Lint
        entry: bash -c 'cd frontend && npx next lint'
        language: system
        files: '\.(ts|tsx)$'
        pass_filenames: false

      - id: frontend-typecheck
        name: Frontend Type Check
        entry: bash -c 'cd frontend && npx tsc --noEmit'
        language: system
        files: '\.(ts|tsx)$'
        pass_filenames: false

      - id: frontend-format
        name: Frontend Format Check
        entry: bash -c 'cd frontend && npx prettier --check "src/**/*.{ts,tsx}"'
        language: system
        files: '\.(ts|tsx)$'
        pass_filenames: false

      # --- Backend ---
      - id: backend-lint
        name: Backend Lint + Fix
        entry: bash -c 'cd backend && ruff check --fix .'
        language: system
        files: '\.py$'
        pass_filenames: false

      - id: backend-format
        name: Backend Format
        entry: bash -c 'cd backend && ruff format .'
        language: system
        files: '\.py$'
        pass_filenames: false

      - id: backend-typecheck
        name: Backend Type Check
        entry: bash -c 'cd backend && mypy --strict .'
        language: system
        files: '\.py$'
        pass_filenames: false
```

---

## 6. Frontend 설정

### 6.1 next.config.ts (보안 헤더)

> Security Headers는 [ARCHITECTURE.md §4.5](./ARCHITECTURE.md#45-보안)를 참조하세요.

```typescript
// frontend/next.config.ts
import type { NextConfig } from "next";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
  {
    key: "Strict-Transport-Security",
    value: "max-age=31536000; includeSubDomains",
  },
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "font-src 'self'",
      "connect-src 'self'",
      "frame-ancestors 'none'",
    ].join("; "),
  },
];

const nextConfig: NextConfig = {
  output: "standalone",
  headers: async () => [
    {
      source: "/(.*)",
      headers: securityHeaders,
    },
  ],
};

export default nextConfig;
```

### 6.2 vitest.config.ts

> 테스트 설정은 [CONVENTIONS-FRONTEND.md §7.1](./CONVENTIONS-FRONTEND.md#71-vitest--react-testing-library)을 참조하세요.

```typescript
// frontend/vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/tests/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      exclude: [
        "src/client/**",
        "src/tests/**",
        "**/*.d.ts",
      ],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

### 6.3 playwright.config.ts

> E2E 테스트 설정은 [CONVENTIONS-FRONTEND.md §7.2](./CONVENTIONS-FRONTEND.md#72-playwright-e2e)를 참조하세요.

```typescript
// frontend/playwright.config.ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
  },
});
```

### 6.4 tsconfig.json

> TypeScript strict mode와 절대 경로는 [CONVENTIONS.md §2](./CONVENTIONS.md#2-코드-스타일)를 참조하세요.

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### 6.5 package.json

> 의존성 버전은 참고용이며, 실제 프로젝트에서는 `npm install` 시점의 최신 호환 버전을 사용합니다.

```json
{
  "name": "frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "test:e2e": "playwright test",
    "generate:api": "openapi-ts"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@tanstack/react-query": "^5.0.0",
    "@tanstack/react-query-devtools": "^5.0.0",
    "react-hook-form": "^7.0.0",
    "@hookform/resolvers": "^3.0.0",
    "zod": "^3.0.0",
    "sonner": "^1.0.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    "@hey-api/client-fetch": "latest"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "tailwindcss": "^4.0.0",
    "@hey-api/openapi-ts": "latest",
    "vitest": "^2.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "@testing-library/user-event": "^14.0.0",
    "msw": "^2.0.0",
    "jsdom": "^25.0.0",
    "@playwright/test": "^1.0.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "^15.0.0",
    "prettier": "^3.0.0",
    "@v8/coverage": "latest"
  }
}
```

### 6.6 globals.css (Tailwind v4 + shadcn/ui 테마)

> Tailwind v4 CSS-first 설정은 [CONVENTIONS-FRONTEND.md §4](./CONVENTIONS-FRONTEND.md#4-tailwind-css)를 참조하세요.

```css
/* frontend/src/app/globals.css */
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

@theme inline {
  /* shadcn/ui OKLCH 테마 변수 */
  --color-background: oklch(1 0 0);
  --color-foreground: oklch(0.145 0 0);
  --color-card: oklch(1 0 0);
  --color-card-foreground: oklch(0.145 0 0);
  --color-popover: oklch(1 0 0);
  --color-popover-foreground: oklch(0.145 0 0);
  --color-primary: oklch(0.205 0 0);
  --color-primary-foreground: oklch(0.985 0 0);
  --color-secondary: oklch(0.97 0 0);
  --color-secondary-foreground: oklch(0.205 0 0);
  --color-muted: oklch(0.97 0 0);
  --color-muted-foreground: oklch(0.556 0 0);
  --color-accent: oklch(0.97 0 0);
  --color-accent-foreground: oklch(0.205 0 0);
  --color-destructive: oklch(0.577 0.245 27.325);
  --color-destructive-foreground: oklch(0.577 0.245 27.325);
  --color-border: oklch(0.922 0 0);
  --color-input: oklch(0.922 0 0);
  --color-ring: oklch(0.708 0 0);
  --radius: 0.625rem;
}

@layer base {
  *,
  ::after,
  ::before,
  ::backdrop,
  ::file-selector-button {
    border-color: var(--color-border);
  }
  body {
    background-color: var(--color-background);
    color: var(--color-foreground);
  }
}
```

---

## 7. Backend 설정

### 7.1 pyproject.toml

> Ruff, mypy, pytest 설정은 [CONVENTIONS.md §2](./CONVENTIONS.md#2-코드-스타일)과 [CONVENTIONS-BACKEND.md §8](./CONVENTIONS-BACKEND.md#8-테스팅-pytest)을 참조하세요.

```toml
# backend/pyproject.toml
[project]
name = "app"
version = "0.1.0"
requires-python = ">=3.12"

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### 7.2 requirements.txt

```text
# backend/requirements.txt
# === Framework ===
fastapi>=0.115.0
uvicorn[standard]>=0.30.0

# === Database ===
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0

# === Redis ===
redis>=5.0.0

# === Auth ===
PyJWT>=2.8.0
passlib[bcrypt]>=1.7.4

# === Validation ===
pydantic>=2.0.0
pydantic-settings>=2.0.0
email-validator>=2.0.0

# === HTTP ===
httpx>=0.27.0

# === Rate Limiting ===
slowapi>=0.1.9

# === Logging ===
structlog>=24.0.0

# === Testing ===
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
fakeredis[lua]>=2.21.0

# === Lint/Type ===
ruff>=0.4.0
mypy>=1.10.0
```

---

## 8. 공통 설정

### 8.1 .prettierrc

```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "all",
  "printWidth": 80
}
```

### 8.2 .eslintrc.json

```json
{
  "extends": ["next/core-web-vitals", "next/typescript"]
}
```
