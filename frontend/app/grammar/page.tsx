"use client";

import { AlertTriangle, CheckCircle2, ClipboardCheck, FlaskConical, GraduationCap, Info, Repeat, RotateCcw, Search, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Disclosure } from "@/components/Disclosure";
import { Button, Notice } from "@/components/ui";
import { getGrammarTree, getProgress, type GrammarTree, type GrammarUnitSummary, type UnitState } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs, relativeFuture } from "@/lib/i18n/cs";

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
        <p className="mt-auto flex items-center justify-between gap-2 text-xs text-slate-500">
          <span>
            {cs.grammar.exercises(u.exercises)}
            {/* When a studied topic can be checked next (checks open from the next day). */}
            {!u.due && u.next_review_at && u.status !== "new" && (
              <span className="block text-slate-500">{cs.grammar.nextCheck(relativeFuture(u.next_review_at))}</span>
            )}
          </span>
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

type Unit = GrammarUnitSummary;
type Level = (typeof CEFR_LEVELS)[number];

function LevelHeader({ level, units, active }: { level: string; units: Unit[]; active?: boolean }) {
  const complete = units.filter((unit) => unit.status === "known" || unit.status === "mastered").length;
  const dueCount = units.filter((unit) => unit.due).length;
  const percent = units.length ? Math.round((complete / units.length) * 100) : 0;
  return (
    <div className="flex w-full flex-col gap-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id={`level-${level}`} className="flex items-center gap-2 text-lg font-bold">
          {level}
          {active && (
            <span className="rounded-full bg-brand-500 px-2 py-0.5 text-xs font-semibold text-white">{cs.grammar.activeLevel}</span>
          )}
        </h2>
        <p className="text-xs tabular-nums text-slate-500">
          {units.length ? cs.grammar.levelProgress(complete, units.length, dueCount) : cs.grammar.levelNotImplemented}
        </p>
      </div>
      {units.length > 0 && (
        <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800" role="progressbar" aria-label={cs.grammar.levelProgressLabel(level)} aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
          <div className="h-full rounded-full bg-emerald-500 transition-[width]" style={{ width: `${percent}%` }} />
        </div>
      )}
    </div>
  );
}

function UnitGrid({ units, tree }: { units: Unit[]; tree: GrammarTree }) {
  return (
    <ol className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {units.map((u) => (
        <UnitCard key={u.id} u={u} recommended={u.id === tree.recommended} resumable={u.id === tree.active_lesson_unit} />
      ))}
    </ol>
  );
}

function GroupSummary({ title, count }: { title: string; count: number }) {
  return (
    <span className="flex items-center justify-between gap-2 py-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
      {title}
      <span className="rounded-full bg-slate-100 px-2 text-xs tabular-nums text-slate-600 dark:bg-slate-800 dark:text-slate-300">{count}</span>
    </span>
  );
}

// "In progress": what the learner is working on now: studied but not yet known, recommended next,
// an unfinished lesson, due for a check, or recent mistakes. Mastered topics never count.
function inProgress(u: Unit, tree: GrammarTree) {
  if (u.status === "mastered") return false;
  return u.status === "studied" || u.due || u.recent_errors > 0 || u.id === tree.recommended || u.id === tree.active_lesson_unit;
}

function normaliseLevel(value: string | null | undefined): Level | null {
  const m = value?.toUpperCase().match(/^[ABC][12]/);
  return m ? (m[0] as Level) : null;
}

export default function GrammarPage() {
  const me = useRequireMe();
  const router = useRouter();
  const language = me?.acting.active_language;
  const [tree, setTree] = useState<GrammarTree | null>(null);
  const [failed, setFailed] = useState(false);
  const [measured, setMeasured] = useState<{ level: Level; source: "test" | "badge" } | null>(null);
  // The learner's own choice of focus level, remembered per profile and language on this device.
  const [chosen, setChosen] = useState<Level | null>(null);
  const focusKey = me && language ? `polyflow:grammar-focus:${me.acting.id}:${language}` : null;
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<UnitState | null>(null);
  const [dueOnly, setDueOnly] = useState(false);

  useEffect(() => {
    if (!language) return;
    let cancelled = false;
    setTree(null);
    setFailed(false);
    setMeasured(null);
    getGrammarTree(language)
      .then((t) => !cancelled && setTree(t))
      .catch(() => !cancelled && setFailed(true));
    // The active level is a convenience for ordering; without it the page falls back to A1.
    // Evidence order: the CEFR estimate, then the highest passed vocabulary exam.
    getProgress(language)
      .then((p) => {
        if (cancelled) return;
        const test = normaliseLevel(p.cefr_level);
        const badge = p.level_badges.map((b) => normaliseLevel(b.level)).filter((l): l is Level => !!l).sort().at(-1);
        setMeasured(test ? { level: test, source: "test" } : badge ? { level: badge, source: "badge" } : null);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [language, me?.acting.id]);

  useEffect(() => {
    if (!focusKey) return;
    try {
      setChosen(normaliseLevel(window.localStorage.getItem(focusKey)));
    } catch {
      setChosen(null);
    }
  }, [focusKey]);

  function chooseFocus(level: Level | null) {
    setChosen(level);
    if (!focusKey) return;
    try {
      if (level) window.localStorage.setItem(focusKey, level);
      else window.localStorage.removeItem(focusKey);
    } catch {
      /* private mode: the choice lasts for this visit only */
    }
  }

  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const units = tree?.levels.flatMap((l) => l.units) ?? [];
  const unitsOf = (level: string) => tree?.levels.find((section) => section.level === level)?.units ?? [];
  const autoLevel: Level = measured?.level ?? "A1";
  const activeLevel: Level = chosen ?? autoLevel;
  const filtering = !!query.trim() || !!statusFilter || dueOnly;
  const foldedQuery = fold(query.trim());
  const matches = (u: Unit) =>
    (!foldedQuery || fold(`${u.title} ${u.summary}`).includes(foldedQuery)) && (!statusFilter || u.status === statusFilter) && (!dueOnly || u.due);
  const filteredLevels = CEFR_LEVELS.map((level) => ({ level, units: unitsOf(level).filter(matches) })).filter(
    (level) => level.units.length > 0 || !filtering,
  );
  const visibleCount = filteredLevels.reduce((sum, level) => sum + level.units.length, 0);

  const activeUnits = unitsOf(activeLevel);
  const current = activeUnits.filter((u) => tree && inProgress(u, tree));
  const done = activeUnits.filter((u) => !current.includes(u) && (u.status === "known" || u.status === "mastered"));
  const upcoming = activeUnits.filter((u) => !current.includes(u) && !done.includes(u));

  const filters = tree && (
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
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            type="button"
            aria-pressed={statusFilter === status}
            onClick={() => setStatusFilter(statusFilter === status ? null : status)}
            className={`rounded-full px-3 py-1.5 text-sm font-medium ${statusFilter === status ? "ring-2 ring-brand-500" : ""} ${STATUS_STYLE[status]}`}
          >
            {cs.grammar.status[status]} {units.filter((u) => u.status === status).length}
          </button>
        ))}
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
  );

  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <GraduationCap className="size-6 text-brand-500" aria-hidden /> {cs.grammar.title}
          </h1>
          <LanguagePicker me={me} />
        </div>
        {failed && <Notice tone="error">{cs.common.error}</Notice>}
        {!tree && !failed && <p className="text-slate-500">{cs.common.loading}</p>}
        {tree && !tree.open && <Notice>{cs.grammar.locked}</Notice>}
        {tree && tree.open && units.length === 0 && <Notice>{cs.grammar.empty}</Notice>}
        {tree && tree.open && units.length > 0 && (
          <>
            {(tree.due > 0 || tree.active_check_session_id) && (
              <section className="flex flex-col gap-2 rounded-2xl border border-amber-300/70 bg-amber-50 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-amber-800 dark:bg-amber-950/40">
                <p className="text-sm text-slate-700 dark:text-slate-200">{`${cs.grammar.checkDue(tree.due)}. ${cs.grammar.checkHelp}`}</p>
                <Button onClick={() => router.push("/grammar/check")}>
                  <ClipboardCheck className="size-5" aria-hidden />
                  {tree.active_check_session_id ? cs.grammar.checkResume : cs.grammar.checkStart}
                </Button>
              </section>
            )}

            {!filtering && (
              <section
                aria-labelledby={`level-${activeLevel}`}
                className="flex flex-col gap-4 rounded-3xl border-2 border-brand-500/60 bg-brand-500/5 p-4 sm:p-5"
              >
                <LevelHeader level={activeLevel} units={activeUnits} active />
                <p className="-mt-2 text-xs text-slate-500">
                  {chosen
                    ? cs.grammar.activeChosen
                    : measured?.source === "test"
                      ? cs.grammar.activeFromTest
                      : measured?.source === "badge"
                        ? cs.grammar.activeFromBadge(measured.level)
                        : cs.grammar.activeDefault}
                </p>
                <div role="radiogroup" aria-label={cs.grammar.focusLevel} className="-mt-1 flex flex-wrap items-center gap-1">
                  <button
                    type="button"
                    role="radio"
                    aria-checked={!chosen}
                    onClick={() => chooseFocus(null)}
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${!chosen ? "bg-brand-500 text-white" : "bg-white text-slate-700 ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-200 dark:ring-slate-700"}`}
                  >
                    {cs.grammar.focusAuto(autoLevel)}
                  </button>
                  {CEFR_LEVELS.filter((level) => unitsOf(level).length > 0).map((level) => (
                    <button
                      key={level}
                      type="button"
                      role="radio"
                      aria-checked={chosen === level}
                      onClick={() => chooseFocus(level)}
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold tabular-nums ${chosen === level ? "bg-brand-500 text-white" : "bg-white text-slate-700 ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-200 dark:ring-slate-700"}`}
                    >
                      {level}
                    </button>
                  ))}
                </div>
                {activeUnits.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-slate-300 p-3 text-sm text-slate-500 dark:border-slate-700">{cs.grammar.levelNotImplemented}</p>
                ) : (
                  <>
                    <div className="flex flex-col gap-2">
                      <h3 className="flex items-center gap-1.5 text-sm font-semibold text-brand-600 dark:text-brand-50">
                        <Sparkles className="size-4" aria-hidden /> {cs.grammar.inProgress}
                      </h3>
                      {current.length ? <UnitGrid units={current} tree={tree} /> : <p className="text-sm text-slate-500">{cs.grammar.nothingInProgress}</p>}
                    </div>
                    {upcoming.length > 0 && (
                      <Disclosure
                        key={`up-${activeLevel}-${current.length === 0}`}
                        defaultOpen={current.length === 0}
                        summary={<GroupSummary title={cs.grammar.upNext} count={upcoming.length} />}
                        summaryClassName="px-1"
                      >
                        <div className="pt-2"><UnitGrid units={upcoming} tree={tree} /></div>
                      </Disclosure>
                    )}
                    {done.length > 0 && (
                      <Disclosure summary={<GroupSummary title={cs.grammar.completed} count={done.length} />} summaryClassName="px-1">
                        <div className="pt-2"><UnitGrid units={done} tree={tree} /></div>
                      </Disclosure>
                    )}
                  </>
                )}
              </section>
            )}
            {filters}
            {filtering ? (
              <>
                {visibleCount === 0 ? (
                  <Notice>{cs.grammar.noTopicMatches}</Notice>
                ) : (
                  filteredLevels.map((lv) => (
                    <section key={lv.level} className="flex flex-col gap-2" aria-labelledby={`level-${lv.level}`}>
                      <div className="rounded-2xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
                        <LevelHeader level={lv.level} units={unitsOf(lv.level)} active={lv.level === activeLevel} />
                      </div>
                      <UnitGrid units={lv.units} tree={tree} />
                    </section>
                  ))
                )}
              </>
            ) : (
              <section className="flex flex-col gap-2" aria-labelledby="grammar-other-levels">
                <h2 id="grammar-other-levels" className="text-sm font-semibold text-slate-600 dark:text-slate-300">{cs.grammar.otherLevels}</h2>
                {CEFR_LEVELS.filter((level) => level !== activeLevel).map((level) => {
                  const list = unitsOf(level);
                  return (
                    <Disclosure
                      key={level}
                      className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
                      summaryClassName="p-3"
                      summary={<LevelHeader level={level} units={list} />}
                    >
                      <div className="px-3 pb-3">
                        {list.length ? <UnitGrid units={list} tree={tree} /> : <p className="text-sm text-slate-500">{cs.grammar.levelNotImplemented}</p>}
                      </div>
                    </Disclosure>
                  );
                })}
              </section>
            )}

            {me.acting.active_language !== "en" && (
              <section className="grid gap-3 sm:grid-cols-2" aria-label={cs.grammar.tools}>
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
              </section>
            )}
          </>
        )}

        {tree && (
          <footer className="flex flex-col gap-2 border-t border-slate-200 pt-4 text-sm text-slate-600 dark:border-slate-800 dark:text-slate-300" aria-label={cs.grammar.aboutTitle}>
            <h2 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Info className="size-4" aria-hidden /> {cs.grammar.aboutTitle}
            </h2>
            <p className="max-w-2xl">{cs.grammar.intro}</p>
            {tree.open && !tree.due && !tree.active_check_session_id && <p className="max-w-2xl">{cs.grammar.checkNothing}</p>}
            {tree.review_status !== "reviewed" && <Notice>{cs.grammar.unreviewed}</Notice>}
          </footer>
        )}
      </div>
    </AppShell>
  );
}
