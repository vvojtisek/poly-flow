"use client";

import { AudioLines, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { PlayButton } from "@/components/PlayButton";
import { Notice } from "@/components/ui";
import { getSounds, myWordAudioUrl, type Language, type SoundExample, type SoundRule } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { fold } from "@/lib/palette";

const t = cs.sounds;

function Example({ ex, language }: { ex: SoundExample; language: Language }) {
  return (
    <li className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-800/60">
      <span className="flex min-w-0 flex-col">
        <span lang={language} className="text-lg">
          {ex.lemma.slice(0, ex.start)}
          <mark className="rounded bg-brand-500/20 px-0.5 font-bold text-brand-600 dark:text-brand-50">{ex.lemma.slice(ex.start, ex.end)}</mark>
          {ex.lemma.slice(ex.end)}
        </span>
        <span className="truncate text-xs text-slate-500">
          {ex.translation}
          {ex.met && <span className="ml-1 text-emerald-600"> · {t.known}</span>}
        </span>
      </span>
      {ex.met && (
        <span className="ml-auto">
          <PlayButton url={myWordAudioUrl(ex.id)} label={cs.audio.playWord} size="sm" />
        </span>
      )}
    </li>
  );
}

function Rule({ rule, language }: { rule: SoundRule; language: Language }) {
  return (
    <article className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 lang={language} className="text-2xl font-bold">
          {rule.spelling}
        </h2>
        <span className="text-sm text-slate-500">{t.sounds}</span>
        <span className="rounded-lg bg-brand-500/10 px-2 py-0.5 font-semibold text-brand-600 dark:text-brand-50">{rule.czech}</span>
      </header>
      <p className="text-sm text-slate-700 dark:text-slate-200">{rule.note}</p>
      {rule.examples.length ? (
        <ul className="grid gap-2 sm:grid-cols-2">
          {rule.examples.map((ex) => (
            <Example key={ex.id} ex={ex} language={language} />
          ))}
        </ul>
      ) : (
        <p className="text-xs text-slate-500">{t.noExamples}</p>
      )}
    </article>
  );
}

function Guide({ language }: { language: Language }) {
  const [rules, setRules] = useState<SoundRule[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [q, setQ] = useState("");

  useEffect(() => {
    let cancelled = false;
    getSounds(language)
      .then((r) => !cancelled && setRules(r))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [language]);

  const shown = useMemo(() => {
    const f = fold(q.trim());
    if (!rules || !f) return rules;
    return rules.filter((r) => fold(r.spelling).includes(f) || fold(r.czech).includes(f) || r.examples.some((e) => fold(e.lemma).includes(f)));
  }, [rules, q]);

  if (failed) return <Notice tone="error">{cs.common.error}</Notice>;
  if (!shown) return <p className="text-sm text-slate-500">{cs.common.loading}</p>;
  return (
    <div className="flex flex-col gap-4">
      <label className="flex max-w-md items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900">
        <Search className="size-4 text-slate-400" aria-hidden />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.search} aria-label={t.search} className="min-w-0 flex-1 bg-transparent outline-none" />
      </label>
      <div className="grid gap-4 lg:grid-cols-2">
        {shown.map((r) => (
          <Rule key={r.id} rule={r} language={language} />
        ))}
      </div>
    </div>
  );
}

export default function SoundsPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const language = me.acting.active_language;
  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-2">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <AudioLines className="size-6 text-brand-500" aria-hidden /> {t.title}
        </h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />
        <Notice>{t.unreviewed}</Notice>
      </div>
      <Guide key={language} language={language} />
    </AppShell>
  );
}
