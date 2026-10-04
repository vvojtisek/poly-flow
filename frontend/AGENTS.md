# Frontend instructions

Read the repository `AGENTS.md` before editing. This app is a Next.js App Router PWA; the frontend owns presentation, browser state, API-client orchestration, and Czech UI copy.

- Put visible Czech strings in `lib/i18n/cs.ts`; components should consume the localization table.
- Use `lib/api.ts` for backend requests and `hooks/` for reusable browser-side state. Do not duplicate domain rules or authorization in React.
- Use semantic controls, keyboard-accessible interactions, visible focus, responsive layouts, and explicit loading, empty, unavailable, and error states.
- Keep score scales and unknown values clear: backend normalized scores use 0–1 and user-facing percentages use 0–100; `null` means unmeasured.
- Treat all learner content as untrusted display data. Never expose another profile's data based only on hidden navigation or client-selected IDs.
- Before changing API calls, inspect the backend response model and handle the actual error and cancellation behavior.
- Run `npm run typecheck` and `npm run build` for frontend changes. Do not claim frontend component coverage when no frontend test runner is configured.


<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
