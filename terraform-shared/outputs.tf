output "project" {
  value = var.project
}

output "domain" {
  value = var.domain
}

output "bucket" {
  value = var.bucket
}

output "db-table" {
    value = aws_dynamodb_table.an-sync
}