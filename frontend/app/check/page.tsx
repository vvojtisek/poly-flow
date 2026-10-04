"use client";

import { AppShell, FullPageStatus } from "@/components/AppShell";
import { LessonRunner } from "@/components/LessonRunner";
import { useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

export default function CheckPage() {
  const me = useRequireMe();
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  return (
    <AppShell me={me}>
      <div className="mx-auto w-full max-w-xl">
        <LessonRunner
          key={`${me.acting.id}:${me.acting.active_language}:check`}
          language={me.acting.active_language}
          mode="check"
        />
      </div>
    </AppShell>
  );
}
