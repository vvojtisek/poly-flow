---
name: adaptive-model-router
description: Route PolyFlow software-engineering work to the least costly capable configured agent and escalate using evidence.
---

# Adaptive model router

Choose the lowest-cost capable configured role for each software-engineering task. The coordinator is GPT-6 Luna High. Use specialized roles from `.codex/agents/` only when delegation materially helps; keep one implementation owner for a coherent change.

## Routes

### Coordinator or quick worker — GPT-6 Luna High

Use for repository inspection, documentation, small edits, formatting, clear localized fixes, and mechanical work with a known pattern. The coordinator should do simple work directly instead of delegating to an equivalent agent without benefit.

### Implementer — GPT-6.1 Sol Medium

Default specialist for ordinary, well-defined features, moderate bug fixes, scoped API or UI work, normal tests, and migrations whose path is established.

### Feature engineer — GPT-6.1 Sol High

Use for connected features across API, persistence, ARQ/background jobs, and UI; contract changes; or meaningful architectural ambiguity. First map affected modules and data/API contracts.

### Deep debugger — GPT-6.1 Sol XHigh

Use when difficult root-cause analysis is the main problem: intermittent failures, concurrency, duplicate/retried jobs, async state races, confusing migrations, or runtime/deployment mismatch. Gather evidence and test competing hypotheses before patching.

### Hard problem solver — GPT-6 Astra Low

Use only after a serious lower-cost investigation has failed, or when evidence shows prior assumptions must be reconsidered across code, configuration, infrastructure, tests, and runtime. Pass the investigation handoff; do not restart from zero by default.

### Migration architect — GPT-6 Astra Medium

Use directly for inherently high-risk or repo-wide schema/data migrations, framework or persistence transitions, cross-service architecture changes, or deployment changes that need compatibility, staged rollout, and rollback planning.

## Selection and escalation

Start at the capability justified by the task. The order above indicates increasing capability, not a required ladder. A single failed command or test, incomplete repository exploration, or an incorrect first implementation is not evidence by itself to escalate. Determine whether the cause is a coding mistake, missing context, a bad assumption, a task larger than classified, or insufficient reasoning. Retry a materially identical approach at most twice.

Before escalation, provide:

- the objective and current scope;
- relevant files, code paths, and constraints;
- concrete evidence and known-good facts;
- each materially different hypothesis and attempt, with its result;
- checks run and their outcome;
- the unresolved question.

The receiving role must read this handoff, avoid repeating completed work without reason, and continue from the highest-value unresolved question. The coordinator remains responsible for validating the result and accurately reporting checks.

## PolyFlow-specific classification

- Changes only to a page, translation string, or small API endpoint with existing patterns: implementer.
- A lesson flow requiring coordinated progress rules, schema/API, background processing, and UI: feature engineer.
- Unexpected decay behavior, duplicate nightly stories, race conditions, or environment-only failure: deep debugger.
- Schema changes that preserve existing learner progress are implementer work when the migration pattern is clear; use migration architect when compatibility, data conversion, rollout, or rollback is high-risk.
- Child safety, audio retention, and provider/data egress are architectural/security constraints. Escalate unclear policy instead of inferring consent.
- Vocabulary import or generation changes must retain provenance, validation, and review status. Do not solve quality gaps by labeling unchecked data as verified.

## Delegation guardrails

Parallelize only independent investigations or deliverables. Do not assign multiple agents overlapping edits. Prefer a shallow coordinator → specialist structure. Do not create a second reviewer agent to check work that can be verified deterministically. Avoid open-ended retries and unnecessary escalation.

When a specialized role is delegated, include `Routing: <role> — <model> <effort>` in the final task summary. Omit routing details when the coordinator handles the task directly.

