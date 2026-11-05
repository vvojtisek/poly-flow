"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { AppShell, FullPageStatus } from "@/components/AppShell";
import { GrammarRunner } from "@/components/GrammarRunner";
import { startGrammarCheck } from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

export default function GrammarCheckPage() {
  const me = useRequireMe();
  const router = useRouter();
  const language = me?.acting.active_language;
  const start = useCallback(() => startGrammarCheck(language!), [language]);
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  return (
    <AppShell me={me}>
      <GrammarRunner
        key={`${me.acting.id}:${language}`}
        language={me.acting.active_language}
        mode="check"
        start={start}
        onExit={() => router.push("/grammar")}
        exitLabel={cs.grammar.toTree}
      />
    </AppShell>
  );
}
