// Typed API client. Response types mirror backend Pydantic models (app/api/*).

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface DependencyCheck {
  ok: boolean;
  error: string | null;
}

export interface Readiness {
  status: "ready" | "unready";
  checks: Record<string, DependencyCheck>;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function apiGet<T>(
  path: string,
  init?: RequestInit & { acceptStatuses?: number[] },
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  if (!res.ok && !init?.acceptStatuses?.includes(res.status)) {
    throw new ApiError(res.status, `GET ${path} failed with ${res.status}`);
  }
  return (await res.json()) as T;
}

export type CefrLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2";

export interface Milestone {
  rank: number;
  key: string;
  cefr: CefrLevel | null;
  voluntary: boolean;
  passive_focus: boolean;
}

export interface Progression {
  curriculum_end: number;
  milestones: Milestone[];
}

export const getProgression = (signal?: AbortSignal) =>
  apiGet<Progression>("/api/v1/progression/milestones", { signal });

// /readyz answers 503 with a valid body when a dependency is down.
export const getReadiness = (signal?: AbortSignal) =>
  apiGet<Readiness>("/readyz", { signal, cache: "no-store", acceptStatuses: [503] });
