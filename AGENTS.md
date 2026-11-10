# Project instructions

- `src/collector/` contains the Python collector and its offline tests and fixtures.
- `src/web/` contains the static auction explorer. Deployment: see README.
- Use focused functions, type hints where appropriate, and no code comments.
- Run `make test` for the collector and web tests. See `make help` for commands.
- Develop against fixtures; do not contact REMAJU, paid services, or deploy without explicit approval.
- Preserve datasets, history, sessions, and caches. Failed or partial collections must not replace published data.
- To debug a refresh run, use `make trace` (latest run) or `make trace RUN_ID=<id>`. It downloads `run.json`, `events.jsonl`, and response files from the private R2 bucket to `var/private/runs/<id>/`, using a read-only key from Infisical (`.infisical.json`). Do not ask for or use the GitHub Actions R2 secret. Never print secret values.
