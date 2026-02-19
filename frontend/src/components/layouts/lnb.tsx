"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactElement } from "react";

import { useCurrentUser } from "@/hooks/queries/use-current-user";

interface NavigationItem {
  href: string;
  label: string;
  adminOnly?: boolean;
}

const navigationItems: NavigationItem[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/admin/users", label: "Users", adminOnly: true }
];

function isActivePath(pathname: string, href: string): boolean {
  if (href === "/dashboard") {
    return pathname === href;
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Lnb(): ReactElement {
  const pathname = usePathname();
  const currentUserQuery = useCurrentUser();
  const isAdmin = currentUserQuery.data?.is_admin === true;
  const visibleItems = navigationItems.filter((item) => !item.adminOnly || isAdmin);

  return (
    <nav className="dashboard-lnb" aria-label="Primary">
      <ul className="dashboard-lnb__list">
        {visibleItems.map((item) => {
          const isCurrent = isActivePath(pathname, item.href);

          return (
            <li key={item.href} className="dashboard-lnb__item">
              <Link
                href={item.href}
                className="dashboard-lnb__link"
                aria-current={isCurrent ? "page" : undefined}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
