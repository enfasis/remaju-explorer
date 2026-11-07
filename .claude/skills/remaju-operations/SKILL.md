---
name: remaju-operations
description: Plan or implement RemaJu Docker/Make development, GitHub collection workflows, durable file storage and Cloudflare publication.
---

# Operations workflow

1. Read `AGENTS.md` and `docs/implementation-plan.md`, especially sections 7–9, 11, 13 and 14.
2. Keep local and CI execution behind the same containerized CLI/Make contracts. Use glibc Debian, locked uv/npm dependencies and optional browser profiles; do not rely on the host virtualenv.
3. No collection, paid API usage, cloud deployment, schedule activation or secret inspection without appropriate explicit approval. Offline CI must not contact REMAJU.
4. Preserve datasets, history, sessions and paid caches. `clean` removes only reproducible build outputs.
5. Always log actions; upload only sanitized bounded summaries/captures. Never put `.env`, browser state, raw traces or private data into images or public assets.
6. Use shared-volume OS locks locally and a shared production concurrency group in GitHub. Independent machines additionally need tested remote CAS or a strict single-publisher policy.
7. Restore authoritative prior state before collection. Actions caches/artifacts are not durable history. A missing/corrupt baseline must fail, not reset the archive.
8. Stage and validate immutable objects first, promote one consistent manifest/site last, and preserve last-good data through failures. Test retry and rollback.
9. Use Pages Direct Upload initially and explicitly choose Pages-bundled history or R2 persistence. Recheck official quotas/pricing before operational changes; do not promise unlimited free hosting.
10. Keep PR jobs unprivileged/offline. Enable a daily schedule only after approved real-source feasibility tests, and retain manual/local fallback.

Report implemented safeguards, actual test evidence, deployment status and unresolved source/provider assumptions separately.
