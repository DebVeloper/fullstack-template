import type { ReactElement, ReactNode } from "react";

import { DashboardShell } from "@/components/layouts/dashboard-shell";
import { QueryProvider } from "@/components/layouts/query-provider";

interface AuthLayoutProps {
  readonly children: ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps): ReactElement {
  return (
    <QueryProvider>
      <DashboardShell>{children}</DashboardShell>
    </QueryProvider>
  );
}
