"use client";

import type { DictationResult, DictationVerdict } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const t = cs.dictation;

const VERDICT_STYLE: Record<DictationVerdict, string> = {
  ok: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100",
  case: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-100",
  accents: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-100",
  wrong: "bg-rose-100 text-rose-900 dark:bg-rose-950 dark:text-rose-100",
  extra: "bg-rose-100 text-rose-900 line-through decoration-rose-500 dark:bg-rose-950 dark:text-rose-100",
  missing: "border border-dashed border-slate-400 text-slate-500 dark:border-slate-600",
};

/** The learner's sentence, word by word, with what was expected under every miss. */
export function WordDiff({ marks }: { marks: DictationResult["marks"] }) {
  return (
    <div className="flex flex-col gap-3">
      <ol className="flex flex-wrap gap-1.5" aria-label={t.title}>
        {marks.map((m, i) => (
          <li
            key={i}
            className={`flex flex-col items-center rounded-lg px-2 py-1 text-lg motion-safe:animate-pop-in ${VERDICT_STYLE[m.verdict]}`}
            style={{ animationDelay: `${i * 30}ms` }}
            title={t.legend[m.verdict]}
          >
            <span>{m.verdict === "missing" ? m.expected : m.typed}</span>
            {m.verdict !== "ok" && m.verdict !== "missing" && m.verdict !== "extra" && (
              <span className="text-xs font-semibold opacity-80">{m.expected}</span>
            )}
            <span className="sr-only">{t.legend[m.verdict]}</span>
          </li>
        ))}
      </ol>
      <ul className="flex flex-wrap gap-2 text-xs text-slate-500">
        {(["ok", "accents", "wrong", "missing", "extra"] as DictationVerdict[]).map((v) => (
          <li key={v} className="flex items-center gap-1">
            <span className={`inline-block size-3 rounded ${VERDICT_STYLE[v]}`} aria-hidden />
            {t.legend[v]}
          </li>
        ))}
      </ul>
    </div>
  );
}
