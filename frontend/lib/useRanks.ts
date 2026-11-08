"use client";

import { useCallback, useEffect, useState } from "react";

import { getRanks, type Language, type RanksOverview } from "@/lib/api";

// One fetch per language per page view is plenty: ranks only change after checks and exams.
const cache = new Map<string, { at: number; data: RanksOverview }>();
const TTL_MS = 30_000;
// Header and page mount together: share one request per key instead of racing two.
const inflight = new Map<string, Promise<RanksOverview>>();

export function invalidateRanks() {
  cache.clear();
  inflight.clear();
}

function fetchRanks(key: string, language: Language): Promise<RanksOverview> {
  let p = inflight.get(key);
  if (!p) {
    p = getRanks(language)
      .then((fresh) => {
        cache.set(key, { at: Date.now(), data: fresh });
        return fresh;
      })
      .finally(() => inflight.delete(key));
    inflight.set(key, p);
  }
  return p;
}

/** The profile's rank overview for `language`, or null while loading / when it failed. */
export function useRanks(language: Language | undefined, profileId: string | undefined) {
  const key = `${profileId}:${language}`;
  const [data, setData] = useState<RanksOverview | null>(() => cache.get(key)?.data ?? null);

  const reload = useCallback(async () => {
    if (!language) return;
    try {
      setData(await fetchRanks(key, language));
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
