import type { NextConfig } from "next";

// The browser only talks to this origin; /api/* and health probes are proxied to the backend.
// Same-origin keeps the session cookie first-party and removes CORS from the picture.
// Note: for `output: "standalone"` rewrites are resolved at build time (BACKEND_URL build arg).
const backend = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/readyz", destination: `${backend}/readyz` },
    ];
  },
};

export default nextConfig;
