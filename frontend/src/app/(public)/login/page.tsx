import Link from "next/link";
import type { ReactElement } from "react";

interface LoginPageProps {
  searchParams: Promise<{
    callbackUrl?: string | string[];
  }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps): Promise<ReactElement> {
  const resolvedSearchParams = await searchParams;
  const callbackUrlParam = Array.isArray(resolvedSearchParams.callbackUrl)
    ? resolvedSearchParams.callbackUrl[0]
    : resolvedSearchParams.callbackUrl;
  const googleLoginHref = callbackUrlParam
    ? `/api/auth/google/login?callbackUrl=${encodeURIComponent(callbackUrlParam)}`
    : "/api/auth/google/login";

  return (
    <main className="page-shell">
      <section className="login-content" aria-labelledby="login-title">
        <h1 id="login-title">Sign in</h1>
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
