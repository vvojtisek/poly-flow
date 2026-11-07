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
| 18 | Tap to look up (Klepni na slovo) | every word in stories, role-play and dictation opens its dictionary entry: form → lemma by rules |
| 19 | Take your words with you (export) | own dictionary as a spreadsheet CSV or an Anki import file, with hooks, status and source |
| 20 | Number trainer (Čísla) | 0–9999 written, heard and read in DE/FR/IT/EN, spelled by rules with both French spellings accepted |
| 21 | Word order (Slovosled) | rebuild shuffled sentences from met scenes and example sentences; Czech meaning as the goal |
| 22 | Telling the time (Kolik je hodin?) | analog clock, everyday spoken forms in four languages, the Czech "čtvrt na" trap as a distractor |
| 23 | Accent colours (Barva) | five accent hues per profile; same contrast, never green or red, gender colours unchanged |
| 24 | Focus mode (Soustředění) | lessons and checks without header, tabs or links; key F, remembered per device |
| 25 | How letters sound (Jak se to čte) | spelling-to-sound rules for Czech readers in four languages, examples from the learner's own words |
| 26 | Minimal pairs (Slyšíš rozdíl?) | hear one word of a pair (ship/sheep, Tür/Tier, pala/palla, rue/roue) and pick it |
| 27 | Practice hub filters | filter 12 practice modes by skill, recently used modes first on the hub and dashboard |
| 28 | Weekly recap (Týden v kostce) | last 7 days against the 7 before, the words that gave trouble, and one suggested next step |
| 29 | Verb lab in French and Italian | the present tense lab from cycle 15 now conjugates French and Italian verbs, with spelling changes, elision and the irregular verbs |
| 30 | What's new (Co je nového) | the family finds the 26 features of this loop: a dashboard line with what is new, a page with links, seen per profile |

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

## Cycle 18/30: tap any word to look it up

**Before:** lesson scenes glossed their linked words, but stories, role-play lines and dictation
sentences were plain text. A learner who met "Kinder" or "gibt" had to leave the page and guess
the dictionary form.

**Built:** `GET /api/v1/lookup?word=&language=` and a `TapText` component.

- `app/domain/lookup.py` (pure rules): the tapped word is cleaned (punctuation, French and Italian
  elision such as l'homme, dell'acqua) and turned into candidate lemmas: the word itself, a short
  irregular list per language (ist → sein, went → go, ont → avoir, sono → essere), suffix rules
  (Kinder → Kind, cities → city, chevaux → cheval, ragazzi → ragazzo) and German umlaut plurals
  (Städte → Stadt). For German verbs the service adds a reverse index of the cycle-15 present
  forms (gibt → geben, stehe → aufstehen), ranked above suffix guesses (heiße → heißen, then heiß).
- The service matches candidates against the lexicon the profile may see (child filter applies),
  at most three entries, with the learner's status and memory hook. A word not met yet is shown
  as "Nové slovo"; looking up records nothing, so it never counts as knowing.
- The card shows the matched dictionary form (with article and gender colour), the meaning, the
  status, the hook, and the word's audio for met words. It stays inside the viewport and closes
  on Escape or a tap elsewhere. Results are cached per page load.
- Used in stories, every role-play line and the dictation answer.
- Known limit, stated in the module: a guess can hit a real but different lemma; the card shows
  the dictionary form so the learner can see which one was matched.

## Cycle 19/30: take your words with you (export)

**Before:** a learner's dictionary, hooks and review dates lived only inside PolyFlow. A family
that also uses Anki or a spreadsheet had to copy words by hand.

**Built:** `GET /api/v1/words/export?language=&format=csv|anki` and a "Stáhnout" menu in Můj
slovník.

- Only the acting profile's own met words in that language, child filter applied, frequency order.
- CSV for spreadsheets: lemma, article, Czech meaning, status, part of speech, rank, example,
  memory hook, next review date, right/wrong counts and the lexicon source. UTF-8 with a BOM so
  accents open correctly; cells that a spreadsheet would run as a formula (=, +, -, @) are
  prefixed with an apostrophe (CSV-injection guard, tested).
- Anki file: Anki's own file headers (tab separator, no HTML, tags in column 3), so it imports
  without settings. Front "der Hund", back "pes (hook)", tags `polyflow::de`, the status and
  `polyflow::source::claude-drafted` for drafted translations, so unreviewed glosses stay marked.
- Pure formatting in `app/domain/export.py`; the download is `no-store`.

## Cycle 20/30: number trainer (Čísla)

**Before:** numbers appeared only as a few lexicon words (eins, zwei ...). Prices, times, years
and phone numbers, which every A1 learner meets on day one, had no practice at all, and French
70–99 or German "einundzwanzig" are exactly where Czech speakers stumble.

**Built:** `app/domain/numbers.py`, `/api/v1/numbers/{spell,check,audio}` and the `/numbers` page.

- Rules for 0 to 9999 in all four languages: German unit-before-ten and one word; French
  soixante-dix / quatre-vingts (the s only on a bare 80 and bare hundreds), "et un" and
  "et onze"; Italian one word with the elided ventuno / ventotto / centotto and ventitré;
  British English with "and" after hundred and thousand.
- Accepted alternatives, so correct answers are never marked wrong: einhundert, eintausend,
  elfhundert; the French 1990 reform (hyphens everywhere) and "onze cents"; centootto, centuno,
  a missing accent on tre; English without "and", "a hundred", "eleven hundred". Hyphen and
  space count as the same; letters do not ("quatre-vingt" for 80 is wrong).
- Three modes: write the shown number in words, listen and type digits, read the words and type
  digits; four ranges. A right written answer plays the spoken number. A run of right answers is
  shown for the visit only; nothing is stored or graded.
- 93 tests: a table of pinned spellings per language, accepted and rejected answers, and every
  number 0–9999 in every language round-trips through `check`.
- Listening needs the local TTS; without it the page says so and points to the read mode.

## Cycle 21/30: word order (Slovosled)

**Before:** word order, the main structural difference between Czech (free order) and German
(verb second, verb at the end) or English (fixed SVO), was never practised on its own. Every
exercise checked words, not their position.

**Built:** `app/domain/word_order.py`, `/api/v1/word-order/{next,check}` and `/word-order`.

- The pool is reviewed text the learner has met: lines of scenes they finished (role-play rule:
  completed lesson or all words met), shown with the Czech line as the goal, and example
  sentences of introduced words, with "word = meaning" as the hint. 3 to 10 words; child filter
  as everywhere. Nothing is generated.
- The end punctuation is fixed, commas stay on their word, and the first word loses its capital
  when the lexicon (or a short closed list of pronouns and possessives) says it is not a noun or
  name, so the capital does not give the start away. The shuffle is deterministic per sentence.
- Tap (or press the number on) words to place them, tap a placed word to take it back,
  Backspace undoes. The check colours each position, shows the original sentence (tappable, the
  cycle-18 lookup) and says plainly that another order may also be possible: only the original is
  compared, so a different order is never called wrong grammar.
- Ungraded; nothing recorded. Tests cover splitting, usability, the shuffle, marks, the empty
  pool, capital handling, mismatched tiles (422) and unknown refs (404).

## Cycle 22/30: telling the time (Kolik je hodin?)

**Before:** time expressions were absent, although they are A1 material and a real trap for
Czech speakers: Czech "čtvrt na čtyři" is 3:15, German says "Viertel nach drei"; English
"half past three" is 3:30, not Czech "půl třetí".

**Built:** `app/domain/clock.py`, `/api/v1/clock/{quiz,audio}`, a `ClockFace` SVG and `/clock`.

- Everyday forms in five-minute steps: German (nach / vor / halb, "fünf vor halb vier"), French
  (et quart, et demie, moins le quart, une heure, midi / midi et demi), Italian (sono le / è l'una,
  e un quarto, e mezza, meno un quarto, mezzogiorno), British English (past / to, o'clock).
  One standard form per language; regional variants are named in the module and not used.
- Distractors are the mistakes learners make: the hour one off for quarters and halves (what the
  Czech anchor suggests), the mirrored minute (Viertel nach / vor), and five minutes off.
- Two modes: read the clock and pick the phrase, or hear and read the phrase and pick the clock.
  Quarter hours or every five minutes. After each answer: digits, the phrase with audio, and the
  Czech everyday form ("česky: čtvrt na osm") as the anchor.
- Tests pin the phrases per language, check that all 144 times read differently in every
  language, the Czech forms, distractors for every time, and the quiz API. Practice only.

## Cycle 23/30: accent colours (Barva)

**Before:** every profile looked the same blue. On a shared family device a child and a parent
could not tell at a glance whose profile was active, and a child could not make the app theirs.

**Built:** a per-profile `accent` setting (blue, teal, violet, orange, pink) in Nastavení > Vzhled.

- The accent redefines the four brand tokens on `<html data-accent>`; every brand button, link,
  ring and progress bar follows, with no component changes. Lightness and chroma match the
  default blue, so white text on brand buttons keeps the same contrast; only the hue turns.
- No accent is green or red, so a brand button never reads as "right" or "wrong", and the
  gender colours (der blue, die red, das green) are separate tokens that never change.
- Applied before first paint from local storage (same script as theme and text size), then from
  the profile on sign-in, so switching to a child's profile switches the colour.
- Server validation: only the five names are accepted (tested; "#ff0000" is a 422).

## Cycle 24/30: focus mode (Soustředění)

**Before:** a lesson or check sat under the full header (search, five links, rank, settings,
family, logout) and, on a phone, above the tab bar: a lot to look at for a child or anyone who
is easily distracted, and every link an exit from the task.

**Built:** focus mode on the lesson and check pages (`AppShell focusable`).

- "Soustředění" in the header or the F key (outside text fields) hides the navigation, the rank
  line and the mobile tab bar; a slim bar keeps the app name and "Ukončit soustředění". The
  version line moves to the foot of the page, so a build stays identifiable.
- "Return to the parent" stays visible on a handed-over device; the command palette (Ctrl+K)
  still works.
- Remembered per device (local storage, like the slow-audio toggle); other pages are unaffected.

## Cycle 25/30: how letters sound (Jak se to čte)

**Before:** Czech is read almost letter by letter, and nothing in the app told a Czech reader that
German "ei" is [aj], French "ou" is [u] or Italian "ci" is [č]. Learners met these only one word
at a time, by ear.

**Built:** `app/domain/sounds.py`, `GET /api/v1/sounds` and the `/sounds` page.

- 60 rules (German 19, French 17, Italian 10, English 14): the spelling, the nearest Czech sound
  (or "we do not have it": German soft ch, English th, ö, ü, French nasals) and a one-line note.
- Examples are taken from the lexicon at request time (child filter applied): words the learner
  has met first, each with the letters highlighted, its meaning and, for met words, its audio.
- Patterns are conservative on purpose and tested both ways: what must match (euch has a soft
  ch) and what must not (Schule is not ch, sechs reads ks, ville is an exception, school is k,
  book is a short u, tomorrow keeps its r).
- Marked on the page as simplified and not yet reviewed by a native speaker; "obvykle" marks
  rules with frequent exceptions. Reference only; nothing is recorded.

## Cycle 26/30: minimal pairs (Slyšíš rozdíl?)

**Before:** listening practice used whole sentences. Nothing trained the single contrasts a
Czech ear merges: German ü/i and long/short vowels, French u/ou and the nasals, Italian single
and double consonants, English ship/sheep, th, w/v and voiced final consonants (Czech devoices
them, so "bag" and "back" sound the same to a Czech speaker).

**Built:** `app/domain/minimal_pairs.py` (18 sets, 63 pairs), `/api/v1/pairs` and `/pairs`.

- Each set names the contrast and how to hear or make it; each pair has short Czech meanings so
  both words are real words to the learner (Tür dveře / Tier zvíře, pala lopata / palla míč).
- One word of a random pair is spoken (local TTS, slow toggle available); the learner picks it
  with a click or 1/2, then can play both to compare. A visit score is shown; nothing is stored.
- The audio endpoint speaks only words from the fixed sets (no free text). Without the speech
  server the page says so and the pairs stay readable.
- Marked as a drafted, unreviewed set. Tests check the data shape, lookups and the API bounds.

## Cycle 27/30: a practice hub that scales (filters and recents)

**Before:** cycles 7 to 26 grew the practice hub to 12 modes. A flat grid of 12 cards is
hard to scan on a phone, and the dashboard chips listed them in a fixed order.

**Built:** skill filters and "Naposledy" on `/practice`; recency order on the dashboard chips.

- Filter chips (Vše, poslech, mluvení, psaní, čtení, gramatika), only for skills the language
  has, with a live count ("6 způsobů procvičování").
- The last three practice modes opened on this device are shown first, recorded centrally in
  `AppShell` from the page path, so every way of getting there counts (hub, tab bar, palette,
  dashboard). Stored in local storage only: never sent, never progress.
- `lib/practice.ts` gains `SKILLS`, `readRecent`, `recordVisit` and `byRecent`.

## Cycle 28/30: weekly recap (Týden v kostce)

**Before:** the statistics page had a 26-week calendar, weekly accuracy and a forecast: good for
looking back over months, but it gave no short answer to "how did this week go, and what now?".

**Built:** `app/domain/recap.py`, `app/services/recap.py`, `GET /api/v1/insights/recap` and a
`WeeklyRecap` panel at the top of Statistiky.

- The last seven local days (the profile's time zone) against the seven before: days with
  learning, words introduced and newly known, graded and practice answers, and first-try
  accuracy with a trend. Accuracy is `null` and shown as "zatím nic k měření" when nothing was
  graded; unknown is never shown as 0 %.
- Up to three words with the most wrong graded answers this week, with gender colour.
- One suggestion, in a fixed order: due reviews first, then a five-minute start after a quiet
  week, then this week's trouble words, then a new lesson; with a button to the right page.
- A quiet week is described ("Nevadí: nic se tím neztrácí"), never scored. No streaks.
- Tests: accuracy unknown vs 0, trend margins, suggestion order, and the API over seeded events
  in two weeks and another language.

## Cycle 29/30: verb lab in French and Italian

**Before:** Časování (cycle 15) was German only; French and Italian learners saw "Časování je
zatím jen pro němčinu", although both languages have a present tense at least as demanding.

**Built:** `app/domain/conjugation_romance.py`; `GET /api/v1/grammar/verbs?language=de|fr|it`.

- French: -er verbs with the spelling changes that keep the sound (nous mangeons, nous
  commençons, j'achète, je préfère, j'appelle, je paie), -ir with -iss- (finir), the partir,
  ouvrir and conduire patterns, -re (vendre), 22 irregular verbs listed whole and found through a
  prefix (comprendre, revenir, permettre), and je to j' before a vowel or mute h.
- Italian: -are, -ere, -ire and -isc- (finire), the h kept in cerchi / paghiamo, one i in mangi /
  mangiamo (two in the stressed invii), and 22 irregular verbs, with prefixes (ottenere).
- Forms are now a list of six with their pronoun, so the same table and drill serve all three
  languages; each pattern has a Czech explanation. English is left out on purpose (one change,
  he/she/it -s) and the page says why. The rules are drafted and marked as not yet reviewed by a
  native speaker.
- Tests: 38 domain cases (every pattern, é kept in réparer, the stressed i, `changed` marks
  only the forms that differ, features), API in French and Italian, reflexive entries skipped,
  English rejected with 422.

## Cycle 30/30: what's new (Co je nového)

**Before:** 29 cycles added a dozen practice modes and many smaller features, but nothing in the
app told a returning learner about them. A feature nobody finds does not help anyone.

**Built:** `app/domain/news.py` (26 learner-facing entries in Czech), `GET /api/v1/news`,
`POST /api/v1/news/seen`, a `/news` page, a `NewsBanner` line on the dashboard and a palette
entry.

- Each entry has a number that only grows; the profile stores the newest number it has seen
  (`settings.news_seen`, no new table or migration). The banner says how many are new and
  names the three newest; "Ukázat" opens the page, "Už vím" marks them seen. Opening the page
  marks them seen but keeps the "Nové" marks for that visit.
- Entries limited to some languages (the case lab, gender sorter, verb lab) are shown and
  counted only for those.
- A fresh profile finishing the welcome wizard starts with everything seen; the banner is also
  hidden while the placement offer is shown. Marking seen is idempotent and per profile; a
  failed request only means the line shows again next time.
- The page says plainly that none of this counts as knowing a word; only Ověření does.
- Tests: numbering contiguous and never reused, language filter, unseen count, the API
  (repeat-safe, CSRF required, per profile: the parent marking seen leaves the child's count).

# Fresh innovation run: 2026-11-06

This is a new 30-cycle run on top of the already completed loop above. Each cycle adds a distinct
learner-facing improvement, records focused verification, and lands in its own local commit.

## Cycle 1/30: learner-made vocabulary collections (Slovní sady)

**Before:** the dictionary held every encountered word in one long list. Learners could add a
personal memory hook, but could not gather a topic set such as travel words for later reference.

**Built:** private, language-specific word collections backed by `word_collections` and
`word_collection_items` (migration 0021), with API operations for creating, listing, viewing,
adding, removing and deleting collections. The dictionary inspector can create a collection and
add the current word in one action; `/collections` provides a responsive manager, reached from
the dictionary and command palette.

- A collection accepts only words that profile has encountered in that same language; the
  existing content filter is checked on every add and read. Unseen and child-filtered words stay
  unavailable, and collection data cannot be read by another profile.
- Duplicate names in one profile and language return a conflict. Retried item additions are
  idempotent. Collection counts also exclude words that are no longer visible to the profile.
- This organizes the learner's own curriculum for reference without changing evidence, mastery,
  review scheduling, or the words available in lessons and checks.
- Verification: collection and dictionary API tests passed (6 tests), including CRUD, whitespace
  cleanup, duplicate requests and names, language boundaries, unseen words, child filtering,
  filtered counts and profile isolation. The backend suite passed (802 passed, 1 skipped) with
  the test process pointed at Compose Redis; Ruff and `alembic check` passed. Frontend typecheck
  and production build passed. Local Compose applied revision 0021; `/collections` and `/readyz`
  returned HTTP 200.

## Cycle 2/30: context-first listening from a word collection

**Before:** collections grouped the learner's words for reference, but did not provide a way to
return to them as useful in-context listening practice.

**Built:** *Slova v kontextu* in the collection manager. Each eligible word is presented with its
own example sentence and local TTS playback; the learner tries to infer the target word's meaning
before revealing the Czech gloss. Playback can be slowed and the learner can move back and forth
through the set.

- Only collection words with a stored example sentence appear. The existing word audio endpoint
  serves the clip and validates profile visibility; examples are reviewed lexicon text, not model
  output.
- The activity is explicitly ungraded and does not save attempts or alter review scheduling,
  mastery, or daily goal evidence. Empty collections or collections without examples have a clear
  message and remain usable for reference.
- Verification: a collection API regression asserts example sentences are returned only with
  the profile's visible collection words; frontend typecheck/build and targeted API tests run
  before the local Cycle 2 commit.

## Cycle 3/30: safe offline recovery for the installed app

**Before:** PolyFlow had an installable manifest, but a full reload during a Wi-Fi or homelab
outage produced a browser error. Learners had no clear way to tell whether their work had saved.

**Built:** a production-only service worker in `public/sw.js`, a global online/offline status
banner, and a self-contained Czech fallback page with a retry button.

- The worker caches only same-origin `/_next/static/` assets. It never caches HTML pages, API
  responses, learner content, or answers; learning still needs a live server connection.
- Navigation stays network-first. On failure the worker returns a minimal standalone fallback
  page which doesn't depend on app JavaScript or reveal cached profile data. The banner appears
  in normal and focus mode when the browser reports offline.
- Verification: frontend typecheck/build passed; the production Docker runner build succeeded.
  A Playwright browser confirmed the worker controlled the page, cached 10 static assets and no
  API URLs, then returned the Czech retry screen when taken offline.

## Cycle 4/30: searchable grammar roadmap

**Before:** the grammar page rendered every topic in long CEFR sections. Learners had to scroll
through the full curriculum to return to an unfinished topic or find a specific explanation.

**Built:** a diacritics-insensitive search across topic titles and summaries, status chips with
per-status counts, and a one-tap filter for topics due for verification. The roadmap reports how
many topics match and gives a clear no-results state. The introduction now describes grammar
generically across all four languages instead of saying every learner is on the German path.

- Filters affect presentation only. Every unit remains open from A1; the suggested order, mastery,
  and graded verification contracts are unchanged.
- Verification: frontend typecheck and production build; current local grammar route request and
  git diff checks before the local Cycle 4 commit.

## Cycle 5/30: export a selected vocabulary collection

**Before:** learners could export their full dictionary as a spreadsheet or Anki deck, but a
carefully assembled topic collection had to be copied out by hand.

**Built:** CSV and Anki download actions in each non-empty collection, backed by a profile-owned
collection export endpoint. The export preserves the existing dictionary formats, including
German noun articles, memory hooks, review state and lexicon provenance.

- The endpoint intersects collection membership with the acting profile's learned words and
  current content visibility; another profile receives not found. Both file formats contain only
  the chosen set and are sent with private, no-store download headers.
- The collection page explains that downloads contain only currently visible words and their
  personal notes. Existing CSV spreadsheet-safety handling and Anki tags are reused.
- Verification: collection API tests passed (5 tests), covering CSV and Anki contents, selected
  words, file naming, and profile isolation. Ruff check/format, frontend typecheck, production
  build, and `git diff --check` passed.

## Cycle 6/30: practice recommendations from recent errors

**Before:** the practice hub helped learners browse by skill and reopen recent modes, but it did
not connect those choices to the kinds of mistakes they had recently made in graded checks.

**Built:** a compact recommendation panel that reads the profile's recent error aggregates and
links the most frequent supported error types to a relevant exercise. Article/ending/gender
recommendations respect the active language; spelling and orthography point to dictation, and
word-order errors point to the word-order trainer.

- Recommendations name the error type and observed count so the learner can judge why a mode was
  suggested. The panel is omitted when there are no supported signals; practice remains ungraded.
- This is a navigation aid only: it does not change error history, lesson planning, evidence or
  review timing. A failed recommendation request is shown as an error instead of guessing.
- Verification: mistake API tests passed (4 tests); frontend typecheck and production build passed;
  `git diff --check` passed.

## Cycle 7/30: listen through a full story

**Before:** generated reading had a play button on every line, so listening to a complete story
required stopping and starting each sentence by hand.

**Built:** a continuous reader control that plays approved story audio line by line, advances
automatically, highlights the line currently playing, and exposes native audio controls for pause
and seek. Learners can restart the text or stop playback at any time.

- Audio still comes from the existing per-line story endpoint; the UI does not synthesize or
  publish any new text. A failed line shows a retry hint while keeping individual line playback.
- Playback state resets when the selected daily story changes and does not affect question
  answers or learning evidence.
- Verification: story API tests passed (12 tests); frontend typecheck and production build passed;
  `git diff --check` passed.

## Cycle 8/30: recognize sound patterns by ear

**Before:** the pronunciation guide explained spelling patterns and let learners play individual
known examples, but it did not offer a listening activity to help distinguish those patterns.

**Built:** an ungraded sound challenge above the guide. It plays a word the learner has already
encountered and asks which spelling-to-sound rule it demonstrates. After the choice, the guide
shows the rule's Czech sound cue and explanation, then offers another word.

- The challenge only uses currently visible, encountered examples and offers a clear message until
  examples exist for at least two rules. It avoids exposing new lexicon through audio.
- Scores are temporary round counts in the page; there is no grade, saved answer, mastery event or
  change to lesson scheduling. The original reference guide and individual replay remain available.
- Verification: sound API tests passed (39 tests); frontend typecheck and production build passed;
  `git diff --check` passed.

## Cycle 9/30: generate a story around a learner's collection

**Before:** a learner could organize a theme set and generate a daily reading, but the story
generator chose its target words independently of those personal collections.

**Built:** before creating the day's story, the learner can optionally select a same-language
collection. The generator uses up to five words from that set as its story targets, supplies the
collection name as the topic, and identifies the source collection in the finished reader.

- The server requires at least three currently visible, already encountered words and checks
  collection ownership and language before model availability. It keeps the existing vocabulary
  coverage validation, blacklist checks and child-profile model policy.
- A small set is disabled with an explanation, and generation reports a clear error if a selected
  set no longer has enough visible words. Ordinary generation from the learning plan is unchanged.
- Verification: story API tests passed (14 tests), including collection target selection,
  minimum-size handling and cross-profile isolation. Ruff, frontend typecheck/build and
  `git diff --check` passed.

## Cycle 10/30: inspect the review forecast by day

**Before:** the 14-day chart showed how many word and grammar reviews were coming, but learners
could not see which words or topics made up a selected day's total.

**Built:** each forecast column is now a keyboard-accessible selector. Choosing a day reveals its
due vocabulary and grammar topics, with links to the relevant study areas. The current day is
selected initially, and empty dates have a clear explanation.

- The API returns item details alongside the existing counts, and applies the learner's current
  visibility filter before including vocabulary. A regression test confirms child-hidden content
  is absent from both details and forecast counts.
- The forecast remains a schedule estimate; selecting a date changes no progress or evidence.
- Verification: insights API tests passed (2 tests), including exact due-item details and child
  filtering. Ruff, frontend typecheck/build and `git diff --check` passed.

## Cycle 11/30: revisit earlier daily readings

**Before:** the reader showed today's generated story or dialogue. Once a new day arrived, older
texts had no learner-facing path back into the reading experience.

**Built:** a recent-reading archive on the story page, with dates, titles and story/dialogue type.
Selecting an entry loads its original text, glossary, comprehension state and per-line audio; a
one-tap action returns to today's reading.

- The API returns only generated, safety-checked entries owned by the acting profile and selected
  language, with a bounded 30-item default. Pending, rejected or failed generations stay hidden.
- The archive is read-only for learning records; revisiting text and questions does not create new
  mastery evidence.
- Verification: story API tests passed (14 tests), including language and profile isolation.
  Ruff, frontend typecheck/build and `git diff --check` passed.

## Cycle 12/30: pause a lesson and resume it later

**Before:** the learning session already stayed open on the server, but the focused lesson view had
no explicit pause action. Learners had to leave the page and rely on the dashboard's resume label.

**Built:** a visible *Pozastavit* control during the scene, word-introduction and practice phases.
It returns to the dashboard without completing or deleting the lesson, where the existing resume
action continues the open session.

- The control is disabled while an answer request is in flight. Its accessible hint explains that
  an unsubmitted text answer is not saved.
- Verification: the server resume regression passed (1 test); frontend typecheck and production
  build passed; `git diff --check` passed.

## Cycle 13/30: search learned words from the command palette

**Before:** Ctrl+K and `/` could jump to learning pages and change settings, but finding a word
required opening the dictionary and searching there.

**Built:** after two characters, the palette makes a debounced, cancellable search against the
acting profile's dictionary and adds up to six word-and-translation results. Choosing a result
opens its dictionary inspector directly; the dictionary also accepts a focused word ID from that
route.

- Search uses the existing profile-scoped, child-filtered word-list API. No unseen words or other
profiles' entries are introduced into global navigation; API failures leave ordinary commands
available.
- Verification: dictionary API tests passed (2 tests); frontend typecheck and production build
passed; `git diff --check` passed.

## Cycle 14/30: delete a saved generated reading

**Before:** learners could revisit readings from the archive but had no way to remove one they no
longer wanted to keep.

**Built:** a per-reading delete control with an explicit confirmation. The server permanently
removes only a completed, safety-checked generated story owned by the acting profile; deleting
today's story also lets the learner generate a replacement for that day.

- Other profiles receive not found, and pending or failed generations cannot be deleted through
  the archive action. The UI removes the item and closes its reader if that item was open.
- Verification: story API tests passed (15 tests), including owned deletion, regeneration,
  cross-profile rejection and archive visibility. Ruff, frontend typecheck/build and
  `git diff --check` passed.

## Cycle 15/30: save selected dictionary words to a collection

**Before:** learners could add words to a personal collection one at a time, making it tedious
to gather a group of related words from a dictionary search.

**Built:** dictionary rows now have independent selection checkboxes and a contextual bulk action
to add the selected words to any same-language collection. The toolbar shows selection and
collection counts, reports how many items were newly added, and offers a direct path to create a
collection when none exists.

- The server checks ownership, language, encounter history and child visibility for the entire
  selection before inserting anything; duplicate submissions are idempotent. Keyboard navigation
  shortcuts no longer hijack inputs or selection controls.
- Verification: collection API tests passed (6 tests), including duplicate handling and atomic
  rejection of an unavailable word. Ruff, frontend typecheck/build and `git diff --check` passed.

## Cycle 16/30: recall every word in a collection

**Before:** collection practice depended on example sentences, so saved words without an example
could not be practiced there. The only activity also focused on listening to the sentence.

**Built:** collection practice now offers a shuffled recall-card mode for every word. The learner
sees the Czech meaning, reveals the target word and audio, then either continues or queues that
word to appear again in the current session.

- Recall choices are temporary and ungraded; they do not change review schedules, mastery, or
  learning history. The existing sentence-listening activity remains available when examples
  exist, and the recall mode still works when none do.
- Verification: frontend typecheck and production build passed; `git diff --check` passed.

## Cycle 17/30: search and organize large word collections

**Before:** a collection always appeared in frequency order. As a set grew, finding a word or
returning to useful example sentences meant scanning the full list.

**Built:** collection details now include local search across words, Czech meanings and example
sentences, alphabetical or frequency sorting, and a filter for words with examples. A live result
count and clear empty state keep each combination understandable.

- Filtering changes only the current view; collection membership and saved learning records stay
  untouched.
- Verification: frontend typecheck and production build passed; `git diff --check` passed.

## Cycle 18/30: continue story audio from any sentence

**Before:** the reader could play an individual sentence or listen to the whole story, but whole
story playback always restarted from the beginning.

**Built:** every sentence now has a clearly labeled action to start continuous playback there.
Audio proceeds through the remaining lines and highlights the active sentence; the existing
whole-story action still starts from the first line.

- Sentence playback remains available separately for replaying just one line. Starting playback
  from a line near the end finishes at the end of the story.
- Verification: frontend typecheck and production build passed; `git diff --check` passed.

## Cycle 19/30: combine practice skill filters

**Before:** the practice hub could filter exercises by only one skill at a time, so a learner
looking for an activity that combines listening and writing had to choose between those goals.

**Built:** the skill picker now supports multiple simultaneous selections. It shows every practice
mode that covers at least one selected skill, explains that matching rule, and retains a clear
one-tap reset to all modes.

- The filter remains a discovery aid only; it does not alter learner settings or progress.
- Verification: frontend typecheck and production build passed; `git diff --check` passed.

## Cycle 20/30: pin favorite practice modes to the dashboard

**Before:** the dashboard surfaced only the three most recently opened practice modes. Learners
could not keep a preferred routine visible when their recent activity changed.

**Built:** practice cards can now be pinned or unpinned, and favorites appear as quick links on
both the practice hub and dashboard. Favorites are stored on the current browser, independent of
server-side learning records, and modes unavailable in the selected language are hidden.

- If browser storage is unavailable, pinning still updates the current view but cannot persist
  across visits.
- Verification: frontend typecheck and production build passed; `git diff --check` passed.

## Cycle 21/30: show personal progress along vocabulary milestones

**Before:** the dashboard listed the vocabulary milestones but did not show which milestones the
active learner had reached or how far away the next one was.

**Built:** the path now marks completed milestones, highlights the next target, and shows an
accessible progress bar with the current known-word count and remaining words. It explains when
the required B2 vocabulary path is complete.

- The path uses the existing profile-scoped progress count and keeps its CEFR disclaimer; the
  visual never describes vocabulary rank as a certified communication level.
- Verification: frontend typecheck and production build passed; `git diff --check` passed.

## Cycle 22/30: see grammar progress by level

**Before:** the grammar roadmap grouped topics by level and showed each topic's state, but gave no
at-a-glance sense of how much of a level was known or due for review.

**Built:** each visible grammar level now has a progress bar based on topics marked known or
mastered, plus counts for those topics and the topics due for review. The summary follows the
current search and filters, so it describes the topics currently on screen.

- Progress is based on the existing grammar states; it does not award a level or alter review
  scheduling.
- Verification: frontend typecheck and production build passed; `git diff --check` passed.

## Cycle 23/30: turn weekly difficult words into a study set

**Before:** the weekly recap identified words that had caused repeated mistakes, but learners had
to find those words again and add them to a collection one at a time.

**Built:** the recap now offers a short naming form that creates a personal word collection and
adds its listed difficult words in one bulk request. Success and partial-failure states link back
to the collection area.

- The bulk endpoint rechecks word ownership, language and child visibility. The collection can
  support future practice without turning recap errors into a new mastery result.
- Verification: collection API safety/idempotency tests were already green in Cycle 15; frontend
  typecheck and production build passed for this integration; `git diff --check` passed.

## Cycle 24/30: replace the gender speed test with an untimed round

**Before:** the gender practice page included a 60-second challenge and saved a local best score,
which put time pressure and a persistent record inside ordinary practice.

**Built:** the challenge is now a fixed 10-word round with a simple progress bar and no clock.
Learners can pause to read the suffix rule after a miss, and the round ends without saving a
score or record.

- Ordinary gender practice remains available, including filtering to words the learner has met.
  This brings the challenge in line with the project's rule that timed assessment belongs in an
  explicit test mode.
- Verification: frontend typecheck and production build passed; `git diff --check` passed.

## Cycle 25/30: recover story answers after a network error

**Before:** if a comprehension answer request failed, the reader left the learner with no retry
path. Switching to another story could also carry the previous reading's local answer state.

**Built:** a failed submission now locks the original choice and offers a one-action retry for
that same answer. Changing stories clears local results, errors and busy state, and late responses
from the previous story are ignored. Previously saved archive answers stay locked.

- The server records the first answer per question; retrying the identical choice is safe and
  does not change saved results.
- Verification: frontend typecheck and production build passed; `git diff --check` passed.

## Cycle 26/30: surface the install action for the web app

**Before:** the production app had a manifest and service worker, but no navigation control for
the install prompt offered by supported browsers.

**Built:** the shared navigation now listens for the browser's installability event and shows a
clearly labeled install button only when that prompt is available. The action opens the native
browser prompt and disappears after installation or dismissal.

- Browsers that do not expose the install prompt keep the regular navigation unchanged. The
  button does not claim that personal learning data is available offline.
- Verification: frontend typecheck and production build passed; `git diff --check` passed.

## Cycle 27/30: reopen recent readings from the dashboard

**Before:** the dashboard linked to today's reading, but returning to a saved story required
opening the stories page and finding it in the archive list.

**Built:** the daily plan now shows the three most recent saved readings, each opening directly
in the story archive reader through a profile-checked story link.

- The archive API already limits results to generated, safety-checked readings for the acting
  profile and selected language. A deep link is opened only when its ID is in that archive list.
- Verification: frontend typecheck and production build passed; `git diff --check` passed.

## Cycle 28/30: explore a day in the activity calendar

**Before:** the 26-week activity calendar showed daily totals in tooltips, but selecting a day
could not reveal which words or grammar topics were practiced.

**Built:** calendar cells are now keyboard-selectable. A selected day shows its word and grammar
topics with separate graded and practice counts, and links directly to the relevant dictionary
card or grammar lesson.

- The new API is limited to the learner's own 182-day calendar, returns no answer text, filters
  vocabulary through the active child-content policy, and omits inactive grammar units.
- Verification: insights API tests passed (2 tests), including grouped counts, out-of-range dates
  and child-hidden word filtering. Ruff, frontend typecheck/build and `git diff --check` passed.

## Cycle 29/30: rename personal word collections

**Before:** learners could organize encountered words into collections, but a collection's name
could not be updated when their study plan changed.

**Built:** collection owners can now rename a collection inline. Names are whitespace-normalized,
limited to 60 characters, scoped to the learner, and duplicate names return a clear conflict.

- Added API coverage for normalized renames, cross-profile access, and duplicate-name conflicts.
- Verification: all 8 word-collection API tests passed, Ruff passed, and frontend typecheck and
  production build passed; `git diff --check` passed.

## Cycle 30/30: bring the weekly learning coach to the dashboard

**Before:** the personalized weekly recap, difficult words, and suggested next activity were
available on the insights page, away from the dashboard where learners choose what to do next.

**Built:** the home dashboard now includes the weekly recap and its actionable next step, so
learners can see recent progress and continue into review, mistake correction, or a lesson from
their main entry point.

- The recap keeps its existing profile and language scoped API, reports unknown accuracy as
  unknown, and does not add streak pressure or graded activity.
- Verification: all 4 recap API tests passed; frontend typecheck and production build passed;
  Compose config passed; rebuilt Compose stack reports `/readyz` ready and serves the frontend
  with HTTP 200 on port 3001.

---

# Innovation log: 120-cycle page-by-page loop

Started 2026-11-07 at Vlad's request, on branch `claude/project-thread-can89h` from `main` at
`0b8e6e6` (1.0.0-alpha.13). Fifteen cycles per page, in this order: `/`, `/grammar`, `/practice`,
`/words`, `/insights`, `/lesson`, `/shadowing`, `/stories/library`. Page cycles 1-5 fix flows and
wire data, 6-10 add learning ergonomics, 11-15 consolidate and harden. Commits stay local until
Vlad approves a push.

## Baseline

- Working tree clean at `0b8e6e6`. Node 22, Next.js 16.3, Python 3.13 via `uv`, Postgres 16 and
  Redis 7 running locally.
- Backend (`backend/`): `uv run pytest` 872 passed, 1 skipped (with `POLYFLOW_TEST_DATABASE_URL`);
  `ruff check` and `ruff format --check` clean.
- Frontend (`frontend/`): `npm run typecheck` and `npm run build` clean, 36 routes.
- Local run: `uvicorn app.main:app --port 8000`, `python -m app.workers`, `next dev --port 3001`
  (the dev server proxies `/api` to port 8000).
- Route audit: `/`, `/grammar`, `/practice`, `/words`, `/insights`, `/lesson` and `/shadowing`
  exist. `/stories/library` does not exist (only `/stories`); its 15 cycles build it inside the
  existing stories design.
- Pre-existing defect found while rendering `/`: React warns about duplicate `extension_passive`
  keys in the progression path (two milestones share that key).

## Global Cycle 1/120 | Page: [/] (Page Cycle 1/15)

**Summary:** show voluntary vocabulary bands once, as rank ranges

**Observed Problem:** The dashboard progression path listed "Pasivní slovní zásoba – dobrovolné" twice (6 000+ and 7 000+) because two backend milestones share the key `extension_passive`, and React logged duplicate-key errors on every render of `/`.

**Implemented Solution:** `components/ProgressionPath.tsx` now merges consecutive voluntary milestones with the same key into one row that shows the rank range it covers (5 001–7 000, 7 001–8 000) and, once the learner has proven words in that range, how many. Required milestone rows are keyed by rank. New `cs.progression.inBand` string in `lib/i18n/cs.ts`.

**Verification:** typecheck, production build, ruff and `git diff --check` passed; rendering `/` in Chromium shows no console errors (previously 2 duplicate-key errors).

## Global Cycle 2/120 | Page: [/] (Page Cycle 2/15)

**Summary:** replace the obsolete grammar lock line with real grammar progress

**Observed Problem:** Grammar has been open from A1 since 2026-11-06, but the dashboard still printed the old word-gate copy ("Gramatické minilekce jsou odemčené" / "odemknou po 1 000 slov"), and the Grammar quick action always said "Témata tvé úrovně" regardless of what was due or in progress.

**Implemented Solution:** `app/page.tsx` now loads the learner's grammar tree for the active language alongside progress. The Grammar quick action shows a resumable lesson (and links straight to it), the number of topics due for review (highlighted), or the recommended next topic. `components/ProgressCard.tsx` replaces the lock line with "Gramatika: X z Y témat prošlo ověřením", counting only units in the known or mastered state. Obsolete `grammarLocked`/`grammarUnlocked` strings removed from `lib/i18n/cs.ts`.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; dashboard rendered with seeded German progress shows "Gramatika: 0 z 37 témat prošlo ověřením" and no console errors.

## Global Cycle 3/120 | Page: [/] (Page Cycle 3/15)

**Summary:** make weak spots actionable: audio, dictionary links, top five first

**Observed Problem:** The Weak spots panel listed every unresolved word (10+ rows on a phone after one check) as plain text: the learner could not hear the word or open its dictionary card from the place where the mistake was surfaced.

**Implemented Solution:** The weak-spots API now returns each word's `item_id` (`backend/app/schemas/learning.py`, `backend/app/api/learning.py`). `components/WeakSpotsCard.tsx` shows the five worst words first with a "Zobrazit všechna (N)" toggle, each row has a play button (dictionary audio) and links to `/words?word=<id>`, which opens that word's inspector. Types in `lib/api.ts`, copy in `lib/i18n/cs.ts`; `tests/test_mistakes.py` asserts the ids.

**Verification:** `tests/test_mistakes.py` 4 passed; ruff, typecheck, production build, `git diff --check` passed; dashboard renders the capped list with audio buttons and no console errors.

## Global Cycle 4/120 | Page: [/] (Page Cycle 4/15)

**Summary:** say when the next review opens instead of a dead "nothing due" card

**Observed Problem:** After a lesson the Daily review card showed a greyed "Dnes nic nečeká" with no hint of when checking becomes possible (words are checkable from the next day), so learners could not plan their return.

**Implemented Solution:** `services/learning.py` progress overview now also returns `next_review_at`, the earliest future review among introduced words (one extra aggregate in the existing query; schema in `schemas/learning.py`). The dashboard card reads "Teď nic nečeká · další za 3 h / zítra / ve středu / 12. 11." via a new Czech `relativeFuture` helper in `lib/i18n/cs.ts` with correct weekday prepositions. `tests/test_learning.py` covers the new field.

**Verification:** `tests/test_learning.py -k progress` 2 passed; ruff, typecheck, production build and `git diff --check` passed.

## Global Cycle 5/120 | Page: [/] (Page Cycle 5/15)

**Summary:** show each language's words and due checks in the dashboard switcher

**Observed Problem:** Learners studying several languages had to switch blindly: the language buttons gave no sign which language had checks waiting or had not been started, and the radio group ignored arrow keys.

**Implemented Solution:** New `GET /api/v1/learning/languages` (`api/learning.py`, `services/learning.language_summaries`, `LanguageSummaryOut`) returns introduced, known and due words for all four languages from one grouped query over the acting profile's own progress. On the dashboard, `LanguagePicker` (`components/AppShell.tsx`) shows "41 slov · 3 k ověření" or "zatím nezačato" under each language (amber when checks are waiting) and now implements the radio-group keyboard pattern (arrow keys move and select, roving tabindex). Other pages keep the compact switcher. Test `test_language_summaries_count_only_own_words`.

**Verification:** `tests/test_learning.py` summaries/progress tests passed; ruff (import order fixed), typecheck, production build, `git diff --check` passed; screenshot shows per-language summaries.

## Global Cycle 6/120 | Page: [/] (Page Cycle 6/15)

**Summary:** open the four daily actions with keys 1-4

**Observed Problem:** On desktop the dashboard had one shortcut (Enter continues today's plan); reaching review, grammar, flashcards or practice needed the mouse or several Tab presses.

**Implemented Solution:** `app/page.tsx`: the quick actions carry `data-hotkey` 1-4 (`aria-keyshortcuts` for assistive tech) and show a key badge on wide screens via `KeyHint`. The dashboard's existing hotkey listener (installed by `TodayPlan`, layout-independent digit codes from `lib/keyboard.ts`) clicks them; a disabled Daily review card (nothing due) is not a link and ignores its key.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; a Playwright run on the dev server pressed 2, 3 and 4 on `/` and landed on `/grammar`, `/words?tab=levels` and `/practice`.

## Global Cycle 7/120 | Page: [/] (Page Cycle 7/15)

**Summary:** change the daily goal inline and fix the grammar-check step link

**Observed Problem:** Adjusting the daily goal meant leaving the dashboard for Settings, although the goal ring sits right on the plan. The plan's "Ověřit gramatiku" step opened the grammar overview instead of the grammar check, and the lesson step said "Nová lekce (5 slova)".

**Implemented Solution:** `components/TodayPlan.tsx`: a "Změnit cíl" toggle under the ring reveals 5/10/15/20/30-minute choices (radio group); picking one saves `daily_goal_minutes` through the existing partial profile PATCH, updates the signed-in profile in auth state and re-reads today's plan. Failures show an inline alert. The `grammar_check` step now goes to `/grammar/check`; lesson step pluralization fixed in `lib/i18n/cs.ts`.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright on a 390 px viewport changed the goal to 20 and back to 10 minutes and the plan text updated each time.

## Global Cycle 8/120 | Page: [/] (Page Cycle 8/15)

**Summary:** send "Start/continue lesson" straight into the vocabulary lesson

**Observed Problem:** The dashboard's main button ("Začít lekci" / "Pokračovat v lekci" for an open session), today's plan lesson step, the welcome wizard's first lesson, the command palette's "Začít lekci" and the weekly coach's lesson suggestion all went to `/lesson`, which is the lesson overview with a grammar recommendation. Resuming a half-finished vocabulary lesson took an extra, misleading click.

**Implemented Solution:** These five entry points now open `/lesson/vocabulary` (the scene-first LessonRunner, which resumes an active session): `app/page.tsx`, `components/TodayPlan.tsx`, `components/Welcome.tsx`, `components/CommandPalette.tsx`, `components/WeeklyRecap.tsx`. The bottom tab "Lekce" still opens the `/lesson` overview.

**Verification:** typecheck, production build, ruff, `git diff --check` passed.

## Global Cycle 9/120 | Page: [/] (Page Cycle 9/15)

**Summary:** hold the dashboard layout with loading skeletons

**Observed Problem:** While the dashboard loaded, today's plan rendered nothing and then popped in above the other panels, pushing them down; progress and weak spots showed a bare "Načítám…" line and the progression path was blank. On a slow home-server connection the page jumped several times.

**Implemented Solution:** New `Skeleton` component in `components/ui.tsx` (sized placeholder lines, one polite "Načítám" status for screen readers, shimmer only when motion is allowed). Used by `TodayPlan` (ring-shaped placeholder of the final height), the progress panel in `app/page.tsx`, `WeakSpotsCard` and `ProgressionPath`.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright with the dashboard APIs delayed by 4 s shows the placeholders in place of the panels.

## Global Cycle 10/120 | Page: [/] (Page Cycle 10/15)

**Summary:** preview the next lesson's scene and word counts on the start button

**Observed Problem:** The main dashboard button said only "Začít lekci"; the learner could not see which situation came next or that missed words would be practised again, although lessons are built around a scene (context first).

**Implemented Solution:** New read-only `GET /api/v1/learning/next-lesson` (`api/learning.py`, `services/learning.preview_lesson`, `LessonPreviewOut`) runs the same lesson planner used by session start, with the child-content filter, and returns the scene's Czech title, new-word count and remediation count without creating a session. The dashboard hero shows "Další scénka: „Oběd“ · 4 nová slova · 2 slova znovu k procvičení", or a clear message when every word has been met. New test checks that the preview matches the started lesson and starts nothing.

**Verification:** `tests/test_learning.py` preview/summary tests passed; ruff, typecheck, production build, `git diff --check` passed; mobile screenshot shows the preview.

## Global Cycle 11/120 | Page: [/] (Page Cycle 11/15)

**Summary:** one primary action: the hero button follows today's plan

**Observed Problem:** The dashboard had two competing primary buttons: the hero's "Začít lekci" (always a new lesson) and today's plan "Pokračovat" (first plan step, bound to Enter). When checks were due they pointed to different places, so the page gave contradictory advice.

**Implemented Solution:** `TodayPlan` no longer renders its own button; it exports its step map and hands the loaded plan up via `onPlan`. The hero button in `app/page.tsx` is now the only primary action and the Enter target: resume an open lesson, otherwise the plan's first step (for example "Ověřit 12 slov"), otherwise a new lesson. The note under it switches between the ungraded-lesson note and a new graded-check note (`cs.dashboard.checkNote`), and the lesson preview from cycle 10 only appears when the action is a lesson.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; desktop screenshot shows one primary button with its Enter hint and the plan panel without a duplicate.

## Global Cycle 12/120 | Page: [/] (Page Cycle 12/15)

**Summary:** merge duplicated band bars into the milestone path

**Observed Problem:** Vocabulary progress was shown twice on the dashboard: the Progress panel had six "≤ 100 … ≤ 5 000" bars and the "Tvoje cesta" panel listed the same six milestones again, plus a third "Další milník" line. A second panel called "Moje cesta" (rank path) made the two "cesta" titles indistinguishable.

**Implemented Solution:** `components/ProgressCard.tsx` keeps the six counters and the grammar line; band bars and the next-milestone line are removed. `components/ProgressionPath.tsx` now shows each milestone's band fill (known / words in that band) as a thin labelled progressbar under the row, for the current band and any band with known words. The panel is renamed "Milníky slovní zásoby" in `lib/i18n/cs.ts`; the unused `nextMilestone` string is removed.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; mobile dashboard shrinks from 4 317 px to 4 113 px with no console errors.

## Global Cycle 13/120 | Page: [/] (Page Cycle 13/15)

**Summary:** fit the language switcher and daily actions to phone width

**Observed Problem:** On a 390 px phone the four language buttons (now with summaries) wrapped into a ragged 3 + 1 layout, and the four daily actions stacked as full-width rows, pushing today's plan below the first screen.

**Implemented Solution:** `LanguagePicker` with summaries uses an even 2 × 2 grid on phones and the inline row from `sm` up (`components/AppShell.tsx`). The quick actions in `app/page.tsx` form a 2-column grid on phones with the icon above the text and help clamped to two lines; from `sm` they return to the icon-beside-text layout and four columns on wide screens.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; 390 px screenshot shows the 2 × 2 switcher and action grid, no console errors.

## Global Cycle 14/120 | Page: [/] (Page Cycle 14/15)

**Summary:** retry failed dashboard panels instead of dead ends

**Observed Problem:** If today's plan failed to load, the panel stayed a loading skeleton forever (its error was swallowed); progress, weak spots and the milestone path showed a red "Něco se nepovedlo" with no way to recover short of reloading the whole page.

**Implemented Solution:** New `RetryNotice` in `components/ui.tsx` (alert text plus "Zkusit znovu"). `TodayPlan` now records failures and offers a retry; the progress panel in `app/page.tsx`, `WeakSpotsCard` and `ProgressionPath` re-run their own request through an attempt counter. Copy `cs.today.failed` added.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright with `/today` and `/learning/progress` returning 500 showed two retry notices, and after the API recovered, pressing them restored both panels.

## Global Cycle 15/120 | Page: [/] (Page Cycle 15/15)

**Summary:** share in-flight rank and milestone requests

**Observed Problem:** A production-build load of `/` sent 14 API requests, with `/api/v1/ranks` twice (the header emblem and the rank card mounted together and both missed the 30 s cache), and the static milestone ladder was refetched on every visit to the dashboard.

**Implemented Solution:** `lib/useRanks.ts` shares one in-flight request per profile and language between concurrent users of the hook (cleared by `invalidateRanks`). `components/ProgressionPath.tsx` keeps the static milestone ladder in a module-level promise for the page session, dropping it after a failure so the retry from cycle 14 asks again.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright against `next start` counts 13 API requests on `/` with `/ranks` once (was 14 with two).

## Global Cycle 16/120 | Page: [/grammar] (Page Cycle 1/15)

**Summary:** pick the focus level; fall back to passed vocabulary exams

**Observed Problem:** The highlighted grammar level came only from the CEFR estimate and otherwise stayed on A1, ignoring passed vocabulary level exams, and a learner who wanted to work on A2 topics had no way to bring them to the top: they stayed collapsed under "Ostatní úrovně".

**Implemented Solution:** `app/grammar/page.tsx`: the default focus level now uses the CEFR estimate, then the highest earned vocabulary badge, then A1, with a matching explanation (`activeFromBadge`). A radio row under the level header lets the learner choose any level that has topics, or go back to "Podle odhadu (A1)"; the choice is a per-device convenience stored per profile and language in localStorage (guarded for private mode). Copy in `lib/i18n/cs.ts`.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright chose A2, saw the A2 panel promoted, and the choice survived a reload.

## Global Cycle 17/120 | Page: [/grammar] (Page Cycle 2/15)

**Summary:** show when each studied topic can be checked

**Observed Problem:** A studied grammar topic looked the same as any other until it became due; the learner could not tell that its check opens tomorrow (topics become checkable from the next day), so a "Prostudováno" card gave no next step.

**Implemented Solution:** `app/grammar/page.tsx` unit cards now show "Ověření za 3 h / zítra / ve středu / 12. 11." under the exercise count for studied, known or mastered topics that are not yet due, using the tree's existing `next_review_at` and the shared `relativeFuture` helper. Due topics keep the amber "K ověření" badge. Copy `cs.grammar.nextCheck`.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; after studying two German A1 units through the API, the mobile grammar page shows "Ověření za 1 h" on both cards.

## Global Cycle 18/120 | Page: [/grammar] (Page Cycle 3/15)

**Summary:** keep topic filters in the URL; dashboard opens the due list

**Observed Problem:** Search text and the status/due filters lived only in component state: reloading, going back from a lesson or following a link always reset the list, and the dashboard could not send a learner straight to the topics waiting for a check.

**Implemented Solution:** `app/grammar/page.tsx` reads `q`, `status` and `due` from the query string on load and keeps them in sync with `history.replaceState` (no extra history entries while typing). The dashboard's Grammar action (`app/page.tsx`) links to `/grammar?due=1` when topics are due and no lesson is open.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright opened `/grammar?status=studied` ("Zobrazeno 2 z 37 témat") and typing a search updated the URL to `?status=studied&q=sein`.

## Global Cycle 19/120 | Page: [/grammar] (Page Cycle 4/15)

**Summary:** search inside explanations, tables and examples

**Observed Problem:** The topic search promised "Hledat téma nebo vysvětlení" but matched only titles and summaries: searching "vykání" or a form like "bist" found nothing, although the explanation of sein covers both.

**Implemented Solution:** New `GET /api/v1/grammar/search-index` (`api/grammar.py`, `SearchEntryOut`) returns each active unit's objective, note headings and text, table cells and examples as plain text (markdown markers stripped). `app/grammar/page.tsx` fetches it lazily the first time the learner types a query (about 30 kB for German), folds diacritics like the existing search, and also matches the objective; titles and summaries keep working if the index fails. Test `test_search_index_has_plain_explanation_text`.

**Verification:** `tests/test_grammar.py` search/tree tests passed; ruff, typecheck, production build, `git diff --check` passed; Playwright search "vykání" now shows 1 of 37 topics (was 0).

## Global Cycle 20/120 | Page: [/grammar] (Page Cycle 5/15)

**Summary:** show graded check results on each topic

**Observed Problem:** Topic cards showed a status label and recent errors, but not how the learner actually did in grammar checks, so "Prostudováno" after three good checks looked the same as after none.

**Implemented Solution:** The grammar tree now returns `checked_correct` and `checked_errors` per unit (first-try graded answers already counted in `UserGrammarProgress`; `schemas/grammar.py`, `api/grammar.py`). Cards in `app/grammar/page.tsx` show "V ověřeních: 3 správně, 1 chyba" once at least one check answer exists; unmeasured topics show nothing instead of a misleading zero. The check test asserts both counts.

**Verification:** `tests/test_grammar.py` 14 passed; ruff, typecheck, production build, `git diff --check` passed.

## Global Cycle 21/120 | Page: [/grammar] (Page Cycle 6/15)

**Summary:** keyboard topic search: /, Enter opens, Esc clears

**Observed Problem:** Finding a grammar topic on desktop needed the mouse: no shortcut reached the search box, Enter did nothing, and resetting search plus filters took several clicks.

**Implemented Solution:** `components/CommandPalette.tsx`: "/" now focuses the current page's own search box when one is marked `data-page-search` and visible, and still opens the global palette elsewhere (Ctrl+K always opens the palette). `app/grammar/page.tsx` marks its topic search, shows a "/" key badge, opens the first matching topic on Enter and clears search and status/due filters on Escape; a desktop hint "Enter otevře první, Esc vše zruší" appears while filtering.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright: "/" then typing "akuzativ" filtered to 1 of 37, Escape restored 37, typing "sein" + Enter opened `/grammar/de-a1-sein`.

## Global Cycle 22/120 | Page: [/grammar] (Page Cycle 7/15)

**Summary:** preview a topic's goal, first rule and examples in place

**Observed Problem:** The only way to see what a grammar topic teaches was to open it, and opening a topic immediately starts a lesson session; browsing several topics created several open sessions and lost the overview.

**Implemented Solution:** `app/grammar/page.tsx`: every topic card has a "Náhled výkladu" toggle below it (a separate button, not nested in the card link) that expands the unit's objective, first explanation note (markdown markers removed) and up to three examples with Czech translations, read through the existing read-only `GET /grammar/units/{id}`. Unit details are cached per page session and a failed load can be retried by reopening. Copy in `lib/i18n/cs.ts`.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright opened the preview on a 390 px screen without leaving `/grammar`.

## Global Cycle 23/120 | Page: [/grammar] (Page Cycle 8/15)

**Summary:** order in-progress topics by urgency; add a "S chybami" filter

**Observed Problem:** "Právě se učíš" listed topics in curriculum order, so a topic due for a check or with fresh check mistakes could sit behind the recommendation and studied topics; there was also no way to list only the topics with recent mistakes.

**Implemented Solution:** `app/grammar/page.tsx`: in-progress topics are sorted by urgency (open lesson, due for check, recent mistakes, recommended, other studied; stable within groups). A new "S chybami N" chip filters to topics with unresolved recent check mistakes, is kept in the URL as `errors=1` and is cleared by Escape with the other filters. Copy `cs.grammar.withErrors`.

**Verification:** typecheck, production build, ruff, `git diff --check` passed.

## Global Cycle 24/120 | Page: [/grammar] (Page Cycle 9/15)

**Summary:** return from a lesson to the topic just studied

**Observed Problem:** Finishing a grammar lesson sent the learner to the top of `/grammar`; on a phone the topic they had just studied, now marked "Prostudováno" with its check date, was several screens down, so the result of the lesson was invisible.

**Implemented Solution:** The lesson's exit (`app/grammar/[unit]/page.tsx`) now opens `/grammar?studied=<unit>`. `app/grammar/page.tsx` scrolls that card into view (instant when reduced motion is preferred), moves focus to its link, rings it in green for four seconds and announces "Právě prostudováno: …" to screen readers. The parameter is one-shot: it is removed from the URL so a reload does not scroll again.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright opened `/grammar?studied=de-a1-articles`: focus landed in that card, it carried the highlight, and the URL was cleaned to `/grammar`.

## Global Cycle 25/120 | Page: [/grammar] (Page Cycle 10/15)

**Summary:** listen to topic examples from the preview

**Observed Problem:** Grammar examples could only be read; the overview offered no way to hear how "Sind Sie Herr Novák?" sounds, while vocabulary, stories and drills all have audio.

**Implemented Solution:** New `GET /api/v1/grammar/units/{id}/audio?example=N` (`api/grammar.py`) speaks one of the unit's curated examples through the existing TTS path and the profile's chosen voice; it never accepts free text and returns 404 for unknown units or example indexes. The topic preview in `app/grammar/page.tsx` gets a play button per example (`PlayButton` shows the unavailable state when no voice is installed). Test `test_example_audio_only_for_existing_examples`.

**Verification:** `tests/test_grammar.py` 15 passed; ruff (one file reformatted), typecheck, production build, `git diff --check` passed. Audio playback itself not verified: this container has no TTS voices (the endpoint returns 503 there, as the test expects).

## Global Cycle 26/120 | Page: [/grammar] (Page Cycle 11/15)

**Summary:** compact topic cards: one meta line, clamped summary

**Observed Problem:** After cycles 17 and 20 a studied card stacked up to four small text lines (exercise count, next check, check tally, open link) under a full-length summary; on a phone two cards filled the screen.

**Implemented Solution:** `app/grammar/page.tsx`: the card's meta is one line ("8 cvičení · v ověřeních 3 správně, 1 chyba · ověření zítra") next to the open/resume link, and the summary is clamped to two lines. Strings in `lib/i18n/cs.ts` lower-cased to read as one sentence fragment.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; 390 px screenshot shows a single meta line per card and the mobile page at 2 521 px.

## Global Cycle 27/120 | Page: [/grammar] (Page Cycle 12/15)

**Summary:** skeleton while loading, retry when the topic list fails

**Observed Problem:** `/grammar` showed a single "Načítám…" line while the tree loaded and then reflowed the whole page; if the request failed, the learner got "Něco se nepovedlo." with no way to try again except reloading.

**Implemented Solution:** `app/grammar/page.tsx`: a placeholder in the shape of the focus panel (two text lines and three card blocks, pulse only with motion allowed) holds the layout while loading; a failure shows `RetryNotice` ("Gramatiku se nepodařilo načíst." + Zkusit znovu) that re-runs the tree and level requests through an attempt counter.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright with the tree request failing showed the retry alert, and after recovery the retry loaded all 37 topics.

## Global Cycle 28/120 | Page: [/grammar] (Page Cycle 13/15)

**Summary:** one swipeable filter row on phones

**Observed Problem:** On a 390 px phone the seven status/due/error chips wrapped into three rows and, together with the search box, pushed the topic list half a screen down.

**Implemented Solution:** `app/grammar/page.tsx`: below `sm` the chips form one horizontally scrollable row that bleeds to the screen edge (no scrollbar, chips never shrink or wrap their labels); from `sm` up they wrap as before. The search field takes the full width on phones.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; 390 px screenshot shows a single chip row with the next chip cut at the edge as a swipe cue.

## Global Cycle 29/120 | Page: [/grammar] (Page Cycle 14/15)

**Summary:** list empty levels once instead of as empty panels

**Observed Problem:** C1 and C2 have no grammar topics yet, but each still rendered as a full collapsible level panel; opening one revealed only "Pro tuto úroveň zatím není připravené žádné téma", a dead end that also lengthened the page.

**Implemented Solution:** `app/grammar/page.tsx`: "Ostatní úrovně" renders panels only for levels with topics and adds one quiet line for the rest ("C1, C2: zatím bez připravených témat.", `cs.grammar.emptyLevels`). The focus-level picker already offered only levels with topics.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; mobile page shrinks from 2 521 px to 2 277 px with no console errors.

## Global Cycle 30/120 | Page: [/grammar] (Page Cycle 15/15)

**Summary:** open the collapsed group that holds the topic just studied

**Observed Problem:** The return-to-topic jump from cycle 24 failed silently when the studied topic sat in a collapsed group ("Další témata", "Hotovo" or another level such as A2): the card was not rendered, so nothing scrolled or got focus.

**Implemented Solution:** `app/grammar/page.tsx` remembers the `studied` unit for the page visit (separately from the 4-second highlight) and opens whichever disclosure contains it (upcoming, completed or another level's panel) via `defaultOpen`; the group then stays open after the highlight fades. Measured API timings showed no backend bottleneck on this page (tree, progress and levels each answer in about 20 ms locally), so this consolidation cycle went to the edge case instead.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright opened `/grammar?studied=de-a2-dative` (an A2 topic while the focus level is A1): the A2 panel opened, the card got focus and the highlight.

## Global Cycle 31/120 | Page: [/practice] (Page Cycle 1/15)

**Summary:** concrete mistake recommendations: example words and the right next step

**Observed Problem:** The "Zaměř se na to, co teď dělá potíže" panel showed only an error type and a count ("Význam slova 13×"), and meaning or word-choice mistakes linked to the `/lesson` overview, where nothing practises those words.

**Implemented Solution:** `app/practice/page.tsx`: each recommendation lists up to three of the learner's own words or grammar topics with that mistake type (from the weak-spots API, German nouns with their article) and names the action ("Procvičit rody", "Procvičit v diktátu", "Zopakovat v příští lekci"…). Meaning and word-choice mistakes now go to `/lesson/vocabulary`, whose next lesson re-practises recently missed words. Copy in `lib/i18n/cs.ts`.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; mobile screenshot shows "Význam slova · Například: der Hund, lesen, nein · Zopakovat v příští lekci".

## Global Cycle 32/120 | Page: [/practice] (Page Cycle 2/15)

**Summary:** show when each practice mode was last used

**Observed Problem:** The hub listed twelve modes with no sign of which ones the learner had been neglecting; only the last three opened modes appeared in a chip row, without dates.

**Implemented Solution:** `lib/practice.ts` now also stores the last-open time per mode (`pf_mode_visits`, validated on read, local to the device and never sent to the server, like the existing recent list). Each card in `app/practice/page.tsx` shows "Naposledy dnes / včera / před 5 dny" or "Zatím nevyzkoušeno". New `relativePast` helper in `lib/i18n/cs.ts`.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright opened `/dictation`, then `/practice` showed "Naposledy dnes" on the Diktát card.

## Global Cycle 33/120 | Page: [/practice] (Page Cycle 3/15)

**Summary:** mark modes that need lesson words before the first lesson

**Observed Problem:** In a language with no lessons yet, role-play, dictation, shadowing and word order looked as available as the rest, but each builds on scenes or example sentences the learner has met and opened to an empty state.

**Implemented Solution:** `lib/practice.ts` flags the four modes with `needsWords`. `app/practice/page.tsx` reads the learner's introduced-word count for the active language from the cheap per-language summary endpoint (cycle 5) and, while it is zero, replaces those cards' last-used line with "Pracuje se slovy z lekcí: nejdřív projdi první lekci." The cards stay links (the modes explain themselves); the other eight modes, which use the whole lexicon, are unchanged.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright in French (no lessons) shows the note on exactly 4 cards, and none in German.

## Global Cycle 34/120 | Page: [/practice] (Page Cycle 4/15)

**Summary:** keep the skill filter in the URL and show counts per skill

**Observed Problem:** Choosing "mluvení" on the hub, opening a mode and pressing Back reset the filter to all twelve modes; the chips also gave no idea how many modes each skill offers in the current language.

**Implemented Solution:** `app/practice/page.tsx` reads `?skill=a,b` on load (unknown values ignored) and mirrors the selection with `history.replaceState`, so Back and shared links restore it. Each skill chip shows how many modes train it for the active language (for example "mluvení 2").

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright opened `/practice?skill=speaking` ("2 způsoby procvičování") and adding listening updated the URL to `?skill=speaking,listening`.

## Global Cycle 35/120 | Page: [/practice] (Page Cycle 5/15)

**Summary:** a daily tip that balances neglected skills

**Observed Problem:** With twelve modes and no guidance beyond recent mistakes, learners tended to reopen the same one or two modes; skills such as listening or speaking could go untrained for weeks without any hint.

**Implemented Solution:** `lib/practice.ts` gains `suggestMode`: from the modes usable now (lesson-dependent ones excluded before the first lesson), it picks the skill opened longest ago on this device (never-trained first, stable tie-break) and its least recently opened mode. `app/practice/page.tsx` shows it as a "Tip na dnes" link card with the reason ("Na poslech ses na tomto zařízení naposledy zaměřil(a) před 5 dny."). The tip is deterministic and local, with no streaks or pressure.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; mobile screenshot on a fresh browser suggests "Hraj roli" for listening, never trained on that device.

## Global Cycle 36/120 | Page: [/practice] (Page Cycle 6/15)

**Summary:** open modes with 1-9 and today's tip with Enter

**Observed Problem:** The practice hub had no keyboard shortcuts; on desktop each mode needed the mouse or many Tab stops past the language switcher, recommendations and chips.

**Implemented Solution:** `app/practice/page.tsx` installs the shared hotkey listener: digits 1-9 open the visible cards in order (so they follow the active skill filter), Enter opens the "Tip na dnes" card. Cards and the tip show key badges on wide screens and carry `aria-keyshortcuts`; digit codes are layout-independent (`lib/keyboard.ts`), so the Czech number row works.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright pressed 2 on `/practice?skill=speaking` and landed on `/sounds` (the second speaking mode), and Enter on `/practice` opened the tip's `/roleplay`.

## Global Cycle 37/120 | Page: [/practice] (Page Cycle 7/15)

**Summary:** flashcards from the words you got wrong

**Observed Problem:** The hub's mistake panel pointed to other modes, but there was no quick way to simply rehearse the specific words missed in recent checks; flashcards existed only per level or topic in the dictionary.

**Implemented Solution:** The deck API accepts a third scope, `weak=true`: the profile's unresolved check mistakes from the weak-spots service, still child-filtered and due-first (`services/words.word_deck`, `api/words.py`; exactly one scope is still enforced). `lib/api.ts` adds `DeckScope`; `FlashcardSession` accepts it and an optional close label. `app/practice/page.tsx` offers "Kartičky ze slov s chybami (N)" in the mistake panel and runs the ungraded flashcards in place, returning "Zpět na procvičování". New test `test_weak_deck_holds_exactly_the_unresolved_words`.

**Verification:** `tests/test_mistakes.py` and `tests/test_words.py` 11 passed; ruff, typecheck, production build, `git diff --check` passed; Playwright opened the deck from `/practice` (10 cards, first "können").

## Global Cycle 38/120 | Page: [/practice] (Page Cycle 8/15)

**Summary:** "Jiný tip": step through ranked suggestions

**Observed Problem:** Today's tip offered a single mode; a learner who did not feel like that mode had to fall back to scanning all twelve cards.

**Implemented Solution:** `lib/practice.ts`: `suggestModes` replaces `suggestMode` and returns a full ranking: one mode per skill in order of how long ago the skill was trained (each mode used once), then the remaining modes oldest first. `app/practice/page.tsx` shows the first suggestion and a "Jiný tip" button that cycles through the ranking; the tip text is a polite live region so the change is announced. Enter still opens the shown tip.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright cycled six tips on a fresh device: Hraj roli (listening), Stínování (speaking), Diktát (writing), Slovosled (reading), Rody (grammar), Laboratoř pádů.

## Global Cycle 39/120 | Page: [/practice] (Page Cycle 9/15)

**Summary:** after flashcards, repeat only the cards you did not know

**Observed Problem:** At the end of the weak-word flashcards (and any deck) the only options were to run the whole deck again or leave; the few cards the learner had just marked "Ještě zopakovat" could not be rehearsed on their own.

**Implemented Solution:** `components/FlashcardSession.tsx`: the summary offers "Znovu jen 3 kartičky, které jsem nevěděl(a)" (focused, primary) whenever any card was marked again, starting a round with exactly those cards; "Projít znovu" and the close button stay. Still practice only, nothing is stored. Copy with Czech plural forms in `lib/i18n/cs.ts`.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright ran the 10-card weak deck from `/practice` with the keyboard, marked 3 cards again, and the follow-up round had exactly 3 cards.

## Global Cycle 40/120 | Page: [/practice] (Page Cycle 10/15)

**Summary:** pinned modes lead the grid and keep their shortcuts

**Observed Problem:** Pinning a mode only added a chip above the grid; the card itself stayed in the middle of the list, so pinned favourites got shifting 1-9 shortcuts and the pin button gave no feedback beyond its icon.

**Implemented Solution:** `app/practice/page.tsx`: the grid now lists pinned modes first in pin order (then the usual order, after the skill filter), so a favourite keeps key 1, 2… Toggling a pin announces "Čísla je připnuté a ukazuje se první." / "… už není připnuté." through a polite live region. Copy in `lib/i18n/cs.ts`.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright pinned "Čísla", it became the first card, and pressing 1 opened `/numbers`.

## Global Cycle 41/120 | Page: [/practice] (Page Cycle 11/15)

**Summary:** drop the duplicate pinned and recent chip rows

**Observed Problem:** After cycles 32 and 40 the hub said the same thing three times: a "Moje oblíbené" chip row, a "Naposledy" chip row, and the cards themselves (pinned first, each with its last-used date). On a phone the two rows pushed the grid further down.

**Implemented Solution:** `app/practice/page.tsx` removes both chip rows and their state; pinned modes are visible as the first cards with an active pin button, and recency lives on each card. The dashboard keeps its own shortcut chips.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; no console errors on the 390 px render.

## Global Cycle 42/120 | Page: [/practice] (Page Cycle 12/15)

**Summary:** steady tip while loading; retry when mistakes fail to load

**Observed Problem:** The tip was computed before the word count arrived, so in a fresh language it first suggested a lesson-dependent mode and then jumped to another one; a failed weak-spots request left a dead "Něco se nepovedlo" in the mistake panel.

**Implemented Solution:** `app/practice/page.tsx` waits for the per-language summary (success or failure) before suggesting, showing a tip-sized placeholder meanwhile; if the summary fails, nothing is locked. The mistake panel uses `RetryNotice` ("Nepodařilo se načíst poslední chyby.") that re-runs both requests.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; Playwright with weak-spots returning 500 showed the retry notice, and after recovery the recommendations ("Například: …") appeared.

## Global Cycle 43/120 | Page: [/practice] (Page Cycle 13/15)

**Summary:** shorter mode cards on phones

**Observed Problem:** On a 390 px phone each of the twelve cards was about 190 px tall (large padding, full blurb, a row of skill tags that duplicates the filter chips), so the hub needed 3 600 px of scrolling.

**Implemented Solution:** `app/practice/page.tsx`: below `sm` cards use tighter padding, a smaller icon tile, a two-line clamped blurb and no skill-tag row (skills remain available as filter chips); the grid gap shrinks. From `sm` up the cards are unchanged.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; 390 px page height drops from 3 618 px to 2 842 px with no console errors.

## Global Cycle 44/120 | Page: [/practice] (Page Cycle 14/15)

**Summary:** trim repeated copy and fold skill chips into one row

**Observed Problem:** The top of the hub repeated itself: the intro and the mistake panel both explained that practice is not graded, and the skill label plus six chips wrapped into three rows on a phone, so the first mode card sat below the fold.

**Implemented Solution:** `lib/i18n/cs.ts`: the mistake panel's help is now one line ("Podle posledních chyb v ověřeních."); the ungraded note stays once, in the intro. `app/practice/page.tsx`: the skill label sits above the chips, which form one swipeable row on phones (the group is labelled by it) and wrap from `sm` up.

**Verification:** typecheck, production build, ruff, `git diff --check` passed; 390 px page height 2 754 px (from 2 842 px), no console errors.

## Global Cycle 45/120 | Page: [/practice] (Page Cycle 15/15)

**Summary:** keep pins, recent modes and last-used dates per profile

**Observed Problem:** Pinned modes, the recent list and the new last-used dates were stored under one browser key, so on a shared family tablet a child's pins and "Naposledy dnes" appeared on a parent's practice hub and dashboard after switching profiles, and today's tip was based on someone else's activity. (A request audit of `/practice` on a production build showed 4 API calls, so no performance work was needed here.)

**Implemented Solution:** `lib/practice.ts` keys `pf_pinned_modes`, `pf_recent_modes` and `pf_mode_visits` by the acting profile id; all readers and writers take the profile (`app/practice/page.tsx`, `app/page.tsx`, `components/AppShell.tsx`) and re-read when the acting profile changes. Older unkeyed entries are ignored rather than attributed to whoever logs in next.

**Verification:** typecheck, production build, ruff, `git diff --check` passed.

## Global Cycle 46/120 | Page: [/words] (Page Cycle 1/15)

**Summary:** keep filters, scope and the open word in the URL

**Observed Problem:** The word list read q, word and tab once on mount and never wrote anything back. Status, due and level/topic scope filters and the open word were lost on reload or Back, and a filtered view could not be shared or bookmarked. The groups effect also cleared the scope on its first run, so even a URL scope could not survive.

**Implemented Solution:** The page now writes tab, q, status, due, level/topic and word back with history.replaceState and restores all of them on load. A topic scope from the URL is resolved to its title once the group list arrives. The scope is dropped only when the language or profile actually changes, not on first load.

**Verification:** Playwright: Show words on A1, filter Učím se, open a word -> URL ?tab=all&level=A1&status=learning&word=…; reload restores chip 'Jen: A1', pressed status and open inspector; ?topic=<id> shows 'Jen: Ahoj, jak se jmenuješ?'. No console errors. typecheck, next build, ruff, git diff --check pass.

## Global Cycle 47/120 | Page: [/words] (Page Cycle 2/15)

**Summary:** show the lesson scene and line where a word is taught

**Observed Problem:** The word card showed rank, an example sentence and statistics, but not where the learner met the word. The product teaches words inside scenes (context first), yet the dictionary cut that link: a learner looking up 'bin' or 'Frau' could not see the dialogue line it came from or go back to that lesson's words.

**Implemented Solution:** Word detail now returns up to three lesson scenes that teach the word, in curriculum order, filtered with the same child-scene rule as topics. For each it returns the first line that uses the word, found by the scene's tagged segment id (so inflected forms such as 'bin' for 'sein' are found), with a word-boundary lemma fallback for plain lines. The inspector shows a 'Kde se slovo učí' block with the scene title, the line with the word highlighted and its Czech translation. Tapping it scopes the list to that lesson's words.

**Verification:** New pytest test_word_detail_shows_the_lesson_scenes_that_teach_it covers plain-line match, no-line scene, a word with no scene, tagged inflected segment ('Hauses') and the child profile not seeing the hidden scene; tests/test_words.py 7 passed. Real data: sein -> 'Hallo, Anna! Ich bin Tom.' match 'bin'. Playwright: inspector shows 'Moje rodina / Wer ist der Mann?', click scopes list to 'Jen: Moje rodina' (?topic=…). No console errors. typecheck, next build, ruff check/format pass.

## Global Cycle 48/120 | Page: [/words] (Page Cycle 3/15)

**Summary:** show recognition and recall evidence separately on the word card

**Observed Problem:** The word card collapsed knowledge into one linear ladder (Viděné to Zvládnuté) plus raw correct/error totals that mix lesson practice with checks. A learner could not see that recognising and producing a word are separate states, or how many first-try check answers on how many days each one still needs. A word with no checks looked the same as one that was nearly known.

**Implemented Solution:** The word detail API now returns check-evidence tallies (correct answers and distinct days) for recognition and for recall, plus the policy thresholds. The counting moved into a shared evidence_counts() helper, so the card and the progress update use the same query. The inspector shows a 'Co ukázala ověření' block with two separate rows. Each row says 'splněno', 'zatím neověřeno' (no evidence: unknown, not zero) or 'N z 3 správně · N z 2 dnů', with a bar that follows the weaker of the two requirements.

**Verification:** New pytest test_word_detail_counts_check_evidence_separately_for_recognition_and_recall: recall counts toward both, a non-evidence miss is ignored, and a word without events shows 0/0. tests/test_words.py and tests/test_learning.py pass. Playwright with a stubbed response shows 'splněno' and '2 z 3 správně · 1 z 2 dnů', and real data shows 'zatím neověřeno'. No console errors. typecheck, next build, ruff check/format pass.

## Global Cycle 49/120 | Page: [/words] (Page Cycle 4/15)

**Summary:** sort the word list by next check, mistakes or lesson date

**Observed Problem:** The list could only be read in frequency order. A learner who wanted to see which words are checked next, which ones cause the most mistakes, or what the last lesson brought had to scan up to the full list page by page. The row also said 'teď k ověření' for a check due in up to 12 hours, because the date was rounded to whole days.

**Implemented Solution:** The words API accepts sort=rank|review|errors|recent. The order is server-side and always ends on rank and id, so offset paging stays stable. Words with no date sort last. The page adds a 'Řadit' select that is kept in the URL (?sort=). Rows show the next check time when sorted by review and an error count when sorted by mistakes. Due wording uses relativeFuture, so only a past date reads as due ('do hodiny', 'zítra' and so on otherwise).

**Verification:** New pytest test_word_list_sorts_by_review_errors_and_recent covers all four orders, the null-last rule and 422 on an unknown sort; tests/test_words.py 9 passed. Playwright: each option reorders rows (errors shows '1 chyba', review shows 'do hodiny', recent starts with Schule), the URL gets ?sort=… and a reload keeps it. Mobile 390px screenshot checked. No console errors. typecheck, next build, ruff pass.

## Global Cycle 50/120 | Page: [/words] (Page Cycle 5/15)

**Summary:** make status counts follow the search and due filters

**Observed Problem:** The status chips always counted every word in the scope and ignored the search and 'K opakování' filters. With the due filter on, the chips still said 'Učím se 41' over a list of 3 rows. The 'Vše' chip added up the same unfiltered counts, so it disagreed with the list, and the chips were no help for narrowing a search result.

**Implemented Solution:** The list endpoint now applies search, due and scope before counting statuses (the status filter still narrows only the rows, not its own chips). The chips and 'Vše' now always match what the list can show. The empty-state copy now depends on whether any filter is active, not on a zero count, so a search with no match reads 'Nic neodpovídá hledání.' rather than the first-run 'Zatím tu nic není'. The export stays available while filtering.

**Verification:** New pytest test_status_counts_follow_search_and_due_filters (search, due, status-filter facet rule); tests/test_words.py 10 passed. Playwright: unfiltered 'Vše 41 | Učím se 41'; search 'hund' gives 'Vše 1 | Učím se 1' with 1 row; 'zzzz' gives 0 counts with 'Nic neodpovídá hledání.' and export still visible. The command palette only reads items, so it is unaffected. typecheck, next build, ruff pass.

## Global Cycle 51/120 | Page: [/words] (Page Cycle 6/15)

**Summary:** drive the word list from the search box and browse cards with arrows

**Observed Problem:** Keyboard use of the dictionary was fragmented. '/' opened the command palette instead of the page search. ↑/↓/Enter worked only when focus was on the list background, not in the search box where typing happens. Once a row was clicked (a button), the arrows did nothing. With a word card open, moving down the list did not change the card, so reading through words meant clicking each one.

**Implemented Solution:** The search input is now the page search ('/' focuses it) and acts as a combobox: ↑/↓ move the highlighted row (aria-activedescendant), Enter opens it, Escape clears the search and a second Escape closes the card. Arrows also work from a focused row and move focus with the highlight. While a card is open, moving the highlight browses: the card follows the row. The hint shows / ↑ ↓ Enter.

**Verification:** Playwright: '/' focuses data-page-search; typing 's', ↓, Enter opens 'sie'; ↓ switches the card to 'ja'; Escape clears the query, a second Escape closes the card; clicking row 3 ('sein') then ↓ opens 'in' with focus on word-row-3. No console errors. typecheck, next build, ruff pass.

## Global Cycle 52/120 | Page: [/words] (Page Cycle 7/15)

**Summary:** play words from the list and make P work on the word card

**Observed Problem:** Hearing a word in the dictionary took a click to open its card first, and the card's play button advertised the P hotkey that never fired: the words page did not install the shared hotkey listener. Slower playback, offered on practice screens, was missing here.

**Implemented Solution:** Each list row now has a small play button labelled 'Přehrát <lemma>' next to the row (not nested inside the row button). The page installs useHotkeys, so P plays the open word and Alt+P works from the search box. The card shows the P key hint and the shared 'Pomaleji' toggle.

**Verification:** Playwright: no audio request on load (60 play buttons stay idle); 'Přehrát sein' requests that word's audio without opening the card; P with the card open requests the open word; Alt+P from the focused search plays and types nothing. The container has no TTS, so audio answers 503 and the button shows its unavailable state; the requests are what was checked. No other console errors. typecheck, next build, ruff pass.

## Global Cycle 53/120 | Page: [/words] (Page Cycle 8/15)

**Summary:** filter the word list by part of speech

**Observed Problem:** The list could be narrowed by status, due date and scope but not by kind of word, although learners practise by kind: noun genders, verb forms, adjectives. Finding the 8 verbs among 41 German words meant scrolling or guessing search terms.

**Implemented Solution:** The words API takes kind=noun|verb|adj|adv|other, which maps Universal Dependencies POS tags to learner-facing groups (PROPN counts with nouns, AUX with verbs, every other tag is 'other'). Kind is one of the facet filters, so the status counts follow it. The page adds a swipeable 'Druh slova' chip row (Podstatná jména, Slovesa, Přídavná jména, Příslovce, Ostatní). Tapping a chip again clears it, and the choice is kept in the URL (?kind=).

**Verification:** New pytest test_word_list_filters_by_word_kind (noun/verb/adj/other, counts add up to total, 422 on unknown); tests/test_words.py 11 passed. Playwright: Slovesa shows 'Vše 8' with sein, haben, können, kommen; nouns show der Mann, die Frau; Ostatní shows der, und, in, ein; a reload keeps the choice; no horizontal overflow at 390px. No console errors. typecheck, next build, ruff pass.

## Global Cycle 54/120 | Page: [/words] (Page Cycle 9/15)

**Summary:** practise hand-picked words as flashcards and select a whole filtered view

**Observed Problem:** Selecting words in the list only let a learner add them to a collection. To rehearse a few chosen words (say all verbs due this week), the learner had to create a collection first, and selecting a filtered view meant ticking each row. Nothing showed the 100-word limit of the bulk endpoint until a request failed.

**Implemented Solution:** The flashcard deck API takes a hand-picked scope (ids=…, up to 100). The same own-words join and child filter apply, so ids of unmet or hidden words are just left out. The selection bar gets 'Kartičky z vybraných', which opens the practice-only flashcard session on exactly those words. A 'Vybrat zobrazená (N)' checkbox selects or clears all visible rows. Selection is capped at 100 with a note, and further row checkboxes are disabled.

**Verification:** New pytest test_deck_from_picked_words_keeps_only_own_suitable_words: a child profile gets Haus and gehen (Mord hidden, neu unmet), with the due word first; mixing ids with level gives 422, and 101 ids give 422. tests/test_words.py 12 passed. Playwright: ?kind=verb, select shown gives 'Vybráno slov: 8', 'Kartičky z vybraných' opens 'Vybraná slova (8)' with a deck request. No console errors. typecheck, next build, ruff pass.

## Global Cycle 55/120 | Page: [/words] (Page Cycle 10/15)

**Summary:** explain the status chips, due clock and gender colours in a legend

**Observed Problem:** The dictionary used five status labels, a clock icon and coloured articles without saying what any of them meant. 'Učím se' versus 'Poznám' versus 'Umím' encodes the separate recognition and recall evidence rules, and 'Zvládnuté' needs a later confirming check. A learner seeing 41 words stuck at 'Učím se' could not tell that lesson practice does not count and that only checks move a word on.

**Implemented Solution:** A collapsed 'Co znamenají stavy a barvy' disclosure under the status chips explains each state in ladder order with its pill colour. Each explanation matches the backend rules: seen is exposure without a lesson; learning is a lesson or placement word waiting for a check; passive is repeated correct recognition in checks on different days; known adds recall; mastered is confirmed again later. It also explains the due clock, including the 30-day review rule, and, for German, French and Italian, the article colours (der/die/das or m/f).

**Verification:** Copy checked against services/words._status, learning.mark_seen, placement re-queueing and LearningPolicy (decay_after 30 days). Playwright at 390px: the legend opens, has no horizontal overflow, and the screenshot was inspected. No console errors. typecheck, next build, ruff pass.

## Global Cycle 56/120 | Page: [/words] (Page Cycle 11/15)

**Summary:** add skeletons and retry for the list, groups, word card and load more

**Observed Problem:** The page's failure and loading states were dead ends. A failed list, group or card load showed a plain error with no way to retry except reloading the page, and loading was the bare text 'Načítám…'. A failed 'Načíst další' threw an unhandled promise rejection and left the button looking idle. Once one card failed, the error stuck to every word opened next, because the inspector never reset its failure flag. Switching language briefly showed the previous language's words.

**Implemented Solution:** The list, the level/topic groups and the word card each show a RetryNotice with their own message and refetch on retry, through an attempt counter in the effect deps. Loading shows shape-matching skeletons: list rows, three group cards and card lines. 'Načíst další' catches failures, shows a retry notice and shows 'Načítám…' while busy. The inspector clears its failure on every new word. A language or profile switch clears the old list before the new one arrives.

**Verification:** Playwright with request interception: a failed groups request shows the alert, and retry gives 4 group cards; a failed list shows the alert, and retry gives 41 rows; a failed card shows the alert, and retry shows 'der'. Load-more failure was not exercised: local data has 41 words, under the 60-row page, so the button never appears. No console errors apart from the injected 500s. typecheck, next build, ruff pass.

## Global Cycle 57/120 | Page: [/words] (Page Cycle 12/15)

**Summary:** make the word card a proper bottom sheet on phones

**Observed Problem:** On a 390px phone the word card was a fixed panel at z-20, under the z-30 bottom navigation. Its last rows (answer history and legend) were hidden behind the nav. There was no backdrop, the page behind kept scrolling, and the close button scrolled out of view in a long card. The new context line also highlighted the substring 'in' inside 'Berlin' instead of the tagged word 'in'.

**Implemented Solution:** On phones the card is a sheet above the navigation (z-50) with a dimmed backdrop that closes it. Page scroll is locked while the sheet is open and restored on close, and the sheet uses overscroll-contain, a max of 85dvh and safe-area bottom padding. A sticky header with a grab handle keeps the close button reachable, and Escape closes the card on every screen size (unless typing). On desktop the card stays a sticky side panel with no backdrop or scroll lock and is capped at the viewport height. Highlighting now matches the tagged word on Unicode word boundaries.

**Verification:** Playwright at 390px: the card opens with body overflow hidden; scrolled to the end, the last text ends at y=823 and is visible above the bottom edge; a backdrop tap closes it and restores overflow; Escape closes it. At 1280px the backdrop is hidden and there is no scroll lock. The highlight for 'in' marks the word in 'Berlin ist eine Stadt in Deutschland', not Berl-in. Screenshot inspected. No console errors. typecheck, next build, ruff pass.

## Global Cycle 58/120 | Page: [/words] (Page Cycle 13/15)

**Summary:** search without diacritics and explain links to words not in the dictionary

**Observed Problem:** Search matched exact characters only. A Czech learner typing 'skola' did not find 'die Schule — škola', 'dum' did not find 'dům', and a German learner typing 'gross' or 'schon' missed 'groß' and 'schön'. Desktop keyboards without a Czech layout make that the common case. A shared or stale ?word= link to a word the profile has never met showed 'could not load' with a retry button that could never work.

**Implemented Solution:** Search now folds diacritics on both sides without a database extension. In Python, fold() lowercases, maps the Czech, German, French and Italian accented letters and turns ß into ss. In SQL, replace(translate(lower(col))) does the same, so 'dum', 'dům' and 'DŮM' all match the same rows. LIKE wildcards in the input stay literal. A 404 on the word card now shows a calm note ('Toto slovo ve tvém slovníku zatím není…') instead of an error with a useless retry.

**Verification:** New pytest test_word_search_ignores_diacritics_on_both_sides covers dum/dům, schon, HEZKÝ, the '50%' literal and fold('Straße Žluťoučký'); tests/test_words.py 13 passed. Playwright on real data: 'skola' finds die Schule and 'gross' finds groß; ?word=<unknown uuid> shows the missing-word note without a retry button. No console errors apart from the expected 404. typecheck, next build, ruff pass.

## Global Cycle 59/120 | Page: [/words] (Page Cycle 14/15)

**Summary:** load the word list and collections only when they are needed

**Observed Problem:** Every visit to /words (which opens on the level tab) made 5 API calls. Two of them were not needed: the full word list (three SQL queries for counts, total and rows) was rendered into a hidden panel, and the collection list is only used once a word is selected. Every list change also waited a fixed 180 ms debounce, including the first load and chip taps, which need no debounce.

**Implemented Solution:** The word list loads the first time the 'Všechna slova' tab is shown and stays loaded across tab switches. Collections load the first time something is selected, and the bar shows 'Načítám…' until then. The 180 ms debounce now applies only while typing in the search, so the first load, chips, sort and kind run at once.

**Verification:** Production build (next start on :3002): /words went from 5 API requests to 3 (me, ranks, groups). Opening 'Všechna slova' makes 1 list request; going back and forth makes 0 more; typing 'haus' makes 1 list request; the first selection makes 1 collections request. Deep links with ?tab=all still load the list at once (cycle 46 test path). No console errors. typecheck, next build, ruff pass.

## Global Cycle 60/120 | Page: [/words] (Page Cycle 15/15)

**Summary:** bring the first word into view on a phone

**Observed Problem:** Fourteen cycles of filters, legend and selection piled controls above the list. On a 390x844 phone the first word row started at y=812, under the bottom navigation, so opening the dictionary showed no words at all. The intro paragraph, a full-width collections button, a wrapping tab label, an export disclosure and two rows of wrapping status chips came first.

**Implemented Solution:** On phones the intro is hidden and the collections link sits beside the title. The tabs no longer wrap. The status chips scroll in one row (they still wrap on wider screens). Sort shares a row with the legend toggle. The rarely used CSV/Anki export moved below the list. Desktop keeps the same structure, with the intro and the collections button in the header.

**Verification:** Playwright 390x844: the first row moved from y=812 to y=627 with no horizontal overflow, and mobile and 1280px screenshots were inspected. Regression scripts for sort (cycle 49), kind filter (cycle 53) and URL state (cycle 46) pass. No console errors. typecheck, next build, ruff pass.

## Global Cycle 61/120 | Page: [/insights] (Page Cycle 1/15)

**Summary:** split weekly check accuracy into recognition, recall and grammar

**Observed Problem:** The accuracy chart averaged every graded answer, word recognition, word recall and grammar, into one line. The product keeps passive recognition and active production as separate knowledge states, but the chart could not show that a learner recognises words at 95% and produces them at 40%. A week without answers was joined across as if the line continued.

**Implemented Solution:** The insights API returns, per week, the total and separate tallies for recognition (non-recall word checks), recall (written or spoken production) and grammar. The tallies come from one grouped query by task type plus the grammar query. The chart draws one coloured line per skill that has data. Weeks without answers break the line instead of being bridged, and dot size grows with the number of answers, so a 1/1 week no longer looks as solid as 40/50. A legend gives each skill's overall share and count, and point titles give 'N z M správně'.

**Verification:** tests/test_insights.py extended: recognition 1/2, recall 1/1 and grammar 0 tallied apart, and the totals equal their sum; 2 passed. Real data: week of 2 Nov shows 'Poznat význam, Týden od 2. 11.: 23 z 23 správně' and the legend 'Poznat význam 100 % · 23×'. Screenshot inspected. No console errors. typecheck, next build, ruff pass.

## Global Cycle 62/120 | Page: [/insights] (Page Cycle 2/15)

**Summary:** show which words and topics are behind each mistake type

**Observed Problem:** The mistakes panel listed error types with counts ('Rod: 7') and nothing else, so the learner knew a weakness existed but not where. To find the nouns behind the gender errors they had to search the dictionary word by word. The word query also lacked the child content filter, so a child profile's miss on a since-flagged word still counted in the panel (the forecast already filtered it).

**Implemented Solution:** Each mistake type now carries up to six words or grammar topics behind it, with per-item counts, most frequent first. Words show their article and Czech meaning, topics their level. Rows in the panel are buttons (aria-expanded) that open the list, and each entry links to the word card (/words?word=…) or the grammar topic. The word side uses _suitable(user), like the forecast and day views.

**Verification:** tests/test_insights.py: gender mistake lists ('word', und, 1); the child profile's tagged miss on a violence-flagged word no longer appears. Run against the old service, both tests fail ('Left contains one more item: meaning'), confirming the leak; with the change, 2 passed. Playwright with stubbed data at 390px: 'Rod (der/die/das)' expands to 'der Mann · muž 2×' and 'Členy · A1 1×' with correct hrefs. No console errors. typecheck, next build, ruff pass.

## Global Cycle 63/120 | Page: [/insights] (Page Cycle 3/15)

**Summary:** turn the review forecast into actions: check today, open words later

**Observed Problem:** The forecast showed what is due per day, but its links all went to the unfiltered dictionary or grammar index, and the word chips were plain text. Seeing '41 words due today' led nowhere near the check that clears them. Future days gave no hint that those words do not need checking yet.

**Implemented Solution:** Today's detail now offers 'Ověřit slova (N)' (/check) and 'Ověřit gramatiku (N)' (/grammar/check), and its heading reads 'Co tě čeká dnes'. For a later day, the link opens the dictionary ordered by next check (/words?tab=all&sort=review, cycle 49), and a note says those items can wait. Every word chip links to its word card, and topics use client-side Links.

**Verification:** Playwright, real data (no words due before local midnight): 8 Nov shows 'Otevřít slovník -> /words?tab=all&sort=review', chips link to /words?word=…, and the later note is shown. With a stub that makes today due: 'Ověřit slova (41) -> /check', 'Ověřit gramatiku (1) -> /grammar/check', and no later note. No console errors. typecheck, next build, ruff pass.

## Global Cycle 64/120 | Page: [/insights] (Page Cycle 4/15)

**Summary:** show what the knowledge funnel means and which words are fading

**Observed Problem:** The funnel showed five bare numbers with bars. It did not say how many studied words still wait for their first check-based recognition, or how many recognised words have gone past the 30-day decay window and are due for review, the product's core spaced-repetition rule. It also counted child-filtered words that the forecast already hid.

**Implemented Solution:** The funnel query applies the child content filter and adds 'fading': recognised words whose last error-free check is older than POLICY.decay_after. Rows show count and share of studied words. Rows that match a dictionary filter (all studied, mastered) link to it; passive and active overlap the status ladder and stay plain. Two action lines follow: 'N probraných slov ještě čeká…' links to status=learning, and 'N slov přes 30 dní bez ověření' links to due words. A help line says the counts come from checks only, with recognition and recall measured separately. An empty state covers a profile with no studied words.

**Verification:** tests/test_insights.py: a passive word with last_error_free_at 31 days ago counts as fading=1, and the child profile's funnel no longer counts the violence-flagged word (introduced 0); 2 passed. Playwright on real data: '41 probraných slov ještě čeká…', shares '0 · 0 %', links /words?tab=all, …status=mastered and …status=learning. No console errors. typecheck, next build, ruff pass.

## Global Cycle 65/120 | Page: [/insights] (Page Cycle 5/15)

**Summary:** keep the selected activity and forecast day across navigation

**Observed Problem:** The activity calendar and forecast details link out to word cards and grammar topics, but the chosen day lived only in component state. After opening a word from 5 Nov and pressing Back, the page reset to the most recent active day (7 Nov), so the learner lost their place every time they followed a link. A specific day could not be linked either.

**Implemented Solution:** The selected activity day (?day=) and a non-default forecast day (?forecast=) are mirrored to the URL with replaceState once data has loaded, and read back on load. Unknown or out-of-range dates fall back to the previous defaults: the last active day and today.

**Verification:** Playwright: default load writes ?day=2026-11-07; picking 5 Nov sets ?day=2026-11-05 and the heading 'Učení · 5. 11.'; opening a word from that day and going Back restores ?day=2026-11-05 with the same heading. No console errors. typecheck, next build, ruff pass.

## Global Cycle 66/120 | Page: [/insights] (Page Cycle 6/15)

**Summary:** navigate the activity calendar and forecast with arrow keys

**Observed Problem:** The activity calendar rendered 182 day buttons, each its own tab stop, and the forecast added 14 more. A keyboard user had to press Tab about 190 times to get past the calendar, and could not move to the previous week or day directly.

**Implemented Solution:** Both charts use a roving tabindex. The calendar is one tab stop (the selected day): ←/→ move a week, ↑/↓ a day, Home/End jump to the first/last day, and the moved-to day is selected (and its details load) with focus following. The forecast is one tab stop with ←/→/Home/End. A desktop hint 'Šipky: ← → týden, ↑ ↓ den' is linked through aria-describedby.

**Verification:** Playwright: 2 tab stops across 196 chart buttons; from 7 Nov, ← goes to 31 Oct (URL ?day=2026-10-31), ↑ to 30 Oct, End to 7 Nov, Home to 10 May; in the forecast, →→ focuses and selects 9 Nov (?forecast=2026-11-09). No console errors. typecheck, next build, ruff pass.

## Global Cycle 67/120 | Page: [/insights] (Page Cycle 7/15)

**Summary:** filter the activity calendar by checks or practice

**Observed Problem:** The calendar coloured each day by all answers together. A day with 84 lesson-practice answers looked the same as a day of real checks, although only checks count as evidence. A learner who wanted to see how regularly they actually verify words (the rule that moves words forward and keeps them from fading) could not see it.

**Implemented Solution:** A segmented control above the calendar (Vše / Ověření / Procvičování) recolours the days by the chosen count, scaled to that count's own maximum. The summary line then reads, for example, 'Dny s ověřením: 1 z posledních 182.' The default stays 'Vše' with the existing no-streak sentence.

**Verification:** Playwright on real data: Vše colours 5 Nov and 7 Nov brand-600; Ověření makes 5 Nov empty (0 checks) and keeps 7 Nov; Procvičování colours both. The summary changes to 'Dny s ověřením: 1 z posledních 182.' No console errors. typecheck, next build, ruff pass.

## Global Cycle 68/120 | Page: [/insights] (Page Cycle 8/15)

**Summary:** hear the words listed in activity, forecast and mistake details

**Observed Problem:** Insights lists many words (those practised on a day, those due on a forecast day, those behind a mistake type) but each was text only. To hear one, the learner had to leave the page and open the word card, which broke the review-by-ear flow the other pages support.

**Implemented Solution:** Each word in the activity-day list, the forecast chips and the mistake drill-down has a small PlayButton ('Přehrát <lemma>'). It sits next to the link, not inside it, so playing does not navigate. Clips load only on click.

**Verification:** Playwright 390px with ?day=2026-11-05&forecast=2026-11-08: 77 play buttons render with no audio request on load; clicking the first requests that word's audio and stays on /insights. TTS is not available in the container (503), so the request was checked, not playback. The same run found a pre-existing horizontal overflow at 390px from the calendar panel (section 560px wide); it is left for the mobile cycle. No console errors. typecheck, next build, ruff pass.

## Global Cycle 69/120 | Page: [/insights] (Page Cycle 9/15)

**Summary:** label the activity calendar with weekdays and months and open it on recent weeks

**Observed Problem:** The 26-week calendar was an unlabelled grid of squares: no weekday or month labels, so 'which day was that?' meant hovering each cell. The padding cells in the first column were smaller than the day cells (size-3 vs size-4), so the first week's days sat one pixel step off. On a phone the panel was wider than the screen (560px at 390px, because the grid item could not shrink), so the page scrolled sideways and opened on May.

**Implemented Solution:** A sticky weekday column (Po, St, Pá, Ne) and a month label over the first week of each month (Czech abbreviations, aria-hidden, since every day button already has its full date). Padding cells now match the day size. The panel grid items get min-w-0, so the calendar scrolls inside its own panel, and it opens scrolled to the latest weeks.

**Verification:** Playwright: at 390px there is no page overflow (overflow scan finds no element) and the calendar's scrollLeft equals its maximum (209) on load; at 1280px it fits without scrolling. Desktop and mobile screenshots show 'čvn … lis' labels and Po/St/Pá/Ne aligned with the rows. No console errors. typecheck, next build, ruff pass.

## Global Cycle 70/120 | Page: [/insights] (Page Cycle 10/15)

**Summary:** mark thin weekly evidence and offer the accuracy numbers as a table

**Observed Problem:** The accuracy chart drew a week with 1 of 1 correct answers as a solid 100% point, visually as strong as a week of 40 answers. The exact numbers were only in SVG <title> tooltips, which touch screens and many screen readers never show. On a phone the chart could not be read precisely at all.

**Implemented Solution:** Points for weeks with fewer than five answers get a dashed ring, and the help text explains this (together with the dot size growing with answer count). A 'Zobrazit čísla po týdnech' disclosure under the chart opens a real table: rows are weeks with answers, columns are the skills, cells show 'správně/odpovědí' or '–'. It scrolls inside its panel on narrow screens.

**Verification:** Playwright 390px with stubbed tallies: 2 of 4 points are dashed (recall 1/2 and grammar 3/3); the table lists '19. 10. – 1/2 –', '26. 10. – 6/12 3/3' and '2. 11. 23/23 – –'; no page overflow. No console errors. typecheck, next build, ruff pass.

## Global Cycle 71/120 | Page: [/insights] (Page Cycle 11/15)

**Summary:** add panel skeletons and retry for statistics and the day view

**Observed Problem:** While the statistics loaded, the page showed the bare text 'Načítám…' and then jumped into five panels. A failed load showed a generic error with no retry, and the failure flag was never reset, so a later language switch could show the error above fresh data. A failed day view also had no way to try again except picking another day.

**Implemented Solution:** Loading shows four outlined skeleton panels titled like the real ones (calendar full width), so the layout does not jump. Failures show RetryNotice with their own messages: 'Statistiky se nepodařilo načíst.' refetches the whole page through an attempt counter, and 'Přehled dne se nepodařilo načíst.' refetches only the selected day. The failure flag resets on every load. The day view uses a skeleton instead of loading text.

**Verification:** Playwright with interception: during a 1.2s delayed request, 4 skeletons (role=status) show; a failing insights request shows the statistics alert; retry renders all panels; a failing day request shows the day alert, and retry shows 'Učení · 7. 11.'. No console errors apart from the injected 500s. typecheck, next build, ruff pass.

## Global Cycle 72/120 | Page: [/insights] (Page Cycle 12/15)

**Summary:** replace five empty charts with one first-run step

**Observed Problem:** For a language with no lessons yet (French for the test admin), the page showed an empty 26-week calendar, an empty forecast, 'Zatím žádné odpovědi', a funnel of zeros and 'Žádné chyby s rozpoznaným druhem'. The last one implied checks had happened and were clean. The weekly recap above repeated its own 'Začít lekci' prompt.

**Implemented Solution:** When the language has no active days, no studied words and nothing in the forecast, the page shows one dashed card: what the statistics will show, why nothing is there yet, and a 'Začít lekci' button to /lesson/vocabulary. The weekly recap is hidden in that state. With data present but no checks, the mistakes panel says 'Zatím žádné ověření…' instead of claiming there were no mistakes.

**Verification:** Playwright 390px: switching to Francouzština shows the first-run card once with no recap (screenshot inspected); switching back to Němčina shows the 6 panels including the recap. API confirms fr has active_days 0 and an all-zero funnel. No console errors. typecheck, next build, ruff pass.

## Global Cycle 73/120 | Page: [/insights] (Page Cycle 13/15)

**Summary:** shorten the statistics page on phones

**Observed Problem:** At 390px the statistics page was 4361px tall. The weekly recap stacked its four stat tiles one per row, a busy day's activity listed all 41 practised words, and the 14 forecast labels ('8. 11.') wrapped onto two lines under bars about 20px wide.

**Implemented Solution:** The recap tiles form a 2x2 grid on phones (four across on desktop), which also tightens the dashboard where the recap is reused. A day's word list shows the first 8 words with 'Zobrazit všech N slov' / 'Zobrazit méně'; the toggle resets when another day is picked. Forecast labels show only the day of month ('9.'), with the full date at a month start, and do not wrap.

**Verification:** Playwright 390px: page height went from 4361px to 2918px; the overflow scan finds no element wider than the viewport; the forecast screenshot shows single-line labels 'dnes 8. 9. … 20.'. No console errors. typecheck, next build, ruff pass.

## Global Cycle 74/120 | Page: [/insights] (Page Cycle 14/15)

**Summary:** bound the forecast payload and fetch only the day the calendar settles on

**Observed Problem:** Insights is fast on test data (about 15ms, 16KB), but the forecast sent every word due in the next 14 days with lemma and translation. At the 2500-5000 words the curriculum aims for, the response grows without limit while the page shows a few chips per day. Walking the calendar with the new arrow keys also fired one day request per key press.

**Implemented Solution:** The forecast keeps exact per-day counts but sends at most 30 words per day, ordered by next check and then frequency, so the first items are stable. The day view shows 'a N dalších…' linking to the dictionary ordered by review, and the 'Ověřit slova (N)' count uses the exact total. The day request waits 150ms and is cancelled when the selection moves on, so only the settled day is fetched.

**Verification:** New pytest test_forecast_lists_at_most_30_words_per_day_but_counts_all: 35 due words give words=35, 30 items, Wort1 first; tests/test_insights.py 3 passed. Real data: 8 Nov is words=41 with 30 items, and the UI shows 30 chips plus 'a 11 dalších…'. Playwright: six ↑ presses make 1 day request (2026-11-01). Endpoint timings measured locally: insights 15-19ms, recap 11-13ms, day 6-7ms. No console errors. typecheck, next build, ruff pass.

## Global Cycle 75/120 | Page: [/insights] (Page Cycle 15/15)

**Summary:** order the statistics panels by what the learner can act on

**Observed Problem:** Fourteen cycles made the forecast (with check buttons) and the mistake drill-down the actionable parts of the page, but they sat below a full-width half-year calendar. On a phone, reaching 'Co tě čeká' meant scrolling past the recap, the calendar and a 41-word day list. The calendar answers 'how regular was I', which is the least urgent question.

**Implemented Solution:** The panels now go forecast, mistake types, accuracy, funnel, then the activity calendar full width last. The loading skeletons follow the same order, so nothing jumps when data arrives. URL state, arrow-key navigation and the day view are unchanged.

**Verification:** Playwright 390px: panel order is Týden v kostce, Co tě čeká, Druhy chyb, Přesnost, Od lekce k jistotě, Aktivita; the forecast heading is now at y=780 (it was below the calendar). Regression scripts for keyboard navigation (cycle 66), URL day restore after Back (cycle 65) and retry states (cycle 71) pass after updating their selectors to the calendar's label. No console errors. typecheck, next build, ruff pass.

## Global Cycle 76/120 | Page: [/lesson] (Page Cycle 1/15)

**Summary:** recommend the next unstudied topic, an open lesson or due checks

**Observed Problem:** The lesson overview recommended 'the first non-mastered unit' of the target level. A topic the learner had already studied but not yet mastered (the normal state after one lesson) was recommended again as the next lesson: for the test profile, 'Já jsem, ty jsi: sloveso sein' even though it was studied and a lesson in it was still open. The page also ignored the open lesson and the due grammar checks that the API already returned.

**Implemented Solution:** The overview now decides in this order. A lesson still open in a topic: 'Rozdělaná lekce' with 'Pokračovat v lekci'. Otherwise the first topic with status 'new', looking at the target level after the learner's estimate, then higher levels, then gaps in lower levels, with the existing explanation lines, plus 'Ověřit gramatiku (N)' when checks are due. If every topic is studied: a due-check card, or a calm 'all studied' note.

**Verification:** Real data (de): tree has active_lesson_unit=de-a1-sein, due=2; the page shows 'Rozdělaná lekce · Já jsem, ty jsi: sloveso sein · Pokračovat v lekci'. Stubbed variants: no open lesson recommends 'Přítomný čas pravidelných sloves' (the first new A1 topic, not the studied sein); all studied with due=2 shows 'Ověřit gramatiku (2)'; all studied with due=0 shows the all-studied note. No console errors. typecheck, next build, ruff pass.

## Global Cycle 77/120 | Page: [/lesson] (Page Cycle 2/15)

**Summary:** preview the next vocabulary lesson and survive partial load failures

**Observed Problem:** The vocabulary card on /lesson only said how many words were introduced and linked to the runner. It did not show what the next lesson holds (scene, new and review words), which the dashboard already had, or that a lesson was open, so the button always read 'Otevřít lekce slovní zásoby'. All four data sources loaded with Promise.all, so if the placement estimate or progress request failed, the whole overview (all grammar lists) went blank.

**Implemented Solution:** The card shows the next lesson preview from /learning/next-lesson, for example 'Další scénka: „Oběd“ · 4 nová slova · 2 slova znovu k procvičení', or 'all words known' when empty. When a session is open, the button reads 'Pokračovat v lekci'. Loading uses Promise.allSettled: only a failed grammar tree is fatal. A failed estimate, progress or preview just leaves that detail out, and the 'Představeno slov' counter no longer sticks on 'Načítám…'.

**Verification:** Playwright real data: the card shows 'Další scénka: „Oběd“ | 4 nová slova · 2 slova znovu k procvičení'. With progress and diagnostic requests forced to 500, the page still renders the preview and all 6 level sections, and the counter is hidden rather than stuck loading. No console errors besides the injected 500s. typecheck, next build, ruff pass.

## Global Cycle 78/120 | Page: [/lesson] (Page Cycle 3/15)

**Summary:** show coverage per level and mark open and due topics

**Observed Problem:** The 'Dostupné gramatické lekce' list gave each level only an availability count ('15 lekcí'). Each topic card showed its status word but not that a lesson in it was still open or that its check was due. A learner could not see how far into A1 they were or which topic cards needed attention without opening /grammar.

**Implemented Solution:** Each level header shows 'prostudováno X z Y' and, when any are verified, '· ověřeno Z', with a two-tone bar (verified emerald, studied sky). Topic cards get a 'rozdělaná' badge for the open lesson and 'k ověření' when due, both from the grammar tree the page already loads.

**Verification:** Playwright on real data: headers read 'A1 prostudováno 2 z 15', 'A2 prostudováno 0 z 11', 'B1 … 0 z 6', 'B2 … 0 z 5'; the sein card shows 'rozdělaná | k ověření | Prostudováno'. Screenshot inspected. No console errors. typecheck, next build, ruff pass.

## Global Cycle 79/120 | Page: [/lesson] (Page Cycle 4/15)

**Summary:** say where the level estimate comes from and link to the level test

**Observed Problem:** The overview based its recommendation on a placement estimate, vocabulary badge or progress level, but it never showed which one or what level, except inside the explanation under the recommended topic (and not at all while a lesson was open). A learner without an estimate had no route to the CEFR level test from this page, and an open test was not offered for resuming.

**Implemented Solution:** A one-line strip under the header names the basis: 'Orientační úroveň A2 z testu 3. 11. 2026.', 'Orientační úroveň X podle postupu.', 'Bez testu úrovně; zkouška slovní zásoby X.' or 'Zatím bez odhadu úrovně, doporučení začíná od A1.'. When the test is available it adds 'Zjistit úroveň testem', 'Udělat test znovu' or 'Pokračovat v testu úrovně' linking to /placement/cefr. The wording stays 'orientační' (indicative), as the product requires for CEFR labels.

**Verification:** Playwright 390px, real data: 'Zatím bez odhadu úrovně, doporučení začíná od A1. Zjistit úroveň testem' -> /placement/cefr. With a stubbed A2 estimate dated 3 Nov: 'Orientační úroveň A2 z testu 3. 11. 2026. Udělat test znovu'. No console errors. typecheck, next build, ruff pass.

## Global Cycle 80/120 | Page: [/lesson] (Page Cycle 5/15)

**Summary:** say each topic's goal once and show its size and check record

**Observed Problem:** On the topic cards the summary and the 'Cíl:' line repeated the same sentence. In the German course that is 37 of 37 topics, so every card said it twice. The cards did not show how long a topic is (number of exercises) or how the learner did in its checks, although the tree returns both.

**Implemented Solution:** The objective line is shown only when it differs from the summary. Each card ends with 'N cvičení' and, once checked, 'v ověření X z Y správně' from checked_correct and checked_errors.

**Verification:** API: 37 German topics, 37 with identical summary and objective. Playwright: the sein card now reads '… Řekneš, kdo jsi a odkud jsi … | 8 cvičení' without the duplicate Cíl line. No console errors. typecheck, next build, ruff pass.

## Global Cycle 81/120 | Page: [/lesson] (Page Cycle 6/15)

**Summary:** open the recommended step with Enter and the vocabulary lesson with V

**Observed Problem:** The lesson overview had no keyboard shortcuts, while the dashboard and practice pages open their main step with Enter. On desktop, reaching the recommended topic meant tabbing through the header, the language picker and the estimate link first.

**Implemented Solution:** The page installs the shared hotkey listener. The single primary action (resume the open lesson, open the recommended topic, or start the due grammar check) carries data-hotkey='enter' with an Enter key hint. V opens the vocabulary lesson, with a hint on its button. V is a page-local letter shortcut: the page has no text input, and it is ignored with modifiers or while typing.

**Verification:** Playwright: Enter on the page body navigates to /grammar/de-a1-sein (the open lesson); V navigates to /lesson/vocabulary. Key hints render on desktop only (KeyHint is lg-only). No console errors. typecheck, next build, ruff pass.

## Global Cycle 82/120 | Page: [/lesson] (Page Cycle 7/15)

**Summary:** let the learner hear and read the recommended topic's first example

**Observed Problem:** The recommended or open topic was introduced only by a one-line Czech summary. The product's rule is context before drill, but the overview gave no feel for the target language before the click. The grammar example audio added earlier was not used here.

**Implemented Solution:** The recommended and open-lesson cards load that topic's first example (one extra request, optional: the card works without it) and show it in the target language with its Czech translation and a play button for the sentence audio. P plays it on desktop, with a P key hint.

**Verification:** Playwright on real data: the open-lesson card shows 'Ich bin Anna und ich bin acht. | Jsem Anna a je mi osm.'; pressing P requests grammar/units/de-a1-sein/audio?example=0 (TTS is unavailable in the container, so the request was checked, not playback). No console errors besides the expected 503. typecheck, next build, ruff pass.

## Global Cycle 83/120 | Page: [/lesson] (Page Cycle 8/15)

**Summary:** filter the lesson list to new, studied or due topics

**Observed Problem:** The full topic list showed all 37 German topics across six level boxes. Finding the 2 studied ones or the 2 due for a check meant scanning every card. C1 and C2 also showed empty boxes regardless of what the learner was looking for.

**Implemented Solution:** A chip row above the list (Vše 37 / Nové 35 / Prostudované 2 / K ověření 2) filters the topic cards. Chips with no match are disabled. With a filter on, levels without matches are hidden, while each level header keeps its full coverage numbers. The choice is kept in the URL (?show=), so Back from a topic returns to the same filtered list.

**Verification:** Playwright 390px: the chips read 'Vše 37, Nové 35, Prostudované 2, K ověření 2'; K ověření shows only the A1 box with sein and der/die/das and sets ?show=due; opening a topic and going Back keeps ?show=due and the same two cards; no horizontal overflow. No console errors. typecheck, next build, ruff pass.

## Global Cycle 84/120 | Page: [/lesson] (Page Cycle 9/15)

**Summary:** fold levels away from the learner's focus

**Observed Problem:** With 37 topic cards spread across six level boxes that were all open, the page was about 4000px tall on a phone, and the learner's own level was buried under levels they had not reached.

**Implemented Solution:** Each level is now a details/summary disclosure with its coverage bar in the summary. It is open for the focus level (the level of the recommended next topic, otherwise the one above the placement/badge estimate), for any level holding a due or open lesson, and for every level while a filter is active.

**Verification:** l84.js: default A1 open and A2-C2 closed; clicking A2 opens it; the Nové filter shows A1-B2 open; no console errors. Typecheck, build, ruff passed.

## Global Cycle 85/120 | Page: [/lesson] (Page Cycle 10/15)

**Summary:** point back to the explanation after failed checks

**Observed Problem:** When a grammar check went wrong, /lesson kept recommending only the next new topic. The tree already returned recent_errors per unit (check mistakes within the 21-day remediation window), but nothing on the page used it, so a learner who failed a topic had no route back to its ungraded explanation.

**Implemented Solution:** A 'Vrátit se k výkladu' panel lists up to three topics with recent check mistakes, worst first and lower level first on ties, excluding the topic already on the recommendation card. Each links to the ungraded lesson, which already replays the missed exercises as remediation. Topic cards get a matching 'N chyby' badge. No score is created: the panel only reads check evidence.

**Verification:** Made 4 wrong check answers in de (sein 2, articles 2) through the API. l85.js at 390px: panel lists articles only (sein is the open-lesson card), link /grammar/de-a1-articles, both cards show '2 chyby', no horizontal overflow, no console errors. Typecheck, build, ruff passed.

## Global Cycle 86/120 | Page: [/lesson] (Page Cycle 11/15)

**Summary:** retry a failed overview and never pass off a failed estimate as no estimate

**Observed Problem:** A grammar tree failure left a dead red notice with no way to retry except reloading. Loading was a single 'Načítám…' line, so the page jumped when the content arrived. When only the diagnostic or progress request failed, the estimate line said 'Zatím bez odhadu úrovně', which presents a failed request as a fact about the learner.

**Implemented Solution:** Tree failure now shows a RetryNotice that refetches all four requests and says the vocabulary lesson still works. A failed estimate or progress request is tracked as partial: the estimate line says it could not be loaded, with a 'Načíst odhad úrovně znovu' button. Loading shows skeleton cards in the shape of the recommendation and vocabulary panels.

**Verification:** l86.js with routed 500s: the alert shows the new text, and the vocabulary link is still present. Retry restores 6 level sections. The estimate line reads the failure text. The partial retry restores the real estimate and hides its button. l86b.js with a 3 s delay: 2 skeletons while loading, then 0. No console errors other than the forced 500s. Typecheck, build, ruff passed.

## Global Cycle 87/120 | Page: [/lesson] (Page Cycle 12/15)

**Summary:** show levels without topics as one line, and hide the list when a language has none

**Observed Problem:** C1 and C2 have no grammar topics, but each was rendered as its own box that opened onto 'Pro tuto úroveň zatím nejsou připravené lekce'. A language with no grammar at all showed six such boxes plus a filter row with zero counts above the actual notice.

**Implemented Solution:** Levels without topics are left out of the disclosure list and named on one line, 'C1, C2: zatím bez připravených lekcí.', shown only in the unfiltered view. With no topics at all, only the no-content notice is shown, without a filter or levels. This removes the dead empty branches and two unused copy keys.

**Verification:** l87.js: de shows level boxes A1-B2 and the line 'C1, C2: zatím bez připravených lekcí.'; the line is hidden under the Nové filter. With a routed tree that has no units: 0 level boxes, no filter radios (the 4 radios left are the language picker), and the notice is present. No console errors. Typecheck, build, ruff passed.

## Global Cycle 88/120 | Page: [/lesson] (Page Cycle 13/15)

**Summary:** keep topic titles readable on phones

**Observed Problem:** At 390px the status badges ('rozdělaná', '2 chyby', 'Prostudováno') sat in a non-shrinking column next to the topic title. 'Já jsem, ty jsi: sloveso sein' was squeezed to 68px and four lines, and other titles to about 145px. Every summary was printed in full, so the open A1 list of 15 cards ran about 2500px. The filter chips overflowed their row by 32px, which hid 'K ověření' behind a scroll.

**Implemented Solution:** The card header now wraps: the title takes a 160px-basis flexible column, and the badges wrap underneath when they do not fit. Summaries are clamped to two lines below the sm breakpoint and shown in full from sm up. Filter chips use px-2 on phones and px-3 from sm.

**Verification:** l88.js at 390px, before vs after: title widths changed from 68/260/147/145px to 298/260/260/298px. Sein title height went from 96 to 24px. Radiogroup scrollWidth went from 398 to 366 (equal to clientWidth). Full-page height went from 4056 to 4008px. ov.js /lesson: no overflowing elements. Typecheck, build, ruff passed.

## Global Cycle 89/120 | Page: [/lesson] (Page Cycle 14/15)

**Summary:** show the last overview at once when returning from a topic

**Observed Problem:** The page's own requests are already minimal (7 API calls in the prod build, all under 20 ms locally). The real cost was navigation: /lesson is the hub learners return to after every topic, and each Back discarded the overview and waited for all four requests before showing anything. With a slow tree, levels took 1353 ms to appear.

**Implemented Solution:** A module-level snapshot per profile and language holds the last complete overview: tree, estimate, progress and preview. Returning to the page renders it immediately and refreshes it in the background. Partial loads are not cached. A failed refresh drops the snapshot and shows the retry state, so stale data is never presented as current. Keys include the acting profile id, so profiles never share an entry.

**Verification:** l89.js with the grammar tree delayed 1200 ms. Opening a topic and pressing Back showed the levels in 141 ms with no skeleton, versus 1353 ms on the stashed baseline. After the refresh, 4 level sections were present. No console errors. Typecheck, build, ruff passed.

## Global Cycle 90/120 | Page: [/lesson] (Page Cycle 15/15)

**Summary:** say when topics are an unreviewed draft, and re-run the page's regressions

**Observed Problem:** The grammar tree reports review_status ('unreviewed' for every de topic today), and /grammar shows it. /lesson recommended and listed the same drafted topics with no such signal, which presents generated rules as reviewed fact and breaks a product invariant. Folding the levels into disclosures (cycle 84) also broke two of this page's regression scripts, which still selected sections.

**Implemented Solution:** Under 'Dostupné gramatické lekce' the page now says when topics are an unreviewed draft. It uses a separate wording when only some topics are reviewed, and says nothing when all are reviewed or there is no content. The l78 and l83 regression scripts were updated to the details structure, and l83 now uses the Prostudované filter, because the check made in cycle 85 left nothing due.

**Verification:** l90.js: de shows the draft note; with a routed review_status 'reviewed' the note is gone. Regressions re-run at 390px all completed with no console errors: l76 (resume card and Enter), l78 (coverage and first card), l83 (filter, URL and Back), l84 (folding), l85 (revisit), l87 (empty levels), l88 (title widths and chips fit). Typecheck, build, ruff passed.

## Global Cycle 91/120 | Page: [/shadowing] (Page Cycle 1/15)

**Summary:** shadow whole dialogues from met scenes, with speaker and Czech meaning

**Observed Problem:** /shadowing only offered 20 random example sentences of lesson words, shown with the word's gloss but no meaning for the sentence itself, so a learner repeated sentences they might not understand. Shadowing works best on connected speech, and the met lesson scenes already have ordered dialogue lines with Czech translations and per-line TTS (roleplay API), but nothing on this page used them.

**Implemented Solution:** Shadowing now works on a generic line (text, audio, optional speaker, Czech meaning, lesson word). A source radio switches between 'Věty ze slov' and 'Rozhovor ze scény'. Scene mode lists the scenes the profile has met, with the child filter applied server-side by the roleplay API. It loads the selected dialogue in order, with speaker, line, Czech meaning and line audio. The scene option is disabled when no scene has been met yet, with a note explaining why. Recording state resets per source.

**Verification:** s91.js at 390px (de): word mode unchanged (1/20). Scene mode lists 5 met scenes with line counts. Ahoj, jak se jmenuješ? shows ANNA / 'Hallo! Ich heiße Anna. Wie heißt du?' / Czech line. Switching to Odkud jsi? shows BEN, 1/8. N advances to 2/8. Audio requests go to /roleplay/{id}/audio?line=0, then 1. No console errors other than TTS 503. Typecheck, build, ruff passed.

## Global Cycle 92/120 | Page: [/shadowing] (Page Cycle 2/15)

**Summary:** start word shadowing with the latest lesson's words

**Observed Problem:** Word sentences were a random sample of up to 20 from every word the profile was ever taught. A learner who just finished a lesson saw that lesson's words only by chance (in de, 20 of 41 taught words). Shadowing fresh words right after the lesson is when repetition helps most.

**Implemented Solution:** GET /dictation/sentences takes order=random|recent (default random, so existing callers are unchanged). recent orders by introduced_at descending, then frequency rank and id, using the same taught, child-filtered pool. The page defaults to 'Nejnovější slova z lekcí' with a 'Náhodně ze všech' alternative. The chosen order survives switching to a scene and back.

**Verification:** New test test_shadowing_recent_order_lists_latest_lesson_words_first: newest lesson first, rank within a lesson, untaught words excluded, random still returns the taught pool, and order=rank returns 422. test_dictation.py: 6 passed. s92.js: recent starts at Schule (the latest lesson), random starts elsewhere, requests carry order=recent and then random, and the order is kept after a scene round trip. No console errors. Typecheck, build, ruff passed.

## Global Cycle 93/120 | Page: [/shadowing] (Page Cycle 3/15)

**Summary:** keep the source and sentence in the URL

**Observed Problem:** The page held its position only in memory. A reload, a Back from another page, or a shared link restarted at sentence 1 of the default source, so a learner working through an 8-line dialogue lost their place whenever they left the page.

**Implemented Solution:** ?scene=<id> or ?order=random plus ?line=N (1-based) are read on mount and written with replaceState on every move. line is kept only for stable lists (recent words, scenes); a random sample changes on each load. An out-of-range or malformed line falls back to the first sentence. Switching language while on a scene returns to that language's words, because a scene belongs to one language.

**Verification:** s93.js: words N N gives 3/20 with line=3, and a reload stays at 3/20. Scene Moje rodina plus N N N gives 4/8 with scene=dd12…&line=4. /words then Back restores 4/8 and the select keeps the same scene. ?line=999 falls back to 1/20. No console errors. Typecheck, build, ruff passed.

## Global Cycle 94/120 | Page: [/shadowing] (Page Cycle 4/15)

**Summary:** show which lines are recorded and jump between them

**Observed Problem:** The only progress signal was 'N. pokus', which reset on every line, and Další wrapped silently from the last line back to the first. A learner shadowing a 7-line dialogue could not tell which lines they had already recorded, had no way to go straight to a line, and was never told they had finished.

**Implemented Solution:** Recordings are counted per line for this visit only (nothing is sent or scored), and the header shows 'nahráno X z N'. A numbered line strip under the card fills each line green once recorded, marks the current one, shows the line text on hover, and jumps on tap, which also updates the URL. When every line has been recorded, a note suggests the next step: another pass with the text hidden (H), or roleplay for a scene.

**Verification:** s94.js uses Chromium with a fake microphone on scene Ahoj, jak se jmenuješ?. After the first R R: '1 / 7 · nahráno 1 z 7', and dot 1 reads 'Věta 1, nahraná'. After recording all 7: 'nahráno 7 z 7' and the completion note. Tapping dot 3 goes to 3/7 with line=3. No console errors. Typecheck, build, ruff passed.

## Global Cycle 95/120 | Page: [/shadowing] (Page Cycle 5/15)

**Summary:** add a hands-free echo round: listen, repeat, compare

**Observed Problem:** One shadowing repetition took four separate actions: play the model (P), start recording (R), stop it (R), then compare (C). With a phone in one hand, or while reading the line aloud, that is the friction that makes learners skip the compare step, which is the point of shadowing.

**Implemented Solution:** An 'Kolo' button (key A) runs the whole loop. It plays the model to the end, records for a window sized to the model's voiced length (1.5× + 1 s, clamped to 2-15 s), then plays the model followed by the recording. The button label and an aria-live region name the current step. Pressing R stops the recording early and still compares. Moving to another line abandons the round through a run token, and a recorder error ends it. The recording counts in the per-line tally like a manual one.

**Verification:** s95.js uses a fake microphone and a stubbed 1.5 s WAV model. The steps were: Poslouchej at 48 ms, then Teď ty at 1624 ms (after the model), then Vzor a pak ty at 4955 ms (a 3.3 s window), then back to idle at 10055 ms. Header: nahráno 1 z 7. Pressing A then N during the listening step went to 2/7 with no stray recording (still 1 z 7) and the button idle. No console errors. Typecheck, build, ruff passed.

## Global Cycle 96/120 | Page: [/shadowing] (Page Cycle 6/15)

**Summary:** move, jump and stop from the keyboard

**Observed Problem:** Keyboard shadowing could only go forward (N). There was no key for the previous line, no way to reach line 5 without pressing N four times, and nothing to abort a running echo round or recording. The handler used its own input/select test instead of the shared isTypingTarget, and ignored defaultPrevented. The Předchozí button had no key hint.

**Implemented Solution:** → or N goes to the next line, ← or B to the previous one, and 1-9 jump to a line when it exists. Esc ends whatever is running: a recording (kept, as with R), an echo round (via its run token), and playback. The handler now uses isTypingTarget and respects defaultPrevented, so arrows inside the scene select still change the scene. Both nav buttons show their key on desktop, and the key legend lists the new keys.

**Verification:** s96.js (1280px, fake mic, stubbed audio): →→ gives 3/7, B gives 2/7, ← gives 1/7, 5 gives 5/7, and 9 is ignored on a 7-line scene. A during the speak step followed by Esc leaves the echo button idle and the record button back to Nahrát. ArrowDown in the focused select switches to Moje rodina (1/8). No console errors. Typecheck, build, ruff passed.

## Global Cycle 97/120 | Page: [/shadowing] (Page Cycle 7/15)

**Summary:** offer true shadowing: speak along with the model

**Observed Problem:** The page is called Stínování, but every mode was echo practice: listen first, then repeat. Shadowing proper, speaking over the model as it plays, trains rhythm and linking in a way delayed repetition does not, and nothing on the page allowed it.

**Implemented Solution:** The echo round now has two modes. 'Po vzoru' is the existing listen, repeat and compare flow. 'Současně se vzorem' starts recording first, so the first syllable is not cut, plays the model under it, stops 700 ms after the model ends, then plays the model followed by the recording. The mode is remembered per device in localStorage (read after mount, so SSR is unaffected; storage failures fall back to the default). A note says the mode needs headphones, otherwise the microphone records the model too.

**Verification:** s97.js (fake mic, stubbed 1.5 s model): the headphones note is shown. Steps: 'Mluv současně se vzorem…' at 19 ms, compare at 2326 ms (1.5 s model + 0.7 s tail), idle at 6474 ms. The wave caption reads 'Vzor 1.5 s · ty 1.6 s'. After a reload the mode is still selected. No console errors. Typecheck, build, ruff passed.
