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

function getPlayer(): HTMLAudioElement {
  if (!player) {
    player = new Audio();
    player.addEventListener("ended", () => set(current, "idle"));
    player.addEventListener("error", () => set(current, "error"));
  }
  return player;
}

export async function play(url: string): Promise<void> {
  const audio = getPlayer();
  audio.pause();
  set(url, "loading");
  try {
    let src = clips.get(url);
    if (!src) {
      const res = await fetch(url, { credentials: "same-origin" });
      if (!res.ok) throw new Error(`audio ${res.status}`);
      src = URL.createObjectURL(await res.blob());
      clips.set(url, src);
    }
    if (current !== url) return; // another clip was started meanwhile
    audio.src = src;
    audio.playbackRate = slow ? SLOW_RATE : 1;
    await audio.play();
    set(url, "playing");
  } catch {
    if (current === url) set(url, "error");
  }
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
  if (player) player.playbackRate = value ? SLOW_RATE : 1;
  emit();
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
