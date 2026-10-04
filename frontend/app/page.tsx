"use client";

import { Activity, BarChart3, BookOpen, ClipboardCheck, Map as MapIcon, Play } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Panel } from "@/components/Panel";
import { ProgressCard } from "@/components/ProgressCard";
import { ProgressionPath } from "@/components/ProgressionPath";
import { ServerStatus } from "@/components/ServerStatus";
import { Button, Notice } from "@/components/ui";
import { getProgress, type ProgressOverview } from "@/lib/api";
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

  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;

  return (
    <AppShell me={me}>
      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title={cs.todayPractice} icon={BookOpen}>
          <div className="flex flex-col gap-3">
            <LanguagePicker me={me} />
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
