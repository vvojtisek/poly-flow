"use client";

import { ArrowRightLeft, UserPlus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AppShell, FullPageStatus } from "@/components/AppShell";
import { Panel } from "@/components/Panel";
import { Button, Field, Notice } from "@/components/ui";
import {
  ApiError,
  LANGUAGES,
  createProfile,
  listProfiles,
  switchProfile,
  type Language,
  type Profile,
} from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const EMPTY = { username: "", display_name: "", password: "", pin: "", kind: "child" as "child" | "adult", active_language: "de" as Language };

export default function ProfilesPage() {
  const me = useRequireMe();
  const { setMe } = useAuth();
  const router = useRouter();
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    try {
      setProfiles(await listProfiles());
    } catch {
      setMessage({ tone: "error", text: cs.common.error });
    }
  }, []);

  useEffect(() => {
    if (me && !me.can_manage) router.replace("/");
    else if (me) void load();
  }, [me, router, load]);

  if (!me || !me.can_manage) return <FullPageStatus text={cs.common.loading} />;

  async function create(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await createProfile({
        username: form.username,
        display_name: form.display_name,
        kind: form.kind,
        active_language: form.active_language,
        ...(form.kind === "adult" ? { password: form.password } : form.pin ? { pin: form.pin } : {}),
      });
      setForm(EMPTY);
      setMessage({ tone: "ok", text: cs.profiles.created });
      await load();
    } catch (err) {
      const taken = err instanceof ApiError && err.status === 409;
      setMessage({ tone: "error", text: taken ? cs.profiles.taken : cs.profiles.invalid });
    }
  }

  async function handOver(p: Profile) {
    setMe(await switchProfile(p.id));
    router.push("/");
  }

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <AppShell me={me}>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={cs.profiles.manage} icon={ArrowRightLeft}>
          {profiles === null ? (
            <p className="text-sm text-slate-500">{cs.common.loading}</p>
          ) : (
            <ul className="divide-y divide-slate-200 dark:divide-slate-800">
              {profiles.map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-2 py-3">
                  <div>
                    <p className="font-medium">{p.display_name}</p>
                    <p className="text-xs text-slate-500">
                      @{p.username} · {p.role === "admin" ? cs.profiles.parent : p.is_child ? cs.profiles.child : cs.profiles.adult}
                      {p.is_child && !p.has_pin ? ` · ${cs.profiles.noPin}` : ""} · {cs.languages[p.active_language]}
                    </p>
                  </div>
                  {p.is_child && p.is_active && (
                    <Button variant="secondary" className="!py-2 text-sm" onClick={() => void handOver(p)}>
                      {cs.profiles.learnAs}
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title={cs.profiles.create} icon={UserPlus}>
          <form onSubmit={create} className="flex flex-col gap-3">
            <div role="radiogroup" aria-label={cs.profiles.kind} className="flex gap-2">
              {(["child", "adult"] as const).map((k) => (
                <Button
                  key={k}
                  role="radio"
                  aria-checked={form.kind === k}
                  variant={form.kind === k ? "primary" : "secondary"}
                  className="flex-1 !py-2"
                  onClick={() => setForm((f) => ({ ...f, kind: k }))}
                >
                  {k === "child" ? cs.profiles.child : cs.profiles.adult}
                </Button>
              ))}
            </div>
            <Field label={cs.setup.displayName} value={form.display_name} onChange={set("display_name")} required />
            <Field
              label={cs.auth.username}
              help={cs.setup.usernameHelp}
              autoCapitalize="none"
              pattern="[a-z0-9_.\-]{3,32}"
              value={form.username}
              onChange={set("username")}
              required
            />
            {form.kind === "adult" ? (
              <Field
                label={cs.auth.password}
                help={cs.setup.passwordHelp}
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={form.password}
                onChange={set("password")}
                required
              />
            ) : (
              <Field
                label={cs.profiles.pinOptional}
                help={cs.profiles.pinHelp}
                inputMode="numeric"
                pattern="[0-9]{4,8}"
                value={form.pin}
                onChange={set("pin")}
              />
            )}
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-slate-700 dark:text-slate-300">{cs.profiles.language}</span>
              <select
                className="rounded-xl border border-slate-300 bg-white px-3 py-3 dark:border-slate-700 dark:bg-slate-900"
                value={form.active_language}
                onChange={set("active_language")}
              >
                {LANGUAGES.map((l) => (
                  <option key={l} value={l}>
                    {cs.languages[l]}
                  </option>
                ))}
              </select>
            </label>
            {message && <Notice tone={message.tone}>{message.text}</Notice>}
            <Button type="submit">{cs.profiles.create}</Button>
          </form>
        </Panel>
      </div>
    </AppShell>
  );
}
