# remaju^mm

A Python collector for Peru's REMAJU judicial auction listings and a static web explorer for browsing collected data. The collector currently supports non-publishable sample runs; the site can display fixture data.

Requires Docker Compose and Make:

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
