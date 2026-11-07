variable "cloudflare_api_token" {
  description = "Infrastructure-only token, supplied by Infisical as TF_VAR_cloudflare_api_token."
  type        = string
  sensitive   = true
}

variable "account_id" {
  description = "Cloudflare account owning Pages and R2."
  type        = string
  validation {
    condition     = can(regex("^[a-f0-9]{32}$", var.account_id))
    error_message = "Supply a 32-character Cloudflare account ID."
  }
}

variable "pages_project" {
  description = "Pages project name; copy the actual subdomain output to enfatizados."
  type        = string
  default     = "remaju-explorer"
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,57}$", var.pages_project))
    error_message = "Use a valid Pages project name of up to 58 lowercase letters, digits or hyphens."
  }
}

variable "enable_r2" {
  description = "Provision durable storage only after billing, retention and budget approval."
  type        = bool
  default     = false
}

variable "r2_bucket" {
  type        = string
  description = "Globally unique public-export bucket name. Never store private captures here."
  default     = "remaju-explorer-public"
}

variable "r2_location" {
  description = "Best-effort placement hint, not a residency guarantee."
  type        = string
  default     = "enam"
  validation {
    condition     = contains(["apac", "eeur", "enam", "weur", "wnam", "oc"], var.r2_location)
    error_message = "Use a supported R2 location hint."
  }
}

variable "r2_jurisdiction" {
  type        = string
  description = "Guaranteed jurisdiction; affects the S3 endpoint."
  default     = "default"
  validation {
    condition     = contains(["default", "eu", "fedramp"], var.r2_jurisdiction)
    error_message = "Use default, eu or fedramp."
  }
}

variable "publish_r2" {
  description = "Expose the bucket at data.remaju.mejora.me only after privacy review."
  type        = bool
  default     = false
  validation {
    condition     = !var.publish_r2 || (var.enable_r2 && var.mejora_zone_id != null)
    error_message = "Public access requires enable_r2 and mejora_zone_id."
  }
}

variable "mejora_zone_id" {
  description = "Required only for the R2 custom domain; DNS remains owned by enfatizados otherwise."
  type        = string
  default     = null
}

variable "infisical" {
  description = "Optional dedicated GitHub OIDC identity. Null selects GitHub Secrets authentication."
  type = object({
    identity_id  = string
    project_slug = string
    environment  = optional(string, "prod")
    secret_path  = optional(string, "/remaju/pages")
  })
  default = null
}
