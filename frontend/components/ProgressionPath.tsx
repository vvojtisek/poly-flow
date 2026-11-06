"use client";

import { CheckCircle2, Circle, Info, Target } from "lucide-react";
import { useEffect, useState } from "react";

import { getProgression, type Progression, type ProgressOverview } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const fmt = new Intl.NumberFormat("cs-CZ");

export function ProgressionPath({ progress }: { progress: ProgressOverview | null }) {
  const [data, setData] = useState<Progression | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getProgression(controller.signal)
      .then(setData)
      .catch((err: Error) => err.name !== "AbortError" && setFailed(true));
    return () => controller.abort();
  }, []);

  if (failed) return <p className="text-sm text-red-600">{cs.progression.unavailable}</p>;
  if (!data) return null;

  const required = data.milestones.filter((m) => !m.voluntary);
  const voluntary = data.milestones.filter((m) => m.voluntary);
  const nextIndex = progress ? required.findIndex((m) => progress.known < m.rank) : -1;
  const nextMilestone = nextIndex >= 0 ? required[nextIndex]! : null;
  const previousRank = nextIndex > 0 ? required[nextIndex - 1]!.rank : 0;
  const progressInBand = nextMilestone && progress
    ? Math.min(100, Math.max(0, ((progress.known - previousRank) / (nextMilestone.rank - previousRank)) * 100))
    : 100;

  return (
    <div className="space-y-3">
      <ol className="space-y-1">
        {required.map((m, i) => {
          const complete = !!progress && progress.known >= m.rank;
          const current = i === nextIndex;
          return (
          <li key={m.key} className={`flex items-center justify-between gap-2 rounded-xl px-2 py-1.5 text-sm ${current ? "bg-brand-500/10 font-semibold" : ""}`}>
            <span className="flex items-center gap-2">{complete ? <CheckCircle2 className="size-4 text-emerald-600" aria-hidden /> : current ? <Target className="size-4 text-brand-600" aria-hidden /> : <Circle className="size-4 text-slate-300" aria-hidden />}{cs.progression.milestones[m.key] ?? m.key}</span>
            <span className="flex items-baseline gap-2 text-right tabular-nums text-slate-500">
              {complete && <span className="text-xs text-emerald-700 dark:text-emerald-300">{cs.progression.completed}</span>}
              {fmt.format(m.rank)} {cs.progression.words}
            </span>
          </li>
          );
        })}
      </ol>

      {progress && nextMilestone ? (
        <section className="rounded-xl border border-brand-500/30 p-3" aria-label={cs.progression.nextTarget}>
          <div className="flex justify-between gap-2 text-sm">
            <span className="font-semibold">{cs.progression.nextTarget}: {cs.progression.milestones[nextMilestone.key] ?? nextMilestone.key}</span>
            <span className="tabular-nums">{fmt.format(progress.known)} / {fmt.format(nextMilestone.rank)}</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800" role="progressbar" aria-label={cs.progression.nextTarget} aria-valuenow={Math.round(progressInBand)} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-full rounded-full bg-brand-500 transition-[width]" style={{ width: `${progressInBand}%` }} />
          </div>
          <p className="mt-1 text-xs text-slate-500">{cs.progression.remaining(Math.max(0, nextMilestone.rank - progress.known))}</p>
        </section>
      ) : progress ? (
        <p className="rounded-xl bg-emerald-50 p-3 text-sm font-semibold text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">{cs.progression.curriculumDone}</p>
      ) : null}

      {voluntary.length > 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 p-3 dark:border-slate-700">
          {voluntary.map((m) => (
            <p key={m.key} className="flex items-baseline justify-between gap-2 text-sm text-slate-600 dark:text-slate-300">
              <span>{cs.progression.milestones[m.key] ?? m.key}</span>
              <span className="tabular-nums text-slate-500">{fmt.format(m.rank)}+</span>
            </p>
          ))}
          <p className="mt-2 flex gap-2 text-xs text-slate-600 dark:text-slate-400">
            <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
            <span>{cs.progression.beyondB2}</span>
          </p>
        </div>
      )}

      <p className="text-xs text-slate-500">{cs.progression.cefrDisclaimer}</p>
    </div>
  );
}
