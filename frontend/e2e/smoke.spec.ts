import { expect, test } from "@playwright/test";

test("shows continue with Google action on login", async ({ page }) => {
  await page.goto("/login");

  await expect(
    page.getByRole("link", { name: "Continue with Google" })
  ).toBeVisible();
});
