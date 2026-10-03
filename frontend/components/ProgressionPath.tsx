"use client";

import { Info } from "lucide-react";
import { useEffect, useState } from "react";

import { getProgression, type Progression } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const fmt = new Intl.NumberFormat("cs-CZ");

export function ProgressionPath() {
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

  return (
    <div className="space-y-3">
      <ol className="space-y-1">
        {required.map((m) => (
          <li key={m.key} className="flex items-baseline justify-between gap-2 text-sm">
            <span>{cs.progression.milestones[m.key] ?? m.key}</span>
            <span className="tabular-nums text-slate-500">
              {fmt.format(m.rank)} {cs.progression.words}
            </span>
          </li>
        ))}
      </ol>

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
