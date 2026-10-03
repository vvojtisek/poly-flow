import type { MetadataRoute } from "next";

import { cs } from "@/lib/i18n/cs";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: cs.appName,
    short_name: cs.appName,
    description: cs.tagline,
    lang: "cs-CZ",
    start_url: "/",
    scope: "/",
    display: "standalone",
    display_override: ["fullscreen", "standalone"],
    orientation: "any",
    background_color: "#f8fafc",
    theme_color: "#3b6fd4",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
