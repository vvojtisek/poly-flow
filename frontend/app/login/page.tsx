"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Button, CenteredCard, Field, Notice } from "@/components/ui";
import { ApiError, login } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

export default function LoginPage() {
  const { state, setMe } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [secret, setSecret] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (state.kind === "signed_in") router.replace("/");
    if (state.kind === "anonymous" && state.needsSetup) router.replace("/setup");
  }, [state, router]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setMe(await login(username, secret));
      router.replace("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) setError(cs.auth.tooMany);
      else if (err instanceof ApiError && err.status < 500) setError(cs.auth.invalid);
      else setError(cs.common.offline);
    } finally {
      setBusy(false);
    }
  }

  return (
    <CenteredCard title={cs.auth.loginTitle}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field
          label={cs.auth.username}
          autoComplete="username"
          autoCapitalize="none"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <Field
          label={cs.auth.secret}
          type="password"
          autoComplete="current-password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          required
        />
        {error && <Notice tone="error">{error}</Notice>}
        <Button type="submit" disabled={busy}>
          {cs.auth.submit}
        </Button>
        <p className="text-xs text-slate-500">{cs.auth.childHint}</p>
      </form>
    </CenteredCard>
  );
}
