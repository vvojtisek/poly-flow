"use client";

import { useEffect, useState } from "react";

import { getReadiness, type Readiness } from "@/lib/api";

export type ReadinessState =
  | { kind: "loading" }
  | { kind: "ok"; data: Readiness }
  | { kind: "unreachable" };

export function useReadiness(intervalMs = 15_000): ReadinessState {
  const [state, setState] = useState<ReadinessState>({ kind: "loading" });

  useEffect(() => {
    let controller = new AbortController();
    const poll = async () => {
      controller.abort();
      controller = new AbortController();
      try {
        setState({ kind: "ok", data: await getReadiness(controller.signal) });
      } catch (err) {
        if ((err as Error).name !== "AbortError") setState({ kind: "unreachable" });
      }
    };
    void poll();
    const id = setInterval(poll, intervalMs);
    return () => {
      clearInterval(id);
      controller.abort();
    };
  }, [intervalMs]);

  return state;
}
