"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Notice } from "@/components/ui";
import { getWeakSpots, type Language, type WeakSpots } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

/** Unresolved mistakes from recent checks: words, grammar units and the kinds of mistake. */
export function WeakSpotsCard({ language }: { language: Language }) {
  const [data, setData] = useState<WeakSpots | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setData(null);
    setFailed(false);
    getWeakSpots(language)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language]);

  if (failed) return <Notice tone="error">{cs.common.error}</Notice>;
  if (!data) return <p className="text-sm text-slate-500">{cs.common.loading}</p>;
  const empty = !data.words.length && !data.units.length;
  return (
    <div className="flex flex-col gap-3 text-sm">
      <p className="text-slate-600 dark:text-slate-300">{cs.weak.help(data.window_days)}</p>
      {empty && <Notice tone="ok">{cs.weak.none}</Notice>}
      {data.words.length > 0 && (
        <section className="flex flex-col gap-1">
          <h3 className="font-semibold">{cs.weak.words}</h3>
          <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
            {data.words.map((w) => (
              <li key={`${w.lemma}:${w.translation}`} className="flex flex-wrap items-baseline justify-between gap-2 px-3 py-2">
                <span className="font-medium" lang={language}>
                  {language === "de" && w.gender ? `${w.gender} ` : ""}
                  {w.lemma}
                </span>
                <span className="text-slate-500" lang="cs">
                  {w.translation}
                </span>
                <span className="w-full text-xs text-slate-500">
                  {cs.weak.errors(w.errors)}
                  {w.tags.length > 0 && ` · ${w.tags.map((t) => cs.feedback.errors[t] ?? t).join(", ")}`}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {data.units.length > 0 && (
        <section className="flex flex-col gap-1">
          <h3 className="font-semibold">{cs.weak.grammar}</h3>
          <ul className="flex flex-col gap-1">
            {data.units.map((u) => (
              <li key={u.id}>
                <Link href={`/grammar/${u.id}`} className="flex justify-between gap-2 rounded-lg px-2 py-1 hover:bg-slate-100 dark:hover:bg-slate-800">
                  <span>
                    <span className="mr-1 text-xs text-slate-500">{u.level}</span>
                    {u.title}
                  </span>
                  <span className="shrink-0 text-xs text-slate-500">{cs.weak.errors(u.errors)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
      {data.tags.length > 0 && (
        <section className="flex flex-col gap-1">
          <h3 className="font-semibold">{cs.weak.kinds}</h3>
          <ul className="flex flex-wrap gap-1">
            {data.tags.map(([tag, n]) => (
              <li key={tag} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-800">
                {cs.feedback.errors[tag] ?? tag}: <strong className="tabular-nums">{n}</strong>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
