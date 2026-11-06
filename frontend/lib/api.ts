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

export type Theme = "light" | "dark" | "system";

export interface ProfileSettings {
  daily_goal_minutes: number;
  audio_rate: number;
  autoplay_audio: boolean;
  theme: Theme;
  interests: string[];
  voices: Partial<Record<Language, string>>;
  learn_profanity: boolean;
}

export interface Voice {
  id: string;
  language: Language;
  name: string;
  gender: "female" | "male";
  default: boolean;
  installed: boolean;
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
export const updateOwnProfile = (
  body: Partial<Pick<Profile, "active_language" | "display_name">> & { settings?: Partial<ProfileSettings> },
) => api<Profile>("/api/v1/me/profile", { method: "PATCH", json: body });
export const listVoices = (signal?: AbortSignal) => api<Voice[]>("/api/v1/voices", { signal });
export const voiceSampleUrl = (voiceId: string) => `/api/v1/voices/${encodeURIComponent(voiceId)}/sample`;
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
// learn = Lekce (context first, practice never graded); check = Ověření (the only graded mode);
// placement = rozřazovací test (graded like a check, adaptive);
// exam = zkouška úrovně slovní zásoby A1-B2 (graded like a check, fixed sample of one band)
export type SessionMode = "learn" | "check" | "placement" | "exam";
export type ExamLevel = "A1" | "A2" | "B1" | "B2";

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
export type Verdict =
  | "exact"
  | "accepted_variant"
  | "case"
  | "diacritics"
  | "wrong"
  | "revealed"
  | "spoken" // a spoken answer whose transcript is the word
  | "not_understood"; // a spoken answer the transcript cannot confirm; nothing changed

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
    // placement only
    placed: boolean; // false: stopped before enough answers, nothing changed
    asked: number;
    level: number; // recognised up to about this frequency rank
    level_low: number;
    level_high: number;
    ceiling: number; // highest rank the app holds: the test cannot place higher
    at_ceiling: boolean;
    queued: number; // words up to the level, not asked: waiting in Ověření to be confirmed
    // exam only
    exam_level: ExamLevel;
    passed: boolean;
    correct: number;
    answered: number;
    pass_correct: number;
    missed: { lemma: string; gender: string | null; translation: string }[];
    retry_from: string; // failed: the next try opens then
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
  error?: string | null; // what a wrong answer got wrong (mistake engine)
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
  active_placement_session_id: string | null;
  placement: Placement | null; // null: the test was never taken or skipped for this language
  active_exam_session_id: string | null;
  level_badges: LevelBadge[];
  cefr_level?: string | null;
}

// A passed level exam: a vocabulary level, not a CEFR certificate.
export interface LevelBadge {
  level: ExamLevel;
  earned_at: string;
  correct: number;
  asked: number;
}

export type LevelState =
  | "earned"
  | "in_progress"
  | "missing_words" // the band is not imported yet
  | "needs_previous"
  | "not_ready" // too little of the band known
  | "retry_later" // failed: retake from `retry_from`
  | "available";

export interface LevelStatus {
  level: ExamLevel;
  low: number;
  high: number;
  state: LevelState;
  lexicon_items: number;
  pool: number;
  known: number;
  ready_known: number;
  earned_at: string | null;
  retry_from: string | null;
  active_session_id: string | null;
  last_correct: number | null;
  last_asked: number | null;
}

export interface LevelsInfo {
  language: Language;
  questions: number;
  pass_correct: number;
  levels: LevelStatus[];
}

export interface Placement {
  status: "placed" | "skipped";
  level: number | null;
  level_low: number | null;
  level_high: number | null;
  ceiling: number | null;
  decided_at: string;
}

export interface PlacementInfo {
  language: Language;
  ceiling: number; // highest rank the test can ask now
  max_questions: number;
  placement: Placement | null;
  active_session_id: string | null;
}

export const startLesson = (language: Language, mode: SessionMode = "learn", level?: ExamLevel) =>
  api<{ session: LessonSession | null }>("/api/v1/learning/sessions", {
    json: level ? { language, mode, level } : { language, mode },
  });
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

export const getPlacementInfo = (language: Language) =>
  api<PlacementInfo>(`/api/v1/learning/placement?language=${language}`, { cache: "no-store" });
export const getLevels = (language: Language) =>
  api<LevelsInfo>(`/api/v1/learning/levels?language=${language}`, { cache: "no-store" });
export const skipPlacement = (language: Language) =>
  api<void>("/api/v1/learning/placement/skip", { json: { language } });

// Speech (WAV) for content the lesson already shows; played through lib/audio.ts.
export const sceneLineAudioUrl = (sessionId: string, line: number) =>
  `/api/v1/learning/sessions/${sessionId}/audio?line=${line}`;
export const wordAudioUrl = (sessionId: string, itemId: string, part: "word" | "context") =>
  `/api/v1/learning/sessions/${sessionId}/audio?item=${itemId}&part=${part}`;
export const taskAudioUrl = (taskId: string, part: "word" | "example") =>
  `/api/v1/learning/tasks/${taskId}/audio?part=${part}`;
export const getProgress = (language: Language) =>
  api<ProgressOverview>(`/api/v1/learning/progress?language=${language}`, { cache: "no-store" });

// Answer a recall task by voice; the recording is transcribed on the server and discarded.
export const submitSpeech = (taskId: string, idempotency_key: string, recording: Blob) =>
  api<AnswerResult>(`/api/v1/learning/tasks/${taskId}/speech?idempotency_key=${idempotency_key}`, {
    method: "POST",
    body: recording,
    headers: { "Content-Type": recording.type || "audio/webm" },
  });
// crypto.randomUUID() is only defined in a secure context; a self-hosted LAN served over plain
// HTTP is not one, so fall back to getRandomValues (available everywhere, including insecure
// contexts). Both branches yield 32 hex chars, matching the backend idempotency-key pattern.
export const newIdempotencyKey = () =>
  crypto.randomUUID?.().replaceAll("-", "") ??
  Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, "0")).join("");

// ---------------------------------------------------------------- grammar

export type UnitState = "new" | "studied" | "known" | "mastered";
export type ExerciseKind = "choice" | "gap" | "order" | "translate";

export interface GrammarNote {
  heading: string;
  text: string;
  table?: string[][] | null;
}

export interface GrammarUnitSummary {
  id: string;
  level: CefrLevel;
  title: string;
  summary: string;
  status: UnitState;
  exercises: number;
  due: boolean;
  recent_errors: number;
  next_review_at: string | null;
}

export interface GrammarTree {
  language: Language;
  open: boolean;
  due: number;
  recommended: string | null;
  review_status: "unreviewed" | "reviewed" | "mixed" | null;
  levels: { level: CefrLevel; units: GrammarUnitSummary[] }[];
  active_lesson_unit: string | null;
  active_check_session_id: string | null;
}

export interface GrammarUnit {
  id: string;
  level: CefrLevel;
  title: string;
  summary: string;
  notes: GrammarNote[];
  examples: { text: string; cs: string }[];
  status: UnitState;
  review_status: string;
  source: string;
}

export interface GrammarSession {
  id: string;
  language: Language;
  mode: "learn" | "check";
  status: "active" | "completed";
  unit: GrammarUnit | null;
  total: number;
  remaining: number;
  summary: {
    total?: number;
    done?: number;
    revealed?: number;
    first_try_correct?: number;
    remediation?: number;
    abandoned?: boolean;
  };
}

export interface GrammarExercise {
  item_id: string;
  session_id: string;
  position: number;
  total: number;
  kind: ExerciseKind;
  prompt: string;
  prompt_cs: string | null;
  direction: "cs-target" | "target-cs" | null;
  options: string[] | null;
  tokens: string[] | null;
  unit_id: string;
  unit_title: string;
  is_remediation: boolean;
  status: "pending" | "done" | "revealed";
  attempts: number;
}

export interface GrammarResult {
  item_id: string;
  correct: boolean;
  verdict: string;
  note: string | null;
  error: string | null;
  counted: boolean;
  attempts: number;
  task_done: boolean;
  can_retry: boolean;
  expected: string | null;
  solution: string | null;
  explanation: string | null;
  unit_id: string;
  unit_title: string;
}

export const getGrammarTree = (language: Language) =>
  api<GrammarTree>(`/api/v1/grammar?language=${language}`, { cache: "no-store" });
export const getGrammarUnit = (unitId: string) =>
  api<GrammarUnit>(`/api/v1/grammar/units/${encodeURIComponent(unitId)}`, { cache: "no-store" });
export const startGrammarLesson = (unitId: string) =>
  api<{ session: GrammarSession | null }>(`/api/v1/grammar/units/${encodeURIComponent(unitId)}/lesson`, {
    method: "POST",
  });
export const startGrammarCheck = (language: Language) =>
  api<{ session: GrammarSession | null }>("/api/v1/grammar/check", { json: { language } });
export const nextGrammarItem = (sessionId: string) =>
  api<{ item: GrammarExercise | null }>(`/api/v1/grammar/sessions/${sessionId}/next`, { cache: "no-store" });
export const answerGrammar = (itemId: string, body: { idempotency_key: string; choice?: number; text?: string }) =>
  api<GrammarResult>(`/api/v1/grammar/items/${itemId}/answer`, { json: body });
export const revealGrammar = (itemId: string, idempotency_key: string) =>
  api<GrammarResult>(`/api/v1/grammar/items/${itemId}/reveal`, { json: { idempotency_key } });
export const completeGrammar = (sessionId: string) =>
  api<GrammarSession>(`/api/v1/grammar/sessions/${sessionId}/complete`, { method: "POST" });

// ---------------------------------------------------------------- mistakes

export interface WeakSpots {
  language: Language;
  window_days: number;
  words: { lemma: string; gender: string | null; translation: string; errors: number; last_error_at: string; tags: string[] }[];
  units: { id: string; title: string; level: string; errors: number; last_error_at: string; tags: string[] }[];
  tags: [string, number][];
}

export const getWeakSpots = (language: Language) =>
  api<WeakSpots>(`/api/v1/learning/weak-spots?language=${language}`, { cache: "no-store" });

// ---------------------------------------------------------------- tutor

export interface TutorExplanation {
  source: "curriculum" | "model";
  text: string;
  model: string | null;
  can_ask: boolean;
}

/** "Proč?" for an answered word task or grammar item; refused (409) while it is still open. */
export const explainAnswer = (kind: "word" | "grammar", id: string, question?: string) =>
  api<TutorExplanation>("/api/v1/tutor/explain", { json: { kind, id, ...(question ? { question } : {}) } });

// ---------------------------------------------------------------- generated stories

export interface StoryLine {
  speaker: string | null;
  text: string;
  cs: string;
}

export interface Story {
  id: string;
  language: Language;
  kind: "story" | "dialogue";
  title: string;
  lines: StoryLine[];
  glossary: { word: string; cs: string }[];
  targets: string[];
  questions: { question: string; options: string[]; answered: boolean | null }[];
  model: string | null;
  review_status: "unreviewed";
}

export const getStoryToday = (language: Language) =>
  api<{ model_available: boolean; story: Story | null }>(`/api/v1/stories/today?language=${language}`, {
    cache: "no-store",
  });
export const generateStory = (language: Language, kind: Story["kind"]) =>
  api<Story>("/api/v1/stories/generate", { json: { language, kind } });
export const answerStoryQuestion = (storyId: string, index: number, choice: number) =>
  api<{ correct: boolean; answer_index: number }>(`/api/v1/stories/${storyId}/questions/${index}/answer`, {
    json: { choice },
  });
export const storyAudioUrl = (storyId: string, line: number) => `/api/v1/stories/${storyId}/audio?line=${line}`;

// ---------------------------------------------------------------- CEFR diagnostic (placement part 2)

export type DiagnosticSkill = "grammar" | "vocabulary" | "reading" | "listening" | "idiom";
export type DiagnosticBand = "pre-A1" | "A1" | "A2" | "B1" | "B2" | "B2+";

export interface DiagnosticInfo {
  available: boolean;
  review_status: string | null;
  items: number;
  bands: DiagnosticBand[];
  min_items: number;
  max_items: number;
  active_session_id: string | null;
  latest: { level: DiagnosticBand; decided_at: string; session_id: string | null } | null;
}

export interface DiagnosticQuestion {
  position: number;
  skill: DiagnosticSkill;
  band: DiagnosticBand;
  prompt: string;
  context: string | null;
  has_audio: boolean;
  options: string[];
  asked: number;
  max_items: number;
  theta: number;
}

export interface DiagnosticResult {
  placed: boolean;
  asked: number;
  level?: DiagnosticBand;
  next?: DiagnosticBand | null;
  low?: DiagnosticBand;
  high?: DiagnosticBand;
  theta?: number;
  correct?: number;
  skills?: { skill: DiagnosticSkill; asked: number; correct: number; expected: number; verdict: "strong" | "weak" | "even" | "few" }[];
  bands?: { band: DiagnosticBand; correct: number; asked: number }[];
  grammar_queued?: number;
  grammar_returned?: number;
  exams_opened?: CefrLevel[];
}

export interface DiagnosticState {
  session_id: string;
  language: Language;
  status: "active" | "completed" | "abandoned";
  with_listening: boolean;
  question: DiagnosticQuestion | null;
  result: DiagnosticResult | null;
}

export interface DiagnosticAnswer {
  position: number;
  correct: boolean;
  dont_know: boolean;
  answer: string;
  explain: string;
  transcript: string | null;
  asked: number;
  max_items: number;
  theta: number;
}

export const getDiagnosticInfo = (language: Language) =>
  api<DiagnosticInfo>(`/api/v1/diagnostic?language=${language}`);
export const startDiagnostic = (language: Language) =>
  api<DiagnosticState>("/api/v1/diagnostic/sessions", { json: { language } });
export const getDiagnostic = (sessionId: string) => api<DiagnosticState>(`/api/v1/diagnostic/sessions/${sessionId}`);
export const answerDiagnostic = (sessionId: string, position: number, choice: string | null) =>
  api<DiagnosticAnswer>(`/api/v1/diagnostic/sessions/${sessionId}/answer`, { json: { position, choice } });
export const stopDiagnostic = (sessionId: string) =>
  api<DiagnosticState>(`/api/v1/diagnostic/sessions/${sessionId}/stop`, { method: "POST" });
export const diagnosticAudioUrl = (sessionId: string, position: number) =>
  `/api/v1/diagnostic/sessions/${sessionId}/audio?position=${position}`;
