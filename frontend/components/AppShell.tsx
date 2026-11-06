"use client";

import { BarChart3, BookMarked, Dumbbell, GraduationCap, LogOut, Maximize2, Minimize2, Search, Settings, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { BottomTabs } from "@/components/BottomTabs";
import { BuildInfo } from "@/components/BuildInfo";
import { CommandPalette, openPalette } from "@/components/CommandPalette";
import { Kbd } from "@/components/Kbd";
import { RankEmblem } from "@/components/RankEmblem";
import { Button, Field, Notice } from "@/components/ui";
import { ApiError, LANGUAGES, logout, returnToParent, updateOwnProfile, type Language, type Me } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFocusMode } from "@/lib/focus";
import { cs } from "@/lib/i18n/cs";
import { isTypingTarget } from "@/lib/keyboard";
import { rankName } from "@/lib/ranks";
import { useRanks } from "@/lib/useRanks";

function ReturnToParent({ me }: { me: Me }) {
  const { setMe } = useAuth();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      setMe(await returnToParent(password));
      setOpen(false);
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? cs.auth.tooMany : cs.auth.invalid);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span>{cs.auth.actingAs(me.acting.display_name)}</span>
        {!open && (
          <button type="button" className="font-semibold underline" onClick={() => setOpen(true)}>
            {cs.auth.backToParent}
          </button>
        )}
      </div>
      {open && (
        <form onSubmit={submit} className="flex flex-col gap-2">
          <p>{cs.auth.backToParentHelp}</p>
          <Field
            label={cs.auth.password}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <Notice tone="error">{error}</Notice>}
          <div className="flex gap-2">
            <Button type="submit">{cs.common.continue}</Button>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              {cs.common.cancel}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}

export function LanguagePicker({ me, onChange }: { me: Me; onChange?: (l: Language) => void }) {
  const { setMe } = useAuth();
  const [busy, setBusy] = useState(false);

  async function pick(language: Language) {
    if (language === me.acting.active_language) return;
    setBusy(true);
    try {
      const acting = await updateOwnProfile({ active_language: language });
      setMe({ ...me, acting, principal: me.principal.id === acting.id ? acting : me.principal });
      onChange?.(language);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div role="radiogroup" aria-label={cs.profiles.language} className="flex flex-wrap gap-1">
      {LANGUAGES.map((l) => (
        <button
          key={l}
          type="button"
          role="radio"
          aria-checked={me.acting.active_language === l}
          disabled={busy}
          onClick={() => void pick(l)}
          className={`rounded-lg px-3 py-1.5 text-sm font-semibold ${
            me.acting.active_language === l
              ? "bg-brand-500 text-white"
              : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
          }`}
        >
          {cs.languages[l]}
        </button>
      ))}
    </div>
  );
}

/** Display name with the rank emblem: the avatar evolves with the learner's rank. */
function HeaderRank({ me }: { me: Me }) {
  const { data } = useRanks(me.acting.active_language, me.acting.id);
  if (!data || data.path === "off")
    return <p className="text-sm text-slate-500">{me.acting.display_name}</p>;
  return (
    <Link href="/ranks" className="mt-1 flex items-center gap-2 rounded-full pr-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
      <RankEmblem path={data.path} rank={data.rank} tier={data.tier} size="sm" />
      <span className="flex flex-col leading-tight">
        <span className="text-slate-700 dark:text-slate-200">{me.acting.display_name}</span>
        <span className="text-xs text-slate-500">{rankName(data.path, data.rank)}</span>
      </span>
    </Link>
  );
}

/** focusable: the page (a lesson or a check) offers focus mode, which hides everything but the task. */
export function AppShell({ me, children, focusable = false }: { me: Me; children: ReactNode; focusable?: boolean }) {
  const { setMe } = useAuth();
  const router = useRouter();
  const [focusPref, toggleFocus] = useFocusMode();
  const focus = focusable && focusPref;

  useEffect(() => {
    if (!focusable) return;
    function onKey(e: KeyboardEvent) {
      if (e.code !== "KeyF" || e.ctrlKey || e.metaKey || e.altKey || e.repeat || isTypingTarget(e.target)) return;
      e.preventDefault();
      toggleFocus();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [focusable, toggleFocus]);

  async function signOut() {
    try {
      await logout();
    } finally {
      setMe(null);
      router.replace("/login");
    }
  }

  if (focus) {
    return (
      <main className="mx-auto flex min-h-full max-w-6xl flex-col gap-4 p-4 lg:p-8" data-focus="on">
        <header className="flex items-center justify-between gap-3">
          <Link href="/" className="text-sm font-bold text-brand-600" aria-label={cs.appName}>
            {cs.appName}
          </Link>
          <div className="flex items-center gap-2">
            <Button variant="ghost" className="!px-3 !py-1.5 text-sm" onClick={toggleFocus} aria-pressed>
              <Minimize2 className="size-4" aria-hidden /> {cs.focus.exit}
              <span className="hidden lg:inline">
                <Kbd>F</Kbd>
              </span>
            </Button>
          </div>
        </header>
        {me.acting.id !== me.principal.id && <ReturnToParent me={me} />}
        {children}
        <BuildInfo className="mt-auto justify-center pt-6 text-center opacity-70" />
        <CommandPalette me={me} />
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-full max-w-7xl flex-col gap-4 p-4 pb-24 lg:p-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/" className="text-2xl font-bold text-brand-600">
            {cs.appName}
          </Link>
          <HeaderRank me={me} />
        </div>
        <div className="flex flex-col items-end gap-1">
          <nav className="flex flex-wrap items-center justify-end gap-1">
            {focusable && (
              <button
                type="button"
                onClick={toggleFocus}
                aria-pressed={false}
                title={cs.focus.help}
                className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <Maximize2 className="size-4" aria-hidden /> <span className="hidden sm:inline">{cs.focus.enter}</span>
              </button>
            )}
            <button
              type="button"
              onClick={openPalette}
              aria-label={cs.palette.title}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-500 hover:border-brand-500 dark:border-slate-700"
            >
              <Search className="size-4" aria-hidden />
              <span className="hidden sm:inline">{cs.palette.button}</span>
              <span className="hidden lg:inline">
                <Kbd>Ctrl K</Kbd>
              </span>
            </button>
            <Link
              href="/grammar"
              className="hidden items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 lg:inline-flex dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <GraduationCap className="size-4" aria-hidden /> {cs.grammar.link}
            </Link>
            <Link
              href="/practice"
              className="hidden items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 lg:inline-flex dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <Dumbbell className="size-4" aria-hidden /> {cs.practice.link}
            </Link>
            <Link
              href="/words"
              className="hidden items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 lg:inline-flex dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <BookMarked className="size-4" aria-hidden /> {cs.words.link}
            </Link>
            <Link
              href="/insights"
              className="hidden items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 lg:inline-flex dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <BarChart3 className="size-4" aria-hidden /> {cs.insights.link}
            </Link>
            <Link
              href="/settings"
              aria-label={cs.settings.title}
              className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <Settings className="size-4" aria-hidden /> <span className="hidden sm:inline">{cs.settings.title}</span>
            </Link>
            {me.can_manage && (
              <Link
                href="/profiles"
                aria-label={cs.profiles.title}
                className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <Users className="size-4" aria-hidden /> <span className="hidden sm:inline">{cs.profiles.title}</span>
              </Link>
            )}
            {me.acting.id === me.principal.id && (
              <Button variant="ghost" className="!px-3 !py-2 text-sm" aria-label={cs.auth.logout} onClick={() => void signOut()}>
                <LogOut className="size-4" aria-hidden /> <span className="hidden sm:inline">{cs.auth.logout}</span>
              </Button>
            )}
          </nav>
          <BuildInfo className="justify-end px-3 text-right" />
        </div>
      </header>
      {me.acting.id !== me.principal.id && <ReturnToParent me={me} />}
      {children}
      <CommandPalette me={me} />
      <BottomTabs />
    </main>
  );
}

export function FullPageStatus({ text }: { text: string }) {
  return <p className="p-8 text-center text-slate-500">{text}</p>;
}
