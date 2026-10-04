"use client";

import { Award, Lock } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus } from "@/components/AppShell";
import { LessonRunner } from "@/components/LessonRunner";
import { Button, Notice } from "@/components/ui";
import { getLevels, type ExamLevel, type Language, type LevelStatus, type LevelsInfo } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const date = (iso: string) => new Date(iso).toLocaleDateString("cs-CZ");

function stateText(lv: LevelStatus, prev: ExamLevel | null): string {
  const t = cs.exam.states;
  switch (lv.state) {
    case "earned":
      return t.earned(date(lv.earned_at!));
    case "missing_words":
      return t.missing_words(lv.lexicon_items, lv.high);
    case "needs_previous":
      return t.needs_previous(prev ?? "");
    case "not_ready":
      return t.not_ready(lv.known, lv.ready_known);
    case "retry_later":
      return t.retry_later(date(lv.retry_from!));
    default:
      return t[lv.state];
  }
}

function Levels({ language, onStart }: { language: Language; onStart: (level: ExamLevel) => void }) {
  const router = useRouter();
  const [info, setInfo] = useState<LevelsInfo | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getLevels(language)
      .then((i) => !cancelled && setInfo(i))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language]);

  if (failed) return <Notice tone="error">{cs.common.offline}</Notice>;
  if (!info) return <p className="text-center text-slate-500">{cs.common.loading}</p>;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="flex items-center gap-2 text-xl font-bold">
        <Award className="size-6 text-brand-500" aria-hidden />
        {cs.exam.pageTitle} · {cs.languages[language]}
      </h1>
      <div className="flex flex-col gap-2 text-sm text-slate-700 dark:text-slate-200">
        <p>{cs.exam.intro(info.questions, info.pass_correct)}</p>
        <p>{cs.exam.rules}</p>
      </div>
      <Notice>{cs.exam.disclaimer}</Notice>
      <ol className="flex flex-col gap-2">
        {info.levels.map((lv, i) => {
          const earned = lv.state === "earned";
          const open = lv.state === "available" || lv.state === "in_progress";
          return (
            <li
              key={lv.level}
              className={`flex flex-col gap-2 rounded-2xl border p-4 ${
                earned
                  ? "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950"
                  : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
              }`}
            >
              <div className="flex items-baseline justify-between gap-2">
                <p className="flex items-center gap-2 text-lg font-bold">
                  {earned ? (
                    <Award className="size-5 text-emerald-600" aria-hidden />
                  ) : (
                    !open && <Lock className="size-4 text-slate-400" aria-hidden />
                  )}
                  {cs.exam.badgeName(lv.level)}
                </p>
                <span className="text-xs tabular-nums text-slate-500">{cs.exam.range(lv.low, lv.high)}</span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {stateText(lv, i > 0 ? info.levels[i - 1]!.level : null)}
              </p>
              {lv.last_correct !== null && lv.last_asked !== null && !earned && (
                <p className="text-xs text-slate-500">{cs.exam.last(lv.last_correct, lv.last_asked)}</p>
              )}
              {open && (
                <Button onClick={() => onStart(lv.level)}>
                  {lv.state === "in_progress" ? cs.exam.resume : cs.exam.start}
                </Button>
              )}
            </li>
          );
        })}
      </ol>
      <Button variant="secondary" onClick={() => router.push("/")}>
        {cs.lesson.toDashboard}
      </Button>
    </div>
  );
}

export default function LevelsPage() {
  const me = useRequireMe();
  const [level, setLevel] = useState<ExamLevel | null>(null);
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <div className="mx-auto w-full max-w-xl">
        {level ? (
          <LessonRunner
            key={`${me.acting.id}:${language}:exam:${level}`}
            language={language}
            mode="exam"
            level={level}
            onExit={() => setLevel(null)}
          />
        ) : (
          <Levels key={`${me.acting.id}:${language}`} language={language} onStart={setLevel} />
        )}
      </div>
    </AppShell>
  );
}
