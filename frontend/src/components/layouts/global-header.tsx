import Link from "next/link";
import type { ReactElement } from "react";

export function GlobalHeader(): ReactElement {
  return (
    <header className="global-header">
      <div className="global-header__brand-wrap">
        <Link href="/dashboard" className="global-header__brand">
          Atlas Console
        </Link>
        <p className="global-header__subtitle">Operations dashboard</p>
      </div>
    </header>
  );
}
