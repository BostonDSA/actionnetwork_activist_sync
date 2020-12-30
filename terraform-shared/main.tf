resource "aws_dynamodb_table" "an-sync" {
  name             = var.project
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "email"
  range_key        = "batch"
  stream_enabled   = true
  stream_view_type = "KEYS_ONLY"

  attribute {
    name = "email"
    type = "S"
  }

  attribute {
    name = "batch"
    type = "S"
  }

}