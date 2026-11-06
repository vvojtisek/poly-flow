import { Fragment, type ReactNode } from "react";

import type { GrammarUnit, Language } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

/** "**bold**" marks the key form in a note; everything else is plain text. */
export function Marked({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith("**") && p.endsWith("**") ? (
          <strong key={i} className="font-semibold text-slate-900 dark:text-slate-50">
            {p.slice(2, -2)}
          </strong>
        ) : (
          <Fragment key={i}>{p}</Fragment>
        ),
      )}
    </>
  );
}

function Table({ rows }: { rows: string[][] }) {
  const [head, ...body] = rows;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {head!.map((h, i) => (
              <th
                key={i}
                scope="col"
                className="border-b border-slate-300 px-2 py-1 text-left font-semibold text-slate-600 dark:border-slate-700 dark:text-slate-300"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((r, i) => (
            <tr key={i} className="odd:bg-slate-50 dark:odd:bg-slate-800/40">
              {r.map((c, j) => (
                <td key={j} className="px-2 py-1 align-top">
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A unit's Czech explanation: sections with optional tables, then examples. */
export function GrammarNotes({ unit, language, header, englishVariant = "uk" }: { unit: GrammarUnit; language: Language; header?: ReactNode; englishVariant?: "uk" | "us" }) {
  return (
    <article className="flex flex-col gap-4">
      {header}
      <p className="text-slate-600 dark:text-slate-300">{unit.summary}</p>
      {unit.notes.map((n) => (
        <section key={n.heading} className="flex flex-col gap-2">
          <h3 className="font-semibold">{n.heading}</h3>
          <p className="leading-relaxed text-slate-700 dark:text-slate-200">
            <Marked text={n.text} />
          </p>
          {n.table && <Table rows={n.table} />}
        </section>
      ))}
      <section className="flex flex-col gap-2">
        <h3 className="font-semibold">{cs.grammar.examples}</h3>
        <ul className="flex flex-col gap-2">
          {unit.examples.filter((e) => !e.variant || e.variant === englishVariant).map((e) => (
            <li key={e.text} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
              <p className="font-medium" lang={language}>
                {e.text}
              </p>
              <p className="text-sm text-slate-500" lang="cs">
                {e.cs}
              </p>
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
