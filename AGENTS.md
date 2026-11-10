# Project instructions

- `src/collector/` contains the Python collector and its offline tests and fixtures.
- `src/web/` contains the static auction explorer. Deployment: see README.
- Use focused functions, type hints where appropriate, and no code comments.
- Run `make test` for the collector and web tests. See `make help` for commands.
- Develop against fixtures; do not contact REMAJU, paid services, or deploy without explicit approval.
- Preserve datasets, history, sessions, and caches. Failed or partial collections must not replace published data.
- To debug a refresh run, use `make trace` (latest completed run) or `make trace GH_RUN=<actions run id>`. It downloads the run's public `trace-<run id>` artifact (`run.json`, `events.jsonl`, redacted responses; kept 30 days) with `gh` to `var/private/runs/<run id>/`. No R2 credentials are needed.
