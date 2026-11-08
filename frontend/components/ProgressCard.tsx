"use client";

import { GraduationCap } from "lucide-react";

import type { GrammarTree, ProgressOverview } from "@/lib/api";
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

export function ProgressCard({ progress, grammar }: { progress: ProgressOverview; grammar?: GrammarTree | null }) {
  const p = progress;
  // Grammar is open from A1 (decision 2026-11-06); show proven topics instead of the old word gate.
  const units = grammar?.levels.flatMap((l) => l.units) ?? [];
  const provenUnits = units.filter((u) => u.status === "known" || u.status === "mastered").length;
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

      <div className="flex flex-col gap-1 text-sm text-slate-600 dark:text-slate-300">
        {grammar && (
          <p className="flex items-center gap-2">
            <GraduationCap className="size-4 text-brand-600" aria-hidden />
            {units.length ? cs.progress.grammarTopics(provenUnits, units.length) : cs.progress.grammarNone}
          </p>
        )}
        <p className="text-xs text-slate-500">{cs.progress.available(p.lexicon_items)}</p>
        <p className="text-xs text-slate-500">{cs.progress.pronunciation}</p>
      </div>
    </div>
  );
}
