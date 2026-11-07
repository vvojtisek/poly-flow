"use client";

import { BarChart3, CalendarDays, ChevronRight, Filter, Target, TrendingUp, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Panel } from "@/components/Panel";
import { WeeklyRecap } from "@/components/WeeklyRecap";
import { RetryNotice, Skeleton } from "@/components/ui";
import { PlayButton } from "@/components/PlayButton";
import { getActivityDay, getInsights, myWordAudioUrl, type ActivityDay, type Insights } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const t = cs.insights;
const STEP_ROOT = "/words?tab=all";
const dayFmt = (iso: string) => new Date(iso + "T12:00:00").toLocaleDateString("cs-CZ", { day: "numeric", month: "numeric" });

function level(n: number, max: number): string {
  if (n === 0) return "bg-slate-100 dark:bg-slate-800";
  const r = n / Math.max(max, 1);
  if (r > 0.75) return "bg-brand-600";
  if (r > 0.5) return "bg-brand-500";
  if (r > 0.25) return "bg-brand-500/60";
  return "bg-brand-500/30";
}

/** Activity calendar: 26 weeks, Monday on top. A calendar, not a streak counter. */
type HeatMode = "all" | "graded" | "practice";
const amount = (d: Insights["heatmap"][number], mode: HeatMode) => (mode === "all" ? d.graded + d.practice : d[mode]);

function Heatmap({ data, selected, onSelect, mode }: { data: Insights["heatmap"]; selected: string | null; onSelect: (date: string) => void; mode: HeatMode }) {
  const max = Math.max(...data.map((d) => amount(d, mode)));
  const focusDate = selected && data.some((d) => d.date === selected) ? selected : data[data.length - 1]!.date;
  // ←/→ move a week, ↑/↓ a day, Home/End to the first/last day; the moved-to day is selected.
  function onGridKey(e: React.KeyboardEvent<HTMLDivElement>) {
    const delta = { ArrowLeft: -7, ArrowRight: 7, ArrowUp: -1, ArrowDown: 1 }[e.key];
    const index = data.findIndex((d) => d.date === focusDate);
    let next = index;
    if (delta !== undefined) next = Math.max(0, Math.min(data.length - 1, index + delta));
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = data.length - 1;
    else return;
    e.preventDefault();
    const date = data[next]!.date;
    const root = e.currentTarget; // React clears currentTarget after the handler returns
    onSelect(date);
    requestAnimationFrame(() => root.querySelector<HTMLElement>(`[data-date="${date}"]`)?.focus());
  }
  const first = new Date(data[0]!.date + "T12:00:00");
  const pad = (first.getDay() + 6) % 7; // Monday = 0
  const cells: (Insights["heatmap"][number] | null)[] = [...Array(pad).fill(null), ...data];
  const weeks: (typeof cells)[] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  const monthStarts: Record<number, string> = {};
  weeks.forEach((w, i) => {
    const firstDay = w.find((d) => d)?.date;
    const month = firstDay?.slice(0, 7);
    const prev = i > 0 ? weeks[i - 1]!.find((d) => d)?.date.slice(0, 7) : null;
    if (firstDay && month !== prev && (i > 0 || Number(firstDay.slice(8)) <= 7)) monthStarts[i] = t.months[Number(firstDay.slice(5, 7)) - 1]!;
  });
  // Open on the latest weeks: on a phone only part of the half year fits.
  const scroller = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollLeft = el.scrollWidth;
  }, []);
  return (
    <div className="flex flex-col gap-2">
      <div ref={scroller} className="flex gap-[3px] overflow-x-auto pb-1" role="group" aria-label={t.heatmapLabel} aria-describedby="heatmap-keys" onKeyDown={onGridKey}>
        {/* Weekday labels (Monday on top) and a month label over the first week of each month. */}
        <div aria-hidden className="sticky left-0 z-10 flex shrink-0 flex-col gap-[3px] bg-white pr-1 text-[0.6rem] leading-none text-slate-400 dark:bg-slate-900">
          <span className="h-3" />
          {t.weekdays.map((day, j) => (
            <span key={j} className="flex size-4 items-center lg:size-5">
              {j % 2 === 0 ? day : ""}
            </span>
          ))}
        </div>
        {weeks.map((w, i) => (
          <div key={i} className="flex flex-col gap-[3px]">
            <span aria-hidden className="h-3 whitespace-nowrap text-[0.6rem] leading-none text-slate-400">
              {monthStarts[i] ?? ""}
            </span>
            {w.map((d, j) =>
              d ? (
                <button
                  key={d.date}
                  type="button"
                  data-date={d.date}
                  // One tab stop for the whole calendar (the selected day); arrows move inside it.
                  tabIndex={d.date === focusDate ? 0 : -1}
                  aria-pressed={selected === d.date}
                  aria-label={t.activityDayLabel(dayFmt(d.date), d.graded, d.practice)}
                  onClick={() => onSelect(d.date)}
                  title={`${dayFmt(d.date)}: ${t.dayTitle(d.graded, d.practice)}`}
                  className={`size-4 shrink-0 rounded-[3px] outline-none focus-visible:ring-2 focus-visible:ring-brand-500 lg:size-5 ${level(amount(d, mode), max)} ${selected === d.date ? "ring-2 ring-brand-700 dark:ring-brand-200" : ""}`}
                />
              ) : (
                <span key={`pad-${j}`} className="size-4 lg:size-5" />
              ),
            )}
          </div>
        ))}
      </div>
      <div className="flex items-center justify-end gap-1 text-[0.7rem] text-slate-500">
        <span id="heatmap-keys" className="mr-auto hidden lg:inline">
          {t.heatmapKeys}
        </span>
        {t.less}
        {[0, 0.2, 0.4, 0.6, 0.9].map((r) => (
          <span key={r} className={`size-3 rounded-[3px] ${level(r * 100, 100)}`} />
        ))}
        {t.more}
      </div>
    </div>
  );
}

const DAY_WORDS = 8; // words shown for a day before "show all": a busy day can list 40+

function ActivityDetails({ data, date, loading, failed, language, onRetry }: { data: ActivityDay | null; date: string | null; loading: boolean; failed: boolean; language: string; onRetry: () => void }) {
  const [allWords, setAllWords] = useState(false);
  useEffect(() => setAllWords(false), [date]);
  if (!date) return null;
  return (
    <section className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-800" aria-live="polite">
      <h3 className="mb-2 font-semibold">{t.activityDay(dayFmt(date))}</h3>
      {loading ? <Skeleton lines={3} /> : failed ? <RetryNotice text={t.dayFailed} onRetry={onRetry} /> : !data || (!data.words.length && !data.grammar.length) ? <p className="text-sm text-slate-500">{t.activityEmpty}</p> : (
        <div className="grid gap-4 sm:grid-cols-2">
          {data.words.length > 0 && <section>
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t.activityWords}</h4>
            <ul className="flex flex-col gap-1" lang={language}>
              {(allWords ? data.words : data.words.slice(0, DAY_WORDS)).map((word) => (
                <li key={word.id} className="flex items-center gap-1">
                  <a href={`/words?word=${word.id}`} className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-2 rounded-lg px-2 py-1 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
                    <span className="font-medium">
                      {word.gender && word.gender.length > 1 ? `${word.gender} ` : ""}
                      {word.lemma}
                      <span className="ml-1 text-slate-500" lang="cs">· {word.translation}</span>
                    </span>
                    <span className="shrink-0 text-xs text-slate-500">{t.activityCount(word.graded, word.practice)}</span>
                  </a>
                  <PlayButton url={myWordAudioUrl(word.id)} size="sm" label={cs.words.playRow(word.lemma)} />
                </li>
              ))}
            </ul>
            {data.words.length > DAY_WORDS && (
              <button type="button" onClick={() => setAllWords(!allWords)} className="mt-1 px-2 text-sm font-medium text-brand-700 hover:underline dark:text-brand-200">
                {allWords ? t.fewerWords : t.allWords(data.words.length)}
              </button>
            )}
          </section>}
          {data.grammar.length > 0 && <section>
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t.activityGrammar}</h4>
            <ul className="flex flex-col gap-1">
              {data.grammar.map((unit) => <li key={unit.id}><a href={`/grammar/${unit.id}`} className="flex items-center justify-between gap-2 rounded-lg px-2 py-1 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"><span><span className="mr-1 text-xs text-slate-500">{unit.level}</span>{unit.title}</span><span className="shrink-0 text-xs text-slate-500">{t.activityCount(unit.graded, unit.practice)}</span></a></li>)}
            </ul>
          </section>}
        </div>
      )}
    </section>
  );
}

const SKILLS = [
  { key: "recognition", stroke: "stroke-sky-500", dot: "stroke-sky-600", swatch: "bg-sky-500" },
  { key: "recall", stroke: "stroke-emerald-500", dot: "stroke-emerald-600", swatch: "bg-emerald-500" },
  { key: "grammar", stroke: "stroke-amber-400", dot: "stroke-amber-500", swatch: "bg-amber-400" },
] as const;

const FEW = 5; // answers in a week below which a point is marked as thin evidence

/** One line per skill. A week without answers breaks the line instead of being drawn as 0 %. */
function AccuracyChart({ data }: { data: Insights["accuracy"] }) {
  const W = 480, H = 160, P = 24;
  const step = (W - 2 * P) / Math.max(data.length - 1, 1);
  const y = (share: number) => H - P - (H - 2 * P) * share;
  const most = Math.max(1, ...data.flatMap((w) => SKILLS.map((s) => w[s.key].answered)));
  const shown = SKILLS.filter((s) => data.some((w) => w[s.key].answered));
  return (
    <div className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={t.accuracyLabel}>
        {[0, 0.5, 1].map((v) => (
          <g key={v}>
            <line x1={P} x2={W - P} y1={y(v)} y2={y(v)} className="stroke-slate-200 dark:stroke-slate-800" />
            <text x={2} y={y(v) + 4} className="fill-slate-400 text-[10px]">
              {v * 100}%
            </text>
          </g>
        ))}
        {shown.map((s) => {
          const segments: string[][] = [[]];
          data.forEach((w, i) => {
            const tally = w[s.key];
            if (tally.answered) segments[segments.length - 1]!.push(`${P + i * step},${y(tally.correct / tally.answered)}`);
            else if (segments[segments.length - 1]!.length) segments.push([]);
          });
          return (
            <g key={s.key}>
              {segments.filter((seg) => seg.length > 1).map((seg, i) => (
                <polyline key={i} points={seg.join(" ")} fill="none" className={s.stroke} strokeWidth={2.5} strokeLinejoin="round" />
              ))}
              {data.map((w, i) => {
                const tally = w[s.key];
                if (!tally.answered) return null;
                return (
                  <circle
                    key={w.week}
                    cx={P + i * step}
                    cy={y(tally.correct / tally.answered)}
                    r={2.5 + 3 * Math.sqrt(tally.answered / most)}
                    className={`fill-white dark:fill-slate-900 ${s.dot}`}
                    strokeWidth={2}
                    // Fewer than FEW answers: a dashed ring, so 1 of 1 does not read like a solid 100 %.
                    strokeDasharray={tally.answered < FEW ? "2 2" : undefined}
                  >
                    <title>{t.skillPoint(t.skills[s.key]!, t.weekOf(dayFmt(w.week)), tally.correct, tally.answered)}</title>
                  </circle>
                );
              })}
            </g>
          );
        })}
        {data.map((w, i) =>
          i % 3 === 0 || i === data.length - 1 ? (
            <text key={`l-${w.week}`} x={P + i * step} y={H - 6} textAnchor="middle" className="fill-slate-400 text-[10px]">
              {dayFmt(w.week)}
            </text>
          ) : null,
        )}
      </svg>
      <details className="text-xs">
        <summary className="cursor-pointer text-slate-500 hover:text-brand-600">{t.accuracyTable}</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left tabular-nums">
            <thead className="text-slate-500">
              <tr>
                <th scope="col" className="py-1 pr-2 font-medium">{t.weekCol}</th>
                {shown.map((s) => (
                  <th key={s.key} scope="col" className="py-1 pr-2 font-medium">{t.skills[s.key]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.filter((w) => shown.some((s) => w[s.key].answered)).map((w) => (
                <tr key={w.week} className="border-t border-slate-100 dark:border-slate-800">
                  <th scope="row" className="py-1 pr-2 font-normal">{dayFmt(w.week)}</th>
                  {shown.map((s) => (
                    <td key={s.key} className="py-1 pr-2">
                      {w[s.key].answered ? `${w[s.key].correct}/${w[s.key].answered}` : "–"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <ul className="flex flex-wrap gap-3 text-xs text-slate-600 dark:text-slate-300">
        {shown.map((s) => {
          const answered = data.reduce((n, w) => n + w[s.key].answered, 0);
          const correct = data.reduce((n, w) => n + w[s.key].correct, 0);
          return (
            <li key={s.key} className="flex items-center gap-1.5">
              <span className={`size-2.5 rounded-sm ${s.swatch}`} aria-hidden />
              {t.skills[s.key]} <span className="tabular-nums text-slate-500">{Math.round((correct / answered) * 100)} % · {answered}×</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Forecast({
  data,
  selected,
  onSelect,
}: {
  data: Insights["forecast"];
  selected: string | null;
  onSelect: (date: string) => void;
}) {
  const max = Math.max(1, ...data.map((d) => d.words + d.grammar));
  return (
    <div
      className="flex h-40 items-end gap-1"
      role="group"
      aria-label={t.forecastLabel}
      onKeyDown={(e) => {
        const index = Math.max(0, data.findIndex((d) => d.date === selected));
        const next = e.key === "ArrowRight" ? index + 1 : e.key === "ArrowLeft" ? index - 1 : e.key === "Home" ? 0 : e.key === "End" ? data.length - 1 : null;
        if (next === null) return;
        e.preventDefault();
        const date = data[Math.max(0, Math.min(data.length - 1, next))]!.date;
        onSelect(date);
        const root = e.currentTarget;
        requestAnimationFrame(() => root.querySelector<HTMLElement>(`[data-date="${date}"]`)?.focus());
      }}
    >
      {data.map((d, i) => {
        const total = d.words + d.grammar;
        return (
          <button key={d.date} type="button" data-date={d.date} tabIndex={selected === d.date || (!selected && i === 0) ? 0 : -1} aria-pressed={selected === d.date} aria-label={t.forecastAction(dayFmt(d.date), d.words, d.grammar)} onClick={() => onSelect(d.date)} className={`flex h-full flex-1 flex-col items-center justify-end gap-1 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${selected === d.date ? "bg-brand-500/10" : "hover:bg-slate-100/70 dark:hover:bg-slate-800/70"}`} title={`${dayFmt(d.date)}: ${t.forecastTitle(d.words, d.grammar)}`}>
            <span className="text-[0.65rem] tabular-nums text-slate-500">{total || ""}</span>
            <div className="flex w-full flex-col justify-end overflow-hidden rounded-md" style={{ height: `${(total / max) * 75}%` }}>
              <div className="bg-amber-400" style={{ flexGrow: d.grammar }} />
              <div className="bg-brand-500" style={{ flexGrow: d.words }} />
            </div>
            <span className={`whitespace-nowrap text-[0.6rem] ${i === 0 ? "font-bold text-slate-700 dark:text-slate-200" : "text-slate-400"}`}>
              {/* Day of month only (the month when it changes) so 14 labels fit a phone. */}
              {i === 0 ? t.today : d.date.slice(8) === "01" ? dayFmt(d.date) : `${Number(d.date.slice(8))}.`}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function ForecastDetails({ data, language, isToday }: { data: Insights["forecast"][number]; language: string; isToday: boolean }) {
  const empty = data.word_items.length === 0 && data.grammar_items.length === 0;
  return (
    <section className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-800" aria-live="polite">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{t.forecastDetails(isToday ? t.today.toLowerCase() : dayFmt(data.date))}</h3>
        {/* Today: go straight to the checks. Later days: the dictionary ordered by the next check. */}
        <div className="flex flex-wrap gap-2 text-sm">
          {isToday && data.word_items.length > 0 && (
            <Link href="/check" className="rounded-lg bg-brand-600 px-3 py-1.5 font-semibold text-white hover:bg-brand-700">
              {t.checkWordsNow(data.words)}
            </Link>
          )}
          {isToday && data.grammar_items.length > 0 && (
            <Link href="/grammar/check" className="rounded-lg border border-amber-400 px-3 py-1.5 font-semibold text-amber-800 hover:bg-amber-50 dark:text-amber-200 dark:hover:bg-amber-950">
              {t.checkGrammarNow(data.grammar)}
            </Link>
          )}
          {!isToday && data.word_items.length > 0 && (
            <Link href="/words?tab=all&sort=review" className="font-medium text-brand-700 hover:underline dark:text-brand-200">
              {t.openWords}
            </Link>
          )}
        </div>
      </div>
      {empty ? <p className="text-sm text-slate-500">{t.forecastEmpty}</p> : (
        <div className="grid gap-4 sm:grid-cols-2">
          {data.word_items.length > 0 && (
            <section>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t.words}</h4>
              <ul className="flex flex-wrap gap-1.5" lang={language}>
                {data.word_items.map((word) => (
                  <li key={word.id} className="flex items-center rounded-lg bg-brand-500/10">
                    <Link href={`/words?word=${word.id}`} className="block rounded-l-lg py-1 pl-2 pr-1 text-sm hover:bg-brand-500/20">
                      {word.gender && word.gender.length > 1 ? `${word.gender} ` : ""}
                      {word.lemma}
                      <span className="ml-1 text-slate-500" lang="cs">· {word.translation}</span>
                    </Link>
                    <PlayButton url={myWordAudioUrl(word.id)} size="sm" label={cs.words.playRow(word.lemma)} />
                  </li>
                ))}
                {data.words > data.word_items.length && (
                  <li>
                    <Link href="/words?tab=all&sort=review" className="block rounded-lg px-2 py-1 text-sm font-medium text-brand-700 hover:underline dark:text-brand-200">
                      {t.moreDue(data.words - data.word_items.length)}
                    </Link>
                  </li>
                )}
              </ul>
            </section>
          )}
          {data.grammar_items.length > 0 && (
            <section>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t.grammar}</h4>
              <ul className="flex flex-col gap-1">
                {data.grammar_items.map((unit) => <li key={unit.id}><Link href={`/grammar/${unit.id}`} className="flex items-center gap-2 rounded-lg px-2 py-1 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"><span className="text-xs text-slate-500">{unit.level}</span>{unit.title}</Link></li>)}
              </ul>
            </section>
          )}
        </div>
      )}
      {!isToday && !empty && <p className="mt-2 text-xs text-slate-500">{t.laterNote}</p>}
    </section>
  );
}

export default function InsightsPage() {
  const me = useRequireMe();
  const language = me?.acting.active_language;
  const [data, setData] = useState<Insights | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [dayAttempt, setDayAttempt] = useState(0);
  const [forecastDate, setForecastDate] = useState<string | null>(null);
  const [activityDate, setActivityDate] = useState<string | null>(null);
  const [activity, setActivity] = useState<ActivityDay | null>(null);
  const [activityLoading, setActivityLoading] = useState(false);
  const [activityFailed, setActivityFailed] = useState(false);
  const [openMistake, setOpenMistake] = useState<string | null>(null);
  const [heatMode, setHeatMode] = useState<HeatMode>("all");

  useEffect(() => {
    if (!language) return;
    let cancelled = false;
    setData(null);
    setFailed(false);
    getInsights(language)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        // The selected days live in the URL, so Back from a word card or topic returns to the same day.
        const params = new URLSearchParams(window.location.search);
        const wantedForecast = params.get("forecast");
        const wantedDay = params.get("day");
        setForecastDate(d.forecast.find((f) => f.date === wantedForecast)?.date ?? d.forecast[0]?.date ?? null);
        setActivityDate(
          d.heatmap.find((h) => h.date === wantedDay)?.date ??
            [...d.heatmap].reverse().find((day) => day.graded + day.practice > 0)?.date ??
            d.today,
        );
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language, me?.acting.id, attempt]);

  useEffect(() => {
    if (!data) return;
    const params = new URLSearchParams(window.location.search);
    const set = (k: string, v: string | null) => (v ? params.set(k, v) : params.delete(k));
    set("day", activityDate);
    set("forecast", forecastDate && forecastDate !== data.forecast[0]?.date ? forecastDate : null);
    const qs = params.toString();
    const next = `${window.location.pathname}${qs ? `?${qs}` : ""}`;
    if (next !== `${window.location.pathname}${window.location.search}`) window.history.replaceState(window.history.state, "", next);
  }, [data, activityDate, forecastDate]);

  useEffect(() => {
    if (!language || !activityDate) return;
    let cancelled = false;
    setActivity(null);
    setActivityLoading(true);
    setActivityFailed(false);
    // Arrow keys can walk the calendar a day per key press; only the day it settles on is fetched.
    const timer = window.setTimeout(() => {
      getActivityDay(language, activityDate)
        .then((day) => !cancelled && setActivity(day))
        .catch(() => !cancelled && setActivityFailed(true))
        .finally(() => !cancelled && setActivityLoading(false));
    }, 150);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [language, activityDate, me?.acting.id, dayAttempt]);

  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const funnel = data?.funnel;
  // Rows that match a dictionary filter link to it; "passive" and "active" overlap the status
  // ladder (a known word is both), so they stay plain numbers.
  const steps: [string, number, string | null][] = funnel
    ? [
        [t.funnel.introduced, funnel.introduced, STEP_ROOT],
        [t.funnel.passive, funnel.passive, null],
        [t.funnel.active, funnel.active, null],
        [t.funnel.known, funnel.known, null],
        [t.funnel.mastered, funnel.mastered, "/words?tab=all&status=mastered"],
      ]
    : [];
  const firstRun = Boolean(data && data.active_days === 0 && data.funnel.introduced === 0 && data.forecast.every((d) => d.words + d.grammar === 0));
  const mistakeMax = Math.max(1, ...(data?.mistakes.map((m) => m.count) ?? [1]));
  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="flex items-center gap-2 text-xl font-bold">
              <BarChart3 className="size-6 text-brand-500" aria-hidden />
              {t.title}
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-300">{t.intro}</p>
          </div>
          <LanguagePicker me={me} />
        </div>
        {/* The recap would repeat the first-run call to action, so it waits for something to recap. */}
        {language && data && !firstRun && <WeeklyRecap language={language} />}
        {failed && <RetryNotice text={t.loadFailed} onRetry={() => setAttempt((n) => n + 1)} />}
        {!data ? (
          !failed && (
            <div className="grid gap-4 lg:grid-cols-2">
              {[t.activity, t.forecast, t.accuracy, t.funnelTitle].map((title, i) => (
                <div key={title} className={`rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 ${i === 0 ? "lg:col-span-2" : ""}`}>
                  <p className="mb-3 text-sm font-semibold text-slate-400">{title}</p>
                  <Skeleton lines={i === 0 ? 5 : 4} />
                </div>
              ))}
            </div>
          )
        ) : firstRun ? (
          // Nothing to measure yet: one clear next step instead of five empty charts.
          <section className="flex flex-col items-start gap-3 rounded-2xl border border-dashed border-slate-300 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
            <BarChart3 className="size-8 text-slate-300 dark:text-slate-600" aria-hidden />
            <p className="font-semibold">{t.firstRunTitle}</p>
            <p className="max-w-prose text-sm text-slate-600 dark:text-slate-300">{t.firstRunText}</p>
            <Link href="/lesson/vocabulary" className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
              {t.firstRunCta}
            </Link>
          </section>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2 [&>*]:min-w-0">
            <Panel title={t.activity} icon={CalendarDays} className="lg:col-span-2">
              <div role="radiogroup" aria-label={t.heatModeLabel} className="mb-2 inline-flex rounded-lg bg-slate-100 p-0.5 text-xs dark:bg-slate-800">
                {(["all", "graded", "practice"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    role="radio"
                    aria-checked={heatMode === m}
                    onClick={() => setHeatMode(m)}
                    className={`rounded-md px-2.5 py-1 font-medium ${heatMode === m ? "bg-white text-brand-600 shadow-sm dark:bg-slate-900 dark:text-brand-50" : "text-slate-600 dark:text-slate-300"}`}
                  >
                    {t.heatModes[m]}
                  </button>
                ))}
              </div>
              <Heatmap data={data.heatmap} selected={activityDate} onSelect={setActivityDate} mode={heatMode} />
              <ActivityDetails data={activity} date={activityDate} loading={activityLoading} failed={activityFailed} language={data.language} onRetry={() => setDayAttempt((n) => n + 1)} />
              <p className="mt-2 text-xs text-slate-500">
                {heatMode === "all" ? t.activeDays(data.active_days) : t.modeDays(heatMode, data.heatmap.filter((d) => d[heatMode] > 0).length)}
              </p>
            </Panel>
            <Panel title={t.forecast} icon={Target}>
              <Forecast data={data.forecast} selected={forecastDate} onSelect={setForecastDate} />
              {forecastDate && data.forecast.find((day) => day.date === forecastDate) && (
                <ForecastDetails data={data.forecast.find((day) => day.date === forecastDate)!} language={data.language} isToday={forecastDate === data.forecast[0]?.date} />
              )}
              <p className="mt-2 flex gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <span className="size-2.5 rounded-sm bg-brand-500" /> {t.words}
                </span>
                <span className="flex items-center gap-1">
                  <span className="size-2.5 rounded-sm bg-amber-400" /> {t.grammar}
                </span>
              </p>
            </Panel>
            <Panel title={t.accuracy} icon={TrendingUp}>
              {data.accuracy.some((w) => w.answered) ? <AccuracyChart data={data.accuracy} /> : <p className="text-sm text-slate-500">{t.noAnswers}</p>}
              <p className="mt-1 text-xs text-slate-500">{t.accuracyHelp}</p>
            </Panel>
            <Panel title={t.funnelTitle} icon={Filter}>
              {funnel && funnel.introduced === 0 ? (
                <p className="text-sm text-slate-500">{t.funnelEmpty}</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {steps.map(([label, n, href]) => {
                    const row = (
                      <>
                        <div className="flex justify-between text-xs">
                          <span>{label}</span>
                          <span className="tabular-nums text-slate-500">{t.funnelShare(n, href === STEP_ROOT ? 0 : steps[0]![1])}</span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                          <div className="h-full rounded-full bg-emerald-500" style={{ width: `${steps[0]![1] ? (n / steps[0]![1]) * 100 : 0}%` }} />
                        </div>
                      </>
                    );
                    return (
                      <li key={label}>
                        {href ? (
                          <Link href={href} className="flex flex-col gap-1 rounded-lg p-1 -m-1 hover:bg-slate-100 dark:hover:bg-slate-800">
                            {row}
                          </Link>
                        ) : (
                          <div className="flex flex-col gap-1">{row}</div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
              {funnel && funnel.introduced > funnel.passive && (
                <p className="mt-3 text-xs text-slate-600 dark:text-slate-300">
                  <Link href="/words?tab=all&status=learning" className="hover:underline">
                    {t.funnelWaiting(funnel.introduced - funnel.passive)}
                  </Link>
                </p>
              )}
              {funnel && funnel.fading > 0 && (
                <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
                  <Link href="/words?tab=all&due=1" className="hover:underline">
                    {t.funnelFading(funnel.fading)}
                  </Link>
                </p>
              )}
              <p className="mt-2 text-xs text-slate-500">{t.funnelHelp}</p>
            </Panel>
            <Panel title={t.mistakes} icon={TriangleAlert}>
              {data.mistakes.length === 0 ? (
                <p className="text-sm text-slate-500">{data.accuracy.some((w) => w.answered) ? t.noMistakes : t.noChecksYet}</p>
              ) : (
                <ul className="flex flex-col gap-1">
                  {data.mistakes.map((m) => {
                    const label = cs.feedback.errors[m.tag] ?? m.tag;
                    const isOpen = openMistake === m.tag;
                    return (
                      <li key={m.tag}>
                        <button
                          type="button"
                          aria-expanded={isOpen}
                          aria-controls={`mistake-${m.tag}`}
                          onClick={() => setOpenMistake(isOpen ? null : m.tag)}
                          className="flex w-full items-center gap-2 rounded-lg px-1 py-1 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
                        >
                          <ChevronRight className={`size-4 shrink-0 text-slate-400 transition-transform ${isOpen ? "rotate-90" : ""}`} aria-hidden />
                          <span className="w-36 shrink-0 truncate">{label}</span>
                          <span className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                            <span className="block h-full rounded-full bg-rose-400" style={{ width: `${(m.count / mistakeMax) * 100}%` }} />
                          </span>
                          <span className="w-8 text-right tabular-nums text-slate-500">{m.count}</span>
                        </button>
                        {isOpen && (
                          <ul id={`mistake-${m.tag}`} aria-label={t.mistakeBehind(label)} className="mb-1 ml-7 mt-1 flex flex-col gap-0.5 border-l border-slate-200 pl-2 dark:border-slate-800">
                            {m.items.map((item) => (
                              <li key={`${item.kind}-${item.id}`} className="flex items-center gap-1">
                                <a
                                  href={item.kind === "word" ? `/words?word=${item.id}` : `/grammar/${item.id}`}
                                  className="flex min-w-0 flex-1 items-center justify-between gap-2 rounded-lg px-2 py-1 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
                                >
                                  <span className="min-w-0 truncate">
                                    {item.kind === "word" ? (
                                      <span className="font-medium" lang={data.language}>
                                        {item.label}
                                      </span>
                                    ) : (
                                      <span className="font-medium">{item.label}</span>
                                    )}
                                    <span className="ml-1 text-slate-500">· {item.detail}</span>
                                  </span>
                                  <span className="shrink-0 text-xs tabular-nums text-rose-600 dark:text-rose-400">{t.mistakeTimes(item.count)}</span>
                                </a>
                                {item.kind === "word" && <PlayButton url={myWordAudioUrl(item.id)} size="sm" label={cs.words.playRow(item.label)} />}
                              </li>
                            ))}
                          </ul>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
              <p className="mt-2 text-xs text-slate-500">{t.mistakesHelp}</p>
            </Panel>
          </div>
        )}
      </div>
    </AppShell>
  );
}
