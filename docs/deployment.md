# Cloudflare deployment and data

## Intended architecture

Cloudflare Pages serves the static explorer. GitHub Actions will eventually collect on a schedule and publish validated, versioned JSON and CSV to R2 without adding datasets to Git history. The browser requires a manifest and JSON summaries as well as optional CSV downloads; CSV alone is not the current explorer contract. The collector and R2 publisher are **not production-ready**: the scheduled workflow remains disabled and no real data is uploaded. A sample of three pages is not a complete observation.

## Deploy the site

Terraform now defines the infrastructure in [`infra/terraform/`](../infra/terraform/README.md). Use its bootstrap, plan/approval and DNS-ordering instructions instead of manually creating duplicate resources. Defaults are Pages Direct Upload at `remaju.mejora.me`, with R2 disabled. Pages uses a **CNAME**, not an A record; `enfatizados` owns that DNS record. Infrastructure has not been applied merely by adding these files.

Terraform outputs `github_repository_variables`, `required_secret_names`, `dns_records`, `site_url` and `pages_url`. Copy output variables into GitHub Actions repository variables. Secrets are configured separately and never output. The account ID can now be a repository variable; the workflow still supports the legacy secret.

The deployment workflow supports either a GitHub Pages API-token secret or **GitHub OIDC → Infisical → scoped Cloudflare token**, selected by `DEPLOY_AUTH_METHOD`. Cloudflare's documented Direct Upload flow does not provide a native GitHub OIDC exchange. Infisical federation removes the long-lived secret from GitHub, not from Cloudflare. See the infrastructure guide for exact trust restrictions and setup. The `production` GitHub environment must restrict deployments to `main`.

The following dashboard steps remain an alternative to Terraform, not additional resources to create after applying it:

1. Create a Cloudflare Pages project using **Direct Upload**, not Git integration; set its production branch to `main`. Choose a project name and either its `pages.dev` hostname or a custom domain.
2. In Cloudflare create a scoped account API token with **Account → Cloudflare Pages → Edit**. Find the account ID in the dashboard.
3. In GitHub under **Settings → Secrets and variables → Actions**, add repository variables `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_PAGES_PROJECT`, and secret `CLOUDFLARE_API_TOKEN` (or use the documented Infisical OIDC mode). Create the `production` environment restricted to `main`. Do not put tokens in chat, Git, or browser environment variables.
4. Push to `main` or run **Deploy explorer to Cloudflare Pages** manually. It tests and builds the demo, then uses Wrangler Direct Upload. The job skips if the project variable is absent. Review the action output and deployment URL. This deploy does not start the scraper or upload real data.

The frontend in `src/web/` currently uses the local example manifest in its demo build. Once a verified R2 publication exists, the reader must be configured and tested for its public data origin, CORS, caching, and manifest path before changing the build. Do not silently replace an accepted publication with sample data.

## Prepare R2 for the future collector

1. Enable R2 in Cloudflare (Cloudflare may require billing enrollment), create a Standard bucket, and decide a name, location/jurisdiction, retention policy and acceptable monthly budget.
2. Create an R2 API token scoped to that bucket with **Object Read & Write**. Store the resulting access key ID and secret access key as GitHub Actions secrets `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY`. The R2 token is separate from the Pages API token. Add variables `R2_BUCKET`, `R2_ENDPOINT` (`https://<ACCOUNT_ID>.r2.cloudflarestorage.com`, or the jurisdiction-specific endpoint), and `R2_PUBLIC_BASE_URL` when a public domain is configured. These are proposed names for the future pipeline; the current workflow does not consume them.
3. Choose whether public access uses a custom domain or development-only `r2.dev`; configure restrictive CORS for the Pages origin. Keep private captures, session state, sensitive data and secrets out of the public bucket. Configure cache and content types for manifest, versioned files, CSV and JSON.
4. Before enabling a schedule, implement and test full-source collection, challenge detection, completeness validation, privacy review, durable prior-state restoration, immutable versioned uploads, single-writer locking, manifest-last promotion and rollback. Never publish a partial crawl, infer removals from one, or overwrite last-good data on errors. GitHub's scheduler is best-effort and may be delayed or disabled after repository inactivity.

Provide the project name, hostname, R2 bucket name/region, retention and budget decisions, and confirmation that the secrets were configured. Never send the secret values to an assistant. See [Pages Direct Upload](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/) and [R2 token setup](https://developers.cloudflare.com/r2/api/tokens/).

## Cost considerations

Cloudflare's [R2 pricing](https://developers.cloudflare.com/r2/pricing/) currently includes 10 GB-month Standard storage, 1 million Class A and 10 million Class B operations monthly, and no direct egress charge. Requests and storage beyond those allowances can incur charges, as can connected services; the Infrequent Access class has different pricing. Cloudflare Pages Free has [build, file count and asset size limits](https://developers.cloudflare.com/pages/platform/limits/). GitHub Actions has its own plan-dependent allowances. Check current terms and pricing and set budget alerts; the architecture is not guaranteed to remain free.
