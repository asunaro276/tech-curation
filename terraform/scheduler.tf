resource "aws_scheduler_schedule" "collect" {
  name = "tech-curation-daily-collect"

  flexible_time_window {
    mode = "OFF"
  }

  # Daily at 07:00 JST (22:00 UTC previous day)
  schedule_expression          = "cron(0 22 * * ? *)"
  schedule_expression_timezone = "UTC"

  target {
    arn      = aws_lambda_function.collect.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({})
  }
}
