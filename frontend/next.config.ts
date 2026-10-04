import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";

import type { NextConfig } from "next";

// The browser only talks to this origin; /api/* and health probes are proxied to the backend.
// Same-origin keeps the session cookie first-party and removes CORS from the picture.
// Note: for `output: "standalone"` rewrites are resolved at build time (BACKEND_URL build arg).
const backend = process.env.BACKEND_URL ?? "http://localhost:8000";

// Build provenance shown in the page header (components/BuildInfo.tsx). Docker builds get it from scripts/build-info.sh;
// a local `npm run dev` / `npm run build` falls back to asking git directly.
function git(args: string): string | undefined {
  try {
    return execSync(`git ${args}`, { stdio: ["ignore", "pipe", "ignore"] }).toString().trim() || undefined;
  } catch {
    return undefined;
  }
}
const known = (v: string | undefined) => (v && v !== "unknown" ? v : undefined);
const version: string = JSON.parse(readFileSync("./package.json", "utf8")).version;

const nextConfig: NextConfig = {
  output: "standalone",
  env: {
    NEXT_PUBLIC_APP_VERSION: version,
    NEXT_PUBLIC_GIT_SHA: known(process.env.POLYFLOW_GIT_SHA) ?? git("rev-parse HEAD") ?? "unknown",
    NEXT_PUBLIC_GIT_BRANCH:
      known(process.env.POLYFLOW_GIT_BRANCH) ?? git("rev-parse --abbrev-ref HEAD") ?? "unknown",
    NEXT_PUBLIC_BUILD_TIME: process.env.POLYFLOW_BUILD_TIME ?? "",
  },
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/readyz", destination: `${backend}/readyz` },
      { source: "/version", destination: `${backend}/version` },
    ];
  },
};

export default nextConfig;
