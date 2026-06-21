output "api_gateway_url" {
  description = "Base URL for API Gateway (used in Obsidian Button and collect Lambda env)"
  value       = "${aws_apigatewayv2_api.this.api_endpoint}/${aws_apigatewayv2_stage.prod.name}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for docker build/push"
  value       = aws_ecr_repository.this.repository_url
}

output "ob_credentials_secret_name" {
  description = "Secrets Manager secret name for ob login credentials"
  value       = aws_secretsmanager_secret.ob_credentials.name
}
