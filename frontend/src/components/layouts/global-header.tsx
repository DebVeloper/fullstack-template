"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactElement } from "react";
import { useMemo, useState } from "react";

import { useCurrentUser } from "@/hooks/queries/use-current-user";

function getAvatarLabel(name: string | undefined, email: string | undefined): string {
  const preferredLabel = (name ?? "").trim() || (email ?? "").trim();

  if (!preferredLabel) {
    return "?";
  }

  return preferredLabel[0]?.toUpperCase() ?? "?";
}

export function GlobalHeader(): ReactElement {
  const router = useRouter();
  const currentUserQuery = useCurrentUser();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const profile = useMemo(() => {
    const name = currentUserQuery.data?.name;
    const email = currentUserQuery.data?.email;

    return {
      name: name?.trim() || "Unknown user",
      email: email?.trim() || "No email",
      avatarLabel: getAvatarLabel(name, email)
    };
  }, [currentUserQuery.data?.email, currentUserQuery.data?.name]);

  async function handleLogout(): Promise<void> {
    if (isLoggingOut) {
      return;
    }

    setIsLoggingOut(true);
    try {
      await fetch("/api/auth/logout", {
        method: "POST"
      });
    } finally {
      router.push("/login");
      router.refresh();
    }
  }

  return (
    <header className="global-header">
      <div className="global-header__brand-wrap">
        <Link href="/dashboard" className="global-header__brand">
          Atlas Console
        </Link>
        <p className="global-header__subtitle">Operations dashboard</p>
      </div>
      <div className="global-header__actions">
        <div className="global-header__profile">
          <span className="global-header__avatar" aria-hidden="true">
            {profile.avatarLabel}
          </span>
          <div className="global-header__identity">
            <p className="global-header__name">{profile.name}</p>
            <p className="global-header__email">{profile.email}</p>
          </div>
        </div>
        <button
          type="button"
          className="global-header__logout"
          onClick={() => void handleLogout()}
          disabled={isLoggingOut}
        >
          {isLoggingOut ? "Logging out..." : "Logout"}
        </button>
      </div>
    </header>
  );
}
