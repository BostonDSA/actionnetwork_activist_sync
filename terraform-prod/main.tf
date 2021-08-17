terraform {
  backend "s3" {
    bucket  = "terraform.bostondsa.org"
    key     = "actionnetwork_activist_sync.tfstate"
    region  = "us-east-1"
    profile = "bostondsa"
  }
}

provider "aws" {
  profile = "bostondsa"
  region  = "us-east-1"
}

module "shared" {
  source     = "../terraform-shared"
  bucket_arn = aws_s3_bucket.an-sync-bucket.arn
}

locals {
  email = format("%s@%s", module.shared.project, module.shared.domain)
}

data "aws_caller_identity" "current" {}

# Simple Email Service (SES) to receive emails

resource "aws_ses_receipt_rule_set" "default" {
  rule_set_name = "default"
}

resource "aws_ses_active_receipt_rule_set" "default" {
  rule_set_name = aws_ses_receipt_rule_set.default.rule_set_name
}

resource "aws_ses_receipt_rule" "an-sync-ses-rule" {
  name          = "${module.shared.project}_ingester"
  rule_set_name = aws_ses_receipt_rule_set.default.rule_set_name
  recipients    = [local.email]
  enabled       = true

  s3_action {
    bucket_name = aws_s3_bucket.an-sync-bucket.bucket
    position    = 1
  }
}

# Let SES put emails in S3 Bucket
data "aws_iam_policy_document" "an-sync-bucket-policy" {
  statement {
    sid       = "AllowSESPuts"
    actions   = ["s3:PutObject"]
    resources = [format("%s/*", aws_s3_bucket.an-sync-bucket.arn)]
    principals {
      type        = "Service"
      identifiers = ["ses.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:Referer"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_s3_bucket_policy" "an-sync-bucket-policy" {
  bucket = aws_s3_bucket.an-sync-bucket.bucket
  policy = data.aws_iam_policy_document.an-sync-bucket-policy.json
}

# This makes sure we don't accidentally put anything in the bucket publically

resource "aws_s3_bucket_public_access_block" "an-sync-bucket-policy" {
  bucket = aws_s3_bucket.an-sync-bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "an-sync-bucket" {
  bucket = format("%s.%s", module.shared.bucket, module.shared.domain)
  acl    = "private"
}

resource "aws_s3_bucket_public_access_block" "an-sync-bucket-policy-cloudtrail" {
  bucket = aws_s3_bucket.an-sync-bucket-cloudtrail.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}


data "aws_iam_policy_document" "an-sync-bucket-cloudtrail" {
  statement {
    sid = "AWSCloudTrailAclCheck"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    actions   = ["s3:GetBucketAcl"]
    resources = ["arn:aws:s3:::${format("%s-cloudtrail", module.shared.bucket)}"]
  }
  statement {
    sid = "AWSCloudTrailWrite"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]

    }
    actions   = ["s3:PutObject"]
    resources = ["arn:aws:s3:::${format("%s-cloudtrail", module.shared.bucket)}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"]
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }
}

resource "aws_s3_bucket" "an-sync-bucket-cloudtrail" {
  bucket = format("%s-cloudtrail", module.shared.bucket)
  acl    = "private"
  policy = data.aws_iam_policy_document.an-sync-bucket-cloudtrail.json
}

# Logging

resource "aws_cloudwatch_log_group" "an-sync-ingester-lambda" {
  name              = "/aws/lambda/${module.shared.lambda-ingester.function_name}"
  retention_in_days = 60
}

resource "aws_cloudwatch_log_group" "an-sync-processor-lambda" {
  name              = "/aws/lambda/${module.shared.lambda-processor.function_name}"
  retention_in_days = 60
}
resource "aws_cloudwatch_log_group" "an-sync-lapsed-lambda" {
  name              = "/aws/lambda/${module.shared.lambda-lapsed.function_name}"
  retention_in_days = 60
}

resource "aws_cloudtrail" "an-sync-bucket-cloudtrail" {
  name           = "an-sync-bucket-cloudtrail"
  s3_bucket_name = aws_s3_bucket.an-sync-bucket-cloudtrail.id

  event_selector {
    read_write_type           = "All"
    include_management_events = true

    data_resource {
      type   = "AWS::S3::Object"
      values = ["${aws_s3_bucket.an-sync-bucket.arn}/"]
    }
  }
}