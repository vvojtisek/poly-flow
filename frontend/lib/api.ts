// Typed API client. Response types mirror backend Pydantic models (backend/app/schemas).
// Same-origin: next.config.ts proxies /api/* and /readyz to the backend, so the session
// cookie is first-party and HttpOnly; JS only ever sees the CSRF token.

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
    public readonly code: string,
  ) {
    super(`${status} ${code}`);
  }
}

let csrfToken: string | null = null;
export const setCsrfToken = (token: string | null) => {
  csrfToken = token;
};

type Init = RequestInit & { acceptStatuses?: number[]; json?: unknown };

export async function api<T>(path: string, init: Init = {}): Promise<T> {
  const { json, acceptStatuses, ...rest } = init;
  const method = (rest.method ?? (json !== undefined ? "POST" : "GET")).toUpperCase();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (json !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET" && csrfToken) headers["X-CSRF-Token"] = csrfToken;
  const res = await fetch(path, {
    ...rest,
    method,
    credentials: "same-origin",
    headers: { ...headers, ...(rest.headers as Record<string, string> | undefined) },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (res.status === 204) return undefined as T;
  if (!res.ok && !acceptStatuses?.includes(res.status)) {
    let code = `http_${res.status}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") code = body.detail;
      else if (Array.isArray(body?.detail)) code = "validation_error";
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, code);
  }
  return (await res.json()) as T;
}

export const apiGet = <T>(path: string, init?: Init) => api<T>(path, init);

// ---------------------------------------------------------------- progression & health

export type Language = "de" | "fr" | "it" | "en";
export const LANGUAGES: Language[] = ["de", "fr", "it", "en"];
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
  api<Progression>("/api/v1/progression/milestones", { signal });

// /readyz answers 503 with a valid body when a dependency is down.
export const getReadiness = (signal?: AbortSignal) =>
  api<Readiness>("/readyz", { signal, cache: "no-store", acceptStatuses: [503] });

// ---------------------------------------------------------------- profiles & auth

export interface ProfileSettings {
  daily_goal_minutes: number;
  audio_rate: number;
  autoplay_audio: boolean;
}

export interface Profile {
  id: string;
  username: string;
  display_name: string;
  role: "admin" | "learner";
  is_child: boolean;
  is_active: boolean;
  has_pin: boolean;
  has_password: boolean;
  active_language: Language;
  timezone: string;
  settings: ProfileSettings;
}

export interface Me {
  principal: Profile;
  acting: Profile;
  csrf_token: string;
  can_manage: boolean;
}

export const getSetupStatus = () => api<{ needs_setup: boolean }>("/api/v1/setup");
export const runSetup = (body: { username: string; display_name: string; password: string }) =>
  api<Me>("/api/v1/setup", { json: body });
export const login = (username: string, secret: string) =>
  api<Me>("/api/v1/auth/login", { json: { username, secret } });
export const logout = () => api<void>("/api/v1/auth/logout", { method: "POST" });
export const getMe = () => api<Me>("/api/v1/auth/me");
export const switchProfile = (profile_id: string) =>
  api<Me>("/api/v1/auth/switch", { json: { profile_id } });
export const returnToParent = (password: string) =>
  api<Me>("/api/v1/auth/return", { json: { password } });
export const updateOwnProfile = (body: Partial<Pick<Profile, "active_language" | "display_name">>) =>
  api<Profile>("/api/v1/me/profile", { method: "PATCH", json: body });
export const listProfiles = () => api<Profile[]>("/api/v1/profiles");
export const createProfile = (body: {
  username: string;
  display_name: string;
  kind: "adult" | "child";
  password?: string;
  pin?: string;
}) => api<Profile>("/api/v1/profiles", { json: body });
export const updateProfile = (id: string, body: { is_child?: boolean; is_active?: boolean }) =>
  api<Profile>(`/api/v1/profiles/${id}`, { method: "PATCH", json: body });

// ---------------------------------------------------------------- learning

export type TaskType = "recognition" | "recall";
// learn = Lekce (context first, practice never graded); check = Ověření (the only graded mode)
export type SessionMode = "learn" | "check";

export interface SceneSegment {
  text: string;
  item_id: string | null; // a lexicon word: tap for its gloss
  gloss: string | null;
  new: boolean; // introduced by this lesson
}

export interface Scene {
  title: string;
  lines: { speaker: string | null; cs: string; segments: SceneSegment[] }[];
}

export interface WordCard {
  id: string;
  lemma: string;
  pos: string;
  gender: string | null;
  ipa: string | null;
  translation: string;
  context: string | null;
  context_cs: string | null;
}
export type Verdict = "exact" | "accepted_variant" | "case" | "diacritics" | "wrong" | "revealed";

export interface LessonSession {
  id: string;
  language: Language;
  mode: SessionMode;
  status: "active" | "completed" | "abandoned";
  total: number;
  remaining: number;
  created_at: string;
  completed_at: string | null;
  summary: Partial<{
    total: number;
    done: number;
    revealed: number;
    skipped: number;
    first_try_correct: number;
    new_items: number;
    reviewed_items: number;
  }>;
  scene: Scene | null;
  words: WordCard[];
}

export interface Task {
  id: string;
  session_id: string;
  position: number;
  total: number;
  type: TaskType;
  status: "pending" | "done" | "revealed";
  attempts: number;
  hint_level: number;
  is_new_item: boolean;
  prompt: string;
  pos: string;
  gender: string | null;
  example: string | null;
  cloze: string | null; // recall: example sentence with the target word blanked
  options: { id: number; text: string }[] | null;
  hint: string | null;
}

export interface AnswerResult {
  task_id: string;
  correct: boolean;
  verdict: Verdict;
  note: string | null;
  counted: boolean;
  attempts: number;
  task_done: boolean;
  can_retry: boolean;
  expected: string | null;
  meaning: string | null;
}

export interface ProgressOverview {
  language: Language;
  lexicon_items: number;
  seen: number;
  by_state: Record<"NEW" | "LEARNING" | "MASTERED", number>;
  passive_known: number;
  active_known: number;
  known: number;
  introduced: number;
  due_now: number;
  orthography_avg: number | null;
  phonetic_measured: number;
  grammar_unlocked: boolean;
  grammar_gate: number;
  next_milestone: number | null;
  next_milestone_cefr: CefrLevel | null;
  by_band: { band: number; items: number; known: number }[];
  active_session_id: string | null;
  active_check_session_id: string | null;
}

export const startLesson = (language: Language, mode: SessionMode = "learn") =>
  api<{ session: LessonSession | null }>("/api/v1/learning/sessions", { json: { language, mode } });
export const nextTask = (sessionId: string) =>
  api<{ task: Task | null }>(`/api/v1/learning/sessions/${sessionId}/next`, { cache: "no-store" });
export const requestHint = (taskId: string) =>
  api<Task>(`/api/v1/learning/tasks/${taskId}/hint`, { method: "POST" });
export const submitAnswer = (
  taskId: string,
  body: { idempotency_key: string; choice?: number; text?: string },
) => api<AnswerResult>(`/api/v1/learning/tasks/${taskId}/answer`, { json: body });
export const revealAnswer = (taskId: string, idempotency_key: string) =>
  api<AnswerResult>(`/api/v1/learning/tasks/${taskId}/reveal`, { json: { idempotency_key } });
export const completeLesson = (sessionId: string) =>
  api<LessonSession>(`/api/v1/learning/sessions/${sessionId}/complete`, { method: "POST" });

// Speech (WAV) for content the lesson already shows; played through lib/audio.ts.
export const sceneLineAudioUrl = (sessionId: string, line: number) =>
  `/api/v1/learning/sessions/${sessionId}/audio?line=${line}`;
export const wordAudioUrl = (sessionId: string, itemId: string, part: "word" | "context") =>
  `/api/v1/learning/sessions/${sessionId}/audio?item=${itemId}&part=${part}`;
export const taskAudioUrl = (taskId: string, part: "word" | "example") =>
  `/api/v1/learning/tasks/${taskId}/audio?part=${part}`;
export const getProgress = (language: Language) =>
  api<ProgressOverview>(`/api/v1/learning/progress?language=${language}`, { cache: "no-store" });

export const newIdempotencyKey = () => crypto.randomUUID().replaceAll("-", "");
