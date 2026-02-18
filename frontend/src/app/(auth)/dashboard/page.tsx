import type { ReactElement } from "react";

export default function DashboardPage(): ReactElement {
  return (
    <section className="dashboard-panel" aria-labelledby="dashboard-title">
      <h1 id="dashboard-title">Dashboard</h1>
      <p>Use the left navigation to access admin management screens.</p>
    </section>
  );
}
