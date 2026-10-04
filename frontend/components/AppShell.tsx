"use client";

import { Compass, LogOut, Settings, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";

import { BuildInfo } from "@/components/BuildInfo";
import { Button, Field, Notice } from "@/components/ui";
import { ApiError, LANGUAGES, logout, returnToParent, updateOwnProfile, type Language, type Me } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

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

export function AppShell({ me, children }: { me: Me; children: ReactNode }) {
  const { setMe } = useAuth();
  const router = useRouter();

  async function signOut() {
    try {
      await logout();
    } finally {
      setMe(null);
      router.replace("/login");
    }
  }

  return (
    <main className="mx-auto flex min-h-full max-w-7xl flex-col gap-4 p-4 lg:p-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/" className="text-2xl font-bold text-brand-600">
            {cs.appName}
          </Link>
          <p className="text-sm text-slate-500">{me.acting.display_name}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <nav className="flex flex-wrap items-center justify-end gap-1">
            <Link
              href="/placement"
              className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <Compass className="size-4" aria-hidden /> {cs.placement.link}
            </Link>
            <Link
              href="/settings"
              className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <Settings className="size-4" aria-hidden /> {cs.settings.title}
            </Link>
            {me.can_manage && (
              <Link
                href="/profiles"
                className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <Users className="size-4" aria-hidden /> {cs.profiles.title}
              </Link>
            )}
            {me.acting.id === me.principal.id && (
              <Button variant="ghost" className="!px-3 !py-2 text-sm" onClick={() => void signOut()}>
                <LogOut className="size-4" aria-hidden /> {cs.auth.logout}
              </Button>
            )}
          </nav>
          <BuildInfo className="justify-end px-3 text-right" />
        </div>
      </header>
      {me.acting.id !== me.principal.id && <ReturnToParent me={me} />}
      {children}
    </main>
  );
}

export function FullPageStatus({ text }: { text: string }) {
  return <p className="p-8 text-center text-slate-500">{text}</p>;
}
