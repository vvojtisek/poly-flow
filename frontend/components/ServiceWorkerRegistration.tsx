"use client";

import { useEffect } from "react";

/** Production-only; the dev server owns its own update and asset behavior. */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    void navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => {
      // The app remains online-only if service-worker registration is unavailable.
    });
  }, []);
  return null;
}
