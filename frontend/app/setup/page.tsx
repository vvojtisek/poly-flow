"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button, CenteredCard, Field, Notice } from "@/components/ui";
import { ApiError, runSetup } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

export default function SetupPage() {
  const { state, setMe } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ username: "", display_name: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Set once this page created the account, so the "already signed in" redirect below
  // does not race the redirect to profile management.
  const justCreated = useRef(false);

  useEffect(() => {
    if (state.kind === "signed_in" && !justCreated.current) router.replace("/");
    if (state.kind === "anonymous" && !state.needsSetup) router.replace("/login");
  }, [state, router]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await runSetup(form);
      justCreated.current = true;
      setMe(me);
      router.replace("/profiles");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) router.replace("/login");
      else if (err instanceof ApiError && err.status === 422) setError(cs.profiles.invalid);
      else setError(cs.common.offline);
    } finally {
      setBusy(false);
    }
  }

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <CenteredCard title={cs.setup.title}>
      <p className="text-sm text-slate-600 dark:text-slate-300">{cs.setup.intro}</p>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label={cs.setup.displayName} value={form.display_name} onChange={set("display_name")} required />
        <Field
          label={cs.auth.username}
          help={cs.setup.usernameHelp}
          autoComplete="username"
          autoCapitalize="none"
          pattern="[a-z0-9_.\-]{3,32}"
          value={form.username}
          onChange={set("username")}
          required
        />
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
        {error && <Notice tone="error">{error}</Notice>}
        <Button type="submit" disabled={busy}>
          {cs.setup.submit}
        </Button>
      </form>
    </CenteredCard>
  );
}
