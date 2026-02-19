import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import LoginPage from "./page";

afterEach(() => {
  cleanup();
});

describe("LoginPage", () => {
  it("should show inactive-account error message when oauth callback returns account_inactive", async () => {
    const page = await LoginPage({
      searchParams: Promise.resolve({
        error: "account_inactive"
      }) as Promise<{
        callbackUrl?: string | string[];
      }>
    });

    render(page);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Your account is inactive. Contact your administrator."
    );
    expect(screen.getByRole("link", { name: "Continue with Google" })).toBeInTheDocument();
  });

  it("should not show inactive-account error message by default", async () => {
    const page = await LoginPage({
      searchParams: Promise.resolve({})
    });

    render(page);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
