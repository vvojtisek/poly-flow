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
