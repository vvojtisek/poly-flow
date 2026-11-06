"use client";

import { Sparkles } from "lucide-react";
import { useEffect, useRef } from "react";

import { RankEmblem } from "@/components/RankEmblem";
import { Button } from "@/components/ui";
import type { RanksOverview } from "@/lib/api";
import { ACHIEVEMENT_COPY, PATH_NAMES, rankName } from "@/lib/ranks";

const BURST = Array.from({ length: 14 }, (_, i) => i);

/** One-time celebration of a new rank or achievement; nothing is asked of the learner. */
export function RankCelebration({ data, onClose }: { data: RanksOverview; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (d && !d.open) d.showModal();
  }, []);
  const promoted = data.unseen_rank !== null && data.unseen_rank > 1 ? data.unseen_rank : null;
  const tier = (promoted ? data.ranks[promoted - 1]?.tier : undefined) ?? data.tier;
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-labelledby="rank-celebration-title"
      className="m-auto w-[min(92vw,26rem)] overflow-visible rounded-3xl border border-slate-200 bg-white p-0 text-slate-900 shadow-2xl backdrop:bg-slate-950/50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
    >
      <div className="relative flex flex-col items-center gap-3 p-6 text-center">
        {promoted && (
          <div className="pointer-events-none absolute inset-x-0 top-10 flex justify-center" aria-hidden>
            {BURST.map((i) => (
              <span
                key={i}
                className="absolute size-2 rounded-full bg-brand-500 opacity-0 motion-safe:animate-burst"
                style={{
                  ["--burst-x" as string]: `${Math.cos((i / BURST.length) * 2 * Math.PI) * 110}px`,
                  ["--burst-y" as string]: `${Math.sin((i / BURST.length) * 2 * Math.PI) * 80 + 40}px`,
                  backgroundColor: ["#f59e0b", "#3b82f6", "#10b981", "#ec4899"][i % 4],
                  animationDelay: `${(i % 4) * 40}ms`,
                }}
              />
            ))}
          </div>
        )}
        <p className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-50">
          <Sparkles className="size-4" aria-hidden />
          {promoted ? "Postup na novou hodnost" : "Nový odznak"}
        </p>
        {promoted && (
          <>
            <RankEmblem path={data.path} rank={promoted} tier={tier} size="lg" className="motion-safe:animate-pop-in" />
            <h2 id="rank-celebration-title" className="text-2xl font-black">
              {rankName(data.path, promoted)}
            </h2>
            <p className="text-sm text-slate-500">
              {PATH_NAMES[data.path]} · hodnost {promoted} z {data.max_rank}
            </p>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Za tím jsou slova a pravidla, která jsi prokázal(a) v ověření. Hodnost ti zůstane, i když si dáš pauzu.
            </p>
          </>
        )}
        {!!data.unseen_achievements.length && (
          <ul className="flex w-full flex-col gap-1 text-left" id={promoted ? undefined : "rank-celebration-title"}>
            {data.unseen_achievements.map((k) => (
              <li key={k} className="rounded-xl bg-brand-500/10 px-3 py-2 text-sm motion-safe:animate-pop-in">
                <span className="font-semibold">{ACHIEVEMENT_COPY[k]?.title ?? k}</span>
                <span className="block text-xs text-slate-600 dark:text-slate-300">{ACHIEVEMENT_COPY[k]?.text}</span>
              </li>
            ))}
          </ul>
        )}
        <Button className="mt-2 w-full" autoFocus onClick={() => ref.current?.close()}>
          Pokračovat
        </Button>
      </div>
    </dialog>
  );
}
