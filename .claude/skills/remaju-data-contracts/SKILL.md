---
name: remaju-data-contracts
description: Design or implement RemaJu document schemas, current availability, append-only history, JSON/CSV exports and agent queries.
---

# Data-contract workflow

1. Read `AGENTS.md` and `docs/implementation-plan.md`, especially sections 4–7, 11 and 13.
2. Keep current eligibility, observed membership, latest-known records and chronological changes distinct. An absent listing is not proof it was sold.
3. Never derive removals from failed, partial, suspicious or differently scoped observations. Never treat the prototype's accumulated JSON as a current snapshot.
4. Use Decimal money serialized as decimal strings, explicit currencies, source raw values, Lima civil time and UTC collection time. Preserve IDs as strings and multi-property semantics.
5. Generate JSON Schema and checked TS types from a shared contract. Keep source facts and optional enrichment separate.
6. Use immutable bounded history shards and run membership, deterministic event IDs and source revision hashes. Preserve A→B→A chronology and same-run retry idempotency.
7. Export a small current summary, lazy full documents, latest-known archive and replayable history with checksums/schema manifests. Browsing must not download history.
8. Validate atomic writes, restore/reconstruction, corrupt prior input rejection, path safety, CSV formula injection, Unicode and multi-property price aggregation.
9. Preserve all legacy data/caches. Import legacy output only into an explicitly uncertain non-current scope with an audit report.

Do not add a database or silently change published schema semantics. Document migration and consumers whenever a contract changes.
