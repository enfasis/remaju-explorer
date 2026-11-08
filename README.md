# remaju^mm

A Python collector for Peru's REMAJU judicial auction listings and a static web explorer for browsing collected data. Local development uses fixture data; production reads the daily R2 dataset.

Requires Docker Compose and Make:

The web app uses Node.js 26 LTS in Docker and GitHub Actions. Local npm commands also require Node.js 26.

```sh
make help       # list commands
make build      # build collector and web images
make test       # run offline tests and build the web app
make run        # serve the explorer at http://localhost:5173
make web-build  # build the static explorer
make sample     # contact REMAJU for a non-publishable sample
```

`make download` is an alias for `make sample`. Collection does not publish data. Existing data and caches are preserved by `make clean`.

## Deployment

Pushes to `main` build the explorer and deploy it to Cloudflare Pages at <https://remaju.mejora.me> (`.github/workflows/deploy.yml`). The Pages project, domain, DNS record and the deploy token are managed with Terraform in [enfasis/enfatizados](https://github.com/enfasis/enfatizados) (`remaju.tf`). GitHub Actions uses the repository variables `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_PAGES_PROJECT` and the `production` environment secret `CLOUDFLARE_API_TOKEN`.

## Data refresh

The **Refresh data** workflow (`.github/workflows/refresh.yml`) runs daily at 03:00 Peru time (08:00 UTC) and can also be started manually. It checks every listing page from REMAJU with 12 auctions per page, geocodes and converts prices, and updates the four flat files below at <https://data.remaju.mejora.me/>. Each REMAJU GET and POST waits 0.5 seconds plus a random 0–0.5 seconds, and requests are sequential. It restores the previous state and the collector/geocoding/exchange caches first, uploads `manifest.json` last, and keeps raw run traces in the private bucket. For manual experiments, `max_pages` limits the walk; its default is empty (all pages). Capped and early-stop runs never replace the published dataset. Scheduled runs never use a page limit. GitHub may delay scheduled jobs.

The live site reads `manifest.json` from R2 when the `DATA_URL` repository variable is set; otherwise, and always in local development, it uses the bundled sample in `src/web/public/demo/`. The workflow needs the variables `R2_ENDPOINT`, `R2_DATA_BUCKET`, `R2_PRIVATE_BUCKET`, `R2_ACCESS_KEY_ID` and the `production` secrets `R2_SECRET_ACCESS_KEY` and `GEOCODING_API_KEY`.

### Published files

- `manifest.json`: dataset version, observation time, counts, file paths and SHA-256 checksums.
- `ids.txt`: one auction number per line, in the latest complete listing order, restored to memory for comparisons.
- `available.json`: full auction records (listing fields, detail tabs, properties, schedule and tracking) whose phase-3 deadline has not passed in Lima time. Missing/invalid deadlines and cancelled/suspended auctions are excluded. The site derives its filters and cards from these full records and opens their embedded details without requesting per-auction files.
- `history.json`: merged latest content keyed by auction ID, with first/last observation, last change, detail fetch timestamp and whether the auction was present in the latest complete listing. Missing auctions are retained. This is the Archivo histórico download, not an index of releases.

No releases, per-auction objects, events files, archive indexes or CSV exports are generated. JSON is not presented as an Excel-compatible export. Files are mutable; the browser checks their hashes and dataset versions, then refreshes the manifest and retries if it sees an upload in progress.

The next successful full refresh can read a legacy `data/manifest.json` and its checksum-verified state and merge it into the flat history. Legacy R2 objects are not deleted automatically. The browser temporarily supports the old layout until the first flat publication exists.

### Coordinates

Google requests are restricted to `country:PE`. New results, cached coordinates, published history and map points are validated against the same Natural Earth Peru polygon in `src/shared/peru.json`. Foreign/ocean coordinates are cleared, not replaced with invented city centers; the auction remains available without a map pin. A point within Peru is not proof of an exact property location.

### Incremental collection

`--cache-dir` stores `auctions.json` (details with their original fetch timestamps) and `ids.txt` (one auction number per line in listing order) in the private R2 cache. `--baseline-dir` restores the baseline from the published `history.json` and `ids.txt`, verified against the manifest checksums. A first complete run builds the baseline; failed, capped and early-stop runs do not replace it. New auctions, changed summaries, reordered historical auctions and expired details are fetched again. Unchanged, in-order details are reused for up to 168 hours; set `refresh_all_details=true` in the workflow or `--cache-max-age-hours 0` locally to force a fresh scan. Summary checks remain daily, while changes invisible in summaries may take up to seven days to appear. `detail_checked_at` identifies when each auction's details were fetched; `collection` in the manifest reports fetched/reused counts.

`--stop-window 4` (workflow input `stop_window=4`) enables the experimental consecutive-history detector. It looks for four unchanged, cache-valid auction IDs in consecutive positions in the saved order, even across listing pages. Numeric gaps are allowed: `a7,a5,a4,a3` matches if that is the saved order. New, changed, expired or reordered items break the streak. This is a contiguous sequence match, not a longest common subsequence: interleaved IDs cannot satisfy it. A stop is recorded as `known-consecutive-window` and remains non-publishable, even with `--allow-partial`.

The assumption that every modified auction moves to the top is not verified. A matching window cannot prove there are no changes or removals further down the listing. Daily production therefore checks all summaries but avoids unchanged detail requests; experimental early stopping only saves a private run for inspection.
