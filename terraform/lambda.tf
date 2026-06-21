resource "aws_lambda_function" "collect" {
  function_name = "tech-curation-collect"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.this.repository_url}:latest"
  role          = aws_iam_role.lambda.arn
  timeout       = 900
  memory_size   = 1024

  image_config {
    command = ["handler_collect.handler"]
  }

  environment {
    variables = {
      VAULT_ROOT            = "/tmp/vault"
      OB_CREDENTIALS_SECRET = aws_secretsmanager_secret.ob_credentials.name
      API_GATEWAY_URL       = "${aws_apigatewayv2_api.this.api_endpoint}/${aws_apigatewayv2_stage.prod.name}"
    }
  }

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function" "improve" {
  function_name = "tech-curation-improve"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.this.repository_url}:latest"
  role          = aws_iam_role.lambda.arn
  timeout       = 900
  memory_size   = 1024

  image_config {
    command = ["handler_improve.handler"]
  }

  environment {
    variables = {
      VAULT_ROOT            = "/tmp/vault"
      OB_CREDENTIALS_SECRET = aws_secretsmanager_secret.ob_credentials.name
    }
  }

  lifecycle {
    ignore_changes = [image_uri]
  }
}
