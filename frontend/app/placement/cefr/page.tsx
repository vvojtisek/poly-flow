"use client";

import { Compass } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { DiagnosticRunner } from "@/components/DiagnosticRunner";
import { Button, Notice } from "@/components/ui";
import { getDiagnosticInfo, type DiagnosticInfo, type Language, type Me } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

function Intro({ me, language, onStart }: { me: Me; language: Language; onStart: () => void }) {
  const router = useRouter();
  const [info, setInfo] = useState<DiagnosticInfo | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getDiagnosticInfo(language)
      .then((i) => {
        if (cancelled) return;
        if (i.active_session_id) onStart(); // an unfinished test continues where it stopped
        else setInfo(i);
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language, onStart]);

  if (failed) return <Notice tone="error">{cs.common.offline}</Notice>;
  if (!info) return <p className="text-center text-slate-500">{cs.common.loading}</p>;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="flex items-center gap-2 text-xl font-bold">
        <Compass className="size-6 text-brand-500" aria-hidden />
        {cs.cefr.title}
      </h1>
      <div className="flex flex-col gap-1">
        <p className="text-xs text-slate-500">{cs.placement.pickLanguage}</p>
        <LanguagePicker me={me} />
      </div>
      {info.available ? (
        <>
          <div className="flex flex-col gap-2 text-sm text-slate-700 dark:text-slate-200">
            <p>{cs.cefr.intro(info.min_items, info.max_items)}</p>
            <p>{cs.cefr.noGuessing}</p>
            <p>{cs.cefr.calm}</p>
            <p>{cs.cefr.unlocks}</p>
          </div>
          <p className="text-xs text-slate-500">{cs.cefr.honest}</p>
          {info.latest && <p className="text-sm text-slate-500">{cs.cefr.previous(info.latest.level)}</p>}
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button className="flex-1 !py-4 text-lg" onClick={onStart} autoFocus>
              {cs.cefr.start}
            </Button>
            <Button variant="secondary" className="flex-1" onClick={() => router.push("/")}>
              {cs.placement.back}
            </Button>
          </div>
          <Link href="/placement/vocabulary" className="text-center text-sm font-medium text-brand-700 underline-offset-2 hover:underline dark:text-brand-200">
            {cs.cefr.vocabularyTest}
          </Link>
        </>
      ) : (
        <Notice>{cs.cefr.unavailable}</Notice>
      )}
    </div>
  );
}

export default function CefrPlacementPage() {
  const me = useRequireMe();
  const [run, setRun] = useState(0); // 0 = intro; each start or retake mounts a fresh runner
  const start = useCallback(() => setRun(1), []);
  const again = useCallback(() => setRun((n) => n + 1), []);
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <div className="mx-auto w-full max-w-xl">
        {run > 0 ? (
          <DiagnosticRunner key={`${me.acting.id}:${language}:${run}`} language={language} englishVariant={me.acting.settings.english_variant} onAgain={again} />
        ) : (
          <Intro key={`${me.acting.id}:${language}`} me={me} language={language} onStart={start} />
        )}
      </div>
    </AppShell>
  );
}
