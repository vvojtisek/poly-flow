"use client";

import { Lock, LockOpen } from "lucide-react";

import type { ProgressOverview } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const fmt = new Intl.NumberFormat("cs-CZ");

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
      <p className="text-2xl font-bold tabular-nums">{fmt.format(value)}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}

export function ProgressCard({ progress }: { progress: ProgressOverview }) {
  const p = progress;
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Stat label={cs.progress.known} value={p.known} />
        <Stat label={cs.progress.passive} value={p.passive_known} />
        <Stat label={cs.progress.active} value={p.active_known} />
        <Stat label={cs.progress.seen} value={p.seen} />
        <Stat label={cs.progress.due} value={p.due_now} />
        <Stat label={cs.progress.mastered} value={p.by_state.MASTERED} />
      </div>

      {p.by_band.length > 0 && (
        <ul className="flex flex-col gap-2">
          {p.by_band.map((b) => {
            const pct = b.items ? Math.round((b.known / b.items) * 100) : 0;
            return (
              <li key={b.band} className="text-sm">
                <div className="flex justify-between text-xs text-slate-500">
                  <span>≤ {fmt.format(b.band)}</span>
                  <span className="tabular-nums">
                    {fmt.format(b.known)} / {fmt.format(b.items)}
                  </span>
                </div>
                <div
                  className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
                  role="progressbar"
                  aria-valuenow={pct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div className="h-full bg-brand-500" style={{ width: `${pct}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <div className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-300">
        {p.next_milestone && <p>{cs.progress.nextMilestone(p.next_milestone)}</p>}
        <p className="flex items-center gap-2">
          {p.grammar_unlocked ? (
            <LockOpen className="size-4 text-emerald-600" aria-hidden />
          ) : (
            <Lock className="size-4" aria-hidden />
          )}
          {p.grammar_unlocked ? cs.progress.grammarUnlocked : cs.progress.grammarLocked(p.grammar_gate)}
        </p>
        <p className="text-xs text-slate-500">{cs.progress.available(p.lexicon_items)}</p>
        <p className="text-xs text-slate-500">{cs.progress.pronunciation}</p>
      </div>
    </div>
  );
}
