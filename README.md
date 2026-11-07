# RemaJu Explorer

A fast, independent way to explore judicial auctions published on Peru's REMAJU government website.

## Goal

Collect auction listings periodically, parse them into structured data, and publish a fast static website for searching, filtering, comparing, and opening the original notices. Visitors should browse a cached snapshot without waiting for the government website or a live scraper.

## Current status

- Python 3.14+ scraper in `download.py`, managed with `uv`.
- The legacy scraper saves auction data to `data/auctions.json`; this accumulated file is not a verified current snapshot.
- Existing interactive viewer: Streamlit in `main.py`.
- Parsing, models, geocoding, exchange rates, and browser automation live in `src/remaju/`.
- Tests and HTML fixtures are in `tests/` and `test_data/`.
- Server working directory: `susu:/mnt/nvme/opencode/workspace/projects/remaju-explorer`.
- An initial static frontend displays fictional examples locally and in the GitHub Pages demo. It is not a current auction feed.
- GitHub Pages deployment is configured; scheduled collection and real-data publication remain disabled. See [deployment setup](docs/deployment.md).

The original implementation notes are preserved in [docs/scraper-notes.md](docs/scraper-notes.md). Some commands in those historical notes are outdated; use the commands below.

## Run the existing application

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
cd /mnt/nvme/opencode/workspace/projects/remaju-explorer
uv sync --locked
uv run playwright install chromium
uv run pytest
uv run streamlit run main.py --server.address 127.0.0.1
```

Linux may also need Playwright's system dependencies (`uv run playwright install-deps chromium`, requiring system package installation privileges).

To access the viewer from your computer:

```bash
ssh -L 8501:127.0.0.1:8501 susu
```

Open `http://localhost:8501` while Streamlit is running on the server.

Download a small sample:

```bash
uv run python download.py --pages 1 --no-geocoding --no-exchange
```

Download all pages:

```bash
uv run python download.py
```

The existing integrations use `GEMINI_API_KEY` and `geocoding_api_key` from the environment or local `.env`. External API usage may incur charges. Keep `.env` private and exclude it from published files.

## Proposed low-cost architecture

```text
REMAJU
  -> scheduled scraper on susu
  -> parse, normalize, deduplicate, validate
  -> public JSON snapshot + downloadable CSV + freshness metadata
  -> static frontend and snapshot deployed to Cloudflare Pages
  -> browser-side search, filters, sorting, and detail views
```

Start with a daily refresh on the existing server using cron or a systemd timer. This avoids GitHub-hosted execution quotas and reuses the machine already available. The server must be online for refreshes; visitors can still use the last successfully published snapshot when it is offline.

For a small dataset, package the generated JSON and CSV directly with the static site and deploy the build output. Generated data does not need to be committed to Git. Keep each asset within the hosting provider's file-size limits; split larger datasets if needed.

If the dataset grows or needs to update independently of the frontend, put the public snapshots in Cloudflare R2 and serve them through a cache-enabled custom domain. Configure CORS for the frontend origin. Keep full archives and raw downloaded pages separate from the public dataset.

### Publication requirements

1. Run only one refresh at a time, with a timeout and bounded retries.
2. Preserve existing geocoding caches and avoid repeated paid lookups.
3. Export stable auction identifiers, source links, normalized fields, and timestamps.
4. Validate the snapshot before publishing; never replace the last good snapshot with a failed or partial scrape.
5. Build into a separate output directory containing only public assets.
6. Publish a complete snapshot atomically; for R2, upload versioned data before updating its manifest.
7. Display the last successful refresh time and retain logs for failed refreshes.

## Hosting costs and tradeoffs

### Cloudflare Pages and R2

Cloudflare Pages is the proposed static host. Check its current build, asset-size, and file-count limits before deployment. Static hosting does not require an always-running application server.

R2 Standard currently includes 10 GB-month of storage, 1 million Class A operations, and 10 million Class B operations per month. Internet egress from R2 is free, but storage and operations above the free allowance are billed. Zero egress does not mean unlimited free usage. A custom domain and optional external APIs can add costs.

### GitHub Pages and Git history

GitHub Pages can work for a small project, subject to its usage limits and terms. Avoid treating it as an unlimited data distribution service. Git repository history and the published site's size are different limits; a claim that every repository inevitably hits a hard 1 GB history ceiling is misleading.

Prevent history growth by keeping generated snapshots outside Git and deploying build artifacts directly. Track source code, configuration, and small test fixtures. A separate data branch still retains history unless explicitly pruned; Git LFS has its own quotas and is not a free hosting substitute.

### Google Cloud

Yes, Google Cloud can charge for data transferred to internet users. Cloud Storage pricing depends on storage location, destination, operations, and applicable free allowances. Generic Compute Engine Premium/Standard network-tier rates and allowances should not be assumed to apply to Cloud Storage downloads. Estimate using the actual product's pricing page before choosing it.

## Can GitHub Actions run the scraper on cron?

Yes. A workflow can use `schedule` plus `workflow_dispatch` for manual runs. It is an alternative to the server scheduler, especially if the scraper works reliably in a fresh hosted environment.

- Scheduled workflows run from the default branch, with a minimum interval of five minutes.
- Schedules are best-effort: jobs can be delayed or dropped under load. Choose a minute away from the top of the hour.
- In public repositories, scheduled workflows are disabled after 60 days without repository activity. Monitor refresh timestamps and re-enable the workflow when necessary rather than relying on artificial keepalive commits.
- Standard GitHub-hosted runners are free for public repositories. Larger runners are billed separately.
- Private repositories have plan-dependent included minutes; GitHub Free typically includes 2,000 minutes monthly. Verify current billing and runner rates before enabling a frequent schedule.
- GitHub-hosted jobs have a six-hour execution limit. Browser setup and dependency installation contribute to runtime, and artifact/cache storage has separate allowances.
- At 10 minutes per daily run, budget roughly 300 execution minutes per 30-day month; hourly runs would require roughly 7,200, before other workflows and billing adjustments.

Keep credentials in Actions secrets, persist required caches explicitly, use concurrency control, and publish validated output directly to hosting or object storage. Do not commit a new dataset on every refresh.

## Implementation roadmap

- [x] Transfer the existing project, Git history, uncommitted work, configuration, and data to susu.
- [x] Document the current application and static-site direction.
- [ ] Verify a small end-to-end scrape in the server environment.
- [ ] Define the public dataset schema and implement JSON/CSV exports.
- [ ] Build a mobile-friendly static frontend with search, location/status/price filters, sorting, and source links.
- [ ] Add snapshot validation and last-successful-refresh metadata.
- [ ] Deploy frontend and initial snapshot to Cloudflare Pages.
- [ ] Add a daily scheduler, locking, logs, and failure reporting.
- [ ] Measure dataset size and traffic; introduce R2 if needed.

## References

- [Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/)
- [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- [GitHub scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [Google Cloud Storage pricing](https://cloud.google.com/storage/pricing)

Pricing and service limits should be checked again when deployment is configured.
