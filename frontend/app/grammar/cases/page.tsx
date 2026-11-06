"use client";

import { FlaskConical, Shuffle, Table2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { Kbd } from "@/components/Kbd";
import { Panel } from "@/components/Panel";
import { Notice } from "@/components/ui";
import {
  getDeclension,
  type DeclAdjective,
  type DeclCase,
  type DeclCell,
  type DeclDet,
  type DeclGender,
  type DeclNoun,
  type Declension,
} from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { useHotkeys } from "@/lib/keyboard";

const t = cs.cases;
const CASES: DeclCase[] = ["nom", "akk", "dat", "gen"];
const GENDERS: DeclGender[] = ["m", "f", "n", "pl"];
const DETS: DeclDet[] = ["def", "indef", "kein", "poss", "none"];
const GENDER_TEXT: Record<DeclGender, string> = {
  m: "text-sky-700 dark:text-sky-300",
  f: "text-rose-700 dark:text-rose-300",
  n: "text-emerald-700 dark:text-emerald-300",
  pl: "text-violet-700 dark:text-violet-300",
};
const SIGNAL = "rounded bg-amber-300/70 px-0.5 font-bold text-slate-900 dark:bg-amber-400/80";
const QUIET = "text-slate-500 dark:text-slate-400";

function Ending({ text, signal }: { text: string; signal: boolean }) {
  if (!text) return null;
  return <span className={signal ? SIGNAL : QUIET}>{text}</span>;
}

function cellKey(det: DeclDet, c: DeclCase, g: DeclGender) {
  return `${det}:${c}:${g}`;
}

/** The phrase, word by word: stems plain, endings coloured by whether they carry the case signal. */
function PhraseView({ cell, noun, adjective, plural }: { cell: DeclCell; noun: DeclNoun; adjective: DeclAdjective | null; plural: boolean }) {
  const forms = plural ? noun.plural : noun.singular;
  const nounPiece = forms?.[cell.case];
  if (!nounPiece) return null;
  return (
    <p lang="de" className="flex flex-wrap items-baseline justify-center gap-x-3 text-4xl font-semibold motion-safe:animate-pop-in lg:text-5xl">
      {cell.determiner && (
        <span className={GENDER_TEXT[cell.gender]}>
          {cell.determiner.stem}
          <Ending text={cell.determiner.ending} signal={cell.signal === "determiner"} />
        </span>
      )}
      {adjective && (
        <span>
          {adjective.stem ?? adjective.lemma}
          {adjective.stem !== null && <Ending text={cell.adjective_ending} signal={cell.signal === "adjective"} />}
        </span>
      )}
      <span className={GENDER_TEXT[cell.gender]}>
        {nounPiece.stem}
        <Ending text={nounPiece.ending} signal={cell.signal === "noun"} />
      </span>
    </p>
  );
}

function explain(cell: DeclCell, adjective: DeclAdjective | null): string {
  if (!adjective || adjective.stem === null) {
    if (cell.signal === "noun") return t.signal.noun();
    return t.signal.bare(cell.determiner?.ending ?? "");
  }
  if (cell.signal === "determiner") return t.signal.determiner(cell.determiner?.ending ?? "");
  if (cell.signal === "noun") return t.signal.noun();
  return t.signal.adjective(cell.adjective_ending);
}

function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
  render,
  hotkeys = false,
}: {
  options: T[];
  value: T;
  onChange: (v: T) => void;
  label: string;
  render: (v: T) => ReactNode;
  hotkeys?: boolean;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-1">
      {options.map((o, i) => (
        <button
          key={o}
          type="button"
          role="radio"
          aria-checked={value === o}
          data-hotkey={hotkeys ? String(i + 1) : undefined}
          onClick={() => onChange(o)}
          className={`rounded-lg px-3 py-1.5 text-sm font-semibold ${
            value === o ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          }`}
        >
          {render(o)}
        </button>
      ))}
    </div>
  );
}

function Lab({ data }: { data: Declension }) {
  const cells = useMemo(() => new Map(data.cells.map((c) => [cellKey(c.det, c.case, c.gender), c])), [data]);
  const [det, setDet] = useState<DeclDet>("def");
  const [kase, setKase] = useState<DeclCase>("nom");
  const [plural, setPlural] = useState(false);
  const [nounLemma, setNounLemma] = useState(() => data.nouns.find((n) => n.singular)?.lemma ?? data.nouns[0]?.lemma ?? "");
  const [adjLemma, setAdjLemma] = useState<string>(() => data.adjectives.find((a) => a.stem)?.lemma ?? "");
  useHotkeys();

  const noun = data.nouns.find((n) => n.lemma === nounLemma) ?? data.nouns[0];
  const adjective = data.adjectives.find((a) => a.lemma === adjLemma) ?? null;
  const pluralOnly = noun?.gender === "pl";
  const isPlural = pluralOnly || plural;
  const gender: DeclGender = isPlural ? "pl" : (noun?.gender ?? "m");

  const randomNoun = useCallback(
    (want?: DeclGender) => {
      const pool = data.nouns.filter((n) =>
        want === "pl" ? !!n.plural : want ? n.gender === want : isPlural ? !!n.plural : !!n.singular,
      );
      if (!pool.length) return;
      const pick = pool[Math.floor(Math.random() * pool.length)]!;
      setNounLemma(pick.lemma);
      if (want) setPlural(want === "pl");
    },
    [data.nouns, isPlural],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement | null;
      if (e.ctrlKey || e.metaKey || e.altKey || el?.closest("input, select, textarea")) return;
      if (e.code === "KeyR") {
        e.preventDefault();
        randomNoun();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [randomNoun]);

  if (!noun) return <Notice>{cs.common.error}</Notice>;
  const cell = cells.get(cellKey(det, kase, gender))!;
  const nounForms = isPlural ? noun.plural : noun.singular;
  const nounEnding = nounForms?.[kase]?.ending ?? "";

  return (
    <div className="grid gap-4 lg:grid-cols-5">
      <Panel title={t.title} icon={FlaskConical} className="lg:col-span-3">
        <div className="flex flex-col gap-4">
          <div className="flex min-h-36 flex-col items-center justify-center gap-2 rounded-2xl bg-gradient-to-br from-brand-500/10 to-amber-300/10 p-6 text-center">
            {nounForms ? (
              <PhraseView key={`${det}${kase}${gender}${noun.lemma}${adjLemma}`} cell={cell} noun={noun} adjective={adjective} plural={isPlural} />
            ) : (
              <p className="text-sm text-slate-500">{t.noPlural}</p>
            )}
            <p className="text-sm text-slate-500">
              {t.case[kase]} · {t.gender[gender]} · {t.kind[cell.kind]}
            </p>
          </div>
          <div className="flex flex-col gap-1 text-sm text-slate-700 dark:text-slate-200" aria-live="polite">
            <p>{explain(cell, adjective)}</p>
            {nounEnding && cell.signal !== "noun" && <p>{t.nounEnding(nounEnding)}</p>}
            {noun.n_declension && !isPlural && <p className="text-amber-700 dark:text-amber-300">{t.nDecl}</p>}
            {pluralOnly && <p className="text-slate-500">{t.pluralOnly}</p>}
          </div>

          <div className="flex flex-col gap-1">
            <Segmented options={CASES} value={kase} onChange={setKase} label={t.case.nom!} hotkeys render={(c) => t.case[c]} />
            <p className="text-xs text-slate-500">{t.caseHint[kase]}</p>
          </div>
          <Segmented options={DETS} value={det} onChange={setDet} label={t.det.def!} render={(d) => t.det[d]} />
          {!pluralOnly && (
            <Segmented
              options={["sg", "pl"] as ("sg" | "pl")[]}
              value={plural ? "pl" : "sg"}
              onChange={(v) => setPlural(v === "pl")}
              label={t.plural}
              render={(v) => (v === "pl" ? t.plural : t.singular)}
            />
          )}
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-slate-600 dark:text-slate-300">{t.adjective}</span>
              <select
                value={adjLemma}
                onChange={(e) => setAdjLemma(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
              >
                <option value="">{t.noAdjective}</option>
                {data.adjectives.map((a) => (
                  <option key={a.lemma} value={a.lemma}>
                    {a.lemma} ({a.translation}){a.met ? " ✓" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-slate-600 dark:text-slate-300">{t.noun}</span>
              <span className="flex gap-1">
                <select
                  value={noun.lemma}
                  onChange={(e) => setNounLemma(e.target.value)}
                  className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
                >
                  {data.nouns.map((n) => (
                    <option key={n.lemma} value={n.lemma}>
                      {n.lemma} ({n.translation}){n.met ? " ✓" : ""}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => randomNoun()}
                  aria-label={t.random}
                  title={t.random}
                  className="rounded-lg bg-slate-100 px-3 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700"
                >
                  <Shuffle className="size-4" aria-hidden />
                </button>
              </span>
            </label>
          </div>
          <p className="hidden text-xs text-slate-500 lg:block">
            <Kbd>1</Kbd>–<Kbd>4</Kbd> {t.keyCases} · <Kbd>R</Kbd> {t.random.toLowerCase()} · ✓ {t.met}
          </p>
        </div>
      </Panel>

      <Panel title={`${t.table}: ${t.det[det]}`} icon={Table2} className="lg:col-span-2">
        <div className="flex flex-col gap-3">
          <table className="w-full table-fixed border-separate border-spacing-1 text-sm" lang="de">
            <thead>
              <tr>
                <th className="w-20" />
                {GENDERS.map((g) => (
                  <th key={g} scope="col" className={`text-xs font-semibold ${GENDER_TEXT[g]}`}>
                    {t.gender[g]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {CASES.map((c) => (
                <tr key={c}>
                  <th scope="row" className="text-left text-xs font-semibold text-slate-600 dark:text-slate-300">
                    {t.case[c]}
                  </th>
                  {GENDERS.map((g) => {
                    const x = cells.get(cellKey(det, c, g))!;
                    const active = c === kase && g === gender;
                    return (
                      <td key={g} className="p-0">
                        <button
                          type="button"
                          aria-pressed={active}
                          onClick={() => {
                            setKase(c);
                            if (g !== gender) randomNoun(g);
                          }}
                          className={`flex w-full flex-col items-center rounded-lg px-1 py-2 leading-tight ${
                            active ? "bg-brand-500/15 ring-2 ring-brand-500" : "bg-slate-50 hover:bg-slate-100 dark:bg-slate-800/60 dark:hover:bg-slate-800"
                          }`}
                        >
                          <span className={GENDER_TEXT[g]}>
                            {x.determiner ? (
                              <>
                                {x.determiner.stem}
                                <Ending text={x.determiner.ending} signal={x.signal === "determiner"} />
                              </>
                            ) : (
                              "–"
                            )}
                          </span>
                          <span className="text-xs">
                            …<Ending text={x.adjective_ending} signal={x.signal === "adjective"} />
                          </span>
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-slate-500">{t.tableHelp}</p>
          <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100">{t.rule}</p>
        </div>
      </Panel>
    </div>
  );
}

export default function CasesPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  const [data, setData] = useState<Declension | null>(null);
  const [failed, setFailed] = useState(false);
  const german = me?.acting.active_language === "de";

  useEffect(() => {
    if (!german) return;
    let cancelled = false;
    getDeclension()
      .then((d) => !cancelled && setData(d))
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
        <p className="text-slate-600 dark:text-slate-300">{t.intro}</p>
      </div>
      {!german ? (
        <div className="flex flex-col gap-3">
          <Notice>{t.onlyGerman}</Notice>
          <LanguagePicker me={me} />
        </div>
      ) : failed ? (
        <Notice tone="error">{cs.common.error}</Notice>
      ) : data ? (
        <Lab data={data} />
      ) : (
        <p className="text-sm text-slate-500">{cs.common.loading}</p>
      )}
    </AppShell>
  );
}
