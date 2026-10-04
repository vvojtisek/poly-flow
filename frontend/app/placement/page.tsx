"use client";

import { Compass } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AppShell, FullPageStatus } from "@/components/AppShell";
import { LessonRunner } from "@/components/LessonRunner";
import { Button, Notice } from "@/components/ui";
import { getPlacementInfo, skipPlacement, type Language, type PlacementInfo } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

function Intro({ language, onStart }: { language: Language; onStart: () => void }) {
  const router = useRouter();
  const [info, setInfo] = useState<PlacementInfo | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getPlacementInfo(language)
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

  async function skip() {
    setBusy(true);
    try {
      await skipPlacement(language);
      router.push("/");
    } catch {
      setFailed(true);
      setBusy(false);
    }
  }

  if (failed) return <Notice tone="error">{cs.common.offline}</Notice>;
  if (!info) return <p className="text-center text-slate-500">{cs.common.loading}</p>;
  const previous = info.placement?.status === "placed" ? info.placement.level : null;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="flex items-center gap-2 text-xl font-bold">
        <Compass className="size-6 text-brand-500" aria-hidden />
        {cs.placement.title} · {cs.languages[language]}
      </h1>
      <div className="flex flex-col gap-2 text-sm text-slate-700 dark:text-slate-200">
        <p>{cs.placement.intro(info.max_questions)}</p>
        <p>{cs.placement.noGuessing}</p>
        <p>{cs.placement.calm}</p>
        <p>{cs.placement.counts}</p>
      </div>
      <Notice>{cs.placement.coverage(info.ceiling)}</Notice>
      {previous !== null && <p className="text-sm text-slate-500">{cs.placement.previous(previous)}</p>}
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button className="flex-1 !py-4 text-lg" onClick={onStart} disabled={busy || info.ceiling === 0} autoFocus>
          {cs.placement.start}
        </Button>
        {info.placement === null ? (
          <Button variant="secondary" className="flex-1" onClick={() => void skip()} disabled={busy}>
            {cs.placement.skip}
          </Button>
        ) : (
          <Button variant="secondary" className="flex-1" onClick={() => router.push("/")}>
            {cs.placement.back}
          </Button>
        )}
      </div>
    </div>
  );
}

export default function PlacementPage() {
  const me = useRequireMe();
  const [started, setStarted] = useState(false);
  const start = useCallback(() => setStarted(true), []);
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <div className="mx-auto w-full max-w-xl">
        {started ? (
          <LessonRunner key={`${me.acting.id}:${language}:placement`} language={language} mode="placement" />
        ) : (
          <Intro key={`${me.acting.id}:${language}`} language={language} onStart={start} />
        )}
      </div>
    </AppShell>
  );
}
