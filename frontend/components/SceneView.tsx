"use client";

import { Languages } from "lucide-react";
import { useState } from "react";

import type { Language, Scene, SceneSegment } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

function Word({ seg, language }: { seg: SceneSegment; language: Language }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      type="button"
      lang={language}
      aria-expanded={open}
      onClick={() => setOpen((o) => !o)}
      className={`relative rounded px-0.5 underline decoration-dotted underline-offset-4 ${
        seg.new ? "bg-brand-500/15 font-semibold text-brand-600 dark:text-brand-50" : ""
      }`}
    >
      {seg.text}
      {open && seg.gloss && (
        <span
          role="tooltip"
          lang="cs"
          className="absolute bottom-full left-1/2 z-10 mb-1 -translate-x-1/2 whitespace-nowrap rounded-lg bg-slate-900 px-2 py-1 text-xs font-normal text-white no-underline dark:bg-slate-100 dark:text-slate-900"
        >
          {seg.gloss}
        </span>
      )}
    </button>
  );
}

/** The lesson's context: a short dialogue, new words highlighted, Czech on demand. */
export function SceneView({ scene, language }: { scene: Scene; language: Language }) {
  const [translate, setTranslate] = useState(false);
  return (
    <section className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <h2 className="text-lg font-bold">{scene.title}</h2>
      <ul className="flex flex-col gap-3">
        {scene.lines.map((line, i) => (
          <li key={i} className="flex flex-col gap-0.5">
            {line.speaker && <span className="text-xs font-semibold text-slate-500">{line.speaker}</span>}
            <p className="text-lg leading-relaxed" lang={language}>
              {line.segments.map((seg, j) =>
                seg.item_id ? <Word key={j} seg={seg} language={language} /> : <span key={j}>{seg.text}</span>,
              )}
            </p>
            {translate && (
              <p className="text-sm text-slate-500" lang="cs">
                {line.cs}
              </p>
            )}
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="inline-flex items-center gap-2 self-start text-sm font-medium text-brand-600 dark:text-brand-50"
        onClick={() => setTranslate((t) => !t)}
      >
        <Languages className="size-4" aria-hidden />
        {translate ? cs.lesson.hideTranslation : cs.lesson.showTranslation}
      </button>
    </section>
  );
}
