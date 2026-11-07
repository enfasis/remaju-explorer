# Implementation status

This is an incremental implementation, not a completed replacement. The original scraper and Streamlit viewer remain available and unchanged. The user requested their retirement, but the replacement cannot yet provide a verified complete crawl; removing the only existing source implementation before parity would leave no working collector.

## Implemented

- Offline CLI: `python -m remaju validate`, `query`, `show`, `import-legacy`, and `export-csv`. These commands operate on explicitly supplied local files. Validation only checks the input structure and unique numeric IDs; it does not prove that a crawl was complete.
- Legacy imports are marked `legacy-import`, have no assumed observation time, and cannot overwrite the source or an existing output file.
- File helpers, deterministic revision/event hashing, observation reconciliation, CSV escaping and gzip event serialization. Reconciliation is a low-level function and does not perform crawl completeness checks or publish history.
- A hardened basic JSF partial-response parser and offline unit tests.
- A Debian-based collector test image, a container test target, and a safe non-destructive `make clean`.
- A React/Vite static explorer with Generouted routing, nuqs URL filters, a Nyxhora-derived button, date ordering, lazy details, filtered JSON export, and public data-access instructions.
- Containerized frontend build and tests; npm dependencies are locked. Compose and Make provide build/test/dev entry points.
- A sample-only collection adapter and offline fixture replay. A sample is always non-publishable; the adapter has not been tested against the live source.
- Local publication primitives with basic validation, local file locking, versioned releases and atomic manifest replacement. This is an experimental local fixture pipeline, not a verified production publisher.
- Offline CI workflow. GitHub Pages can deploy the static frontend with explicitly fictional examples; the refresh workflow remains disabled.
- Local data was copied to a private temporary backup; no changes to source data were intended.

## Not yet implemented

- No full source collector, tested all-phase selection, detailed JSF navigation, complete action redaction, browser session handling, or end-to-end verified collection. Sample traces can contain sensitive source content and must remain private.
- No independently verified completeness gate, durable chunked append-only history store, portable production restore/rollback, generated schemas, or cloud integration. The local publisher's flags/count checks are not proof of source completeness. Do not publish real data or infer absences from unverified input.
- The frontend is an initial implementation: structured detail rendering, complete filter validation, downloadable CSV, and browser/accessibility tests are still required. It has no current data until an accepted manifest is supplied. Local development and the GitHub Pages demo use fictional examples, clearly labeled as such.
- GitHub Pages deployment requires repository configuration and verification. No scheduled run is enabled; refresh remains intentionally gated.
- The existing prototype's parser issues and legacy dependency tree remain; do not interpret an offline input validation as proof of current availability.

See `docs/implementation-plan.md` for the remaining requirements and release gates. In particular, no live REMAJU requests or deployments have been authorized by the plan's offline implementation work.
