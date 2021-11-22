output "project" {
  value = var.project
}

output "domain" {
  value = var.domain
}

output "bucket" {
  value = var.bucket
}

output "dry-run-processor" {
  value = var.dry-run-processor
}

output "dry-run-lapsed" {
  value = var.dry-run-lapsed
}

output "db-table" {
  value = aws_dynamodb_table.an-sync
}

output "lambda-ingester" {
  value = aws_lambda_function.an-sync-ingester-lambda
}

output "lambda-processor" {
  value = aws_lambda_function.an-sync-processor-lambda
}

output "lambda-lapsed" {
  value = aws_lambda_function.an-sync-lapsed-lambda
}

output "iam-role-lambda" {
  value = aws_iam_role.an-sync-lambda-role
}

output "secrets" {
  value = aws_secretsmanager_secret.an-sync-secrets
}

output "step" {
  value = aws_sfn_state_machine.an-sync-state-machine
}

output "iam-role-step" {
  value = aws_iam_role.an-sync-step
}