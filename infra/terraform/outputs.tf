output "github_repository_variables" {
  description = "Non-secret GitHub Actions repository variables; R2 values are reserved for the future publisher."
  value = merge({
    CLOUDFLARE_ACCOUNT_ID    = var.account_id
    CLOUDFLARE_PAGES_PROJECT = cloudflare_pages_project.explorer.name
    DEPLOY_AUTH_METHOD       = var.infisical == null ? "github-secrets" : "infisical-oidc"
    }, var.infisical == null ? {} : {
    INFISICAL_IDENTITY_ID  = var.infisical.identity_id
    INFISICAL_PROJECT_SLUG = var.infisical.project_slug
    INFISICAL_ENVIRONMENT  = var.infisical.environment
    INFISICAL_SECRET_PATH  = var.infisical.secret_path
    }, var.enable_r2 ? {
    R2_BUCKET   = cloudflare_r2_bucket.public[0].name
    R2_ENDPOINT = "https://${var.account_id}${local.r2_suffix}.r2.cloudflarestorage.com"
    } : {}, var.publish_r2 ? {
    R2_PUBLIC_BASE_URL = "https://${local.data_hostname}"
  } : {})
}

output "required_secret_names" {
  description = "Names only. Pages token belongs in GitHub Secrets or the dedicated Infisical path. R2 credentials are not consumed yet."
  value = {
    pages               = ["CLOUDFLARE_API_TOKEN"]
    future_r2_publisher = var.enable_r2 ? ["R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"] : []
  }
}

output "dns_records" {
  description = "Apply this CNAME in enfatizados after registering the Pages custom domain. No A records or static IPs."
  value = [{
    zone    = "mejora.me"
    name    = local.site_hostname
    type    = "CNAME"
    content = cloudflare_pages_project.explorer.subdomain
    ttl     = 1
    proxied = false
    owner   = "enfatizados"
  }]
}

output "r2_domain" {
  description = "Cloudflare's R2 custom-domain API provisions its DNS. Do not duplicate it in enfatizados or point at the S3 API endpoint."
  value       = var.publish_r2 ? "https://${cloudflare_r2_custom_domain.public[0].domain}" : null
}

output "site_url" {
  value = "https://${local.site_hostname}"
}

output "pages_url" {
  value = "https://${cloudflare_pages_project.explorer.subdomain}"
}
