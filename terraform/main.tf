provider "aws" {
  profile = "bostondsa"
  region = "us-east-1"
}

locals {
  email = format("%s@%s", var.project, var.domain)
}

data "aws_caller_identity" "current" {}

# S3 Bucket to deposit incoming emails into

data "aws_iam_policy_document" "incoming" {
  statement {
    sid = "AllowSESPuts"
    actions = ["s3:PutObject"]
    resources = [format("%s/*", aws_s3_bucket.incoming.arn)]
    principals {
      type = "Service"
      identifiers = ["ses.amazonaws.com"]
    }
    condition {
      test = "StringEquals"
      variable = "aws:Referer"
      values = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_s3_bucket_policy" "incoming" {
  bucket = aws_s3_bucket.incoming.bucket
  policy = data.aws_iam_policy_document.incoming.json
}

# This makes sure we don't accidentally put anything in the bucket publically

resource "aws_s3_bucket_public_access_block" "incoming" {
  bucket = aws_s3_bucket.incoming.id

  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "incoming" {
  bucket = format("%s.%s", var.bucket, var.domain)
  acl    = "private"
}

# Simple Email Service (SES)

resource "aws_ses_receipt_rule_set" "default" {
  rule_set_name = "default"
}

resource "aws_ses_active_receipt_rule_set" "default" {
  rule_set_name = aws_ses_receipt_rule_set.default.rule_set_name
}

resource "aws_ses_receipt_rule" "incoming" {
  name = "${var.project}_incoming"
  rule_set_name = aws_ses_receipt_rule_set.default.rule_set_name
  recipients = [local.email]
  enabled = true

  s3_action {
    bucket_name = aws_s3_bucket.incoming.bucket
    position = 1
  }
}
