# RemaJu infrastructure

This state owns the Pages project and custom-domain association, plus optional R2 storage/CORS/public-domain association. `enfatizados` owns the Pages DNS CNAME. Never manage the same DNS record in both states. No API tokens or GitHub secrets are created by Terraform.

## Bootstrap

Use Terraform 1.14.x and an Infisical project configured for RemaJu. Do not reuse the DNS-only token or expose the entire DNS project's secrets to CI. A local `.infisical.json` must identify your chosen project/environment before invoking the commands below; this repository does not assume an existing RemaJu Infisical project.

1. Create an HCP Terraform workspace `enfatizados/remaju-prod`, execution mode **Local**, with restricted state access. Do not use `dns-prod`. If choosing another workspace, update your local backend configuration.
2. Create an infrastructure API token scoped to the account with Pages Edit, and Workers R2 Storage Write only if enabling R2. Public R2 domain setup also needs access to the `mejora.me` zone; follow Cloudflare's current API permission requirements. Keep this credential separate from CI's Pages Edit token.
3. Store the infrastructure token as `TF_VAR_cloudflare_api_token` and the HCP token as `TF_TOKEN_app_terraform_io` in the chosen Infisical project. Never put either value in a tfvars file or output.
4. Copy `backend.hcl.example` to `backend.hcl` and `terraform.tfvars.example` to `terraform.tfvars`; set the account ID. These local files are ignored.

Run from the repository root after configuring Infisical:

```sh
infisical run -- terraform -chdir=infra/terraform init -input=false -backend-config=backend.hcl
infisical run -- terraform -chdir=infra/terraform fmt -check -recursive
infisical run -- terraform -chdir=infra/terraform validate
infisical run -- terraform -chdir=infra/terraform plan -input=false -out=tfplan
```

Review the saved plan and obtain explicit approval before applying it:

```sh
infisical run -- terraform -chdir=infra/terraform apply -input=false tfplan
infisical run -- terraform -chdir=infra/terraform output -json github_repository_variables
infisical run -- terraform -chdir=infra/terraform output -json dns_records
```

Backend configuration, plans and state must stay out of Git and public artifacts. Provider credentials come from Infisical at runtime, not Terraform-managed token resources. State can still contain sensitive resource data; protect it.

## DNS ordering

1. Apply the Pages project/domain association here. The association may remain pending until DNS exists; pending validation does not mean the site is live.
2. Compare `dns_records` with the `enfatizados` plan. Its default adds only `remaju.mejora.me CNAME remaju-explorer.pages.dev`, DNS-only, automatic TTL. If Cloudflare assigns a different `subdomain`, use the actual output rather than guessing a target.
3. Approve/apply the DNS plan separately, deploy the site, then verify HTTPS and the Pages custom-domain status. Do not add A records, change the apex records or create an independent CNAME before registering the Pages domain.

The project and bucket have `prevent_destroy`. Disabling R2 after creating it intentionally fails rather than deleting authoritative data. Plan and review any migration explicitly. No lifecycle expiration is configured: durable history is retained indefinitely until an owner-approved policy exists.

## GitHub outputs and authentication

Copy each entry of `github_repository_variables` into **repository** Actions variables in `enfasis/remaju-explorer`. The account ID is not a secret. `required_secret_names` lists names only, never credential values. Terraform does not write GitHub settings automatically.

Create the `production` GitHub environment, restrict deployment branches to `main`, and enable required reviewers if available. The workflow also checks the branch. Builds run without deployment credentials, then a separate production job downloads only the built site and obtains credentials.

Deployment and the disabled future refresh workflow share `remaju-production` concurrency with cancellation disabled. This protects GitHub writers only; independent publishers still need tested remote coordination.

### GitHub Secrets

Default `DEPLOY_AUTH_METHOD=github-secrets`: store a scoped Cloudflare Pages Edit token as `CLOUDFLARE_API_TOKEN` in GitHub repository/environment secrets. Existing installations with the account ID in GitHub Secrets remain supported.

### GitHub OIDC → Infisical → Cloudflare

Cloudflare's documented Pages Direct Upload flow uses an API token, not a direct GitHub OIDC/WIF exchange. R2 S3 uploads likewise need R2 credentials. This workflow optionally federates GitHub's identity to Infisical so no long-lived credential needs to be stored in GitHub; it does **not** turn the Cloudflare token into a short-lived token.

1. Create a dedicated Infisical identity for this deployment, organization role No Access, with OIDC authentication. Do not reuse the susu identity. Give it read-only access to the chosen environment and `/remaju/pages` folder only, without imports. Store only `CLOUDFLARE_API_TOKEN` in that folder; no infrastructure, DNS, HCP or future R2 credentials.
2. Set issuer/discovery URL `https://token.actions.githubusercontent.com`, audience `https://github.com/enfasis`, and exact production-environment subject. The legacy subject is `repo:enfasis/remaju-explorer:environment:production`; newer repositories can use immutable ID-based subjects. Inspect `gh api repos/enfasis/remaju-explorer/actions/oidc/customization/sub` and verify the actual token claims before configuring trust. Also bind `repository_id`, `repository_owner_id`, and `ref=refs/heads/main` where supported. Do not use wildcard repository or environment trust. Remove Universal Auth from this dedicated identity after testing OIDC.
3. Set `infisical` in local tfvars to the identity ID and project slug (identifiers, not secrets):

```hcl
infisical = {
  identity_id  = "your-dedicated-identity-id"
  project_slug = "your-remaju-project-slug"
  environment  = "prod"
  secret_path  = "/remaju/pages"
}
```

4. Plan/apply the output change and copy all generated variables to GitHub. The production job requests `id-token: write` and fetches secrets only after building. Test a manual main deployment, confirm success, then remove the redundant GitHub Pages token manually if migrating. Rotate the underlying Cloudflare token periodically.

The Infisical action is pinned to commit `77ab1f4ccd183a543cb5b42435fbd181189f4995` (release `v1.0.16`). Review upgrades before changing the pin.

The identity and trust configuration are manual prerequisites, not Terraform-managed resources in this implementation. See [Infisical's GitHub Actions guide](https://infisical.com/docs/integrations/cicd/githubactions) and [Cloudflare Direct Upload](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/).

## Optional R2

Keep `enable_r2=false` until billing, location/jurisdiction, indefinite-history retention, and a monthly budget/alerts are approved. Set `enable_r2=true` to create a private Standard bucket and read-only CORS for the production custom domain and production `pages.dev` origin. Location is a placement hint, not a guarantee. Preview origins are deliberately excluded. CORS is not access control for non-browser clients.

Only after public-export privacy review, set `publish_r2=true` and `mejora_zone_id`. Cloudflare's R2 custom-domain API provisions the DNS for `data.remaju.mejora.me`; **do not** create that record in `enfatizados`, use a guessed IP, or point it at the private S3 API endpoint. All objects in a publicly exposed bucket are potentially public. Never upload raw captures, prior private state, sessions or credentials.

`R2_BUCKET`, jurisdiction-aware `R2_ENDPOINT` and optional `R2_PUBLIC_BASE_URL` outputs are reserved for a future publisher. Create bucket-scoped Object Read & Write credentials separately. Do not give them to the frontend deployment identity. No R2 upload workflow, schedule activation, cache rules, billing alerts, or budget hard cap is implemented here. Object Content-Type/Cache-Control and manifest-last promotion belong to the tested future publisher. Provisioning storage does not configure the frontend to consume it.

## Offline contract tests

These use a mocked provider and do not contact Cloudflare or require credentials/state:

```sh
terraform -chdir=infra/terraform init -backend=false -input=false -lockfile=readonly
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform test
```
