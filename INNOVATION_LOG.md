# Innovation log: 30-cycle product loop

Started 2026-11-06 at Vlad's request, on top of `main` at `a31cd1f` (1.0.0-alpha.5). Each cycle
ships one bold, tested change as its own commit (`Cycle N/30: ...`). Work stays local until Vlad
approves a push; bundles are backed up to the project files under `innovation-cycles/`.

Ground rules carried over from `AGENTS.md` and Vlad's decisions: Lekce (ungraded) and Ověření
(graded, the only evidence) stay separate; nothing counts as known by assumption; child profiles
get age-appropriate content only; every feature works without an LLM; drafted content is marked
unreviewed.

| Cycle | Change | Why it helps the learner |
|---|---|---|
| 1 | Adaptive CEFR placement test A1-B2+ | finds the real ceiling up to B2+, unlocks the curriculum |
| 2 | Personal mastery rank path | a visible journey tied to proven learning, no traps |
| 3 | Command palette (Ctrl+K) | keyboard-first navigation and settings from anywhere |
| 4 | Learning insights dashboard | activity calendar, accuracy trend, mistake types, review forecast |
| 5 | My dictionary + word inspector | look up any learned word, its state, audio and history |
| 6 | Today's plan + goal ring | one button to the most useful next step, calm daily goal |
| 7 | Dictation drill (Diktát) | hear a sentence, type it, word-level diff; ungraded practice |
| 8 | German case lab | build a noun phrase, see which word carries the case signal |
| 9 | Shadowing studio (Stínování) | listen, repeat aloud, compare rhythm outlines; recordings never leave the browser |
| 10 | Gender sorter (Rody) | 1-2-3 keyboard sorting with ending rules on a miss, optional 60 s test |
| 11 | Role-play (Hraj roli) | play a lesson scene as one speaker: choose or type your lines |
| 12 | Practice hub + mobile tab bar | one home for all practice modes; thumb-reach navigation on phones |
| 13 | Reading comfort | per-profile text size, wider spacing, no animations; applied before first paint |
| 14 | Memory hooks (oslí můstky) | your own note per word: on lesson cards, in the dictionary, after a miss |
| 15 | German verb lab (Časování) | every lexicon verb in the present tense: stem, ending, prefix, why |
| 16 | Check review (Rozbor) | word-by-word result after a check: your answer, the right one, next review, add a hook |
| 17 | Welcome wizard (Vítej) | first run of a fresh profile: language, daily goal, rank path, text size, then placement or first lesson |

## Cycle 1/30: adaptive CEFR placement test (A1 to B2+)

**Before:** the placement test measured only vocabulary size (frequency rank of recognised
words). With the lexicon ending at 1,000 words it could not place anyone above A2, and it never
looked at grammar, reading or listening.

**Built:** part 2 of the *Rozřazovací test*, "gramatika a porozumění".

- Item banks for DE, EN (British), FR and IT: 40 items each across A1, A2, B1, B2 and an above-B2
  probe (shown as B2+, never as C1). Skills: grammar (cases, verb-final subordinate clauses,
  relative pronouns, conditionals, subjunctive, passive, inversion, nominal style), vocabulary in
  context, reading passages, listening (TTS, transcript after answering) and idioms.
- Adaptive engine (`app/domain/diagnostic.py`, policy `d1`): a 3PL item-response posterior over
  ability; each question is the most informative one at the current estimate, rotating skills.
  Correct A1/A2 answers escalate into B1/B2 within a few questions; struggling learners are held
  around their ceiling. Stops at 10-22 questions when the estimate is narrow. Starts from the
  vocabulary result when there is one. Simulated learners land in their band 70-85 % of the time
  and always in or next to it (tested).
- Unlocks: grammar units at or below the band skip their lesson and wait in Ověření gramatiky
  (`studied_by='placement'`, migration 0018); a retake that places lower returns unconfirmed
  units. Vocabulary level exams up to the band open without the known-words gate.
- UI: `/placement/cefr` with a live A1-B2+ ladder (band being probed plus a moving estimate
  marker), reading passages, listening with replay, "Nevím" (N), digit keys, explanation after
  each answer; a result screen with the band, the per-band score bars, strengths and weaker
  skills relative to the estimate, and what was unlocked. Part 1 now leads straight into part 2;
  the dashboard shows the latest CEFR band.

**Limits (stated in the UI):** items are Claude-drafted and unreviewed; difficulties are nominal
bands, not calibrated on learner data; the result is an estimate, not a certificate.

## Cycle 2/30: personal mastery rank path (hockey or royal)

**Before:** progress was numbers and bars only; nothing marked the journey from beginner to master,
and P6 gamification had been dropped because XP, coins and streaks reward activity, not learning.

**Built:** *Moje cesta*, a single-player rank path. This reverses the P6 drop only for personal
mastery ranks (noted in `AGENTS.md` and the plan).

- 10 ranks per language in two themes the learner picks: hockey (První krůčky na ledě, Jistý
  bruslař, Žákovská liga ... Národní reprezentant, Mistr světa, Olympijský šampion) or royal
  (Poddaný, Učeň, Páže, Panoš ... Vévoda, Král nebo královna jazyka), or hidden.
- Every requirement is evidence from Ověření: verified words (passive and active), grammar topics
  known from grammar checks, passed vocabulary level exams, and recovered mistakes (missed in a
  check, right in a later one). Thresholds follow the 100/500/1000/2500/5000 curriculum ladder.
  Grammar requirements cap at what the language offers, so FR/IT/EN are not held back.
- A reached rank is recorded (`mastery_awards`, migration 0019) and never taken back by decay. No
  points, no streaks, no comparison with other profiles.
- 17 achievements (words, grammar, learning from mistakes, exams, practice), measured the same way.
- Visual evolution: an emblem whose ring moves from bronze to silver, gold, platinum and diamond,
  with a theme icon per rank; it sits next to the learner's name in the header on every page.
- A one-time celebration dialog (pop-in emblem, colour burst, respects reduced motion) when a new
  rank or achievement is reached; the dashboard card and the full journey page show exactly what
  the next rank needs, with progress bars.

## Cycle 3/30: command palette (Ctrl+K)

**Before:** every destination was a header link or a dashboard button; on a desktop the learner had
to reach for the mouse to switch language, theme or page.

**Built:** a global command palette on every page. `Ctrl+K` / `Cmd+K`, or `/` outside text fields,
opens it; typing filters actions with diacritics-insensitive matching (`tmavy` finds *Tmavý*,
`cefr` finds the CEFR test), arrows move, Enter runs, Esc closes. Actions: every page (lesson,
check, grammar, reading, both placement parts, level exams, rank path, settings, family), switch
language, light/dark/system theme, rank theme, sign out. A visible "Hledat Ctrl K" button in the
header makes it discoverable; it is a proper combobox/listbox for screen readers.

## Cycle 4/30: learning insights dashboard (Statistiky)

**Before:** the dashboard showed totals only. A learner could not see when they study, whether
their accuracy improves, what kind of mistakes they make, or how much review is coming.

**Built:** `/insights` (header link, palette) backed by `GET /api/v1/insights`.

- Activity calendar for 26 weeks (graded and practice answers per local day). It is a calendar,
  not a streak: the copy says explicitly that a pause costs nothing.
- Review forecast for 14 days: words and grammar topics due per day (overdue counts as today),
  so the learner can plan instead of being surprised by a pile of reviews.
- First-try accuracy per week over 12 weeks (words and grammar checks).
- "Od lekce k jistotě" funnel: introduced, recognised, written, both, long-term mastered.
- Mistake types over 60 days, from the mistake engine's tags.

## Cycle 5/30: My dictionary (Můj slovník) with a word inspector

**Before:** once a word left a lesson, the learner could not look it up again, see how well they
knew it, or hear it outside a session.

**Built:** `/words` (header link, palette) with `GET /api/v1/words`, `/words/{id}` and
`/words/{id}/audio`.

- Lists only words the learner has met (a progress row exists), never the rest of the lexicon,
  so it does not bypass the lessons; child profiles never see flagged words (tested).
- Instant search over the word and its Czech meaning (debounced, `%`/`_` escaped), status filters
  with counts (učím se, poznám, umím, zvládnuté, viděné) and a "K opakování" filter.
- Keyboard-first: the search box has focus, arrows move through the list, Enter opens the card.
- Word card (side panel on desktop, bottom sheet on mobile): the word with its article coloured by
  gender, audio for the word and its example, IPA and frequency rank, the word's journey from
  seen to mastered, counts, next review in plain words, and a dot timeline of every answer
  (graded vs practice, error type on hover).

## Cycle 6/30: today's plan (Dnešní plán) with a goal ring

**Before:** the dashboard offered four equal buttons; the learner had to decide what to do first,
and the existing `daily_goal_minutes` setting was not shown anywhere.

**Built:** a plan banner on top of the dashboard (`GET /api/v1/today`).

- The next steps in a fixed, explainable order: due word checks first, then due grammar topics,
  then a new lesson, then a short reading. Each step shows its size and a time estimate; one
  "Pokračovat" button (Enter) starts the first step.
- A ring shows today's estimated minutes against the learner's own daily goal. The estimate comes
  from the answers given (no stopwatch runs during learning), the copy says so, and missing the
  goal has no consequence: no streak, nothing lost.
- Also reports how many words come due tomorrow.

## Cycle 7/30: dictation drill (Diktát)

**Before:** listening was only ever paired with a single word or a multiple-choice answer; there
was no way to practise turning a whole spoken sentence into correctly spelled text.

**Built:** `/dictation`, reachable from the dashboard and the command palette.

- Plays the example sentence of a word the learner has already had a lesson on (filtered by the
  child content filter); the text is never sent before an attempt (`GET /api/v1/dictation/next`
  returns only the item id and word count).
- The learner types with the special-character bar and Alt shortcuts; `POST /check` aligns the
  answer with the sentence (`app.domain.dictation`, difflib over folded tokens) and marks each
  word as exact, wrong case, missing accents, a different word, missing, or extra. The UI shows
  the diff with the expected word under every miss, the full sentence, and the lesson word.
- Strictly practice: nothing is recorded, nothing counts toward checks or ranks (learning vs
  testing split kept). Slow playback, Alt+P to replay, Enter to check and then continue; the
  session average stays on the page only.

## Cycle 8/30: German case lab (Laboratoř pádů)

**Before:** German cases and adjective endings were taught only as prose notes inside grammar
units; there was no way to see the whole system or play with it.

**Built:** `/grammar/cases`, linked from the grammar page and the palette.

- `app.domain.declension`: the full paradigm for der, ein, kein, mein and no determiner across four
  cases, three genders and the plural; weak/mixed/strong adjective declension; which word carries
  the case signal; adjective stems (hoch → hoh-, dunkel → dunkl-, teuer → teur-, indeclinable
  lila/rosa); nouns with genitive -s/-es, a listed (not guessed) n-declension set (Junge, Herr,
  Name → Namens), dative plural -n, plural-only nouns, and adjectival nouns excluded. 46 tests
  check every cell against the reference paradigm.
- `GET /api/v1/grammar/declension` sends the paradigm plus German nouns and adjectives from the
  lexicon (the learner's own words first, child filter applied) with all their forms computed
  on the server; the UI only puts pieces together.
- The builder: pick case (keys 1-4), determiner, singular/plural, adjective and noun (R for a
  random one). The phrase is shown large with gender colours, the case-signal ending highlighted,
  and a Czech explanation of why each ending appears (including n-declension). Beside it, the
  full table for the chosen determiner; clicking a cell rebuilds the phrase.
- Reference only: nothing is graded or recorded.

## Cycle 9/30: shadowing studio (Stínování)

**Before:** speaking was limited to saying single words for speech recognition; there was no way
to practise the melody and rhythm of whole sentences.

**Built:** `/shadowing`, on the dashboard next to dictation and in the palette.

- Example sentences of words the learner has had a lesson on (`GET /api/v1/dictation/sentences`,
  child filter applied), with the word and its meaning.
- Listen (normal or slow), record yourself (up to 15 s), play yourself back, or "Vzor a pak já"
  plays the model and then the recording. Text can be blurred for listen-first practice.
- A two-sided loudness outline puts the model (above) and the learner (below) on one time axis,
  with silence trimmed and both durations shown: a visual of rhythm and length, explicitly not
  a pronunciation score (speech-confidence invariant kept).
- Privacy: recordings stay as object URLs in the tab, are never uploaded, and are freed when the
  page closes. Without TTS the page says the model is missing and still allows recording.
- Keyboard: P, R, M, C, H, N. `useRecorder` gained a max-length option; `lib/audio` gained
  `clipSrc`, `playToEnd` and natural-speed playback for own recordings.

## Cycle 10/30: gender sorter (Rody)

**Before:** grammatical gender was only shown next to a word; nothing trained it on its own, and
the ending patterns that make most genders predictable were never taught.

**Built:** `/genders` for German (der/die/das), French and Italian (m/f), on the dashboard and in
the palette.

- `app.domain.gender_hints`: the reliable ending rules (-ung/-heit/-keit/-schaft → die always,
  -chen/-lein → das always, -ling/-ismus → der always, -e → die usually; French -tion/-sion → f,
  -ment/-age/-eau → m usually; Italian -zione/-tà → f, -o → m and -a → f usually) with a minimum
  word length, a certainty level, and an exception flag when the lexicon's gender differs.
  Rules too mixed to teach (French -eur, Italian -e and -ma) are left out on purpose. The
  lexicon gender stays authoritative; "m/f" nouns are skipped.
- `GET /api/v1/genders`: the learner's own nouns first, child filter applied.
- Practice mode (untimed, nothing recorded): keys 1-3 or arrows, gender colours, a correct pick
  moves on by itself; a miss shows the right gender, the ending rule (or that none exists, or
  that this word is an exception) and brings the word back three cards later. Optional "only my
  words" filter. A cheat sheet lists every rule with its certainty.
- "Test rychlosti 60 s": an explicitly separate timed test (learning stays untimed); the score
  is not recorded anywhere, only a personal best kept in this browser.

## Cycle 11/30: role-play a lesson scene (Hraj roli)

**Before:** a lesson's scene (a short dialogue) was read once at the start of the lesson and then
never used again.

**Built:** `/roleplay`, a scripted dialogue simulator over the reviewed scenes (no LLM).

- Offered scenes: ones the learner finished a lesson on, or whose words they have all met (for
  example through placement); scenes with a word hidden from the profile are skipped, as in
  lessons.
- Pick a scene and a role. The partner's lines appear as chat bubbles and are spoken (TTS, with a
  reading pause when TTS is off). On your turn you see what you want to say in Czech and either
  pick the right sentence from three (keys 1-3; a wrong pick is crossed out and you try again) or
  type it and get the word-level diff from the dictation engine.
- Distractors (`app.domain.roleplay`): one line from the same scene that does not fit the moment,
  one of similar length from another scene; deterministic per scene, role and line.
- Translations on demand under every bubble, replay any line, play again or swap roles at the
  end. Nothing is recorded; the "first try" count is shown only on the page.
- `WordDiff` was extracted from the dictation page and is shared.

## Cycle 12/30: practice hub (Procvičovna) and a mobile tab bar

**Before:** cycles 7-11 added five practice modes, each a separate button on the dashboard and a
link in an already crowded header that wrapped into three rows on a phone.

**Built:**

- `/practice`: one hub for every ungraded mode (role-play, dictation, shadowing, genders, case
  lab, reading), each card with what it is for and which skills it trains; modes appear only for
  languages they support (`lib/practice.ts` is the single list).
- Dashboard: the button grid became one "Otevřít procvičovnu" button plus compact chips.
- Phones get a fixed bottom tab bar (Domů, Lekce, Procvičovat, Slovník, Hledat → command
  palette), safe-area aware, hidden from lg up. The header shows text links only on desktop;
  settings, family and logout become icon buttons on small screens with their accessible names
  kept (the e2e suite looks up "Rodina" by name). Placement moved out of the header (it stays on
  the dashboard and in the palette).

## Cycle 13/30: reading comfort settings

**Before:** the only display choice was light/dark. Children, older family members and readers
who struggle with dense text had no way to make the app easier to read.

**Built:** a "Pohodlí při čtení" panel in settings, stored per profile on the server
(`ProfileSettings.text_size` s/m/l/xl, `reading_spacing`, `reduce_motion`), so a handed-over
device switches to the child's own display at once.

- Text size scales the whole UI (Tailwind sizes are rem-based; the root size changes).
- Wider letter, word and line spacing. The copy says it helps "some people, including many
  with dyslexia", which matches the evidence on letter spacing (for example Zorzi et al., 2012)
  without claiming a cure; no special "dyslexia font" is used because the evidence for those is
  weak.
- "Bez animací" switches off motion even when the device allows it (the app already honours the
  operating system's reduced-motion setting).
- Applied before first paint by the existing head script (cached in localStorage), then
  confirmed from the server profile; a live preview sentence shows the effect.

## Cycle 14/30: memory hooks (Oslí můstky)

**Before:** the app had no place for the learner's own way of remembering a word, which is one
of the most effective things a learner can do (self-generated mnemonics and elaboration).

**Built:** a private note per word and profile (migration 0020, table `word_notes`, up to 280
characters, whitespace collapsed, cascades with the profile and the word).

- Add or edit it on the lesson's word cards (while meeting the word), and in My dictionary's
  word card (`PUT /api/v1/words/{id}/note`; empty text removes it; any word the profile may see).
- After a miss in a lesson or a check, and after "show answer", the answer response carries the
  hook (`AnswerOut.hook`) and the feedback shows it. It is never shown before an answer, so a
  check stays a first-try check without hints.
- The note is the learner's own text: treated as untrusted, rendered as plain text, never logged
  and never shown to another profile.
- `NoteEditor` keeps the lesson's Enter hotkey away while typing (Enter saves, Shift+Enter adds a
  space, Escape cancels). Upgrade and downgrade of 0020 verified; `alembic check` clean.

## Cycle 15/30: German verb lab (Časování)

**Before:** verb forms appeared only inside grammar units; a learner could not look up how a
verb from their own dictionary conjugates, or see why.

**Built:** `/grammar/verbs` (linked from grammar, the practice hub and the palette).

- `app.domain.conjugation`: present tense by rules (-e-insertion after -t/-d and consonant + m/n
  with the ch/h distinction, -t only after s/ß/x/z, -eln/-ern), whole tables for sein, haben,
  werden, wissen, tun, the modals and möchten, a list of strong verbs with their du/er stem
  (found through inseparable prefixes: vergessen, gefallen, unterhalten, erfahren), and
  separable prefixes split off (ich lade … ein). `features()` names what is special about a
  verb. All 221 German lexicon verbs were generated and read through by hand; one rule bug
  (zeichnen, rechnen) was found that way and fixed; 47 tests pin the forms.
- `GET /api/v1/grammar/verbs`: the lexicon's verbs (own verbs first, child filter) with forms.
- The page: search, a table with the changed stem highlighted, the ending in colour and the
  prefix at the clause end, a plain-Czech explanation per feature, and an ungraded "type the
  form" drill over the learner's own verbs. The page says the forms are rule-built.

## Cycle 16/30: check review (Rozbor)

**Before:** the end of an Ověření showed two numbers ("1 / 6", "5 to repeat"); the learner could
not see which words they missed or what they had answered.

**Built:** `GET /api/v1/learning/sessions/{id}/review` (completed sessions only, owner only) and a
"Rozbor" section on the check's done screen.

- Missed words first: the word with gender colour and meaning, the learner's first answer
  struck through (or "answer shown"), the right answer, the kind of mistake, and when it comes
  back ("Znovu zítra"). Each missed word offers "Přidat oslí můstek" right there (cycle 14),
  at the moment it is most useful.
- Words right on the first try as chips with where they stand now (recognised / can write).
- Unanswered words are listed separately rather than counted as mistakes.
- Read-only over tasks, first-attempt events and progress; nothing new is recorded.

## Cycle 17/30: welcome wizard (Vítej)

**Before:** a new profile landed on the full dashboard with the placement offer, a language
picker and a rank card at once. The daily goal had no control anywhere in the UI, and the rank
path was only reachable from the ranks page.

**Built:** a five-step welcome dialog on the dashboard for a profile that has learned nothing
yet in its language and has not finished or skipped the welcome (`settings.onboarded`).

- Steps: language, daily goal (5–30 min, "just your goal, nothing is lost"), rank path
  (hockey / royal / none, with the first and last emblems), text size, and a finish step with
  "Rozřazovací test" or "První lekce".
- Every choice saves at once through the existing profile settings PATCH (merged, so nothing
  else is overwritten); "Přeskočit" on any step marks the welcome done.
- While it is shown, the rank celebration waits. Existing profiles with progress never see it.
- The daily goal is now also editable in Nastavení (comfort panel).
- Backend: one new settings field, `onboarded` (default false); test pins default and update.
