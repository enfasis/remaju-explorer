# remaju^mm

A Python collector for Peru's REMAJU judicial auction listings and a static web explorer for browsing collected data. The collector currently supports non-publishable sample runs; the site can display fixture data.

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

The **Refresh data** workflow (`.github/workflows/refresh.yml`, manual) collects from REMAJU, geocodes and converts prices, and publishes a release to the R2 bucket served at <https://data.remaju.mejora.me/>. It restores the previous state and the geocoding/exchange caches from the private R2 bucket first, uploads `data/manifest.json` last, and keeps raw run traces in the private bucket. `max_pages` (default 5) limits the walk and publishes a partial release; leave it empty for a full run.

The live site reads `data/manifest.json` from R2 when the `DATA_URL` repository variable is set; otherwise, and always in local development, it uses the bundled sample in `src/web/public/demo/`. The workflow needs the variables `R2_ENDPOINT`, `R2_DATA_BUCKET`, `R2_PRIVATE_BUCKET`, `R2_ACCESS_KEY_ID` and the `production` secrets `R2_SECRET_ACCESS_KEY` and `GEOCODING_API_KEY`.
