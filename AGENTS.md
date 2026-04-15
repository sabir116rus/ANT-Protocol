# Agent Rules (Project Constitution)

`GEMINI.md` is the constitution of this project. Treat it as the source of truth for:
- North Star and scope boundaries
- Architectural invariants (what must not change)
- Behavioral rules (DO/DO NOT)
- Integration assumptions (Supabase/n8n/Telegram/FastAPI)

Rules for the agent working in this repo:
- Read `GEMINI.md` before making architectural decisions or changing cross-cutting behavior.
- Prefer changes that preserve the invariants defined in `GEMINI.md`.
- Do not delete or substantially rewrite `GEMINI.md` unless the user explicitly requests it.
- Do not commit secrets; never add `.env` to git.

