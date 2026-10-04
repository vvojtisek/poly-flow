"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { ApiError, getMe, getSetupStatus, setCsrfToken, type Me } from "@/lib/api";
import { setBaseRate } from "@/lib/audio";
import { applyTheme } from "@/lib/theme";

type AuthState =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "anonymous"; needsSetup: boolean }
  | { kind: "signed_in"; me: Me };

interface AuthApi {
  state: AuthState;
  setMe: (me: Me | null) => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthApi | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ kind: "loading" });

  const setMe = useCallback((me: Me | null) => {
    setCsrfToken(me?.csrf_token ?? null);
    if (me) {
      // The acting profile's look and speech speed (a handed-over device takes the child's).
      applyTheme(me.acting.settings.theme);
      setBaseRate(me.acting.settings.audio_rate);
    }
    setState(me ? { kind: "signed_in", me } : { kind: "anonymous", needsSetup: false });
  }, []);

  const refresh = useCallback(async () => {
    try {
      setMe(await getMe());
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setCsrfToken(null);
        try {
          const { needs_setup } = await getSetupStatus();
          setState({ kind: "anonymous", needsSetup: needs_setup });
        } catch {
          setState({ kind: "error" });
        }
      } else {
        setState({ kind: "error" });
      }
    }
  }, [setMe]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return <AuthContext.Provider value={{ state, setMe, refresh }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthApi {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}

/** Signed-in session or null while loading/redirecting to /setup or /login. */
export function useRequireMe(): Me | null {
  const { state } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (state.kind === "anonymous") router.replace(state.needsSetup ? "/setup" : "/login");
  }, [state, router]);
  return state.kind === "signed_in" ? state.me : null;
}
