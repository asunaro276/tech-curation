resource "aws_apigatewayv2_api" "this" {
  name          = "tech-curation-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "improve" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.improve.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "improve_post" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "POST /improve"
  target    = "integrations/${aws_apigatewayv2_integration.improve.id}"
}

resource "aws_apigatewayv2_route" "improve_get" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "GET /improve"
  target    = "integrations/${aws_apigatewayv2_integration.improve.id}"
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "prod"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.improve.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
