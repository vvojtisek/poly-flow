"use client";

import { Repeat, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import { AnswerInput } from "@/components/AnswerInput";
import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Panel } from "@/components/Panel";
import { Button, Notice } from "@/components/ui";
import { getVerbs, type VerbEntry, type VerbPerson } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { fold } from "@/lib/palette";

const t = cs.verbs;
const PERSONS: VerbPerson[] = ["ich", "du", "er", "wir", "ihr", "sie"];

function full(v: VerbEntry, p: VerbPerson) {
  const f = v.forms[p];
  return `${f.stem}${f.ending}${v.prefix ? ` ${v.prefix}` : ""}`;
}

function Table({ verb }: { verb: VerbEntry }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 lang="de" className="text-3xl font-bold">
          {verb.lemma}
        </h2>
        <span className="text-slate-500">{verb.translation}</span>
      </div>
      <table className="w-full border-separate border-spacing-y-1 text-lg" lang="de">
        <tbody>
          {PERSONS.map((p) => {
            const f = verb.forms[p];
            return (
              <tr key={p} className="motion-safe:animate-pop-in">
                <th scope="row" className="w-28 pr-3 text-left text-sm font-medium text-slate-500">
                  {t.pronoun[p]}
                </th>
                <td className="rounded-lg bg-slate-50 px-3 py-1.5 dark:bg-slate-800/60">
                  <span className={f.changed ? "rounded bg-amber-200/70 px-0.5 font-semibold dark:bg-amber-500/40" : ""}>{f.stem}</span>
                  <span className="font-bold text-brand-600 dark:text-brand-50">{f.ending}</span>
                  {verb.prefix && (
                    <span className="text-violet-700 dark:text-violet-300">
                      {" "}
                      … {verb.prefix}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <ul className="flex flex-col gap-1 text-sm text-slate-700 dark:text-slate-200">
        {verb.features.length === 0 && <li>{t.regular}</li>}
        {verb.features.map((f) => (
          <li key={f} className="flex gap-2">
            <span
              className={`mt-1.5 inline-block size-2 shrink-0 rounded-full ${
                f === "vowel_change" || f === "irregular" ? "bg-amber-500" : f === "separable" ? "bg-violet-500" : "bg-brand-500"
              }`}
              aria-hidden
            />
            {t.feature[f]}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Drill({ verbs }: { verbs: VerbEntry[] }) {
  const pool = useMemo(() => {
    const met = verbs.filter((v) => v.met);
    return met.length >= 5 ? met : verbs;
  }, [verbs]);
  const pick = () => ({
    verb: pool[Math.floor(Math.random() * pool.length)]!,
    person: PERSONS[Math.floor(Math.random() * PERSONS.length)]!,
  });
  const [q, setQ] = useState(pick);
  const [text, setText] = useState("");
  const [result, setResult] = useState<boolean | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const answer = full(q.verb, q.person);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (result !== null) {
      setQ(pick());
      setText("");
      setResult(null);
      requestAnimationFrame(() => input.current?.focus());
      return;
    }
    if (!text.trim()) return;
    setResult(text.trim().replace(/\s+/g, " ") === answer);
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <p className="text-sm text-slate-500">{t.practiceHelp}</p>
      <p className="text-center text-2xl" lang="de">
        <span className="text-slate-500">{t.pronoun[q.person]}</span> · <strong>{q.verb.lemma}</strong>{" "}
        <span className="text-base text-slate-500">({q.verb.translation})</span>
      </p>
      <AnswerInput ref={input} language="de" value={text} onChange={setText} disabled={result !== null} />
      {result !== null && (
        <p className={`text-center font-semibold ${result ? "text-emerald-600" : "text-rose-600"}`} aria-live="polite">
          {result ? t.right : t.wrong(answer)}
        </p>
      )}
      <Button type="submit" disabled={result === null && !text.trim()}>
        {result === null ? t.check : t.next}
      </Button>
    </form>
  );
}

function Lab({ verbs }: { verbs: VerbEntry[] }) {
  const [query, setQuery] = useState("");
  const [chosen, setChosen] = useState(verbs[0]?.lemma ?? "");
  const shown = useMemo(() => {
    const f = fold(query.trim());
    return f ? verbs.filter((v) => fold(v.lemma).includes(f) || fold(v.translation).includes(f)) : verbs;
  }, [verbs, query]);
  const verb = verbs.find((v) => v.lemma === chosen) ?? verbs[0];
  if (!verb) return <Notice>{t.empty}</Notice>;

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <section className="flex flex-col gap-2">
        <label className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900">
          <Search className="size-4 text-slate-400" aria-hidden />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.search}
            aria-label={t.search}
            className="min-w-0 flex-1 bg-transparent outline-none"
          />
        </label>
        <ul className="flex max-h-[28rem] flex-col overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-800" role="listbox" aria-label={t.title}>
          {shown.length === 0 && <li className="p-3 text-sm text-slate-500">{t.empty}</li>}
          {shown.map((v) => (
            <li key={v.lemma} role="option" aria-selected={v.lemma === verb.lemma}>
              <button
                type="button"
                onClick={() => setChosen(v.lemma)}
                className={`flex w-full items-baseline justify-between gap-2 px-3 py-2 text-left ${
                  v.lemma === verb.lemma ? "bg-brand-500/10" : "hover:bg-slate-50 dark:hover:bg-slate-800/60"
                }`}
              >
                <span lang="de" className="font-medium">
                  {v.lemma}
                  {v.met && <span className="ml-1 text-xs text-emerald-600" title={t.met}>✓</span>}
                </span>
                <span className="truncate text-xs text-slate-500">{v.translation}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>
      <Panel title={t.table} icon={Repeat} className="lg:col-span-2">
        <Table key={verb.lemma} verb={verb} />
      </Panel>
      <Panel title={t.practice} icon={Repeat} className="lg:col-span-3">
        <Drill verbs={verbs} />
      </Panel>
    </div>
  );
}

export default function VerbsPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  const [verbs, setVerbs] = useState<VerbEntry[] | null>(null);
  const [failed, setFailed] = useState(false);
  const german = me?.acting.active_language === "de";

  useEffect(() => {
    if (!german) return;
    let cancelled = false;
    getVerbs()
      .then((v) => !cancelled && setVerbs(v))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [german, me?.acting.id]);

  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  return (
    <AppShell me={me}>
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold">{t.title}</h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-300">{t.intro}</p>
      </div>
      {!german ? (
        <div className="flex flex-col gap-3">
          <Notice>{t.onlyGerman}</Notice>
          <LanguagePicker me={me} />
        </div>
      ) : failed ? (
        <Notice tone="error">{cs.common.error}</Notice>
      ) : verbs ? (
        <Lab verbs={verbs} />
      ) : (
        <p className="text-sm text-slate-500">{cs.common.loading}</p>
      )}
    </AppShell>
  );
}
