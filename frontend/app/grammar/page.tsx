"use client";

import { AlertTriangle, CheckCircle2, ClipboardCheck, FlaskConical, GraduationCap, Repeat, RotateCcw, Search, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Button, Notice } from "@/components/ui";
import { getGrammarTree, type GrammarTree, type GrammarUnitSummary, type UnitState } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const STATUS_STYLE: Record<string, string> = {
  new: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  studied: "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-100",
  known: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100",
  mastered: "bg-emerald-600 text-white",
};

const STATUS_FILTERS: UnitState[] = ["new", "studied", "known", "mastered"];
const CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"] as const;
const fold = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("cs-CZ");

function UnitCard({ u, recommended, resumable }: { u: GrammarUnitSummary; recommended: boolean; resumable: boolean }) {
  return (
    <li>
      <Link
        href={`/grammar/${u.id}`}
        className={`flex h-full flex-col gap-2 rounded-2xl border p-4 outline-none transition hover:border-brand-500 focus-visible:ring-2 focus-visible:ring-brand-500 ${
          recommended
            ? "border-brand-500 bg-brand-500/5"
            : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
        }`}
      >
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className={`rounded-full px-2 py-0.5 font-semibold ${STATUS_STYLE[u.status]}`}>
            {u.status === "mastered" && <CheckCircle2 className="mr-1 inline size-3" aria-hidden />}
            {cs.grammar.status[u.status]}
          </span>
          {recommended && (
            <span className="inline-flex items-center gap-1 font-semibold text-brand-600">
              <Sparkles className="size-3" aria-hidden /> {cs.grammar.recommended}
            </span>
          )}
          {u.due && (
            <span className="inline-flex items-center gap-1 font-semibold text-amber-700 dark:text-amber-300">
              <ClipboardCheck className="size-3" aria-hidden /> {cs.grammar.due}
            </span>
          )}
          {u.recent_errors > 0 && (
            <span className="inline-flex items-center gap-1 text-red-700 dark:text-red-300">
              <AlertTriangle className="size-3" aria-hidden /> {cs.grammar.recentErrors(u.recent_errors)}
            </span>
          )}
        </div>
        <p className="font-semibold">{u.title}</p>
        <p className="text-sm text-slate-600 dark:text-slate-300">{u.summary}</p>
        <p className="mt-auto flex items-center justify-between text-xs text-slate-500">
          <span>{cs.grammar.exercises(u.exercises)}</span>
          <span className="font-semibold text-brand-600">
            {resumable ? (
              <>
                <RotateCcw className="mr-1 inline size-3" aria-hidden />
                {cs.grammar.resume}
              </>
            ) : (
              cs.grammar.open
            )}
          </span>
        </p>
      </Link>
    </li>
  );
}

export default function GrammarPage() {
  const me = useRequireMe();
  const router = useRouter();
  const language = me?.acting.active_language;
  const [tree, setTree] = useState<GrammarTree | null>(null);
  const [failed, setFailed] = useState(false);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<UnitState | null>(null);
  const [dueOnly, setDueOnly] = useState(false);

  useEffect(() => {
    if (!language) return;
    let cancelled = false;
    setTree(null);
    setFailed(false);
    getGrammarTree(language)
      .then((t) => !cancelled && setTree(t))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language, me?.acting.id]);

  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const units = tree?.levels.flatMap((l) => l.units) ?? [];
  const foldedQuery = fold(query.trim());
  const filteredLevels = tree
    ? CEFR_LEVELS.map((level) => ({
      level,
      units: (tree.levels.find((section) => section.level === level)?.units ?? []).filter((u) => {
        const matchesQuery = !foldedQuery || fold(`${u.title} ${u.summary}`).includes(foldedQuery);
        return matchesQuery && (!statusFilter || u.status === statusFilter) && (!dueOnly || u.due);
      }),
    }))
    .filter((level) => level.units.length > 0 || (!query.trim() && !statusFilter && !dueOnly))
    : [];
  const visibleCount = filteredLevels.reduce((sum, level) => sum + level.units.length, 0);
  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h1 className="flex items-center gap-2 text-2xl font-bold">
              <GraduationCap className="size-6 text-brand-500" aria-hidden /> {cs.grammar.title}
            </h1>
            <p className="max-w-2xl text-sm text-slate-600 dark:text-slate-300">{cs.grammar.intro}</p>
          </div>
          <LanguagePicker me={me} />
        </div>
        {failed && <Notice tone="error">{cs.common.error}</Notice>}
        {!tree && !failed && <p className="text-slate-500">{cs.common.loading}</p>}
        {tree && !tree.open && <Notice>{cs.grammar.locked}</Notice>}
        {tree && tree.open && units.length === 0 && <Notice>{cs.grammar.empty}</Notice>}
        {tree && tree.open && (
          <>
            <section className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900">
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {tree.due || tree.active_check_session_id ? `${cs.grammar.checkDue(tree.due)}. ${cs.grammar.checkHelp}` : cs.grammar.checkNothing}
              </p>
              <Button
                variant="secondary"
                disabled={!tree.due && !tree.active_check_session_id}
                onClick={() => router.push("/grammar/check")}
              >
                <ClipboardCheck className="size-5" aria-hidden />
                {tree.active_check_session_id ? cs.grammar.checkResume : cs.grammar.checkStart}
              </Button>
            </section>
            {tree.review_status !== "reviewed" && <Notice>{cs.grammar.unreviewed}</Notice>}
            {me.acting.active_language === "de" && (
              <Link
                href="/grammar/cases"
                className="flex items-center gap-3 rounded-2xl border border-amber-300/60 bg-amber-50 p-4 hover:border-amber-400 dark:border-amber-800 dark:bg-amber-950/40"
              >
                <FlaskConical className="size-6 shrink-0 text-amber-600" aria-hidden />
                <span className="flex flex-col">
                  <span className="font-semibold">{cs.cases.title}</span>
                  <span className="text-sm text-slate-600 dark:text-slate-300">{cs.cases.teaser}</span>
                </span>
              </Link>
            )}
            {me.acting.active_language !== "en" && (
              <Link
                href="/grammar/verbs"
                className="flex items-center gap-3 rounded-2xl border border-brand-500/30 bg-brand-500/5 p-4 hover:border-brand-500"
              >
                <Repeat className="size-6 shrink-0 text-brand-500" aria-hidden />
                <span className="flex flex-col">
                  <span className="font-semibold">{cs.verbs.title}</span>
                  <span className="text-sm text-slate-600 dark:text-slate-300">{cs.verbs.teaser}</span>
                </span>
              </Link>
            )}
            <section className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900" aria-label={cs.grammar.findTopics}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <label className="flex min-w-56 flex-1 items-center gap-2 rounded-xl border border-slate-300 px-3 focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-500/30 dark:border-slate-700">
                  <Search className="size-4 shrink-0 text-slate-400" aria-hidden />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder={cs.grammar.searchTopics}
                    aria-label={cs.grammar.searchTopics}
                    className="min-w-0 flex-1 bg-transparent py-2.5 text-sm outline-none"
                  />
                  {query && (
                    <button type="button" onClick={() => setQuery("")} aria-label={cs.grammar.clearSearch} className="rounded-full p-1 hover:bg-slate-100 dark:hover:bg-slate-800">
                      <X className="size-4" aria-hidden />
                    </button>
                  )}
                </label>
                <span aria-live="polite" className="text-xs tabular-nums text-slate-500">
                  {cs.grammar.visibleTopics(visibleCount, units.length)}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  aria-pressed={!statusFilter}
                  onClick={() => setStatusFilter(null)}
                  className={`rounded-full px-3 py-1.5 text-sm font-medium ${!statusFilter ? "bg-brand-500 text-white" : "bg-slate-100 dark:bg-slate-800"}`}
                >
                  {cs.grammar.allTopics} {units.length}
                </button>
                {STATUS_FILTERS.map((status) => {
                  const count = units.filter((u) => u.status === status).length;
                  return (
                    <button
                      key={status}
                      type="button"
                      aria-pressed={statusFilter === status}
                      onClick={() => setStatusFilter(statusFilter === status ? null : status)}
                      className={`rounded-full px-3 py-1.5 text-sm font-medium ${statusFilter === status ? "ring-2 ring-brand-500" : ""} ${STATUS_STYLE[status]}`}
                    >
                      {cs.grammar.status[status]} {count}
                    </button>
                  );
                })}
                <button
                  type="button"
                  aria-pressed={dueOnly}
                  onClick={() => setDueOnly((value) => !value)}
                  className={`rounded-full px-3 py-1.5 text-sm font-medium ${dueOnly ? "bg-amber-500 text-white" : "bg-slate-100 dark:bg-slate-800"}`}
                >
                  {cs.grammar.due} {tree.due}
                </button>
              </div>
            </section>
            {visibleCount === 0 && units.length > 0 && (query.trim() || statusFilter || dueOnly) ? (
              <Notice>{cs.grammar.noTopicMatches}</Notice>
            ) : filteredLevels.map((lv) => (
              <section key={lv.level} className="flex flex-col gap-2" aria-labelledby={`level-${lv.level}`}>
                {(() => {
                  const complete = lv.units.filter((unit) => unit.status === "known" || unit.status === "mastered").length;
                  const dueCount = lv.units.filter((unit) => unit.due).length;
                  const percent = lv.units.length ? Math.round((complete / lv.units.length) * 100) : 0;
                  return (
                    <div className="rounded-2xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <h2 id={`level-${lv.level}`} className="text-lg font-bold">{lv.level}</h2>
                        <p className="text-xs tabular-nums text-slate-500">{cs.grammar.levelProgress(complete, lv.units.length, dueCount)}</p>
                      </div>
                      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800" role="progressbar" aria-label={cs.grammar.levelProgressLabel(lv.level)} aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
                        <div className="h-full rounded-full bg-emerald-500 transition-[width]" style={{ width: `${percent}%` }} />
                      </div>
                    </div>
                  );
                })()}
                {lv.units.length === 0 ? <p className="rounded-xl border border-dashed border-slate-300 p-3 text-sm text-slate-500 dark:border-slate-700">{cs.grammar.levelNotImplemented}</p> : <ol className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {lv.units.map((u) => (
                    <UnitCard
                      key={u.id}
                      u={u}
                      recommended={u.id === tree.recommended}
                      resumable={u.id === tree.active_lesson_unit}
                    />
                  ))}
                </ol>}
              </section>
            ))}
          </>
        )}
      </div>
    </AppShell>
  );
}
