"use client";

import { useCallback, useEffect, useState } from "react";

import { getRanks, type Language, type RanksOverview } from "@/lib/api";

// One fetch per language per page view is plenty: ranks only change after checks and exams.
const cache = new Map<string, { at: number; data: RanksOverview }>();
const TTL_MS = 30_000;

export function invalidateRanks() {
  cache.clear();
}

/** The profile's rank overview for `language`, or null while loading / when it failed. */
export function useRanks(language: Language | undefined, profileId: string | undefined) {
  const key = `${profileId}:${language}`;
  const [data, setData] = useState<RanksOverview | null>(() => cache.get(key)?.data ?? null);

  const reload = useCallback(async () => {
    if (!language) return;
    try {
      const fresh = await getRanks(language);
      cache.set(key, { at: Date.now(), data: fresh });
      setData(fresh);
    } catch {
      /* ranks are a bonus: the page works without them */
    }
  }, [key, language]);

  useEffect(() => {
    const hit = cache.get(key);
    if (hit && Date.now() - hit.at < TTL_MS) {
      setData(hit.data);
      return;
    }
    setData(null);
    void reload();
  }, [key, reload]);

  return { data, reload };
}
