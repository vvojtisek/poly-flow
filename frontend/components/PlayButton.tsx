"use client";

import { Loader2, Snail, Volume2, VolumeX } from "lucide-react";

import { play, setSlow, stop, useClipState, useSlow } from "@/lib/audio";
import { cs } from "@/lib/i18n/cs";

/** Plays one clip of synthesized speech. Without the TTS service it shows that and stays text-only. */
export function PlayButton({ url, label = cs.audio.play, size = "md" }: { url: string; label?: string; size?: "sm" | "md" }) {
  const state = useClipState(url);
  const Icon = state === "loading" ? Loader2 : state === "error" ? VolumeX : Volume2;
  const title = state === "error" ? cs.audio.unavailable : label;
  return (
    <button
      type="button"
      aria-label={title}
      title={title}
      onClick={() => (state === "playing" ? stop() : void play(url))}
      className={`inline-flex shrink-0 items-center justify-center rounded-full text-brand-600 hover:bg-brand-500/10 dark:text-brand-50 ${
        size === "sm" ? "size-8" : "size-11"
      } ${state === "playing" ? "bg-brand-500/15" : ""} ${state === "error" ? "text-slate-400 dark:text-slate-500" : ""}`}
    >
      <Icon className={`${size === "sm" ? "size-4" : "size-6"} ${state === "loading" ? "animate-spin" : ""}`} aria-hidden />
    </button>
  );
}

/** Switches every clip between normal speed and slower playback; the choice is remembered. */
export function SlowToggle() {
  const slow = useSlow();
  return (
    <button
      type="button"
      aria-pressed={slow}
      onClick={() => setSlow(!slow)}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
        slow ? "bg-brand-500/15 text-brand-600 dark:text-brand-50" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
      }`}
    >
      <Snail className="size-3.5" aria-hidden />
      {cs.audio.slower}
    </button>
  );
}
