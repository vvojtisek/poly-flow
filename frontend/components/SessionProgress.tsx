import type { ReactNode } from "react";

import { cs } from "@/lib/i18n/cs";

/**
 * Progress through a fixed-length test or practice session: a counter, the number still to go and a
 * bar. `done` is the count already answered (the bar), `current` the 1-based item on screen. The row
 * has a fixed height and the bar only animates its width, so stepping never shifts the layout.
 * `upperBound` marks an adaptive test whose `total` is a maximum that may end early.
 */
export function SessionProgress({
  current,
  total,
  done = current - 1,
  label,
  upperBound = false,
  children,
}: {
  current: number;
  total: number;
  done?: number;
  label?: string;
  upperBound?: boolean;
  children?: ReactNode;
}) {
  const safeTotal = Math.max(total, 1);
  const shown = Math.min(Math.max(current, 1), safeTotal);
  const percent = Math.round((Math.min(Math.max(done, 0), safeTotal) / safeTotal) * 100);
  const remaining = Math.max(safeTotal - shown, 0);
  const t = cs.sessionProgress;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex min-h-6 flex-wrap items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
        <span className="font-semibold tabular-nums text-slate-700 dark:text-slate-200">
          {label ?? t.question(shown, safeTotal)}
        </span>
        {children}
        <span className="tabular-nums">{upperBound ? t.remainingAtMost(remaining) : t.remaining(remaining)}</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
        role="progressbar"
        aria-label={t.label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={t.valueText(shown, safeTotal, percent)}
      >
        <div
          className="h-full rounded-full bg-brand-500 transition-[width] duration-500 ease-out motion-reduce:transition-none"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
