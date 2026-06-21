resource "aws_secretsmanager_secret" "ob_credentials" {
  name                    = "tech-curation/ob-credentials"
  description             = "ob login credentials for obsidian-headless sync"
  recovery_window_in_days = 0
}
