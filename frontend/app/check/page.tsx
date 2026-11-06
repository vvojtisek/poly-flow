"use client";

import { AppShell, FullPageStatus } from "@/components/AppShell";
import { LessonRunner } from "@/components/LessonRunner";
import { updateOwnProfile } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { useEffect, useState } from "react";

export default function CheckPage() {
  const me = useRequireMe();
  const { setMe } = useAuth();
  const [autoplayAudio, setAutoplayAudio] = useState(me?.acting.settings.autoplay_audio ?? true);
  useEffect(() => {
    if (me) setAutoplayAudio(me.acting.settings.autoplay_audio);
  }, [me?.acting.id, me?.acting.settings.autoplay_audio]);
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const currentMe = me;
  async function changeAutoplayAudio(enabled: boolean) {
    const previous = autoplayAudio;
    setAutoplayAudio(enabled);
    try {
      const acting = await updateOwnProfile({ settings: { autoplay_audio: enabled } });
      setMe({ ...currentMe, acting, principal: currentMe.principal.id === acting.id ? acting : currentMe.principal });
    } catch {
      setAutoplayAudio(previous);
    }
  }
  return (
    <AppShell me={me} focusable>
      <div className="mx-auto w-full max-w-xl">
        <LessonRunner
          key={`${me.acting.id}:${me.acting.active_language}:check`}
          language={me.acting.active_language}
          mode="check"
          autoplayAudio={autoplayAudio}
          englishVariant={me.acting.settings.english_variant}
          onAutoplayAudioChange={(enabled) => void changeAutoplayAudio(enabled)}
        />
      </div>
    </AppShell>
  );
}
