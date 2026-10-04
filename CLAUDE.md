# PolyFlow: Claude Code instructions

@AGENTS.md

## Claude Code specifics

- `AGENTS.md` above is the shared source of rules for Claude Code and Codex. Change shared rules there, not here.
- Each area with its own `AGENTS.md` (`backend/`, `backend/data/`, `docker/`, `frontend/`) has a `CLAUDE.md` that imports it; read it before editing in that area.
- For substantial work, route with `.claude/skills/model-router/SKILL.md` and the subagents in `.claude/agents/`. Do simple work directly instead of delegating.
