---
name: remaju-collector
description: Refactor or debug RemaJu source collection, JSF navigation, HTML/XML parsing, replay and interaction logging.
---

# Collector workflow

1. Read `AGENTS.md` and `docs/implementation-plan.md`, especially sections 2, 4, 7, 9, 13 and the current implementation phase.
2. Treat `download.py` and saved `test_data/` responses as protocol evidence, not clean architecture. Historic scraper notes may describe code that no longer exists.
3. Work offline from fixtures by default. Never contact REMAJU, create a live browser session or call paid APIs without explicit approval.
4. Keep transport, JSF state/navigation, pure parsing and orchestration separate. Use typed models, small functions and no code comments.
5. Preserve dynamic ViewState/action IDs and correct auction/page context. Never retry a stateful POST blindly or use the first detail button irrespective of auction ID.
6. Log each attempted action before execution and its outcome, correlated to run/action/auction. Redact tokens and session identifiers, including response bodies and URLs.
7. Unknown dates/status/prices stay unknown; parser failure is not an empty result or successful detail. Partial/challenged runs cannot publish.
8. Add exact offline assertions and failure/state-transition tests for each behavior changed. Report which tests actually ran and which live assumptions remain unverified.

The handoff describes a target, not existing modules or working commands. Check current files before invoking a planned command. Do not delete old implementations until migration parity and approval criteria are met.
