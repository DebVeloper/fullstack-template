# Frontend Conventions

> 공통 컨벤션(네이밍, Git, API 규격 등)은 [CONVENTIONS.md](./CONVENTIONS.md)를 참조하세요.
> 참조 구현 코드는 [SPECS-FRONTEND.md](./SPECS-FRONTEND.md)를 참조하세요.

---

## 1. App Router 구조

전체 프로젝트 디렉토리 구조는 [ARCHITECTURE.md §3](./ARCHITECTURE.md#3-디렉토리-구조)을 참조하세요. 아래는 App Router 특화 구조입니다.

```
src/app/
├── (auth)/                      # 인증 필요 라우트 그룹
│   ├── layout.tsx               # 인증 체크 레이아웃
│   ├── dashboard/
│   │   └── page.tsx
│   └── admin/
│       └── users/
│           └── page.tsx
├── (public)/                    # 공개 라우트 그룹
│   ├── login/
│   │   └── page.tsx
├── api/                         # BFF API Routes
│   ├── auth/                    # 인증 전용 BFF 라우트
│   │   ├── google/
│   │   │   ├── login/
│   │   │   │   └── route.ts     # Google authorize redirect (state + PKCE)
│   │   │   └── callback/
│   │   │       └── route.ts     # code exchange → 쿠키 설정 → redirect
│   │   ├── refresh/
│   │   │   └── route.ts         # 토큰 갱신 → 쿠키 교체
│   │   └── logout/
│   │       └── route.ts         # 로그아웃 → 쿠키 삭제
│   │   └── test-login/
│   │       └── route.ts         # (E2E only) test login — AUTH_TEST_MODE=true일 때만
│   └── [...path]/
│       └── route.ts             # 범용 프록시
├── layout.tsx                   # 루트 레이아웃 (Providers) — 구현 코드는 SPECS-FRONTEND.md §1.10 참조
├── page.tsx                     # 홈페이지
├── loading.tsx                  # 글로벌 로딩
├── error.tsx                    # 글로벌 에러
└── not-found.tsx                # 404
```

**파일 컨벤션:**

| 파일 | 용도 |
|------|------|
| `layout.tsx` | 공유 레이아웃 (자식 라우트 유지) |
| `page.tsx` | 라우트 UI |
| `loading.tsx` | Suspense 폴백 (Skeleton UI) |
| `error.tsx` | Error Boundary (`'use client'` 필수) |
| `not-found.tsx` | 404 페이지 |
| `middleware.ts` | 라우트 보호 (인증 체크, 리다이렉트) |

**Server / Client Component 전략:**

| 기준 | Server Component | Client Component |
|------|-----------------|------------------|
| 데이터 페칭 | O | X (TanStack Query 사용 시 예외) |
| 상태 관리 | X | O |
| 이벤트 핸들러 | X | O |
| 브라우저 API | X | O |
| 기본값 | O (default) | `'use client'` 명시 필요 |

**원칙:** Server Component를 기본으로, `'use client'`는 필요한 최소 범위에만 적용.

**Next.js 15 비동기 API:**
- `cookies()`, `headers()`, `params`, `searchParams`는 모두 비동기 — `await` 필수
- React 19: `forwardRef` 대신 `ref`를 prop으로 직접 전달

**인증 라우트 보호:**
`middleware.ts`로 인증 라우트를 보호합니다. 구현 코드는 [SPECS-FRONTEND.md §1.7](./SPECS-FRONTEND.md#17-인증-미들웨어)를 참조하세요.

---

## 2. 컴포넌트 분류

| 디렉토리 | 역할 | 예시 |
|----------|------|------|
| `components/ui/` | shadcn/ui 기본 컴포넌트 | `button.tsx`, `input.tsx`, `dialog.tsx` |
| `components/features/` | 비즈니스 로직 컴포넌트 | `login-form.tsx`, `user-table.tsx` |
| `components/layouts/` | 레이아웃 컴포넌트 | `header.tsx`, `sidebar.tsx`, `footer.tsx` |

**규칙:**
- `ui/`: shadcn/ui CLI로만 추가, 직접 수정 최소화
- `features/`: 도메인별 하위 디렉토리 가능 (`features/auth/`, `features/users/`)
- 컴포넌트 하나당 파일 하나
- 컴포넌트 파일명은 kebab-case, export는 PascalCase
- 하나의 컴포넌트는 하나의 책임만 갖는다
- 모든 컴포넌트의 props는 interface로 정의한다

**Client Component 패턴:**

```typescript
// Client Component 패턴: "use client" + interface + named export
"use client";

interface LoginFormProps {
  onSuccess?: () => void;
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  // ...
}
```

---

## 3. TanStack Query 패턴

**Query Key Factory** — 구현 코드는 [SPECS-FRONTEND.md §1.4](./SPECS-FRONTEND.md#14-query-key-factory)를 참조하세요.

**Custom Hook 캡슐화** — 구현 코드는 [SPECS-FRONTEND.md §1.5](./SPECS-FRONTEND.md#15-custom-hook-패턴)을 참조하세요.

**규칙:**
- 컴포넌트에서 `useQuery`/`useMutation` 직접 호출 금지 → 반드시 커스텀 훅으로 캡슐화
- Query key는 반드시 factory 패턴 사용
- Mutation 성공 시 관련 query invalidation 필수

---

## 4. Tailwind CSS

shadcn/ui 테마는 Tailwind v4 CSS-first 방식으로 `globals.css`에서 OKLCH CSS 변수로 정의합니다.

**cn() 유틸리티** — `lib/utils.ts`의 `cn()` 사용. 구현 코드는 [SPECS-FRONTEND.md §1.6](./SPECS-FRONTEND.md#16-cn-유틸리티)를 참조하세요.

**규칙:**
- Tailwind v4는 CSS-first 설정 — `tailwind.config.ts` 불필요 (`globals.css`의 `@theme`/`@custom-variant` 사용)
- 인라인 `style` 속성 사용 금지 → Tailwind 클래스 사용
- 조건부 클래스는 `cn()` 유틸리티 사용
- 반응형 디자인은 mobile-first (`sm:`, `md:`, `lg:`)
- 다크모드는 CSS 변수 기반 (`@custom-variant dark`)

**다크모드 전환 전략:**
- class 기반 토글: `<html>` 태그의 `dark` 클래스로 전환 (`@custom-variant dark (&:where(.dark, .dark *))`)
- 초기값: `prefers-color-scheme` 미디어 쿼리로 시스템 설정을 감지하여 초기 테마 결정
- 저장: `localStorage`에 사용자 선택을 저장하여 재방문 시 유지
- FOUC 방지: `<head>`의 인라인 스크립트에서 `localStorage` 값을 읽어 `html.dark` 클래스를 동기적으로 적용 (Next.js `<html suppressHydrationWarning>` 필수)

---

## 5. 에러/로딩 처리

- `loading.tsx`: Skeleton UI로 구성 (`@/components/ui/skeleton`)
- `error.tsx`: `'use client'` 필수, `error`와 `reset` props로 에러 표시 + 재시도
- Toast: Sonner 라이브러리 사용 (`toast.success()`, `toast.error()`)
- API 에러 처리: [SPECS-FRONTEND.md §3](./SPECS-FRONTEND.md#3-에러-처리)를 참조하세요.

---

## 6. openapi-ts API 클라이언트

Backend의 OpenAPI 스펙에서 타입과 API 클라이언트를 자동 생성합니다.

**설정:** `openapi-ts.config.ts`에서 `input` (Backend OpenAPI URL), `output` (`src/client`) 지정. 플러그인: `@hey-api/typescript`, `@hey-api/sdk`, `@hey-api/client-fetch`.

**규칙:**
- `src/client/` 디렉토리는 자동 생성 — 수동 수정 금지
- `src/client/`는 git에 커밋하여 PR에서 API 변경 사항을 추적
- Backend 스키마 변경 시 반드시 재생성 (`npm run generate:api`)
- 생성된 타입을 TanStack Query 커스텀 훅에서 import하여 사용
- 수동 API 타입 정의 금지
- Auth 요청(Google OAuth login/callback, 토큰 갱신, 로그아웃, test-login)은 openapi-ts SDK를 사용하지 않고 BFF 전용 라우트(`/api/auth/*`)를 직접 호출 — SDK는 일반 API(`/api/v1/*`)만 사용

---

## 7. 테스팅

### 7.1 vitest + React Testing Library

**설정:** `vitest.config.ts`에서 `environment: "jsdom"`, `setupFiles: ["./src/tests/setup.ts"]` 설정.

**Wrapper fixture** — `src/tests/utils.tsx`의 `renderWithProviders` 사용. 구현 코드는 [SPECS-FRONTEND.md §1.8](./SPECS-FRONTEND.md#18-테스트-wrapper)를 참조하세요.

**규칙:**
- 사용자 행동 기반 테스트 (`getByRole`, `getByLabelText`) — `getByTestId` 최후 수단
- API 모킹은 MSW 사용
- 각 테스트는 독립적 (공유 상태 금지)

**네이밍 규칙:**
- 파일: `{component-name}.test.tsx`, `{hook-name}.test.ts`
- describe: 컴포넌트/훅 이름
- it: `should {expected behavior} when {condition}`
  예: `it("should display error message when login fails")`

### 7.2 Playwright E2E

**설정:** `playwright.config.ts`에서 `testDir: "./e2e"`, `baseURL: "http://localhost:3000"` 설정.

**규칙:**
- E2E 테스트는 `frontend/e2e/` 디렉토리에 작성
- 파일명: `{feature}.spec.ts`
- 주요 사용자 시나리오만 테스트 (세부 로직은 단위 테스트로)
- CI에서 headless 모드로 실행
- Page Object Model 패턴 사용 권장

**Page Object Model 패턴:**

```typescript
// e2e/pages/login.page.ts
export class LoginPage {
  constructor(private page: Page) {}

  async goto() { await this.page.goto("/login"); }
}
```

Google OAuth는 E2E에서 실제 외부 로그인 대신 **test-login(BFF)** 으로 우회합니다:

```typescript
// e2e/helpers/test-login.ts
import type { APIRequestContext } from "@playwright/test";

export async function testLogin(request: APIRequestContext, email: string, name?: string) {
  const response = await request.post("/api/auth/test-login", {
    data: { email, name }
  });

  if (!response.ok()) {
    throw new Error(`test-login failed: ${response.status()}`);
  }
}
```

**Locator 전략:** `getByRole`, `getByLabel` 우선 사용 (RTL과 일관). `getByTestId`는 최후 수단.

---

## 8. 접근성

- 모든 이미지에 `alt` 속성 필수 (장식용: `alt=""`)
- 인터랙티브 요소에 적절한 `aria-*` 속성
- 키보드 네비게이션 지원
- WCAG AA 기준 색상 대비 충족
- 폼 요소에 `<label>` 연결 필수
- **Focus Ring**: 모든 인터랙티브 요소에 가시적 포커스 표시 (`focus-visible:ring-2`)
- **Touch Target**: 터치 대상 최소 44x44px (`min-h-11 min-w-11`)
- **동적 콘텐츠**: 실시간 업데이트 영역에 `aria-live="polite"` 적용
- **Skip Link**: 메인 콘텐츠 건너뛰기 링크 제공 (반복 네비게이션 우회)

---

## 9. 성능

- 이미지: `next/image` 사용 (raw `<img>` 금지)
- 링크: `next/link` 사용 (raw `<a>` 금지, 외부 링크 예외)
- 코드 분할: 무거운 컴포넌트는 `next/dynamic`으로 지연 로딩
- 번들: barrel file import 금지 → 직접 import
- **Waterfall 방지**: 부모-자식 순차 fetch 금지 → `Promise.all` 또는 Server Component에서 병렬 데이터 로딩
- **번들 최적화**: `'use client'` 파일에서 무거운 라이브러리 직접 import 금지 → `next/dynamic`으로 분리
- 추가 규칙: `.agents/skills/vercel-react-best-practices/SKILL.md` 참조
