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
