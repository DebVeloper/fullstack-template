import {
  expect,
  test,
  type APIRequestContext,
  type Page
} from "@playwright/test"

interface TestLoginPayload {
  email: string
  name?: string
}

interface ErrorEnvelope {
  error: {
    code: string
    message: string
    details: unknown
  }
}

interface AdminUserItem {
  id: string
  email: string
}

interface AdminUsersListResponse {
  items: AdminUserItem[]
}

const ADMIN_EMAIL = process.env.ADMIN_EMAIL ?? "admin@example.com"
const AUTH_TEST_MODE_ENABLED = process.env.AUTH_TEST_MODE === "true"
const AUTH_TEST_SECRET = process.env.AUTH_TEST_SECRET ?? ""

function uniqueEmail(prefix: string): string {
  const nonce = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  return `${prefix}-${nonce}@example.com`
}

function escapeForRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

function userRow(page: Page, email: string) {
  return page.getByRole("row", {
    name: new RegExp(escapeForRegex(email), "i")
  })
}

async function testModeLogin(
  request: APIRequestContext,
  payload: TestLoginPayload
) {
  return request.post("/api/auth/test-login", {
    data: payload
  })
}

async function expectTestModeLoginSuccess(
  request: APIRequestContext,
  payload: TestLoginPayload
): Promise<void> {
  const response = await testModeLogin(request, payload)
  expect(response.status()).toBe(204)
}

async function expectTestModeLoginUnauthorized(
  request: APIRequestContext,
  payload: TestLoginPayload
): Promise<void> {
  const response = await testModeLogin(request, payload)
  expect(response.status()).toBe(401)
  const body = (await response.json()) as ErrorEnvelope
  expect(body.error.code).toBe("UNAUTHORIZED")
}

async function expectDashboardRedirectsToLogin(page: Page): Promise<void> {
  await page.goto("/dashboard")
  await page.waitForURL("**/login**")
  expect(page.url()).toContain("/login")
}

test.describe("auth/admin flows with test-mode login", () => {
  test.skip(
    !AUTH_TEST_MODE_ENABLED || AUTH_TEST_SECRET.length === 0,
    "Set AUTH_TEST_MODE=true and AUTH_TEST_SECRET before running E2E"
  )

  test("user test-login allows dashboard access", async ({ page }) => {
    await expectTestModeLoginSuccess(page.request, {
      email: uniqueEmail("e2e-user"),
      name: "E2E User"
    })

    await page.goto("/dashboard")
    await page.waitForURL("**/dashboard")

    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible()
  })

  test("admin test-login allows admin users screen and Users menu", async ({ page }) => {
    await expectTestModeLoginSuccess(page.request, {
      email: ADMIN_EMAIL,
      name: "Admin"
    })

    await page.goto("/dashboard")
    await page.waitForURL("**/dashboard")

    await expect(page.getByRole("link", { name: "Users" })).toBeVisible()
    await page.getByRole("link", { name: "Users" }).click()
    await page.waitForURL("**/admin/users")

    await expect(page.getByRole("heading", { name: "Admin Users" })).toBeVisible()
  })

  test("admin lock blocks user test-login and dashboard access", async ({
    page,
    request,
    browser
  }) => {
    const targetEmail = uniqueEmail("lock-target")
    await expectTestModeLoginSuccess(request, {
      email: targetEmail,
      name: "Lock Target"
    })

    await expectTestModeLoginSuccess(page.request, {
      email: ADMIN_EMAIL,
      name: "Admin"
    })
    await page.goto("/admin/users")
    await page.waitForURL("**/admin/users")

    const row = userRow(page, targetEmail)
    await expect(row).toBeVisible()
    await row.getByRole("button", { name: "Lock" }).click()
    await expect(row.getByRole("button", { name: "Unlock" })).toBeVisible()

    const blockedContext = await browser.newContext({
      baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000"
    })

    try {
      const blockedPage = await blockedContext.newPage()
      await expectTestModeLoginUnauthorized(blockedPage.request, { email: targetEmail })
      await expectDashboardRedirectsToLogin(blockedPage)
    } finally {
      await blockedContext.close()
    }
  })

  test("admin delete blocks user test-login and dashboard access", async ({
    page,
    request,
    browser
  }) => {
    const targetEmail = uniqueEmail("delete-target")
    await expectTestModeLoginSuccess(request, {
      email: targetEmail,
      name: "Delete Target"
    })

    await expectTestModeLoginSuccess(page.request, {
      email: ADMIN_EMAIL,
      name: "Admin"
    })
    await page.goto("/admin/users")
    await page.waitForURL("**/admin/users")

    const row = userRow(page, targetEmail)
    await expect(row).toBeVisible()
    await row.getByRole("button", { name: "Delete" }).click()
    await expect(userRow(page, targetEmail)).toHaveCount(0)

    const blockedContext = await browser.newContext({
      baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000"
    })

    try {
      const blockedPage = await blockedContext.newPage()
      await expectTestModeLoginUnauthorized(blockedPage.request, { email: targetEmail })
      await expectDashboardRedirectsToLogin(blockedPage)
    } finally {
      await blockedContext.close()
    }
  })

  test("superadmin row disables lock/delete and API attempts return 403", async ({
    page
  }) => {
    await expectTestModeLoginSuccess(page.request, {
      email: ADMIN_EMAIL,
      name: "Admin"
    })

    await page.goto("/admin/users")
    await page.waitForURL("**/admin/users")

    const superadminRow = userRow(page, ADMIN_EMAIL)
    await expect(superadminRow).toBeVisible()
    await expect(superadminRow.getByRole("button", { name: "Lock" })).toBeDisabled()
    await expect(superadminRow.getByRole("button", { name: "Delete" })).toBeDisabled()
    await expect(
      superadminRow.getByText("Superadmin account cannot be modified")
    ).toBeVisible()

    const listResponse = await page.request.get(
      "/api/v1/admin/users?page=1&size=100&include_deleted=true"
    )
    expect(listResponse.status()).toBe(200)

    const listBody = (await listResponse.json()) as AdminUsersListResponse
    const superadminUser = listBody.items.find(
      (item) => item.email.trim().toLowerCase() === ADMIN_EMAIL.trim().toLowerCase()
    )

    expect(superadminUser).toBeDefined()
    if (!superadminUser) {
      throw new Error(`Superadmin user not found in admin list: ${ADMIN_EMAIL}`)
    }

    const lockResponse = await page.request.patch(
      `/api/v1/admin/users/${superadminUser.id}/lock`
    )
    expect(lockResponse.status()).toBe(403)
    const lockError = (await lockResponse.json()) as ErrorEnvelope
    expect(lockError.error.code).toBe("SUPERADMIN_PROTECTED")

    const deleteResponse = await page.request.delete(
      `/api/v1/admin/users/${superadminUser.id}`
    )
    expect(deleteResponse.status()).toBe(403)
    const deleteError = (await deleteResponse.json()) as ErrorEnvelope
    expect(deleteError.error.code).toBe("SUPERADMIN_PROTECTED")
  })

  test("dashboard layout uses full-window regions at 1440x900", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await expectTestModeLoginSuccess(page.request, {
      email: uniqueEmail("layout-user"),
      name: "Layout User"
    })

    await page.goto("/dashboard")
    await page.waitForURL("**/dashboard")

    const header = page.getByRole("banner")
    const nav = page.getByRole("navigation", { name: "Primary" })
    const main = page.getByRole("main")

    await expect(header).toBeVisible()
    await expect(nav).toBeVisible()
    await expect(main).toBeVisible()

    const headerBox = await header.boundingBox()
    const navBox = await nav.boundingBox()
    const mainBox = await main.boundingBox()

    expect(headerBox).not.toBeNull()
    expect(navBox).not.toBeNull()
    expect(mainBox).not.toBeNull()

    if (!headerBox || !navBox || !mainBox) {
      return
    }

    expect(headerBox.width).toBeGreaterThanOrEqual(1360)
    expect(navBox.height).toBeGreaterThanOrEqual(700)
    expect(mainBox.width).toBeGreaterThanOrEqual(700)
    expect(mainBox.x).toBeLessThan(500)
  })
})
