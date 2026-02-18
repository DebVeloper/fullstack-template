import type { Metadata } from "next";
import type { ReactElement } from "react";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "App",
  description: "Next.js app",
};

interface RootLayoutProps {
  readonly children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps): ReactElement {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
