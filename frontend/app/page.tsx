"use client";

import { Activity, AlertTriangle, Award, BarChart3, BookOpen, ClipboardCheck, Compass, Gauge, Dumbbell, GraduationCap, Map as MapIcon, Play, Trophy } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
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
import { byRecent, modesFor, readPinned, readRecent } from "@/lib/practice";
import { invalidateRanks, useRanks } from "@/lib/useRanks";

// Mobile: practice first, single column. lg+: dense multi-panel dashboard.
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

  return (
    <AppShell me={me}>
      <div className="grid gap-4 lg:grid-cols-3">
        {language && !offerPlacement && <NewsBanner profileId={me.acting.id} language={language} />}
        {language && <TodayPlan language={language} profileId={me.acting.id} />}
        {language && !offerPlacement && <WeeklyRecap language={language} className="lg:col-span-3" />}
        <Panel title={cs.todayPractice} icon={BookOpen}>
          <div className="flex flex-col gap-3">
            <LanguagePicker me={me} />
            {offerPlacement && (
              <section className="flex flex-col gap-2 rounded-xl border border-brand-500/40 bg-brand-500/5 p-3">
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
            <div className="flex flex-col gap-1">
              <Button className="w-full !py-4 text-lg" onClick={() => router.push("/lesson")}>
                <Play className="size-5" aria-hidden />
                {progress?.active_session_id ? cs.lesson.resume : cs.lesson.start}
              </Button>
              <p className="text-center text-xs text-slate-500">{cs.lesson.learnHelp}</p>
            </div>
            <div className="flex flex-col gap-1">
              <Button
                variant="secondary"
                className="w-full !py-4 text-lg"
                disabled={!progress || (!progress.due_now && !progress.active_check_session_id)}
                onClick={() => router.push("/check")}
              >
                <ClipboardCheck className="size-5" aria-hidden />
                {progress?.active_check_session_id ? cs.check.resume : cs.check.start}
              </Button>
              {progress && (
                <p className="text-center text-xs text-slate-500">
                  {progress.due_now || progress.active_check_session_id
                    ? `${cs.check.dueCount(progress.due_now)}. ${cs.check.help}`
                    : cs.check.nothingDue}
                </p>
              )}
            </div>
            <div className="flex flex-col gap-1">
              <Button variant="secondary" className="w-full !py-4 text-lg" onClick={() => router.push("/grammar")}>
                <GraduationCap className="size-5" aria-hidden />
                {cs.grammar.title}
              </Button>
            </div>
            {language && (
              <section className="flex flex-col gap-2 rounded-2xl bg-slate-50 p-3 dark:bg-slate-800/50">
                <Button variant="secondary" className="w-full" onClick={() => router.push("/practice")}>
                  <Dumbbell className="size-5" aria-hidden />
                  {cs.practice.open}
                </Button>
                {pinned.some((id) => modesFor(language).some((mode) => mode.id === id)) && (
                  <div className="flex flex-wrap justify-center gap-1" aria-label={cs.practice.pinned}>
                    {pinned.map((id) => modesFor(language).find((mode) => mode.id === id)).filter((mode): mode is NonNullable<typeof mode> => !!mode).map((m) => (
                      <Link key={`pinned-${m.id}`} href={m.href} className="inline-flex items-center gap-1 rounded-full border border-brand-500/60 bg-white px-2.5 py-1 text-xs font-semibold text-brand-700 hover:bg-brand-500/10 dark:bg-slate-900 dark:text-brand-100">
                        <m.icon className="size-3.5" aria-hidden />{cs.practice.mode[m.id]?.title}
                      </Link>
                    ))}
                  </div>
                )}
                <div className="flex flex-wrap justify-center gap-1">
                  {byRecent(modesFor(language), recent).map((m) => (
                    <Link
                      key={m.id}
                      href={m.href}
                      title={cs.practice.mode[m.id]?.blurb}
                      className="inline-flex items-center gap-1 rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-brand-500/10 dark:bg-slate-900 dark:text-slate-200"
                    >
                      <m.icon className="size-3.5" aria-hidden />
                      {cs.practice.mode[m.id]?.title}
                    </Link>
                  ))}
                </div>
              </section>
            )}
            {progress && (
              <section className="flex flex-col gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
                <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300">{cs.tests.title}</h3>
                {/* Available at any time; before the first lesson it is also offered above. */}
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
              </section>
            )}
          </div>
        </Panel>

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

        {ranks.data && ranks.data.path !== "off" && (
          <Panel title="Moje cesta" icon={Trophy}>
            <RankCard data={ranks.data} />
          </Panel>
        )}

        <Panel title={cs.progression.title} icon={MapIcon} className="lg:col-span-2">
          <ProgressionPath progress={progress} />
        </Panel>

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
