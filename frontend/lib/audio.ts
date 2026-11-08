// Playback of server-synthesized speech. One shared <audio> element, so starting a clip stops
// the previous one. Clips are fetched (not streamed by URL) to see the status code: a 503 means
// the TTS service is not running and the UI falls back to text only.

import { useSyncExternalStore } from "react";

export type AudioState = "idle" | "loading" | "playing" | "error";

const SLOW_RATE = 0.75;
const SLOW_KEY = "pf_audio_slow";

let player: HTMLAudioElement | null = null;
let current: string | null = null;
let state: AudioState = "idle";
let slow = readSlow();
let baseRate = 1; // the profile's speech speed (settings.audio_rate)
const clips = new Map<string, string>(); // url -> object URL, for this page's lifetime
const listeners = new Set<() => void>();

function readSlow(): boolean {
  try {
    return typeof window !== "undefined" && window.localStorage.getItem(SLOW_KEY) === "1";
  } catch {
    return false;
  }
}

function emit() {
  for (const l of listeners) l();
}

function set(url: string | null, next: AudioState) {
  current = url;
  state = next;
  emit();
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

const inflight = new Map<string, Promise<string>>();

/** Fetches the clip ahead of time (e.g. the next sentence), ignoring failures. */
export function prefetchClip(url: string): void {
  void clipSrc(url).catch(() => undefined);
}

function getPlayer(): HTMLAudioElement {
  if (!player) {
    player = new Audio();
    player.addEventListener("ended", () => set(current, "idle"));
    player.addEventListener("error", () => set(current, "error"));
  }
  return player;
}

/** Object URL of the clip at `url`, fetched once per page. Throws when the clip is unavailable. */
export async function clipSrc(url: string): Promise<string> {
  if (url.startsWith("blob:")) return url;
  const src = clips.get(url);
  if (src) return src;
  // One request per clip even when a prefetch and a play ask at the same time.
  let pending = inflight.get(url);
  if (!pending) {
    pending = (async () => {
      const res = await fetch(url, { credentials: "same-origin" });
      if (!res.ok) throw new Error(`audio ${res.status}`);
      const made = URL.createObjectURL(await res.blob());
      clips.set(url, made);
      return made;
    })().finally(() => inflight.delete(url));
    inflight.set(url, pending);
  }
  return pending;
}

/**
 * Plays the clip at `url`. `natural` plays at normal speed, ignoring the slow toggle and the
 * profile's speech speed (for the learner's own recordings).
 */
export async function play(url: string, opts: { natural?: boolean } = {}): Promise<void> {
  const audio = getPlayer();
  audio.pause();
  set(url, "loading");
  try {
    const src = await clipSrc(url);
    if (current !== url) return; // another clip was started meanwhile
    audio.src = src;
    audio.playbackRate = opts.natural ? 1 : rate();
    await audio.play();
    set(url, "playing");
  } catch {
    if (current === url) set(url, "error");
  }
}

/** Plays the clip and resolves once it has finished, failed, or been replaced by another clip. */
export async function playToEnd(url: string, opts: { natural?: boolean } = {}): Promise<void> {
  await play(url, opts);
  if (current !== url || state !== "playing") return;
  await new Promise<void>((resolve) => {
    const check = () => {
      if (current !== url || state !== "playing") {
        listeners.delete(check);
        resolve();
      }
    };
    listeners.add(check);
  });
}

export function stop() {
  player?.pause();
  set(null, "idle");
}

export function setSlow(value: boolean) {
  slow = value;
  try {
    window.localStorage.setItem(SLOW_KEY, value ? "1" : "0");
  } catch {
    /* storage unavailable: the choice lasts for this page */
  }
  if (player) player.playbackRate = rate();
  emit();
}

function rate(): number {
  return baseRate * (slow ? SLOW_RATE : 1);
}

/** The profile's speech speed; the lesson's "slower" toggle slows it further. */
export function setBaseRate(value: number) {
  baseRate = value > 0 ? value : 1;
  if (player) player.playbackRate = rate();
}

/** State of the clip at `url` (idle unless it is the current one). */
export function useClipState(url: string): AudioState {
  return useSyncExternalStore(
    subscribe,
    () => (current === url ? state : "idle"),
    () => "idle",
  );
}

export function useSlow(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => slow,
    () => false,
  );
}
