import type { ReactElement, ReactNode } from "react";

import { GlobalHeader } from "./global-header";
import { Lnb } from "./lnb";

interface DashboardShellProps {
  readonly children: ReactNode;
}

export function DashboardShell({ children }: DashboardShellProps): ReactElement {
  return (
    <div className="dashboard-shell">
      <a href="#dashboard-main" className="skip-link">
        Skip to main content
      </a>
      <GlobalHeader />
      <div className="dashboard-shell__body">
        <Lnb />
        <main id="dashboard-main" className="dashboard-main" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
