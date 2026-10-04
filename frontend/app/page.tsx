"use client";

import { Activity, Award, BarChart3, BookOpen, ClipboardCheck, Compass, Map as MapIcon, Play } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Panel } from "@/components/Panel";
import { ProgressCard } from "@/components/ProgressCard";
import { ProgressionPath } from "@/components/ProgressionPath";
import { ServerStatus } from "@/components/ServerStatus";
import { Button, Notice } from "@/components/ui";
import { getProgress, skipPlacement, type ProgressOverview } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

// Mobile: practice first, single column. lg+: dense multi-panel dashboard.
export default function HomePage() {
  const me = useRequireMe();
  const { state } = useAuth();
  const router = useRouter();
  const language = me?.acting.active_language;
  const [progress, setProgress] = useState<ProgressOverview | null>(null);
  const [failed, setFailed] = useState(false);

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

        <Panel title={cs.progression.title} icon={MapIcon} className={me.can_manage ? "" : "lg:col-span-3"}>
          <ProgressionPath />
        </Panel>

        {me.can_manage && (
          <Panel title={cs.dashboard.serverHealth} icon={Activity} className="lg:col-span-2">
            <ServerStatus />
          </Panel>
        )}
      </div>
    </AppShell>
  );
}
