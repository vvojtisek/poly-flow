"use client";

import { Gauge, Heart, Mic, Monitor, Moon, Palette, Plus, Sun, X } from "lucide-react";
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
  type Me,
  type ProfileSettings,
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
  onChange,
}: {
  voices: Voice[];
  chosen: ProfileSettings["voices"];
  onChange: (v: ProfileSettings["voices"]) => void;
}) {
  // Piper not running: every voice reads as not installed, which says nothing about the voices.
  const serviceDown = !voices.some((v) => v.installed);
  return (
    <div className="flex flex-col gap-4">
      {serviceDown && <Notice>{cs.settings.speechDown}</Notice>}
      {LANGUAGES.map((lang) => {
        const options = voices.filter((v) => v.language === lang);
        if (!options.length) return null;
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
      <Panel title={cs.settings.theme} icon={Palette}>
        <ThemePicker value={settings.theme} onChange={(theme) => void change({ theme })} />
      </Panel>
      <Panel title={cs.settings.interests} icon={Heart}>
        <Interests value={settings.interests} onChange={(interests) => void change({ interests })} />
      </Panel>
      <Panel title={cs.settings.voice} icon={Mic}>
        <div className="flex flex-col gap-4">
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
            <VoicePicker voices={voices} chosen={settings.voices} onChange={(v) => void change({ voices: v })} />
          )}
        </div>
      </Panel>
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
