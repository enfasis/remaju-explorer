locals {
  site_hostname = "remaju.mejora.me"
  data_hostname = "data.remaju.mejora.me"
  r2_suffix     = var.r2_jurisdiction == "default" ? "" : ".${var.r2_jurisdiction}"
}

resource "cloudflare_pages_project" "explorer" {
  account_id        = var.account_id
  name              = var.pages_project
  production_branch = "main"

  lifecycle {
    prevent_destroy = true
  }
}

resource "cloudflare_pages_domain" "explorer" {
  account_id   = var.account_id
  project_name = cloudflare_pages_project.explorer.name
  name         = local.site_hostname
}

resource "cloudflare_r2_bucket" "public" {
  count         = var.enable_r2 ? 1 : 0
  account_id    = var.account_id
  name          = var.r2_bucket
  location      = var.r2_location
  jurisdiction  = var.r2_jurisdiction
  storage_class = "Standard"

  lifecycle {
    prevent_destroy = true
  }
}

resource "cloudflare_r2_bucket_cors" "public" {
  count        = var.enable_r2 ? 1 : 0
  account_id   = var.account_id
  bucket_name  = cloudflare_r2_bucket.public[0].name
  jurisdiction = var.r2_jurisdiction
  rules = [{
    id = "explorer-read-only"
    allowed = {
      methods = ["GET", "HEAD"]
      origins = ["https://${local.site_hostname}", "https://${cloudflare_pages_project.explorer.subdomain}"]
    }
    expose_headers  = ["ETag", "Content-Encoding"]
    max_age_seconds = 3600
  }]
}

resource "cloudflare_r2_custom_domain" "public" {
  count        = var.publish_r2 ? 1 : 0
  account_id   = var.account_id
  bucket_name  = cloudflare_r2_bucket.public[0].name
  jurisdiction = var.r2_jurisdiction
  zone_id      = var.mejora_zone_id
  domain       = local.data_hostname
  enabled      = true
  min_tls      = "1.2"
}
