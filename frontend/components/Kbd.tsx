import type { ReactNode } from "react";

import { cs } from "@/lib/i18n/cs";

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-slate-300 bg-slate-50 px-1 font-mono text-[0.7rem] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
      {children}
    </kbd>
  );
}

/** Small key badge for a control, shown on wide (desktop) screens only. */
export function KeyHint({ k }: { k: string }) {
  return (
    <span className="hidden lg:inline" aria-hidden>
      <Kbd>{k}</Kbd>
    </span>
  );
}

/** Legend of the keyboard shortcuts on a practice screen (desktop only). */
export function ShortcutLegend({ items }: { items: [string, string][] }) {
  if (!items.length) return null;
  return (
    <p className="hidden flex-wrap justify-center gap-x-3 gap-y-1 text-xs text-slate-500 lg:flex" aria-label={cs.keys.legend}>
      {items.map(([k, label]) => (
        <span key={k}>
          <Kbd>{k}</Kbd> {label}
        </span>
      ))}
    </p>
  );
}
