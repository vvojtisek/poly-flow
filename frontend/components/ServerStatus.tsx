"use client";

import { CircleCheck, CircleX, Loader2, ServerCrash } from "lucide-react";

import { useReadiness } from "@/hooks/useReadiness";
import { cs } from "@/lib/i18n/cs";

export function ServerStatus() {
  const state = useReadiness();

  if (state.kind === "loading") {
    return (
      <p className="flex items-center gap-2 text-sm text-slate-500">
        <Loader2 className="size-4 animate-spin" aria-hidden /> {cs.health.checking}
      </p>
    );
  }
  if (state.kind === "unreachable") {
    return (
      <p className="flex items-center gap-2 text-sm text-red-600">
        <ServerCrash className="size-4" aria-hidden /> {cs.health.unreachable}
      </p>
    );
  }

  const { status, checks } = state.data;
  return (
    <div className="space-y-2">
      <p className={status === "ready" ? "text-sm text-emerald-600" : "text-sm text-amber-600"}>
        {status === "ready" ? cs.health.ready : cs.health.unready}
      </p>
      <ul className="space-y-1">
        {Object.entries(checks).map(([name, check]) => (
          <li key={name} className="flex items-center gap-2 text-sm">
            {check.ok ? (
              <CircleCheck className="size-4 text-emerald-600" aria-hidden />
            ) : (
              <CircleX className="size-4 text-red-600" aria-hidden />
            )}
            <span>{cs.health.services[name] ?? name}</span>
            {check.error && <code className="text-xs text-slate-500">{check.error}</code>}
          </li>
        ))}
      </ul>
    </div>
  );
}
