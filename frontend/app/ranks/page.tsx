"use client";

import { CheckCircle2, Lock } from "lucide-react";
import { useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { RankCelebration } from "@/components/RankCelebration";
import { RankEmblem } from "@/components/RankEmblem";
import { RequirementBar } from "@/components/RankCard";
import { Notice } from "@/components/ui";
import { markRanksSeen, updateOwnProfile, type RankPath } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { ACHIEVEMENT_COPY, PATH_NAMES, TIER_STYLE, rankName } from "@/lib/ranks";
import { invalidateRanks, useRanks } from "@/lib/useRanks";

const PATHS: RankPath[] = ["hockey", "royal", "off"];
const GROUPS: [string, string][] = [
  ["words", "Slova"],
  ["grammar", "Gramatika"],
  ["recovery", "Učení z chyb"],
  ["exams", "Zkoušky"],
  ["practice", "Praxe"],
];
const date = (iso: string) => new Date(iso).toLocaleDateString("cs-CZ");

export default function RanksPage() {
  const me = useRequireMe();
  const { refresh } = useAuth();
  const language = me?.acting.active_language;
  const { data, reload } = useRanks(language, me?.acting.id);
  const [saving, setSaving] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  if (!me) return <FullPageStatus text={cs.common.loading} />;

  async function choose(path: RankPath) {
    setSaving(true);
    try {
      await updateOwnProfile({ settings: { rank_path: path } });
      invalidateRanks();
      await Promise.all([reload(), refresh()]);
    } finally {
      setSaving(false);
    }
  }

  const celebrate = data && !dismissed && data.path !== "off" && ((data.unseen_rank ?? 0) > 1 || data.unseen_achievements.length > 0);
  const path = data?.path ?? "hockey";
  return (
    <AppShell me={me}>
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-xl font-bold">Moje cesta</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Hodnosti a odznaky jsou jen tvoje: žádné žebříčky, žádné srovnávání, žádné body ani série dnů. Každý postup stojí na
            tom, co jsi prokázal(a) v ověření, a co jednou získáš, už neztratíš.
          </p>
          <LanguagePicker me={me} />
        </div>

        <div role="radiogroup" aria-label="Téma cesty" className="grid grid-cols-3 gap-2">
          {PATHS.map((p) => (
            <button
              key={p}
              type="button"
              role="radio"
              aria-checked={path === p}
              disabled={saving}
              onClick={() => void choose(p)}
              className={`rounded-xl px-3 py-2 text-sm font-medium ${
                path === p ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
              }`}
            >
              {PATH_NAMES[p]}
            </button>
          ))}
        </div>

        {!data ? (
          <p className="text-sm text-slate-500">{cs.common.loading}</p>
        ) : data.path === "off" ? (
          <Notice>Hodnosti jsou skryté. Pokrok dál uvidíš na přehledu; téma můžeš kdykoli zapnout.</Notice>
        ) : (
          <>
            <section className="flex flex-col items-center gap-3 rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:text-left">
              <RankEmblem path={path} rank={data.rank} tier={data.tier} size="lg" />
              <div className="flex flex-1 flex-col gap-1">
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  {PATH_NAMES[path]} · {cs.languages[data.language]}
                </p>
                <p className="text-3xl font-black">{rankName(path, data.rank)}</p>
                <p className="text-sm text-slate-500">
                  Hodnost {data.rank} z {data.max_rank} · rám {TIER_STYLE[data.tier].label}
                </p>
                {data.next && (
                  <div className="mt-3 flex flex-col gap-2 text-left">
                    <p className="text-xs font-semibold text-slate-500">Na hodnost {rankName(path, data.next.rank)} chybí:</p>
                    <ul className="flex flex-col gap-2">
                      {data.next.requirements.map((r) => (
                        <RequirementBar key={`${r.key}:${r.target}`} r={r} />
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>

            <section className="flex flex-col gap-2">
              <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300">Celá cesta</h2>
              <ol className="relative flex flex-col gap-2 border-l-2 border-slate-200 pl-4 dark:border-slate-800">
                {[...data.ranks].reverse().map((r) => {
                  const reached = r.reached_at !== null || r.rank <= data.rank;
                  const current = r.rank === data.rank;
                  return (
                    <li
                      key={r.rank}
                      className={`flex items-center gap-3 rounded-2xl p-2 ${
                        current ? "bg-brand-500/10 ring-2 ring-brand-500/40" : ""
                      }`}
                    >
                      <RankEmblem path={path} rank={r.rank} tier={r.tier} size="md" locked={!reached} />
                      <div className="flex min-w-0 flex-1 flex-col">
                        <span className={`font-semibold ${reached ? "" : "text-slate-500"}`}>{rankName(path, r.rank)}</span>
                        {reached ? (
                          <span className="flex items-center gap-1 text-xs text-emerald-700 dark:text-emerald-300">
                            <CheckCircle2 className="size-3.5" aria-hidden />
                            {r.reached_at ? `získáno ${date(r.reached_at)}` : "získáno"}
                          </span>
                        ) : (
                          <span className="flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
                            <Lock className="size-3.5" aria-hidden />
                            {r.requirements
                              .map((q) =>
                                q.key === "badge"
                                  ? `zkouška ${q.level}`
                                  : q.key === "known_words"
                                    ? `${q.target} slov`
                                    : q.key === "grammar_known"
                                      ? `${q.target} témat gramatiky`
                                      : `${q.target} opravených chyb`,
                              )
                              .join(" · ")}
                          </span>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ol>
            </section>

            <section className="flex flex-col gap-3">
              <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300">Odznaky</h2>
              {GROUPS.map(([group, label]) => (
                <div key={group} className="flex flex-col gap-1">
                  <p className="text-xs text-slate-500">{label}</p>
                  <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {data.achievements
                      .filter((a) => a.group === group)
                      .map((a) => (
                        <li
                          key={a.key}
                          className={`rounded-xl border p-3 text-sm ${
                            a.reached_at
                              ? "border-brand-500/40 bg-brand-500/5"
                              : "border-dashed border-slate-300 text-slate-500 dark:border-slate-700"
                          }`}
                        >
                          <p className="font-semibold">{ACHIEVEMENT_COPY[a.key]?.title ?? a.key}</p>
                          <p className="text-xs">{ACHIEVEMENT_COPY[a.key]?.text}</p>
                          {a.reached_at && <p className="mt-1 text-[0.7rem] text-slate-500">{date(a.reached_at)}</p>}
                        </li>
                      ))}
                  </ul>
                </div>
              ))}
            </section>
          </>
        )}
      </div>
      {celebrate && data && (
        <RankCelebration
          data={data}
          onClose={() => {
            setDismissed(true);
            void markRanksSeen(data.language).then(() => {
              invalidateRanks();
              void reload();
            });
          }}
        />
      )}
    </AppShell>
  );
}
