"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback } from "react";

import { AppShell, FullPageStatus } from "@/components/AppShell";
import { GrammarRunner } from "@/components/GrammarRunner";
import { startGrammarLesson } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

export default function GrammarLessonPage() {
  const me = useRequireMe();
  const router = useRouter();
  const { unit } = useParams<{ unit: string }>();
  const start = useCallback(() => startGrammarLesson(unit), [unit]);
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  return (
    <AppShell me={me}>
      <GrammarRunner
        key={`${me.acting.id}:${unit}`}
        language={me.acting.active_language}
        mode="learn"
        start={start}
        onExit={() => router.push("/grammar")}
        exitLabel={cs.grammar.toTree}
      />
    </AppShell>
  );
}
