mock_provider "cloudflare" {
  mock_resource "cloudflare_pages_project" {
    override_during = plan
    defaults = {
      subdomain = "remaju-explorer.pages.dev"
    }
  }
}

variables {
  account_id           = "0123456789abcdef0123456789abcdef"
  cloudflare_api_token = "offline-test-placeholder"
}

run "pages_only" {
  command = plan

  assert {
    condition     = cloudflare_pages_project.explorer.production_branch == "main" && cloudflare_pages_project.explorer.source == null
    error_message = "Pages must use Direct Upload on main."
  }

  assert {
    condition     = length(cloudflare_r2_bucket.public) == 0 && output.github_repository_variables.DEPLOY_AUTH_METHOD == "github-secrets"
    error_message = "R2 must remain opt-in and secrets auth must work by default."
  }

  assert {
    condition     = output.dns_records[0].type == "CNAME" && output.dns_records[0].name == "remaju.mejora.me"
    error_message = "Pages needs a CNAME, not an A record."
  }
}

run "private_eu_storage_with_oidc" {
  command = plan
  variables {
    enable_r2       = true
    r2_jurisdiction = "eu"
    infisical = {
      identity_id  = "dedicated-ci-identity"
      project_slug = "remaju"
    }
  }

  assert {
    condition     = output.github_repository_variables.R2_ENDPOINT == "https://0123456789abcdef0123456789abcdef.eu.r2.cloudflarestorage.com"
    error_message = "Jurisdiction-specific endpoints must be preserved."
  }

  assert {
    condition     = length(cloudflare_r2_custom_domain.public) == 0 && output.github_repository_variables.DEPLOY_AUTH_METHOD == "infisical-oidc"
    error_message = "Storage must stay private unless separately approved."
  }

  assert {
    condition     = cloudflare_r2_bucket.public[0].storage_class == "Standard" && cloudflare_r2_bucket_cors.public[0].rules[0].allowed.methods == tolist(["GET", "HEAD"])
    error_message = "Use Standard storage and read-only browser CORS."
  }

  assert {
    condition     = cloudflare_r2_bucket_cors.public[0].rules[0].allowed.origins == tolist(["https://remaju.mejora.me", "https://remaju-explorer.pages.dev"])
    error_message = "CORS must allow only production origins, never wildcards or previews."
  }
}

run "public_storage" {
  command = plan
  variables {
    enable_r2      = true
    publish_r2     = true
    mejora_zone_id = "0123456789abcdef0123456789abcdef"
  }

  assert {
    condition     = output.github_repository_variables.R2_PUBLIC_BASE_URL == "https://data.remaju.mejora.me" && cloudflare_r2_custom_domain.public[0].min_tls == "1.2"
    error_message = "Publish only through the TLS custom domain."
  }
}

run "reject_public_without_bucket" {
  command = plan
  variables {
    publish_r2 = true
  }
  expect_failures = [var.publish_r2]
}
