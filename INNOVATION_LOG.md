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
| 1 | Adaptive CEFR placement test A1-B2+ | see below |

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
