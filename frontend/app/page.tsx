"use client";

import { Activity, AlertTriangle, ArrowRight, Award, BarChart3, ClipboardCheck, Compass, Dumbbell, Flag, Gauge, GraduationCap, Layers, Map as MapIcon, Play, Trophy, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Disclosure } from "@/components/Disclosure";
import { Panel } from "@/components/Panel";
import { ProgressCard } from "@/components/ProgressCard";
import { ProgressionPath } from "@/components/ProgressionPath";
import { RankCard } from "@/components/RankCard";
import { NewsBanner } from "@/components/NewsBanner";
import { TodayPlan } from "@/components/TodayPlan";
import { WeeklyRecap } from "@/components/WeeklyRecap";
import { RankCelebration } from "@/components/RankCelebration";
import { ServerStatus } from "@/components/ServerStatus";
import { WeakSpotsCard } from "@/components/WeakSpotsCard";
import { Welcome } from "@/components/Welcome";
import { Button, Notice } from "@/components/ui";
import { getProgress, markRanksSeen, skipPlacement, type ProgressOverview } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { modesFor, readPinned, readRecent } from "@/lib/practice";
import { invalidateRanks, useRanks } from "@/lib/useRanks";

function QuickAction({
  href,
  icon: Icon,
  title,
  help,
  highlight = false,
}: {
  href: string;
  icon: LucideIcon;
  title: string;
  help: string;
  highlight?: boolean;
}) {
  return (
    <li>
      <Link
        href={href}
        className={`flex h-full items-center gap-3 rounded-2xl border p-4 outline-none transition hover:border-brand-500 hover:shadow-sm focus-visible:ring-2 focus-visible:ring-brand-500 ${
          highlight ? "border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40" : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
        }`}
      >
        <span className={`grid size-11 shrink-0 place-items-center rounded-xl ${highlight ? "bg-amber-500 text-white" : "bg-brand-500/10 text-brand-600 dark:text-brand-50"}`}>
          <Icon className="size-5" aria-hidden />
        </span>
        <span className="flex min-w-0 flex-col">
          <span className="font-semibold">{title}</span>
          <span className="text-sm text-slate-600 dark:text-slate-300">{help}</span>
        </span>
      </Link>
    </li>
  );
}

// Daily-first: the next learning step and one-click daily actions above the fold; progress below;
// placement, CEFR estimate and level exams (occasional) in a collapsed section at the bottom.
export default function HomePage() {
  const me = useRequireMe();
  const { state } = useAuth();
  const router = useRouter();
  const language = me?.acting.active_language;
  const [progress, setProgress] = useState<ProgressOverview | null>(null);
  const [failed, setFailed] = useState(false);
  const ranks = useRanks(language, me?.acting.id);
  const [celebrated, setCelebrated] = useState(false);
  const [recent, setRecent] = useState<ReturnType<typeof readRecent>>([]);
  const [pinned, setPinned] = useState<ReturnType<typeof readPinned>>([]);
  useEffect(() => {
    setRecent(readRecent());
    setPinned(readPinned());
  }, []);

  useEffect(() => {
    if (!language) return;
    let cancelled = false;
    setProgress(null);
    setFailed(false);
    getProgress(language)
      .then((p) => !cancelled && setProgress(p))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language, me?.acting.id]);

  // Offered once per language, before anything is learned; skipping or taking it decides.
  const offerPlacement =
    !!progress && progress.placement === null && progress.introduced === 0 && progress.lexicon_items > 0;

  // First run of a fresh profile: the welcome wizard comes before the placement offer.
  const welcome = offerPlacement && !me?.acting.settings.onboarded;

  async function skip() {
    if (!language) return;
    try {
      await skipPlacement(language);
      setProgress(await getProgress(language));
    } catch {
      setFailed(true);
    }
  }

  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;

  const t = cs.dashboard;
  const checkDue = !!progress && (progress.due_now > 0 || !!progress.active_check_session_id);
  const assessmentInProgress = !!progress && (!!progress.active_placement_session_id || !!progress.active_exam_session_id);
  return (
    <AppShell me={me}>
      <div className="grid gap-4 lg:grid-cols-3">
        <section
          aria-labelledby="continue-title"
          className="flex flex-col gap-4 rounded-3xl bg-gradient-to-br from-brand-500 to-brand-600 p-5 text-white shadow-md sm:p-6 lg:col-span-3"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex flex-col gap-1">
              <h1 id="continue-title" className="text-2xl font-bold">{t.continueTitle}</h1>
              <p className="max-w-xl text-sm text-white/85">{progress?.active_session_id ? t.continueResume : t.continueNext}</p>
            </div>
            <div className="rounded-xl bg-white p-1 text-slate-900 dark:bg-slate-900 dark:text-slate-100">
              <LanguagePicker me={me} />
            </div>
          </div>
          {offerPlacement && (
            <section className="flex flex-col gap-2 rounded-2xl bg-white p-4 text-slate-800 dark:bg-slate-900 dark:text-slate-100">
              <p className="flex items-center gap-2 font-semibold">
                <Compass className="size-5 text-brand-500" aria-hidden />
                {cs.placement.offerTitle}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">{cs.placement.offer}</p>
              <div className="flex gap-2">
                <Button className="flex-1" onClick={() => router.push("/placement")}>
                  {cs.placement.take}
                </Button>
                <Button variant="secondary" className="flex-1" onClick={() => void skip()}>
                  {cs.placement.skip}
                </Button>
              </div>
            </section>
          )}
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
            <button
              type="button"
              onClick={() => router.push("/lesson")}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-6 py-4 text-lg font-bold text-brand-700 shadow-sm transition hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/60"
            >
              <Play className="size-5" aria-hidden />
              {progress?.active_session_id ? cs.lesson.resume : cs.lesson.start}
              <ArrowRight className="size-5" aria-hidden />
            </button>
            <p className="text-xs text-white/80">{cs.lesson.learnHelp}</p>
          </div>
        </section>

        <section aria-labelledby="quick-actions" className="flex flex-col gap-2 lg:col-span-3">
          <h2 id="quick-actions" className="text-sm font-semibold text-slate-600 dark:text-slate-300">{t.quickActions}</h2>
          <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <QuickAction
              href="/check"
              icon={ClipboardCheck}
              title={t.daily}
              highlight={checkDue}
              help={
                !progress
                  ? cs.common.loading
                  : progress.active_check_session_id
                    ? t.dailyResume
                    : progress.due_now
                      ? t.dailyDue(progress.due_now)
                      : t.dailyNone
              }
            />
            <QuickAction href="/grammar" icon={GraduationCap} title={t.grammar} help={t.grammarHelp(progress?.cefr_level ?? null)} />
            <QuickAction href="/words?tab=levels" icon={Layers} title={t.flashcards} help={t.flashcardsHelp} />
            <QuickAction href="/practice" icon={Dumbbell} title={t.practice} help={t.practiceHelp} />
          </ul>
          {language && (pinned.length > 0 || recent.length > 0) && (
            <div className="flex flex-wrap gap-1" aria-label={cs.practice.pinned}>
              {[...pinned, ...recent.filter((id) => !pinned.includes(id))]
                .map((id) => modesFor(language).find((mode) => mode.id === id))
                .filter((mode): mode is NonNullable<typeof mode> => !!mode)
                .slice(0, 6)
                .map((m) => (
                  <Link
                    key={m.id}
                    href={m.href}
                    title={cs.practice.mode[m.id]?.blurb}
                    className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium hover:bg-brand-500/10 ${
                      pinned.includes(m.id)
                        ? "border-brand-500/60 bg-white text-brand-700 dark:bg-slate-900 dark:text-brand-100"
                        : "border-slate-200 bg-white text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                    }`}
                  >
                    <m.icon className="size-3.5" aria-hidden />
                    {cs.practice.mode[m.id]?.title}
                  </Link>
                ))}
            </div>
          )}
        </section>

        {language && <TodayPlan language={language} profileId={me.acting.id} />}
        {language && !offerPlacement && <NewsBanner profileId={me.acting.id} language={language} />}

        <Panel title={cs.progress.title} icon={BarChart3} className="lg:col-span-2">
          {failed ? (
            <Notice tone="error">{cs.common.error}</Notice>
          ) : progress ? (
            <ProgressCard progress={progress} />
          ) : (
            <p className="text-sm text-slate-500">{cs.common.loading}</p>
          )}
        </Panel>

        <Panel title={cs.weak.title} icon={AlertTriangle}>
          {language && <WeakSpotsCard key={`${me.acting.id}:${language}`} language={language} />}
        </Panel>

        {language && !offerPlacement && <WeeklyRecap language={language} className="lg:col-span-3" />}

        {ranks.data && ranks.data.path !== "off" && (
          <Panel title="Moje cesta" icon={Trophy}>
            <RankCard data={ranks.data} />
          </Panel>
        )}

        <Panel title={cs.progression.title} icon={MapIcon} className="lg:col-span-2">
          <ProgressionPath progress={progress} />
        </Panel>

        {progress && (
          <Disclosure
            key={`milestones-${assessmentInProgress}`}
            defaultOpen={assessmentInProgress}
            className="rounded-2xl border border-slate-200 bg-white shadow-sm lg:col-span-3 dark:border-slate-800 dark:bg-slate-900"
            summaryClassName="p-4"
            summary={
              <span className="flex flex-col gap-0.5">
                <span className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
                  <Flag className="size-4" aria-hidden /> {t.milestones}
                  {assessmentInProgress && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-200">{t.inProgress}</span>
                  )}
                </span>
                <span className="text-xs font-normal text-slate-500">{t.milestonesHelp}</span>
              </span>
            }
          >
            <div className="grid gap-3 px-4 pb-4 sm:grid-cols-3">
              {/* Before the first lesson the placement is also offered in the hero above. */}
              {!offerPlacement && (
                <div className="flex flex-col gap-1">
                  <Button variant="secondary" className="w-full" onClick={() => router.push("/placement")}>
                    <Compass className="size-5" aria-hidden />
                    {progress.active_placement_session_id ? cs.placement.resume : cs.placement.link}
                  </Button>
                  <p className="text-center text-xs text-slate-500">{cs.placement.anytime}</p>
                </div>
              )}
              <div className="flex flex-col gap-1">
                <Button variant="secondary" className="w-full" onClick={() => router.push("/placement/cefr")}>
                  <Gauge className="size-5" aria-hidden />
                  {cs.cefr.short}
                  {progress.cefr_level && (
                    <span className="rounded-md bg-brand-500/15 px-1.5 text-sm text-brand-600 dark:text-brand-50">
                      {progress.cefr_level}
                    </span>
                  )}
                </Button>
                <p className="text-center text-xs text-slate-500">{cs.placement.part2}</p>
              </div>
              <div className="flex flex-col gap-1">
                <Button variant="secondary" className="w-full" onClick={() => router.push("/levels")}>
                  <Award className="size-5" aria-hidden />
                  {progress.active_exam_session_id ? cs.exam.resume : cs.tests.levels}
                </Button>
                <p className="text-center text-xs text-slate-500">
                  {progress.level_badges.length
                    ? cs.tests.badges(progress.level_badges.map((b) => b.level))
                    : cs.tests.levelsHelp}
                </p>
              </div>
            </div>
          </Disclosure>
        )}

        {me.can_manage && (
          <Panel title={cs.dashboard.serverHealth} icon={Activity} className="lg:col-span-3">
            <ServerStatus />
          </Panel>
        )}
      </div>
      {welcome && <Welcome me={me} />}
      {ranks.data &&
        !welcome &&
        !celebrated &&
        ranks.data.path !== "off" &&
        ((ranks.data.unseen_rank ?? 0) > 1 || ranks.data.unseen_achievements.length > 0) && (
          <RankCelebration
            data={ranks.data}
            onClose={() => {
              setCelebrated(true);
              const lang = ranks.data!.language;
              void markRanksSeen(lang).then(() => {
                invalidateRanks();
                void ranks.reload();
              });
            }}
          />
        )}
    </AppShell>
  );
}
