"use client";

import { BarChart3, CalendarDays, Filter, Target, TrendingUp, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Panel } from "@/components/Panel";
import { WeeklyRecap } from "@/components/WeeklyRecap";
import { Notice } from "@/components/ui";
import { getInsights, type Insights } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const t = cs.insights;
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
function Heatmap({ data }: { data: Insights["heatmap"] }) {
  const max = Math.max(...data.map((d) => d.graded + d.practice));
  const first = new Date(data[0]!.date + "T12:00:00");
  const pad = (first.getDay() + 6) % 7; // Monday = 0
  const cells: (Insights["heatmap"][number] | null)[] = [...Array(pad).fill(null), ...data];
  const weeks: (typeof cells)[] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-[3px] overflow-x-auto pb-1" role="img" aria-label={t.heatmapLabel}>
        {weeks.map((w, i) => (
          <div key={i} className="flex flex-col gap-[3px]">
            {w.map((d, j) =>
              d ? (
                <span
                  key={d.date}
                  title={`${dayFmt(d.date)}: ${t.dayTitle(d.graded, d.practice)}`}
                  className={`size-3 rounded-[3px] lg:size-4 ${level(d.graded + d.practice, max)}`}
                />
              ) : (
                <span key={`pad-${j}`} className="size-3 lg:size-4" />
              ),
            )}
          </div>
        ))}
      </div>
      <div className="flex items-center justify-end gap-1 text-[0.7rem] text-slate-500">
        {t.less}
        {[0, 0.2, 0.4, 0.6, 0.9].map((r) => (
          <span key={r} className={`size-3 rounded-[3px] ${level(r * 100, 100)}`} />
        ))}
        {t.more}
      </div>
    </div>
  );
}

function AccuracyChart({ data }: { data: Insights["accuracy"] }) {
  const W = 480, H = 160, P = 24;
  const step = (W - 2 * P) / Math.max(data.length - 1, 1);
  const pts = data.map((w, i) => ({ x: P + i * step, y: w.answered ? H - P - ((H - 2 * P) * w.correct) / w.answered : null, w }));
  const line = pts.filter((p) => p.y !== null).map((p) => `${p.x},${p.y}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={t.accuracyLabel}>
      {[0, 0.5, 1].map((v) => (
        <g key={v}>
          <line x1={P} x2={W - P} y1={H - P - (H - 2 * P) * v} y2={H - P - (H - 2 * P) * v} className="stroke-slate-200 dark:stroke-slate-800" />
          <text x={2} y={H - P - (H - 2 * P) * v + 4} className="fill-slate-400 text-[10px]">
            {v * 100}%
          </text>
        </g>
      ))}
      {line && <polyline points={line} fill="none" className="stroke-brand-500" strokeWidth={2.5} strokeLinejoin="round" />}
      {pts.map((p) =>
        p.y === null ? null : (
          <circle key={p.w.week} cx={p.x} cy={p.y} r={4} className="fill-white stroke-brand-600 dark:fill-slate-900" strokeWidth={2}>
            <title>{`${t.weekOf(dayFmt(p.w.week))}: ${p.w.correct}/${p.w.answered}`}</title>
          </circle>
        ),
      )}
      {pts.filter((_, i) => i % 3 === 0 || i === pts.length - 1).map((p) => (
        <text key={`l-${p.w.week}`} x={p.x} y={H - 6} textAnchor="middle" className="fill-slate-400 text-[10px]">
          {dayFmt(p.w.week)}
        </text>
      ))}
    </svg>
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
    <div className="flex h-40 items-end gap-1" role="group" aria-label={t.forecastLabel}>
      {data.map((d, i) => {
        const total = d.words + d.grammar;
        return (
          <button key={d.date} type="button" aria-pressed={selected === d.date} aria-label={t.forecastAction(dayFmt(d.date), d.words, d.grammar)} onClick={() => onSelect(d.date)} className={`flex h-full flex-1 flex-col items-center justify-end gap-1 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${selected === d.date ? "bg-brand-500/10" : "hover:bg-slate-100/70 dark:hover:bg-slate-800/70"}`} title={`${dayFmt(d.date)}: ${t.forecastTitle(d.words, d.grammar)}`}>
            <span className="text-[0.65rem] tabular-nums text-slate-500">{total || ""}</span>
            <div className="flex w-full flex-col justify-end overflow-hidden rounded-md" style={{ height: `${(total / max) * 75}%` }}>
              <div className="bg-amber-400" style={{ flexGrow: d.grammar }} />
              <div className="bg-brand-500" style={{ flexGrow: d.words }} />
            </div>
            <span className={`text-[0.6rem] ${i === 0 ? "font-bold text-slate-700 dark:text-slate-200" : "text-slate-400"}`}>
              {i === 0 ? t.today : dayFmt(d.date)}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function ForecastDetails({ data, language }: { data: Insights["forecast"][number]; language: string }) {
  const empty = data.word_items.length === 0 && data.grammar_items.length === 0;
  return (
    <section className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-800" aria-live="polite">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{t.forecastDetails(dayFmt(data.date))}</h3>
        <div className="flex gap-3 text-sm">
          {data.word_items.length > 0 && <a href="/words" className="font-medium text-brand-700 hover:underline dark:text-brand-200">{t.openWords}</a>}
          {data.grammar_items.length > 0 && <a href="/grammar" className="font-medium text-brand-700 hover:underline dark:text-brand-200">{t.openGrammar}</a>}
        </div>
      </div>
      {empty ? <p className="text-sm text-slate-500">{t.forecastEmpty}</p> : (
        <div className="grid gap-4 sm:grid-cols-2">
          {data.word_items.length > 0 && (
            <section>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t.words}</h4>
              <ul className="flex flex-wrap gap-1.5" lang={language}>
                {data.word_items.map((word) => <li key={word.id} className="rounded-lg bg-brand-500/10 px-2 py-1 text-sm">{word.gender && word.gender.length > 1 ? `${word.gender} ` : ""}{word.lemma}<span className="ml-1 text-slate-500" lang="cs">· {word.translation}</span></li>)}
              </ul>
            </section>
          )}
          {data.grammar_items.length > 0 && (
            <section>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t.grammar}</h4>
              <ul className="flex flex-col gap-1">
                {data.grammar_items.map((unit) => <li key={unit.id}><a href={`/grammar/${unit.id}`} className="flex items-center gap-2 rounded-lg px-2 py-1 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"><span className="text-xs text-slate-500">{unit.level}</span>{unit.title}</a></li>)}
              </ul>
            </section>
          )}
        </div>
      )}
    </section>
  );
}

export default function InsightsPage() {
  const me = useRequireMe();
  const language = me?.acting.active_language;
  const [data, setData] = useState<Insights | null>(null);
  const [failed, setFailed] = useState(false);
  const [forecastDate, setForecastDate] = useState<string | null>(null);

  useEffect(() => {
    if (!language) return;
    let cancelled = false;
    setData(null);
    getInsights(language)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setForecastDate(d.forecast[0]?.date ?? null);
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language, me?.acting.id]);

  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const funnel = data?.funnel;
  const steps: [string, number][] = funnel
    ? [
        [t.funnel.introduced, funnel.introduced],
        [t.funnel.passive, funnel.passive],
        [t.funnel.active, funnel.active],
        [t.funnel.known, funnel.known],
        [t.funnel.mastered, funnel.mastered],
      ]
    : [];
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
        {language && <WeeklyRecap language={language} />}
        {failed && <Notice tone="error">{cs.common.error}</Notice>}
        {!data ? (
          !failed && <p className="text-sm text-slate-500">{cs.common.loading}</p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title={t.activity} icon={CalendarDays} className="lg:col-span-2">
              <Heatmap data={data.heatmap} />
              <p className="mt-2 text-xs text-slate-500">{t.activeDays(data.active_days)}</p>
            </Panel>
            <Panel title={t.forecast} icon={Target}>
              <Forecast data={data.forecast} selected={forecastDate} onSelect={setForecastDate} />
              {forecastDate && data.forecast.find((day) => day.date === forecastDate) && (
                <ForecastDetails data={data.forecast.find((day) => day.date === forecastDate)!} language={data.language} />
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
              <ul className="flex flex-col gap-2">
                {steps.map(([label, n]) => (
                  <li key={label} className="flex flex-col gap-1">
                    <div className="flex justify-between text-xs">
                      <span>{label}</span>
                      <span className="tabular-nums text-slate-500">{n.toLocaleString("cs-CZ")}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: `${steps[0]![1] ? (n / steps[0]![1]) * 100 : 0}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>
            <Panel title={t.mistakes} icon={TriangleAlert}>
              {data.mistakes.length === 0 ? (
                <p className="text-sm text-slate-500">{t.noMistakes}</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {data.mistakes.map((m) => (
                    <li key={m.tag} className="flex items-center gap-2 text-sm">
                      <span className="w-40 shrink-0 truncate">{cs.feedback.errors[m.tag] ?? m.tag}</span>
                      <span className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                        <span className="block h-full rounded-full bg-rose-400" style={{ width: `${(m.count / mistakeMax) * 100}%` }} />
                      </span>
                      <span className="w-8 text-right tabular-nums text-slate-500">{m.count}</span>
                    </li>
                  ))}
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
