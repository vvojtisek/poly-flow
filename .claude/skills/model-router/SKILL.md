---
name: model-router
description: Route substantial PolyFlow software-engineering work to the least costly capable Claude subagent in .claude/agents and escalate with an evidence handoff. Use before delegating or when a task outgrows its first route.
---

# Model router (Claude Code)

Claude Code counterpart of `.codex/skills/adaptive-model-router/SKILL.md`. Both use the same six roles and the same rules in `AGENTS.md`; only the models differ. Choose the lowest-cost capable subagent for each task. The main session is the coordinator. Delegate to a subagent in `.claude/agents/` only when it materially helps; keep one implementation owner for a coherent change.

## Routes

| Role | Subagent | Model | Use for |
|---|---|---|---|
| Coordinator / quick worker | main session or `quick-worker` | session model / Haiku | Repository inspection, documentation, small edits, formatting, clear localized fixes, mechanical work with a known pattern. The coordinator does simple work directly. |
| Implementer | `implementer` | Sonnet | Default specialist: well-defined features, moderate bug fixes, scoped API or UI work, normal tests, migrations with an established path. |
| Feature engineer | `feature-engineer` | Sonnet | Connected features across API, persistence, ARQ jobs, and UI; contract changes; real architectural ambiguity. Map affected modules and contracts first. |
| Deep debugger | `deep-debugger` | Opus | Root-cause analysis: intermittent failures, concurrency, duplicate/retried jobs, async races, confusing migrations, runtime/deployment mismatch. |
| Hard problem solver | `hard-problem-solver` | Opus | Only after a serious lower-cost investigation failed, or when evidence shows prior assumptions must be reconsidered. Pass the handoff; do not restart from zero. |
| Migration architect | `migration-architect` | Opus | Inherently high-risk schema/data migrations, framework or persistence transitions, cross-service architecture or deployment changes needing staged rollout and rollback. |

The order indicates increasing capability, not a required ladder: start at the capability the task justifies.

## Escalation

A single failed command or test, incomplete exploration, or a wrong first implementation is not by itself evidence to escalate. Determine whether the cause is a coding mistake, missing context, a bad assumption, a task larger than classified, or insufficient reasoning. Retry a materially identical approach at most twice.

Before escalating, hand over:

- the objective and current scope;
- relevant files, code paths, and constraints;
- concrete evidence and known-good facts;
- each materially different hypothesis and attempt, with its result;
- checks run and their outcome;
- the unresolved question.

The receiving subagent reads the handoff, does not repeat completed work without reason, and continues from the highest-value open question. The coordinator validates the result and reports only checks that actually ran.

## PolyFlow-specific classification

- A page, translation string, or small API endpoint with existing patterns: `implementer`.
- A lesson flow needing coordinated progress rules, schema/API, background processing, and UI: `feature-engineer`.
- Unexpected decay behavior, duplicate nightly stories, race conditions, or environment-only failures: `deep-debugger`.
- Schema changes that preserve learner progress are `implementer` work when the migration pattern is clear; use `migration-architect` when compatibility, data conversion, rollout, or rollback is high-risk.
- Child content filtering, audio retention, and provider/data egress are architectural and security constraints. Escalate unclear policy to the user instead of inferring consent.
- Vocabulary import or generation changes must keep provenance, validation, and review status. Do not label unchecked data as verified.

## Delegation guardrails

Parallelize only independent investigations or deliverables. Never give multiple subagents overlapping edits. Keep a shallow coordinator → specialist structure. Do not add a reviewer subagent for work that can be verified deterministically. Avoid open-ended retries and unnecessary escalation.

When a subagent did the work, include `Routing: <subagent> (<model>)` in the final task summary. Omit it when the coordinator handled the task directly.
