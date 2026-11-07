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
  english_variant: "uk" | "us";
  theme: Theme;
  interests: string[];
  voices: Partial<Record<Language, string>>;
  learn_profanity: boolean;
  rank_path: RankPath;
  text_size: TextSize;
  reading_spacing: boolean;
  reduce_motion: boolean;
  onboarded: boolean;
  news_seen: number;
  accent: Accent;
}

export type Accent = "blue" | "teal" | "violet" | "orange" | "pink";

export type TextSize = "s" | "m" | "l" | "xl";

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
  note: string | null; // the learner's own memory hook
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
  hook?: string | null; // the learner's memory hook, after a miss
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
  next_review_at: string | null;
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
  objective: string;
  status: UnitState;
  exercises: number;
  due: boolean;
  recent_errors: number;
  next_review_at: string | null;
  checked_correct: number;
  checked_errors: number;
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
  objective: string;
  notes: GrammarNote[];
  examples: { text: string; cs: string; variant?: "uk" | "us" | null }[];
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
export const grammarExampleAudioUrl = (unitId: string, example: number) =>
  `/api/v1/grammar/units/${encodeURIComponent(unitId)}/audio?example=${example}`;
export const getGrammarSearchIndex = (language: Language) =>
  api<{ id: string; text: string }[]>(`/api/v1/grammar/search-index?language=${language}`);
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
  words: { item_id: string; lemma: string; gender: string | null; translation: string; errors: number; last_error_at: string; tags: string[] }[];
  units: { id: string; title: string; level: string; errors: number; last_error_at: string; tags: string[] }[];
  tags: [string, number][];
}

export interface LessonPreview {
  scene_title: string | null;
  new_words: number;
  review_words: number;
}

export const getLessonPreview = (language: Language) =>
  api<LessonPreview>(`/api/v1/learning/next-lesson?language=${language}`, { cache: "no-store" });

export interface LanguageSummary {
  language: Language;
  introduced: number;
  known: number;
  due_now: number;
}

export const getLanguageSummaries = () =>
  api<LanguageSummary[]>("/api/v1/learning/languages", { cache: "no-store" });

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
  story_date: string;
  kind: "story" | "dialogue";
  title: string;
  lines: StoryLine[];
  glossary: { word: string; cs: string }[];
  targets: string[];
  questions: { question: string; options: string[]; answered: boolean | null }[];
  model: string | null;
  source_collection: string | null;
  review_status: "unreviewed";
}

export interface StoryArchiveItem {
  id: string;
  story_date: string;
  title: string;
  kind: "story" | "dialogue";
  source_collection: string | null;
  targets: string[];
}

export const getStoryToday = (language: Language) =>
  api<{ model_available: boolean; story: Story | null }>(`/api/v1/stories/today?language=${language}`, {
    cache: "no-store",
  });
export const listStoryArchive = (language: Language) =>
  api<StoryArchiveItem[]>(`/api/v1/stories/archive?language=${language}`, { cache: "no-store" });
export const getStory = (id: string) => api<Story>(`/api/v1/stories/${id}`, { cache: "no-store" });
export const deleteStory = (id: string) =>
  api<void>(`/api/v1/stories/${id}`, { method: "DELETE" });
export const generateStory = (language: Language, kind: Story["kind"], collectionId?: string) =>
  api<Story>("/api/v1/stories/generate", {
    json: { language, kind, ...(collectionId ? { collection_id: collectionId } : {}) },
  });
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

// ---------------------------------------------------------------- personal mastery ranks

export type RankPath = "hockey" | "royal" | "off";
export type RankTier = "bronze" | "silver" | "gold" | "platinum" | "diamond";

export interface RankRequirement {
  key: "known_words" | "grammar_known" | "badge" | "recoveries";
  target: number;
  current: number;
  level: string | null;
  met: boolean;
}

export interface RanksOverview {
  language: Language;
  path: RankPath;
  rank: number;
  max_rank: number;
  tier: RankTier;
  next: { rank: number; tier: RankTier; requirements: RankRequirement[] } | null;
  ranks: { rank: number; tier: RankTier; reached_at: string | null; requirements: RankRequirement[] }[];
  achievements: { key: string; group: string; reached_at: string | null }[];
  unseen_rank: number | null;
  unseen_achievements: string[];
  stats: {
    known_words: number;
    passive_words: number;
    grammar_known: number;
    grammar_total: number;
    recoveries: number;
    checks_answered: number;
    badges: string[];
  };
}

export const getRanks = (language: Language) => api<RanksOverview>(`/api/v1/ranks?language=${language}`);
export const markRanksSeen = (language: Language) => api<void>("/api/v1/ranks/seen", { json: { language } });

// ---------------------------------------------------------------- insights (statistics)

export interface Insights {
  language: Language;
  today: string;
  heatmap: { date: string; graded: number; practice: number }[];
  active_days: number;
  accuracy: { week: string; answered: number; correct: number }[];
  mistakes: { tag: string; count: number }[];
  forecast: {
    date: string;
    words: number;
    grammar: number;
    word_items: { id: string; lemma: string; gender: string | null; translation: string }[];
    grammar_items: { id: string; title: string; level: string }[];
  }[];
  funnel: { introduced: number; passive: number; active: number; known: number; mastered: number };
}

export interface ActivityDay {
  date: string;
  words: { id: string; lemma: string; gender: string | null; translation: string; graded: number; practice: number }[];
  grammar: { id: string; title: string; level: string; graded: number; practice: number }[];
}

export const getInsights = (language: Language) => api<Insights>(`/api/v1/insights?language=${language}`);
export const getActivityDay = (language: Language, date: string) =>
  api<ActivityDay>(`/api/v1/insights/day?language=${language}&date=${date}`, { cache: "no-store" });

// ---------------------------------------------------------------- my dictionary

export type WordStatus = "mastered" | "known" | "passive" | "learning" | "seen";

export interface WordRow {
  id: string;
  lemma: string;
  gender: string | null;
  pos: string;
  rank: number;
  translation: string;
  status: WordStatus;
  due: boolean;
  next_review_at: string | null;
  correct: number;
  errors: number;
}

export interface WordList {
  total: number;
  counts: Record<WordStatus, number>;
  items: WordRow[];
}

export interface WordDetail extends Omit<WordRow, "due"> {
  language: Language;
  ipa: string | null;
  example: string | null;
  review_status: string | null;
  passive_known: boolean;
  active_known: boolean;
  introduced_at: string | null;
  introduced_by: string | null;
  last_reviewed_at: string | null;
  review_streak: number;
  history: { at: string; correct: boolean; graded: boolean; task: string; mode: string; error_tag: string | null }[];
  note: string | null;
  /** Lesson scenes that teach the word; `line` is the scene line using it as written, if any. */
  contexts: { topic_id: string; title: string; line: string | null; line_cs: string | null; match: string | null }[];
  /** First-try, hint-free correct check answers toward the two separate knowledge states. */
  evidence: {
    recognition: { correct: number; days: number };
    production: { correct: number; days: number };
    required_correct: number;
    required_days: number;
    production_required_correct: number;
    production_required_days: number;
  };
}

// Vocabulary groups: levels by frequency rank (indicative CEFR, "extension" past the C1 band) and
// lesson topics. `mine` = words of the group this profile has met; only those become flashcards.
export interface WordLevelGroup {
  key: string;
  first_rank: number;
  last_rank: number | null;
  total: number;
  mine: number;
}
export interface WordTopicGroup {
  id: string;
  title: string;
  total: number;
  mine: number;
}
export interface WordGroups {
  levels: WordLevelGroup[];
  topics: WordTopicGroup[];
}
export type WordScope = { kind: "level"; key: string; label: string } | { kind: "topic"; id: string; label: string };
// Flashcard decks also accept the learner's unresolved check mistakes as a scope.
export type DeckScope = WordScope | { kind: "weak"; label: string };

export interface DeckCard {
  id: string;
  lemma: string;
  gender: string | null;
  pos: string;
  rank: number;
  translation: string;
  example: string | null;
  status: WordStatus;
  due: boolean;
}
export interface Deck {
  total: number;
  items: DeckCard[];
}

export const getWordGroups = (language: Language, signal?: AbortSignal) =>
  api<WordGroups>(`/api/v1/words/groups?language=${language}`, { signal, cache: "no-store" });

function scopeParams(p: URLSearchParams, scope: WordScope | null | undefined) {
  if (scope?.kind === "level") p.set("level", scope.key);
  if (scope?.kind === "topic") p.set("topic", scope.id);
}

export function getWordDeck(language: Language, scope: DeckScope, signal?: AbortSignal) {
  const p = new URLSearchParams({ language });
  if (scope.kind === "weak") p.set("weak", "true");
  else scopeParams(p, scope);
  return api<Deck>(`/api/v1/words/deck?${p}`, { signal, cache: "no-store" });
}

export type WordSort = "rank" | "review" | "errors" | "recent";

export function listWords(
  language: Language,
  opts: { q?: string; status?: WordStatus | null; due?: boolean; offset?: number; limit?: number; scope?: WordScope | null; sort?: WordSort },
  signal?: AbortSignal,
) {
  const p = new URLSearchParams({ language });
  scopeParams(p, opts.scope);
  if (opts.q) p.set("q", opts.q);
  if (opts.status) p.set("status", opts.status);
  if (opts.due) p.set("due", "true");
  if (opts.offset) p.set("offset", String(opts.offset));
  if (opts.limit) p.set("limit", String(opts.limit));
  if (opts.sort && opts.sort !== "rank") p.set("sort", opts.sort);
  return api<WordList>(`/api/v1/words?${p}`, { signal });
}
export const getWord = (id: string) => api<WordDetail>(`/api/v1/words/${id}`);
export const wordExportUrl = (language: Language, format: "csv" | "anki") =>
  `/api/v1/words/export?language=${language}&format=${format}`;
export const myWordAudioUrl = (id: string, part: "word" | "example" = "word") => `/api/v1/words/${id}/audio?part=${part}`;

// ---------------------------------------------------------------- today's plan

export interface TodayPlan {
  language: Language;
  date: string;
  minutes_today: number;
  answers_today: number;
  goal_minutes: number;
  steps: { kind: "check" | "grammar_check" | "lesson" | "reading"; count: number; minutes: number }[];
  tomorrow_due: number;
}

export const getToday = (language: Language) => api<TodayPlan>(`/api/v1/today?language=${language}`);

// ---------------------------------------------------------------- dictation (ungraded)

export interface DictationNext {
  item_id: string | null;
  words: number;
  pool: number;
}

export type DictationVerdict = "ok" | "case" | "accents" | "wrong" | "missing" | "extra";

export interface DictationResult {
  sentence: string;
  lemma: string;
  translation: string;
  marks: { expected: string | null; typed: string | null; verdict: DictationVerdict }[];
  score: number;
}

export function getDictationNext(language: Language, exclude: string[]) {
  const p = new URLSearchParams({ language });
  for (const id of exclude.slice(-50)) p.append("exclude", id);
  return api<DictationNext>(`/api/v1/dictation/next?${p}`);
}
export const checkDictation = (item_id: string, text: string) =>
  api<DictationResult>("/api/v1/dictation/check", { json: { item_id, text } });

// ---------------------------------------------------------------- German case lab

export type DeclCase = "nom" | "akk" | "dat" | "gen";
export type DeclGender = "m" | "f" | "n" | "pl";
export type DeclDet = "def" | "indef" | "kein" | "poss" | "none";
export interface DeclPiece {
  stem: string;
  ending: string;
}
export interface DeclCell {
  det: DeclDet;
  case: DeclCase;
  gender: DeclGender;
  determiner: DeclPiece | null;
  adjective_ending: string;
  kind: "weak" | "mixed" | "strong";
  signal: "determiner" | "adjective" | "noun";
}
export interface DeclNoun {
  lemma: string;
  gender: DeclGender;
  translation: string;
  met: boolean;
  n_declension: boolean;
  singular: Record<DeclCase, DeclPiece> | null;
  plural: Record<DeclCase, DeclPiece> | null;
}
export interface DeclAdjective {
  lemma: string;
  stem: string | null;
  translation: string;
  met: boolean;
}
export interface Declension {
  cells: DeclCell[];
  nouns: DeclNoun[];
  adjectives: DeclAdjective[];
}
export const getDeclension = () => api<Declension>("/api/v1/grammar/declension");

export interface PracticeSentence {
  item_id: string;
  sentence: string;
  lemma: string;
  translation: string;
}
export const getPracticeSentences = (language: Language) =>
  api<PracticeSentence[]>(`/api/v1/dictation/sentences?language=${language}`);

// ---------------------------------------------------------------- gender sorter (ungraded)

export interface GenderHint {
  suffix: string;
  gender: string;
  certainty: "always" | "usually";
  exception: boolean;
}
export interface GenderNoun {
  id: string;
  lemma: string;
  translation: string;
  gender: string;
  met: boolean;
  hint: GenderHint | null;
}
export interface GenderSet {
  language: Language;
  genders: string[];
  rules: { suffix: string; gender: string; certainty: "always" | "usually" }[];
  nouns: GenderNoun[];
}
export const getGenders = (language: Language) => api<GenderSet>(`/api/v1/genders?language=${language}`);

// ---------------------------------------------------------------- role-play (ungraded)

export interface RoleplayScene {
  id: string;
  title: string;
  speakers: string[];
  lines: number;
}
export interface RoleplayLine {
  speaker: string;
  text: string;
  cs: string;
  mine: boolean;
  options: string[] | null;
  answer: number | null;
}
export interface RoleplayScript {
  id: string;
  title: string;
  role: string;
  speakers: string[];
  lines: RoleplayLine[];
}
export const listRoleplay = (language: Language) => api<RoleplayScene[]>(`/api/v1/roleplay?language=${language}`);
export const getRoleplay = (id: string, role: string) =>
  api<RoleplayScript>(`/api/v1/roleplay/${id}?role=${encodeURIComponent(role)}`);
export const checkRoleplay = (id: string, line: number, text: string) =>
  api<{ marks: DictationResult["marks"]; score: number }>(`/api/v1/roleplay/${id}/check`, { json: { line, text } });
export const roleplayAudioUrl = (id: string, line: number) => `/api/v1/roleplay/${id}/audio?line=${line}`;

export const setWordNote = (id: string, text: string) =>
  api<{ note: string | null }>(`/api/v1/words/${id}/note`, { method: "PUT", json: { text } });

export interface WordCollection {
  id: string;
  name: string;
  count: number;
  created_at: string;
}
export interface WordCollectionDetail extends Omit<WordCollection, "count" | "created_at"> {
  language: Language;
  items: {
    id: string;
    lemma: string;
    gender: string | null;
    pos: string;
    translation: string;
    rank: number;
    example: string | null;
  }[];
}
export const listWordCollections = (language: Language) =>
  api<WordCollection[]>(`/api/v1/words/collections?language=${language}`);
export const getWordCollection = (id: string) =>
  api<WordCollectionDetail>(`/api/v1/words/collections/${id}`);
export const wordCollectionExportUrl = (id: string, format: "csv" | "anki") =>
  `/api/v1/words/collections/${id}/export?format=${format}`;
export const createWordCollection = (language: Language, name: string) =>
  api<WordCollection>("/api/v1/words/collections", { json: { language, name } });
export const renameWordCollection = (id: string, name: string) =>
  api<WordCollection>(`/api/v1/words/collections/${id}`, { method: "PUT", json: { name } });
export const addWordToCollection = (collectionId: string, itemId: string) =>
  api<void>(`/api/v1/words/collections/${collectionId}/items`, { json: { item_id: itemId } });
export const addWordsToCollection = (collectionId: string, itemIds: string[]) =>
  api<{ added: number }>(`/api/v1/words/collections/${collectionId}/items/bulk`, { json: { item_ids: itemIds } });
export const removeWordFromCollection = (collectionId: string, itemId: string) =>
  api<void>(`/api/v1/words/collections/${collectionId}/items/${itemId}`, { method: "DELETE" });
export const deleteWordCollection = (collectionId: string) =>
  api<void>(`/api/v1/words/collections/${collectionId}`, { method: "DELETE" });

// ---------------------------------------------------------------- German verb lab

export type VerbLanguage = "de" | "fr" | "it";
export const VERB_LANGUAGES: VerbLanguage[] = ["de", "fr", "it"];
export interface VerbForm {
  pronoun: string;
  stem: string;
  ending: string;
  changed: boolean;
}
export interface VerbEntry {
  lemma: string;
  translation: string;
  met: boolean;
  prefix: string | null;
  features: string[];
  forms: VerbForm[]; // six persons: singular 1-3, plural 1-3
}
export const getVerbs = (language: VerbLanguage) =>
  api<VerbEntry[]>(`/api/v1/grammar/verbs?language=${language}`);

// ---------------------------------------------------------------- session review

export interface ReviewItem {
  item_id: string;
  lemma: string;
  gender: string | null;
  translation: string;
  task: "recognition" | "recall";
  first_try: boolean | null;
  answered: string | null;
  expected: string;
  error: string | null;
  passive_known: boolean;
  active_known: boolean;
  next_review_at: string | null;
  note: string | null;
}
export const getSessionReview = (id: string) =>
  api<{ mode: SessionMode; items: ReviewItem[] }>(`/api/v1/learning/sessions/${id}/review`);

export type LookupHit = {
  id: string;
  lemma: string;
  translation: string;
  gender: string | null;
  pos: string;
  status: string | null;
  note: string | null;
};
export const lookupWord = (word: string, language: Language) =>
  api<LookupHit[]>(`/api/v1/lookup?language=${language}&word=${encodeURIComponent(word)}`);

export type NumberDirection = "write" | "read";
export const spellNumber = (n: number, language: Language) =>
  api<{ n: number; words: string }>(`/api/v1/numbers/spell?n=${n}&language=${language}`);
export const checkNumber = (body: { language: Language; n: number; answer: string; direction: NumberDirection }) =>
  api<{ correct: boolean; n: number; words: string }>("/api/v1/numbers/check", { method: "POST", json: body });
export const numberAudioUrl = (n: number, language: Language) => `/api/v1/numbers/audio?n=${n}&language=${language}`;

export type WordOrderPuzzle = { ref: string; tiles: string[]; end: string; cs: string | null; hint: string | null; pool: number };
export const nextWordOrder = (language: Language, exclude: string[]) =>
  api<WordOrderPuzzle | { ref: null; pool: 0 }>(
    `/api/v1/word-order/next?language=${language}${exclude.map((r) => `&exclude=${encodeURIComponent(r)}`).join("")}`,
  );
export const checkWordOrder = (language: Language, ref: string, order: string[]) =>
  api<{ correct: boolean; marks: boolean[]; sentence: string; cs: string | null }>(`/api/v1/word-order/check?language=${language}`, {
    method: "POST",
    json: { ref, order },
  });

export type ClockTime = { hour: number; minute: number; phrase: string; czech: string; digits: string };
export const clockQuiz = (language: Language, level: "quarters" | "five") =>
  api<{ time: ClockTime; options: ClockTime[]; answer: number }>(`/api/v1/clock/quiz?language=${language}&level=${level}`);
export const clockAudioUrl = (t: { hour: number; minute: number }, language: Language) =>
  `/api/v1/clock/audio?hour=${t.hour}&minute=${t.minute}&language=${language}`;

export type SoundExample = { id: string; lemma: string; translation: string; start: number; end: number; met: boolean };
export type SoundRule = { id: string; spelling: string; czech: string; note: string; examples: SoundExample[] };
export const getSounds = (language: Language) => api<SoundRule[]>(`/api/v1/sounds?language=${language}`);

export type PairWord = { text: string; cs: string };
export type PairSet = { id: string; title: string; hint: string; pairs: [PairWord, PairWord][] };
export const getPairSets = (language: Language) => api<PairSet[]>(`/api/v1/pairs?language=${language}`);
export const pairAudioUrl = (language: Language, set: string, pair: number, side: number) =>
  `/api/v1/pairs/audio?language=${language}&set=${set}&pair=${pair}&side=${side}`;

export type RecapWeek = { active_days: number; graded: number; correct: number; practice: number; introduced: number; newly_known: number; accuracy: number | null };
export type Recap = {
  language: Language;
  from: string;
  to: string;
  this_week: RecapWeek;
  last_week: RecapWeek;
  accuracy_trend: "up" | "down" | "same" | null;
  hard_words: { id: string; lemma: string; gender: string | null; translation: string; misses: number }[];
  due_now: number;
  due_next_7_days: number;
  suggestion: "check_due" | "fix_mistakes" | "new_lesson" | "start_small" | "keep_going";
};
export const getRecap = (language: Language) => api<Recap>(`/api/v1/insights/recap?language=${language}`, { cache: "no-store" });

// ---------------------------------------------------------------- what's new

export interface NewsEntry {
  n: number;
  date: string;
  title: string;
  blurb: string;
  href: string | null;
  new: boolean;
}
export interface News {
  latest: number;
  unseen: number;
  entries: NewsEntry[]; // newest first
}
export const getNews = () => api<News>("/api/v1/news");
export const markNewsSeen = () => api<News>("/api/v1/news/seen", { method: "POST" });
