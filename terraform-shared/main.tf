resource "aws_dynamodb_table" "an-sync" {
  name           = var.project
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "email"
  range_key      = "batch"

  attribute {
    name = "email"
    type = "S"
  }

  attribute {
    name = "batch"
    type = "S"
  }

}