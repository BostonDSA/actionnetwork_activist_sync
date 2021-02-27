output "project" {
  value = var.project
}

output "domain" {
  value = var.domain
}

output "bucket" {
  value = var.bucket
}

output "dry-run-ingester" {
  value = var.dry-run-ingester
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
