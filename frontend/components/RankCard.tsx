"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";

import { RankEmblem } from "@/components/RankEmblem";
import type { RankRequirement, RanksOverview } from "@/lib/api";
import { PATH_NAMES, TIER_STYLE, rankName, requirementLabel } from "@/lib/ranks";

export function RequirementBar({ r }: { r: RankRequirement }) {
  const share = r.target ? Math.min(1, r.current / r.target) : 1;
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className={r.met ? "text-emerald-700 dark:text-emerald-300" : "text-slate-600 dark:text-slate-300"}>
          {requirementLabel(r)}
        </span>
        <span className="tabular-nums text-slate-500">
          {r.key === "badge" ? (r.met ? "✓" : "–") : `${r.current.toLocaleString("cs-CZ")} / ${r.target.toLocaleString("cs-CZ")}`}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div
          className={`h-full rounded-full motion-safe:transition-[width] motion-safe:duration-700 ${r.met ? "bg-emerald-500" : "bg-brand-500"}`}
          style={{ width: `${Math.max(share * 100, r.current > 0 ? 4 : 0)}%` }}
        />
      </div>
    </li>
  );
}

/** Dashboard summary: current rank, its emblem, and what the next rank asks for. */
export function RankCard({ data }: { data: RanksOverview }) {
  const path = data.path;
  return (
    <div className="flex flex-col gap-3">
      <Link href="/ranks" className="group flex items-center gap-3 rounded-xl p-1 hover:bg-slate-50 dark:hover:bg-slate-800/60">
        <RankEmblem path={path} rank={data.rank} tier={data.tier} />
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-lg font-bold">{rankName(path, data.rank)}</span>
          <span className="text-xs text-slate-500">
            {PATH_NAMES[path]} · hodnost {data.rank} z {data.max_rank} · {TIER_STYLE[data.tier].label}
          </span>
        </span>
        <ChevronRight className="size-5 text-slate-400 group-hover:text-brand-500" aria-hidden />
      </Link>
      {data.next ? (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold text-slate-500">Další: {rankName(path, data.next.rank)}</p>
          <ul className="flex flex-col gap-2">
            {data.next.requirements.map((r) => (
              <RequirementBar key={`${r.key}:${r.target}`} r={r} />
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-slate-600 dark:text-slate-300">Nejvyšší hodnost. Dál už vede jen skutečné používání jazyka.</p>
      )}
    </div>
  );
}
