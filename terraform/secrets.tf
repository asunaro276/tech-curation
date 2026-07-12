resource "aws_ssm_parameter" "ob_credentials" {
  name        = "/tech-curation/ob-credentials"
  description = "ob login credentials for obsidian-headless sync"
  type        = "SecureString"
  value       = "PLACEHOLDER"

  lifecycle {
    ignore_changes = [value]
  }
}
