"use client";

import { MessageCircleQuestion } from "lucide-react";
import { useState, type FormEvent } from "react";

import { KeyHint } from "@/components/Kbd";
import { Button, Notice } from "@/components/ui";
import { explainAnswer, type TutorExplanation } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

/**
 * "Proč?" after an answered exercise: the curriculum's Czech explanation, possibly expanded by
 * the local model (labelled as unreviewed), and a follow-up question when a model is available.
 * Render it only for closed exercises; the server refuses open ones. Remount per exercise (key).
 */
export function TutorButton({
  kind,
  id,
}: {
  kind: "word" | "grammar";
  id: string;
}) {
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const [explanation, setExplanation] = useState<TutorExplanation | null>(null);
  const [question, setQuestion] = useState("");

  async function load(q?: string) {
    setState("loading");
    try {
      setExplanation(await explainAnswer(kind, id, q));
      setState("idle");
    } catch {
      setState("error");
    }
  }

  function ask(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (q) void load(q);
  }

  if (!explanation)
    return (
      <div className="flex flex-col gap-2">
        <Button
          variant="ghost"
          disabled={state === "loading"}
          onClick={() => void load()}
          data-hotkey="why"
        >
          <MessageCircleQuestion className="size-4" aria-hidden />
          {state === "loading" ? cs.tutor.loading : cs.tutor.why}{" "}
          <KeyHint k="W" />
        </Button>
        {state === "error" && <Notice tone="error">{cs.tutor.failed}</Notice>}
      </div>
    );

  return (
    <section
      className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm dark:border-slate-700 dark:bg-slate-900"
      aria-live="polite"
    >
      <p className="whitespace-pre-line">{explanation.text}</p>
      <p className="text-xs text-slate-500">
        {explanation.source === "model" && explanation.model
          ? cs.tutor.fromModel(explanation.model)
          : cs.tutor.fromCurriculum}
      </p>
      {explanation.can_ask && (
        <form className="flex flex-col gap-2 sm:flex-row" onSubmit={ask}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={300}
            placeholder={cs.tutor.askPlaceholder}
            aria-label={cs.tutor.ask}
            className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-950"
          />
          <Button
            type="submit"
            variant="secondary"
            disabled={state === "loading" || !question.trim()}
          >
            {state === "loading" ? cs.tutor.loading : cs.tutor.send}
          </Button>
        </form>
      )}
      {state === "error" && <Notice tone="error">{cs.tutor.failed}</Notice>}
    </section>
  );
}
