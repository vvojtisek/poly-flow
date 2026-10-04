import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { BuildFooter } from "@/components/BuildFooter";
import { AuthProvider } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

import "./globals.css";

export const metadata: Metadata = {
  title: cs.appName,
  description: cs.tagline,
  applicationName: cs.appName,
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: cs.appName },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8fafc" },
    { media: "(prefers-color-scheme: dark)", color: "#020617" },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="cs">
      <body>
        <AuthProvider>{children}</AuthProvider>
        <BuildFooter />
      </body>
    </html>
  );
}
