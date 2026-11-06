// Light, dark or the device's setting. The choice is stored per profile on the server and,
// for the first paint, in localStorage: THEME_SCRIPT runs in <head> before the page is drawn.

import type { ProfileSettings, Theme } from "@/lib/api";

const KEY = "pf_theme";
const DISPLAY_KEY = "pf_display";
const DARK_QUERY = "(prefers-color-scheme: dark)";

/** Inline <head> script: applies the stored theme before first paint (no flash). */
export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("${KEY}");var d=t==="dark"||(t!=="light"&&matchMedia("${DARK_QUERY}").matches);var r=document.documentElement;if(d)r.classList.add("dark");r.style.colorScheme=d?"dark":"light";var p=JSON.parse(localStorage.getItem("${DISPLAY_KEY}")||"{}");if(p.text)r.dataset.text=p.text;if(p.spacing)r.dataset.spacing="1";if(p.motion)r.dataset.motion="reduce";if(p.accent)r.dataset.accent=p.accent}catch(e){}})()`;

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

type Display = Pick<ProfileSettings, "text_size" | "reading_spacing" | "reduce_motion"> & Partial<Pick<ProfileSettings, "accent">>;

/** Reading comfort: text size, wider spacing and no animations, as attributes on <html>. */
export function applyDisplay(d: Display) {
  const root = document.documentElement;
  const text = d.text_size ?? "m";
  if (text === "m") delete root.dataset.text;
  else root.dataset.text = text;
  if (d.reading_spacing) root.dataset.spacing = "1";
  else delete root.dataset.spacing;
  if (d.reduce_motion) root.dataset.motion = "reduce";
  else delete root.dataset.motion;
  const accent = d.accent && d.accent !== "blue" ? d.accent : null;
  if (accent) root.dataset.accent = accent;
  else delete root.dataset.accent;
  try {
    window.localStorage.setItem(
      DISPLAY_KEY,
      JSON.stringify({ text: text === "m" ? null : text, spacing: !!d.reading_spacing, motion: !!d.reduce_motion, accent }),
    );
  } catch {
    /* storage unavailable: applies to this page only */
  }
}
