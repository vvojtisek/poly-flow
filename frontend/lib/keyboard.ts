"use client";

import { useEffect } from "react";

import type { Language } from "@/lib/api";

/**
 * Desktop keyboard support.
 *
 * Controls opt in with `data-hotkey="<name>"`; one document-level listener turns a key press into
 * a click on the first visible, enabled control with that name. Digits use the physical key
 * (`event.code`), because on the Czech layout the top row types `+ěščřžýáíé` without Shift.
 */

export type HotkeyName = "enter" | "hint" | "reveal" | "play" | "why" | `${number}`;

const TYPING = new Set(["INPUT", "TEXTAREA", "SELECT"]);

export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return TYPING.has(target.tagName) || target.isContentEditable;
}

/** 1-9 from the digit row or the numeric keypad, whatever the layout types there. */
export function digitOf(e: Pick<KeyboardEvent, "code">): number | null {
  const m = /^(?:Digit|Numpad)([1-9])$/.exec(e.code);
  return m ? Number(m[1]) : null;
}

/** Hotkey for a key press, or null. Letters only fire outside text fields (Alt+letter inside). */
export function hotkeyFor(e: KeyboardEvent): HotkeyName | null {
  if (e.ctrlKey || e.metaKey) return null;
  const typing = isTypingTarget(e.target);
  if (e.key === "Enter" && !e.shiftKey) {
    // Buttons, links and forms already handle Enter themselves.
    if (typing || (e.target instanceof HTMLElement && e.target.closest("button, a, summary"))) return null;
    return "enter";
  }
  if (typing && !e.altKey) return null;
  if (!typing && e.altKey) return null;
  const digit = digitOf(e);
  if (digit !== null && !typing) return `${digit}`;
  switch (e.code) {
    case "KeyH":
      return "hint";
    case "KeyN":
      return "reveal";
    case "KeyP":
      return "play";
    case "KeyW":
      return "why";
  }
  if (!typing && e.key === "?") return "hint";
  return null;
}

function visible(el: HTMLElement): boolean {
  return el.offsetParent !== null || el.getClientRects().length > 0;
}

export function clickHotkey(name: HotkeyName, root: ParentNode = document): boolean {
  const candidates = root.querySelectorAll<HTMLElement>(`[data-hotkey="${name}"]`);
  for (const el of candidates) {
    if ((el as HTMLButtonElement).disabled || el.getAttribute("aria-disabled") === "true") continue;
    if (!visible(el)) continue;
    el.click();
    return true;
  }
  return false;
}

/** Install the document-level hotkey listener while the calling component is mounted. */
export function useHotkeys(enabled = true): void {
  useEffect(() => {
    if (!enabled) return;
    function onKey(e: KeyboardEvent) {
      if (e.defaultPrevented || e.repeat || e.isComposing) return;
      const name = hotkeyFor(e);
      if (name && clickHotkey(name)) e.preventDefault();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [enabled]);
}

// ---------------------------------------------------------------- special characters

export const SPECIAL_CHARS: Record<Language, string[]> = {
  de: ["ä", "ö", "ü", "ß", "Ä", "Ö", "Ü"],
  fr: ["é", "è", "ê", "à", "â", "ç", "ô", "î", "û", "ù", "ë", "œ"],
  it: ["à", "è", "é", "ì", "ò", "ù"],
  en: [],
};

/**
 * Alt+letter shortcuts for characters a Czech keyboard lacks (Alt+Shift for capitals).
 * AltGr arrives as Ctrl+Alt on Windows and is left alone, so Czech AltGr characters keep working.
 */
const ALT_CHARS: Partial<Record<Language, Record<string, [string, string]>>> = {
  de: { KeyA: ["ä", "Ä"], KeyO: ["ö", "Ö"], KeyU: ["ü", "Ü"], KeyS: ["ß", "ẞ"] },
  fr: { KeyE: ["é", "É"], KeyC: ["ç", "Ç"], KeyA: ["à", "À"], KeyO: ["œ", "Œ"] },
  it: { KeyE: ["è", "È"], KeyA: ["à", "À"], KeyO: ["ò", "Ò"], KeyU: ["ù", "Ù"], KeyI: ["ì", "Ì"] },
};

export function altCharFor(language: Language, e: Pick<KeyboardEvent, "altKey" | "ctrlKey" | "metaKey" | "shiftKey" | "code">): string | null {
  if (!e.altKey || e.ctrlKey || e.metaKey) return null;
  const pair = ALT_CHARS[language]?.[e.code];
  return pair ? pair[e.shiftKey ? 1 : 0] : null;
}

export function altCharLegend(language: Language): { key: string; char: string }[] {
  return Object.entries(ALT_CHARS[language] ?? {}).map(([code, [lower]]) => ({
    key: code.replace("Key", ""),
    char: lower,
  }));
}

/** Insert `char` at the caret of `input` (replacing a selection) and return the new value. */
export function insertAtCaret(input: HTMLInputElement | HTMLTextAreaElement | null, value: string, char: string): { value: string; caret: number } {
  const start = input?.selectionStart ?? value.length;
  const end = input?.selectionEnd ?? value.length;
  return { value: value.slice(0, start) + char + value.slice(end), caret: start + char.length };
}
