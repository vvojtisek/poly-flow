"use client";

import { useState } from "react";

import { updateOwnProfile, type Me, type ProfileSettings } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

export type PracticeDifficulty = ProfileSettings["practice_difficulty"];

export function PracticeDifficultyControl({ me }: { me: Me }) {
  const { setMe } = useAuth();
  const [saving, setSaving] = useState(false);
  const selected = me.acting.settings.practice_difficulty ?? "auto";
  const options: PracticeDifficulty[] = ["auto", "easy", "medium", "hard"];

  async function choose(value: PracticeDifficulty) {
    if (value === selected || saving) return;
    setSaving(true);
    try {
      const acting = await updateOwnProfile({ settings: { practice_difficulty: value } });
      setMe({ ...me, acting, principal: me.principal.id === acting.id ? acting : me.principal });
      // Active sessions are persisted on the server. Reloading re-requests the current item with
      // the new response format, so a difficulty change takes effect on the item already open.
      window.location.reload();
    } catch {
      setSaving(false);
    }
  }

  return (
    <fieldset className="flex flex-wrap items-center gap-1 rounded-xl border border-slate-200 bg-white p-1 dark:border-slate-700 dark:bg-slate-900" aria-label={cs.practice.difficulty}>
      <legend className="sr-only">{cs.practice.difficulty}</legend>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={selected === option}
          disabled={saving}
          onClick={() => void choose(option)}
          className={`rounded-lg px-2.5 py-1.5 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:opacity-60 ${selected === option ? "bg-brand-500 text-white" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"}`}
        >
          {cs.practice.difficulties[option]}
        </button>
      ))}
      {saving && <span className="sr-only" role="status">{cs.common.loading}</span>}
    </fieldset>
  );
}
