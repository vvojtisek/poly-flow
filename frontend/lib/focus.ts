// Focus mode for lessons and checks: the header, tabs and links step aside so only the task
// is on screen. A per-device preference (localStorage), like the slow-audio toggle.

import { useCallback, useSyncExternalStore } from "react";

const KEY = "pf_focus";
const listeners = new Set<() => void>();

function read(): boolean {
  try {
    return window.localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

let value: boolean | null = null;

function get(): boolean {
  if (value === null) value = read();
  return value;
}

export function setFocusMode(next: boolean) {
  value = next;
  try {
    if (next) window.localStorage.setItem(KEY, "1");
    else window.localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable: this page only */
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useFocusMode(): [boolean, () => void] {
  const focus = useSyncExternalStore(subscribe, get, () => false);
  const toggle = useCallback(() => setFocusMode(!get()), []);
  return [focus, toggle];
}
