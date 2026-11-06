"use client";

import { Lightbulb, Pencil } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { Button } from "@/components/ui";
import { setWordNote } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const t = cs.hook;
const MAX = 280; // backend: app/models/word_note.py MAX_NOTE

/** The learner's memory hook for one word: shown when set, edited in place. */
export function NoteEditor({
  itemId,
  initial,
  onSaved,
  compact = false,
}: {
  itemId: string;
  initial: string | null;
  onSaved?: (note: string | null) => void;
  compact?: boolean;
}) {
  const [note, setNote] = useState(initial);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(initial ?? "");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const area = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setNote(initial);
    setDraft(initial ?? "");
    setEditing(false);
  }, [itemId, initial]);

  useEffect(() => {
    if (editing) area.current?.focus();
  }, [editing]);

  async function save(text: string) {
    setBusy(true);
    setFailed(false);
    try {
      const { note: saved } = await setWordNote(itemId, text);
      setNote(saved);
      setDraft(saved ?? "");
      setEditing(false);
      onSaved?.(saved);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Keep the lesson's own hotkeys (Enter = next) away from the note.
    e.stopPropagation();
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void save(draft);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setDraft(note ?? "");
      setEditing(false);
    }
  }

  if (editing)
    return (
      <div className="flex flex-col gap-2 text-left">
        <label className="flex flex-col gap-1 text-sm font-medium">
          <span className="flex items-center gap-1">
            <Lightbulb className="size-4 text-amber-500" aria-hidden /> {t.title}
          </span>
          <textarea
            ref={area}
            value={draft}
            maxLength={MAX}
            rows={2}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKey}
            placeholder={t.placeholder}
            className="resize-none rounded-xl border border-slate-300 bg-white px-3 py-2 text-base font-normal outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 dark:border-slate-700 dark:bg-slate-900"
          />
        </label>
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <span>
            {t.help} {t.count(draft.length, MAX)}
          </span>
          <span className="flex gap-1">
            {note && (
              <Button variant="ghost" className="!px-2 !py-1 text-xs" disabled={busy} onClick={() => void save("")}>
                {t.remove}
              </Button>
            )}
            <Button variant="ghost" className="!px-2 !py-1 text-xs" onClick={() => setEditing(false)}>
              {t.cancel}
            </Button>
            <Button className="!px-3 !py-1 text-xs" disabled={busy} onClick={() => void save(draft)}>
              {t.save}
            </Button>
          </span>
        </div>
        {failed && <p className="text-xs text-rose-600">{t.failed}</p>}
      </div>
    );

  if (note)
    return (
      <div className="flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-left text-sm text-amber-950 dark:bg-amber-950/50 dark:text-amber-50">
        <Lightbulb className="mt-0.5 size-4 shrink-0 text-amber-500" aria-label={t.title} />
        <p className="flex-1 whitespace-pre-wrap">{note}</p>
        <button type="button" onClick={() => setEditing(true)} aria-label={t.edit} title={t.edit} className="shrink-0 opacity-60 hover:opacity-100">
          <Pencil className="size-4" aria-hidden />
        </button>
      </div>
    );

  return (
    <button
      type="button"
      onClick={() => setEditing(true)}
      className={`inline-flex items-center gap-1 self-center rounded-full border border-dashed border-amber-400 px-3 py-1 text-amber-700 hover:bg-amber-50 dark:text-amber-300 dark:hover:bg-amber-950/40 ${compact ? "text-xs" : "text-sm"}`}
    >
      <Lightbulb className="size-4" aria-hidden /> {t.add}
    </button>
  );
}
