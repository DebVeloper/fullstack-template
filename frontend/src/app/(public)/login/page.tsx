import Link from "next/link";
import type { ReactElement } from "react";

interface LoginPageProps {
  searchParams: Promise<{
    callbackUrl?: string | string[];
    error?: string | string[];
  }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps): Promise<ReactElement> {
  const resolvedSearchParams = await searchParams;
  const callbackUrlParam = Array.isArray(resolvedSearchParams.callbackUrl)
    ? resolvedSearchParams.callbackUrl[0]
    : resolvedSearchParams.callbackUrl;
  const errorParam = Array.isArray(resolvedSearchParams.error)
    ? resolvedSearchParams.error[0]
    : resolvedSearchParams.error;
  const googleLoginHref = callbackUrlParam
    ? `/api/auth/google/login?callbackUrl=${encodeURIComponent(callbackUrlParam)}`
    : "/api/auth/google/login";
  const loginErrorMessage =
    errorParam === "account_inactive"
      ? "Your account is inactive. Contact your administrator."
      : null;

  return (
    <main className="page-shell">
      <section className="login-content" aria-labelledby="login-title">
        <h1 id="login-title">Sign in</h1>
        {loginErrorMessage ? (
          <p className="status-message status-message--error" role="alert">
            {loginErrorMessage}
          </p>
        ) : null}
        <p>Continue with your Google account to access the dashboard.</p>
        <Link
          href={googleLoginHref}
          className="cta-button"
          aria-label="Continue with Google"
        >
          Continue with Google
        </Link>
      </section>
    </main>
  );
}
