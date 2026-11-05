"use client";

import { forwardRef, useImperativeHandle, useRef, type KeyboardEvent } from "react";

import { Kbd } from "@/components/Kbd";
import type { Language } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";
import { SPECIAL_CHARS, altCharFor, altCharLegend, insertAtCaret } from "@/lib/keyboard";

/**
 * Text answer with quick input for the target language's special characters: a button bar and
 * Alt+letter shortcuts (Alt+A → ä, Alt+Shift+A → Ä, Alt+S → ß), inserted at the caret.
 */
export const AnswerInput = forwardRef<
  HTMLInputElement,
  {
    language: Language;
    value: string;
    onChange: (value: string) => void;
    disabled?: boolean;
    placeholder?: string;
    showChars?: boolean;
  }
>(function AnswerInput({ language, value, onChange, disabled, placeholder, showChars = true }, ref) {
  const inputRef = useRef<HTMLInputElement>(null);
  useImperativeHandle(ref, () => inputRef.current!, []);
  const chars = SPECIAL_CHARS[language];
  const legend = altCharLegend(language);

  function insert(char: string) {
    const { value: next, caret } = insertAtCaret(inputRef.current, value, char);
    onChange(next);
    // Restore the caret after React re-renders the controlled value.
    requestAnimationFrame(() => {
      const el = inputRef.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(caret, caret);
    });
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    const char = altCharFor(language, e.nativeEvent);
    if (char) {
      e.preventDefault();
      insert(char);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
        placeholder={placeholder ?? cs.lesson.answerPlaceholder}
        aria-label={placeholder ?? cs.lesson.answerPlaceholder}
        autoCapitalize="none"
        autoCorrect="off"
        autoComplete="off"
        spellCheck={false}
        lang={language}
        className="rounded-xl border border-slate-300 bg-white px-4 py-4 text-center text-xl outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 dark:border-slate-700 dark:bg-slate-900"
      />
      {showChars && !disabled && chars.length > 0 && (
        <div className="flex flex-col items-center gap-1">
          <div className="flex flex-wrap justify-center gap-1" aria-label={cs.keys.specialChars} role="group">
            {chars.map((c) => (
              <button
                key={c}
                type="button"
                tabIndex={-1}
                className="min-w-9 rounded-lg bg-slate-100 px-2 py-1.5 font-medium hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700"
                // Keep the caret where it is: a mouse-down on the bar would blur the input first.
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => insert(c)}
              >
                {c}
              </button>
            ))}
          </div>
          {legend.length > 0 && (
            <p className="hidden text-xs text-slate-500 lg:block">
              {legend.map(({ key, char }, i) => (
                <span key={key}>
                  {i > 0 && " · "}
                  <Kbd>Alt+{key}</Kbd> {char}
                </span>
              ))}{" "}
              · {cs.keys.shiftCapital}
            </p>
          )}
        </div>
      )}
    </div>
  );
});
