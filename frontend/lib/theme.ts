// Light, dark or the device's setting. The choice is stored per profile on the server and,
// for the first paint, in localStorage: THEME_SCRIPT runs in <head> before the page is drawn.

import type { Theme } from "@/lib/api";

const KEY = "pf_theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

/** Inline <head> script: applies the stored theme before first paint (no flash). */
export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("${KEY}");var d=t==="dark"||(t!=="light"&&matchMedia("${DARK_QUERY}").matches);var r=document.documentElement;if(d)r.classList.add("dark");r.style.colorScheme=d?"dark":"light"}catch(e){}})()`;

let current: Theme = "system";
let watching = false;

function paint() {
  const dark = current === "dark" || (current === "system" && window.matchMedia(DARK_QUERY).matches);
  const root = document.documentElement;
  root.classList.toggle("dark", dark);
  root.style.colorScheme = dark ? "dark" : "light";
}

/** Applies `theme` at once (no reload) and remembers it on this device. */
export function applyTheme(theme: Theme) {
  current = theme;
  try {
    window.localStorage.setItem(KEY, theme);
  } catch {
    /* storage unavailable: the theme still applies to this page */
  }
  if (!watching) {
    watching = true;
    // "Podle zařízení" follows the device when it switches between light and dark.
    window.matchMedia(DARK_QUERY).addEventListener("change", () => current === "system" && paint());
  }
  paint();
}
