"use client";

import { CheckCircle2, CircleDashed, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { NoteEditor } from "@/components/NoteEditor";
import { getSessionReview, type Language, type ReviewItem } from "@/lib/api";
import { genderClass } from "@/lib/gender";
import { cs } from "@/lib/i18n/cs";

const t = cs.review;

function when(iso: string | null): string | null {
  if (!iso) return null;
  const days = Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000);
  if (days <= 0) return t.today;
  if (days === 1) return t.tomorrow;
  return t.inDays(days);
}

function Word({ item, language }: { item: ReviewItem; language: Language }) {
  const article = language === "de" && item.gender && item.gender.length > 1 ? `${item.gender} ` : "";
  return (
    <span lang={language} className={`font-semibold ${genderClass(item.gender)}`}>
      {article}
      {item.lemma}
    </span>
  );
}

function stateOf(i: ReviewItem) {
  return i.active_known ? "active" : i.passive_known ? "passive" : "none";
}

/** Word-by-word rozbor of a finished session; mistakes first, each with room for a memory hook. */
export function SessionReview({ sessionId, language }: { sessionId: string; language: Language }) {
  const [items, setItems] = useState<ReviewItem[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    getSessionReview(sessionId)
      .then((r) => !cancelled && setItems(r.items))
      .catch(() => !cancelled && setItems([]));
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  if (!items || items.length === 0) return null;
  // One row per word: a lesson asks for a word twice (recognise, then write).
  const byWord = new Map<string, ReviewItem>();
  for (const i of items) {
    const prev = byWord.get(i.item_id);
    if (!prev || (prev.first_try !== false && i.first_try === false)) byWord.set(i.item_id, i);
  }
  const words = [...byWord.values()];
  const missed = words.filter((i) => i.first_try === false);
  const right = words.filter((i) => i.first_try === true);
  const skipped = words.filter((i) => i.first_try === null);

  return (
    <section className="flex flex-col gap-3" aria-label={t.title}>
      <h3 className="font-semibold">{t.title}</h3>
      {missed.length === 0 && right.length > 0 && (
        <p className="flex items-center gap-2 rounded-xl bg-emerald-50 p-3 text-sm font-semibold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-100">
          <CheckCircle2 className="size-5" aria-hidden /> {t.allRight}
        </p>
      )}
      {missed.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="flex items-center gap-1 text-sm font-semibold text-rose-700 dark:text-rose-300">
            <XCircle className="size-4" aria-hidden /> {t.missed} ({missed.length})
          </h4>
          <ul className="flex flex-col gap-2">
            {missed.map((i) => (
              <li key={i.item_id} className="flex flex-col gap-2 rounded-xl border border-rose-200 p-3 text-sm dark:border-rose-900">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span>
                    <Word item={i} language={language} /> <span className="text-slate-500">= {i.translation}</span>
                  </span>
                  {when(i.next_review_at) && <span className="text-xs text-slate-500">{t.next(when(i.next_review_at)!)}</span>}
                </div>
                <p className="text-slate-600 dark:text-slate-300">
                  {t.youAnswered}{" "}
                  {i.answered ? <span className="text-rose-700 line-through decoration-rose-400 dark:text-rose-300">{i.answered}</span> : <em>{t.revealed}</em>}{" "}
                  · {t.correct} <strong>{i.expected}</strong>
                  {i.error && <span className="text-xs text-slate-500"> ({cs.feedback.errors[i.error] ?? i.error})</span>}
                </p>
                {!i.note && <p className="text-xs text-slate-500">{t.hookHint}</p>}
                <NoteEditor itemId={i.item_id} initial={i.note} compact />
              </li>
            ))}
          </ul>
        </div>
      )}
      {right.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="flex items-center gap-1 text-sm font-semibold text-emerald-700 dark:text-emerald-300">
            <CheckCircle2 className="size-4" aria-hidden /> {t.right} ({right.length})
          </h4>
          <ul className="flex flex-wrap gap-1.5">
            {right.map((i) => (
              <li key={i.item_id} className="rounded-full bg-emerald-50 px-3 py-1 text-sm dark:bg-emerald-950/50" title={`${i.translation} · ${t.state[stateOf(i)]}`}>
                <Word item={i} language={language} />
                <span className="ml-1 text-xs text-slate-500">{t.state[stateOf(i)]}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {skipped.length > 0 && (
        <p className="flex items-center gap-1 text-xs text-slate-500">
          <CircleDashed className="size-4" aria-hidden /> {t.skipped}: {skipped.map((i) => i.lemma).join(", ")}
        </p>
      )}
    </section>
  );
}
