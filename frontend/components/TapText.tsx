"use client";

import { X } from "lucide-react";
import { Fragment, useEffect, useLayoutEffect, useRef, useState } from "react";

import { PlayButton } from "@/components/PlayButton";
import { lookupWord, myWordAudioUrl, type Language, type LookupHit } from "@/lib/api";
import { genderClass } from "@/lib/gender";
import { cs } from "@/lib/i18n/cs";

// A word: letters with inner apostrophes or hyphens (l'homme, well-known, dell’acqua).
const WORD = /\p{L}+(?:['’-]\p{L}+)*/gu;

type Part = { text: string; word: boolean };

export function splitWords(text: string): Part[] {
  const out: Part[] = [];
  let last = 0;
  for (const m of text.matchAll(WORD)) {
    if (m.index > last) out.push({ text: text.slice(last, m.index), word: false });
    out.push({ text: m[0], word: true });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last), word: false });
  return out;
}

// One cache per page load: the same word in a story is looked up once.
const cache = new Map<string, Promise<LookupHit[]>>();
function find(word: string, language: Language) {
  const key = `${language}:${word.toLowerCase()}`;
  let hit = cache.get(key);
  if (!hit) {
    hit = lookupWord(word, language);
    hit.catch(() => cache.delete(key));
    cache.set(key, hit);
  }
  return hit;
}

function Card({ word, language, onClose }: { word: string; language: Language; onClose: () => void }) {
  const [hits, setHits] = useState<LookupHit[] | null>(null);
  const [failed, setFailed] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    let cancelled = false;
    find(word, language)
      .then((h) => !cancelled && setHits(h))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [word, language]);

  // Keep the card inside the viewport near the right edge.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const over = el.getBoundingClientRect().right - (window.innerWidth - 8);
    if (over > 0) el.style.left = `-${over}px`;
  }, [hits]);

  useEffect(() => {
    function away(e: PointerEvent) {
      if (ref.current && !ref.current.parentElement?.contains(e.target as Node)) onClose();
    }
    function key(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("pointerdown", away);
      document.removeEventListener("keydown", key);
    };
  }, [onClose]);

  return (
    <span
      ref={ref}
      role="dialog"
      aria-label={cs.lookup.form(word)}
      className="absolute left-0 top-full z-20 mt-1 flex w-64 text-slate-900 dark:text-slate-100 max-w-[80vw] flex-col gap-2 rounded-xl border border-slate-200 bg-white p-3 text-left text-sm font-normal shadow-xl motion-safe:animate-pop-in dark:border-slate-700 dark:bg-slate-900"
    >
      <span className="flex items-start justify-between gap-2">
        <span className="text-xs text-slate-500">{cs.lookup.form(word)}</span>
        <button type="button" onClick={onClose} aria-label={cs.lookup.close} className="text-slate-400 hover:text-slate-600">
          <X className="size-4" aria-hidden />
        </button>
      </span>
      {failed ? (
        <span className="text-rose-600">{cs.lookup.failed}</span>
      ) : !hits ? (
        <span className="text-slate-500">{cs.lookup.loading}</span>
      ) : hits.length === 0 ? (
        <span className="text-slate-500">{cs.lookup.none}</span>
      ) : (
        hits.map((h) => (
          <span key={h.id} className="flex flex-col gap-0.5 border-t border-slate-100 pt-2 first:border-0 first:pt-0 dark:border-slate-800">
            <span className="flex items-center gap-2">
              <span lang={language} className={`text-base font-bold ${genderClass(h.gender)}`}>
                {h.gender && language === "de" && h.pos === "NOUN" ? `${h.gender} ` : ""}
                {h.lemma}
              </span>
              {h.status && <PlayButton url={myWordAudioUrl(h.id)} label={cs.audio.playWord} size="sm" />}
            </span>
            <span lang="cs">{h.translation}</span>
            <span className={`self-start rounded-full px-2 py-0.5 text-xs ${h.status ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" : "bg-brand-500/10 text-brand-600 dark:text-brand-50"}`}>
              {h.status ? cs.words.status[h.status] : cs.lookup.fresh}
            </span>
            {h.note && <span className="text-xs italic text-slate-600 dark:text-slate-300">{h.note}</span>}
          </span>
        ))
      )}
    </span>
  );
}

/** Text in the target language whose every word can be tapped for its dictionary entry. */
export function TapText({ text, language }: { text: string; language: Language }) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <>
      {splitWords(text).map((p, i) =>
        p.word ? (
          <span key={i} className="relative inline-block">
            <button
              type="button"
              lang={language}
              aria-expanded={open === i}
              onClick={() => setOpen((o) => (o === i ? null : i))}
              className={`rounded px-px hover:bg-brand-500/10 focus-visible:bg-brand-500/10 ${open === i ? "bg-brand-500/15" : ""}`}
            >
              {p.text}
            </button>
            {open === i && <Card word={p.text} language={language} onClose={() => setOpen(null)} />}
          </span>
        ) : (
          <Fragment key={i}>{p.text}</Fragment>
        ),
      )}
    </>
  );
}
