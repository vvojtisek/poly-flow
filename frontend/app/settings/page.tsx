"use client";

import { Check, Gauge, Heart, Mic, Monitor, Moon, Palette, Plus, ShieldAlert, Sun, Type, X } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { AppShell, FullPageStatus } from "@/components/AppShell";
import { Panel } from "@/components/Panel";
import { PlayButton } from "@/components/PlayButton";
import { Button, Field, Notice } from "@/components/ui";
import {
  LANGUAGES,
  listVoices,
  updateOwnProfile,
  voiceSampleUrl,
  type Accent,
  type Me,
  type ProfileSettings,
  type TextSize,
  type Theme,
  type Voice,
} from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const THEMES: { value: Theme; icon: typeof Sun }[] = [
  { value: "light", icon: Sun },
  { value: "dark", icon: Moon },
  { value: "system", icon: Monitor },
];
const SPEEDS = [0.8, 1, 1.2];
const TOPICS = Object.keys(cs.settings.topics);
const MAX_INTERESTS = 20; // backend: app/domain/voices.py MAX_INTERESTS
const KEYWORD = /^[\p{L}\p{N}' -]{1,40}$/u;

type SaveState = "idle" | "saving" | "saved" | "error";

function chip(active: boolean) {
  return `inline-flex items-center gap-1 rounded-full px-3 py-2 text-sm font-medium ${
    active ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
  }`;
}

function ThemePicker({ value, onChange }: { value: Theme; onChange: (t: Theme) => void }) {
  return (
    <div role="radiogroup" aria-label={cs.settings.theme} className="grid grid-cols-3 gap-2">
      {THEMES.map(({ value: t, icon: Icon }) => (
        <button
          key={t}
          type="button"
          role="radio"
          aria-checked={value === t}
          onClick={() => onChange(t)}
          className={`flex flex-col items-center gap-1 rounded-xl px-2 py-3 text-sm font-medium ${
            value === t
              ? "bg-brand-500 text-white"
              : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
          }`}
        >
          <Icon className="size-5" aria-hidden />
          {cs.settings.themes[t]}
        </button>
      ))}
    </div>
  );
}

const ACCENTS: { value: Accent; color: string }[] = [
  { value: "blue", color: "oklch(0.58 0.17 250)" },
  { value: "teal", color: "oklch(0.58 0.15 200)" },
  { value: "violet", color: "oklch(0.58 0.17 295)" },
  { value: "orange", color: "oklch(0.58 0.16 45)" },
  { value: "pink", color: "oklch(0.58 0.17 345)" },
];

function AccentPicker({ value, onChange }: { value: Accent; onChange: (a: Accent) => void }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold">{cs.settings.accent}</h3>
      <div role="radiogroup" aria-label={cs.settings.accent} className="flex flex-wrap gap-3">
        {ACCENTS.map(({ value: a, color }) => (
          <button
            key={a}
            type="button"
            role="radio"
            aria-checked={value === a}
            aria-label={cs.settings.accents[a]}
            title={cs.settings.accents[a]}
            onClick={() => onChange(a)}
            className={`grid size-11 place-items-center rounded-full ring-offset-2 ring-offset-white dark:ring-offset-slate-900 ${
              value === a ? "ring-2 ring-slate-900 dark:ring-white" : ""
            }`}
            style={{ background: color }}
          >
            {value === a && <Check className="size-5 text-white" aria-hidden />}
          </button>
        ))}
      </div>
      <p className="text-xs text-slate-500">{cs.settings.accentHelp}</p>
    </div>
  );
}

function Interests({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const [keyword, setKeyword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const own = value.filter((w) => !TOPICS.includes(w));
  const full = value.length >= MAX_INTERESTS;

  function toggle(word: string) {
    if (value.includes(word)) onChange(value.filter((w) => w !== word));
    else if (!full) onChange([...value, word]);
  }

  function add(e: FormEvent) {
    e.preventDefault();
    const word = keyword.trim().replace(/\s+/g, " ").toLowerCase();
    if (!KEYWORD.test(word)) return setError(cs.settings.ownKeywordHelp);
    if (full) return setError(cs.settings.tooMany(MAX_INTERESTS));
    setError(null);
    setKeyword("");
    if (!value.includes(word)) onChange([...value, word]);
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-slate-600 dark:text-slate-300">{cs.settings.interestsHelp}</p>
      <div className="flex flex-wrap gap-2">
        {TOPICS.map((t) => (
          <button
            key={t}
            type="button"
            aria-pressed={value.includes(t)}
            disabled={full && !value.includes(t)}
            onClick={() => toggle(t)}
            className={`${chip(value.includes(t))} disabled:opacity-50`}
          >
            {cs.settings.topics[t]}
          </button>
        ))}
        {own.map((w) => (
          <button key={w} type="button" onClick={() => toggle(w)} className={chip(true)} aria-label={cs.settings.remove(w)}>
            {w} <X className="size-3.5" aria-hidden />
          </button>
        ))}
      </div>
      <form onSubmit={add} className="flex items-end gap-2">
        <div className="min-w-0 flex-1">
          <Field
            label={cs.settings.ownKeyword}
            value={keyword}
            maxLength={40}
            onChange={(e) => setKeyword(e.target.value)}
          />
        </div>
        <Button type="submit" variant="secondary" className="shrink-0" disabled={!keyword.trim()}>
          <Plus className="size-4" aria-hidden /> {cs.settings.add}
        </Button>
      </form>
      {error && <Notice tone="error">{error}</Notice>}
      {full && !error && <Notice>{cs.settings.tooMany(MAX_INTERESTS)}</Notice>}
    </div>
  );
}

function SpeedPicker({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex flex-col gap-2">
      <div role="radiogroup" aria-label={cs.settings.speed} className="grid grid-cols-3 gap-2">
        {SPEEDS.map((s) => (
          <button
            key={s}
            type="button"
            role="radio"
            aria-checked={Math.abs(value - s) < 0.01}
            onClick={() => onChange(s)}
            className={`rounded-xl px-2 py-3 text-sm font-medium ${
              Math.abs(value - s) < 0.01
                ? "bg-brand-500 text-white"
                : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
            }`}
          >
            {cs.settings.speeds[String(s)]}
          </button>
        ))}
      </div>
      <p className="text-xs text-slate-500">{cs.settings.speedHelp}</p>
    </div>
  );
}

function VoicePicker({
  voices,
  chosen,
  englishVariant,
  onChange,
}: {
  voices: Voice[];
  chosen: ProfileSettings["voices"];
  englishVariant: "uk" | "us";
  onChange: (v: ProfileSettings["voices"]) => void;
}) {
  // Piper not running: every voice reads as not installed, which says nothing about the voices.
  const serviceDown = !voices.some((v) => v.installed);
  return (
    <div className="flex flex-col gap-4">
      {serviceDown && <Notice>{cs.settings.speechDown}</Notice>}
      {LANGUAGES.map((lang) => {
        const allOptions = voices.filter((v) => v.language === lang);
        const options = lang === "en" && englishVariant === "us" ? [] : allOptions;
        if (!options.length) {
          if (lang !== "en" || englishVariant !== "us") return null;
          return <div key={lang} className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600 dark:bg-slate-800 dark:text-slate-300"><h3 className="font-semibold">{cs.settings.voiceFor(cs.languages.en ?? "Angličtina")}</h3><p className="mt-1">{cs.settings.usVoiceUnavailable}</p></div>;
        }
        const current = chosen[lang] ?? options.find((v) => v.default)?.id;
        const installed = options.filter((v) => v.installed).length;
        const title = cs.settings.voiceFor(cs.languages[lang] ?? lang);
        return (
          <div key={lang} className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold">{title}</h3>
            <div role="radiogroup" aria-label={title} className="grid gap-2 sm:grid-cols-2">
              {options.map((v) => (
                <div
                  key={v.id}
                  className={`flex items-center gap-2 rounded-xl border p-2 ${
                    current === v.id ? "border-brand-500 bg-brand-500/10" : "border-slate-200 dark:border-slate-700"
                  } ${v.installed || serviceDown ? "" : "opacity-60"}`}
                >
                  <button
                    type="button"
                    role="radio"
                    aria-checked={current === v.id}
                    disabled={!v.installed && !serviceDown}
                    onClick={() => onChange({ ...chosen, [lang]: v.id })}
                    className="flex min-w-0 flex-1 flex-col items-start px-1 text-left"
                  >
                    <span className="font-semibold">{v.name}</span>
                    <span className="text-xs text-slate-500">
                      {v.gender === "female" ? cs.settings.female : cs.settings.male}
                      {v.default && ` · ${cs.settings.defaultVoice}`}
                      {!v.installed && !serviceDown && ` · ${cs.settings.notInstalled}`}
                    </span>
                  </button>
                  {v.installed && <PlayButton url={voiceSampleUrl(v.id)} label={cs.settings.sample(v.name)} />}
                </div>
              ))}
            </div>
            {installed === 1 && <p className="text-xs text-slate-500">{cs.settings.oneVoice}</p>}
          </div>
        );
      })}
    </div>
  );
}

function SettingsView({ me }: { me: Me }) {
  const { setMe } = useAuth();
  const [settings, setSettings] = useState<ProfileSettings>(me.acting.settings);
  const [save, setSave] = useState<SaveState>("idle");
  const [voices, setVoices] = useState<Voice[] | null>(null);
  const [voicesFailed, setVoicesFailed] = useState(false);

  useEffect(() => {
    const ctl = new AbortController();
    listVoices(ctl.signal)
      .then(setVoices)
      .catch(() => !ctl.signal.aborted && setVoicesFailed(true));
    return () => ctl.abort();
  }, []);

  // Each change is saved at once; the server merges it into the stored settings.
  async function change(patch: Partial<ProfileSettings>) {
    const previous = settings;
    setSettings({ ...settings, ...patch });
    setSave("saving");
    try {
      const acting = await updateOwnProfile({ settings: patch });
      setSettings(acting.settings);
      setMe({ ...me, acting, principal: me.principal.id === acting.id ? acting : me.principal });
      setSave("saved");
    } catch {
      setSettings(previous);
      setSave("error");
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-xl font-bold">{cs.settings.title}</h1>
        <span role="status" className="text-sm text-slate-500">
          {save === "saving" ? cs.settings.saving : save === "saved" ? cs.settings.saved : ""}
        </span>
      </div>
      {save === "error" && <Notice tone="error">{cs.settings.failed}</Notice>}
      <Panel title={cs.settings.englishVariant} icon={Mic}>
        <div className="flex flex-col gap-3">
          <div role="radiogroup" aria-label={cs.settings.englishVariant} className="grid gap-2 sm:grid-cols-2">
            {(["uk", "us"] as const).map((variant) => (
              <button key={variant} type="button" role="radio" aria-checked={settings.english_variant === variant}
                onClick={() => void change({ english_variant: variant })}
                className={`rounded-xl px-3 py-3 text-sm font-semibold ${settings.english_variant === variant ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"}`}>
                {cs.settings.englishVariants[variant]}
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500">{cs.settings.englishVariantHelp}</p>
        </div>
      </Panel>
      <Panel title={cs.settings.theme} icon={Palette}>
        <div className="flex flex-col gap-4">
          <ThemePicker value={settings.theme} onChange={(theme) => void change({ theme })} />
          <AccentPicker value={settings.accent ?? "blue"} onChange={(accent) => void change({ accent })} />
        </div>
      </Panel>
      <Panel title={cs.settings.comfort} icon={Type}>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold">{cs.settings.textSize}</h3>
            <div role="radiogroup" aria-label={cs.settings.textSize} className="grid grid-cols-4 gap-2">
              {(["s", "m", "l", "xl"] as TextSize[]).map((size, i) => (
                <button
                  key={size}
                  type="button"
                  role="radio"
                  aria-checked={settings.text_size === size}
                  onClick={() => void change({ text_size: size })}
                  className={`flex flex-col items-center gap-1 rounded-xl px-2 py-3 font-medium ${
                    settings.text_size === size ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                  }`}
                >
                  <span style={{ fontSize: `${0.9 + i * 0.25}rem` }} aria-hidden>
                    Aa
                  </span>
                  <span className="text-xs">{cs.settings.textSizes[size]}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold">{cs.welcome.goal}</h3>
            <div role="radiogroup" aria-label={cs.welcome.goal} className="grid grid-cols-5 gap-2">
              {[5, 10, 15, 20, 30].map((g) => (
                <button
                  key={g}
                  type="button"
                  role="radio"
                  aria-checked={settings.daily_goal_minutes === g}
                  onClick={() => void change({ daily_goal_minutes: g })}
                  className={`rounded-xl px-2 py-2 text-sm font-medium ${
                    settings.daily_goal_minutes === g ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                  }`}
                >
                  {cs.welcome.minutes(g)}
                </button>
              ))}
            </div>
            <p className="text-xs text-slate-500">{cs.welcome.goalHelp}</p>
          </div>
          <label className="flex items-start gap-3 text-sm font-medium">
            <input
              type="checkbox"
              className="mt-0.5 size-5 accent-brand-500"
              checked={settings.reading_spacing}
              onChange={(e) => void change({ reading_spacing: e.target.checked })}
            />
            <span className="flex flex-col">
              {cs.settings.spacing}
              <span className="text-xs font-normal text-slate-500">{cs.settings.spacingHelp}</span>
            </span>
          </label>
          <label className="flex items-start gap-3 text-sm font-medium">
            <input
              type="checkbox"
              className="mt-0.5 size-5 accent-brand-500"
              checked={settings.reduce_motion}
              onChange={(e) => void change({ reduce_motion: e.target.checked })}
            />
            <span className="flex flex-col">
              {cs.settings.motion}
              <span className="text-xs font-normal text-slate-500">{cs.settings.motionHelp}</span>
            </span>
          </label>
          <p lang="de" className="rounded-xl bg-slate-50 p-3 text-lg dark:bg-slate-800/60">
            {cs.settings.preview}
          </p>
        </div>
      </Panel>
      <Panel title={cs.settings.interests} icon={Heart}>
        <Interests value={settings.interests} onChange={(interests) => void change({ interests })} />
      </Panel>
      <Panel title={cs.settings.voice} icon={Mic}>
        <div className="flex flex-col gap-4">
          <label className="flex items-start gap-3 text-sm font-medium">
            <input type="checkbox" className="mt-0.5 size-5 accent-brand-500" checked={settings.autoplay_audio}
              onChange={(event) => void change({ autoplay_audio: event.target.checked })} />
            <span className="flex flex-col">{cs.settings.autoplayAudio}<span className="text-xs font-normal text-slate-500">{cs.settings.autoplayAudioHelp}</span></span>
          </label>
          <div className="flex flex-col gap-2">
            <h3 className="flex items-center gap-1 text-sm font-semibold">
              <Gauge className="size-4" aria-hidden /> {cs.settings.speed}
            </h3>
            <SpeedPicker value={settings.audio_rate} onChange={(audio_rate) => void change({ audio_rate })} />
          </div>
          {voicesFailed ? (
            <Notice tone="error">{cs.settings.voicesUnavailable}</Notice>
          ) : voices === null ? (
            <p className="text-sm text-slate-500">{cs.common.loading}</p>
          ) : (
            <VoicePicker voices={voices} chosen={settings.voices} englishVariant={settings.english_variant} onChange={(v) => void change({ voices: v })} />
          )}
        </div>
      </Panel>
      {!me.acting.is_child && (
        <Panel title={cs.settings.profanity} icon={ShieldAlert}>
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-3 text-sm font-medium">
              <input
                type="checkbox"
                className="size-5 accent-brand-500"
                checked={settings.learn_profanity}
                onChange={(e) => void change({ learn_profanity: e.target.checked })}
              />
              {cs.settings.profanityToggle}
            </label>
            <p className="text-xs text-slate-500">{cs.settings.profanityHelp}</p>
          </div>
        </Panel>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const me = useRequireMe();
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  return (
    <AppShell me={me}>
      <SettingsView key={me.acting.id} me={me} />
    </AppShell>
  );
}
