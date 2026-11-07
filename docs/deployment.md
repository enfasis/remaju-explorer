# Deployment and data

## GitHub Pages demo

The `Deploy demo to GitHub Pages` workflow builds the static frontend on pushes to `main` and on manual dispatch. It runs frontend tests before deploying. It does not run the scraper, access REMAJU, or publish local data. The build sets `VITE_DEMO=true` and displays the fictional files in `web/public/demo/`. They are not a current dataset.

Repository owner setup:

1. Push `main` to GitHub and open **Settings → Pages**.
2. Under **Build and deployment**, select **GitHub Actions** as the source. The `github-pages` environment must permit deployment from `main`.
3. Run the deploy workflow from **Actions** if the initial push ran before Pages was configured. Check the deployment URL in the workflow. For this repository it is normally `https://enfasis.github.io/remaju-explorer/`.
4. Verify the homepage, filters, sample details, direct links, `llms.txt`, `data-access.md`, and `demo/manifest.json`. GitHub Pages serves the SPA fallback with HTTP 404 on direct application routes; the browser can render the route but some crawlers and clients may treat it as missing. Missing data files also retain HTTP 404.

The Pages build uses the repository-specific base path `/remaju-explorer/`. Change `VITE_BASE_PATH` in the deploy workflow if the repository name or hosting path changes. GitHub Pages availability and repository visibility depend on your GitHub plan and settings.

## Future real data

Do not upload `data/auctions.json`, cookies, browser sessions, caches, raw traces, `.env`, or unreviewed personal/legal information. The legacy file is an accumulated, untimestamped output and cannot establish current availability. A real release requires an approved live-source feasibility test, a complete validated observation, privacy/reuse review, a durable history strategy, and a tested release/promotion and rollback process. See `implementation-status.md` and `implementation-plan.md`. The existing sample collector and publisher do not establish completeness.

## Cloudflare later

No Cloudflare account access or credentials are needed for GitHub Pages. If you later want Cloudflare hosting or durable storage, decide whether the site and a small verified snapshot should be bundled on Cloudflare Pages, or whether independent data/history needs R2. Pages alone does not establish durable append-only history. Check current provider limits and pricing before choosing.

To prepare a Cloudflare deployment, provide the account/project name, preferred public hostname (or permission to use a `pages.dev` hostname), whether the repository should be connected to Cloudflare or deployed through GitHub Actions, and the desired retention/storage policy. For R2, also decide the bucket name, region/jurisdiction, public access domain and acceptable budget. Configure required scoped credentials as GitHub Actions secrets yourself; never send tokens in chat or commit them. Cloudflare's current documentation specifies the permissions required for the chosen method. An approved verified release and tested deployment pipeline are still prerequisites; this repository does not yet implement cloud publication.

## Search discoverability

The static HTML includes a Spanish title, description and Open Graph metadata using relevant terms such as “REMAJU”, “remates judiciales” and “Perú”. The demo is explicitly described as fictional. Google Trends comparisons for those specific terms were not available to verify during implementation, so these are descriptive candidates, not a claim about ranked search volume. To compare them, use [Google Trends](https://trends.google.com/trends/explore?geo=PE&q=REMAJU,remates%20judiciales,remates%20judiciales%20Peru) with Peru and the desired date range; Trends reports relative interest, not exact volume. After launch, verify the site in Google Search Console to inspect actual search queries and indexing. GitHub Pages SPA routes return 404 on direct requests, so only the root is reliably indexable without a different hosting/fallback approach.
