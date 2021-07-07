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
  source = "../terraform-shared"
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

# S3 Bucket to deposit ingester emails into

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

resource "aws_s3_bucket_notification" "an-sync-bucket-notification" {
  bucket = aws_s3_bucket.an-sync-bucket.id

  lambda_function {
    lambda_function_arn = module.shared.lambda-ingester.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.an-sync-ingester-lambda-permission]
}

# Lambda to process ingester messages


data "aws_iam_policy_document" "an-sync-lambda-policy-attach" {
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }
  statement {
    actions = [
      "s3:*"
    ]
    resources = [format("%s/*", aws_s3_bucket.an-sync-bucket.arn)]
  }
  statement {
    actions = [
      "dynamodb:*"
    ]
    resources = [module.shared.db-table.arn]
  }
  statement {
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = [aws_secretsmanager_secret.an-sync-secrets.arn]
  }
}

resource "aws_iam_policy" "an-sync-lambda-policy-attach" {
  policy = data.aws_iam_policy_document.an-sync-lambda-policy-attach.json
}

resource "aws_iam_role_policy_attachment" "an-sync-lambda-policy-attach" {
  role       = module.shared.iam-role-lambda
  policy_arn = aws_iam_policy.an-sync-lambda-policy-attach.arn
}

resource "aws_lambda_permission" "an-sync-ingester-lambda-permission" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = module.shared.lambda-ingester.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.an-sync-bucket.arn
}


resource "aws_cloudwatch_log_group" "an-sync-ingester-lambda" {
  name              = "/aws/lambda/${module.shared.lambda-ingester.function_name}"
  retention_in_days = 60
}

# Lambda to process the DynamoDB items



resource "aws_cloudwatch_log_group" "an-sync-processor-lambda" {
  name              = "/aws/lambda/${module.shared.lambda-processor.function_name}"
  retention_in_days = 60
}

# Lambda to process membership lapses



resource "aws_cloudwatch_event_rule" "an-sync-lapsed" {
  name        = "an-sync-lapsed"
  description = "Weekly job to trigger lapsed lambda"
  # Tuesday 7pm
  schedule_expression = "cron(0 19 ? * 3 *)"
}

resource "aws_cloudwatch_event_target" "an-sync-lapsed" {
  rule      = aws_cloudwatch_event_rule.an-sync-lapsed.name
  target_id = "an-sync-trigger-lambda"
  arn       = module.shared.lambda-lapsed.arn
}

resource "aws_cloudwatch_log_group" "an-sync-lapsed-lambda" {
  name              = "/aws/lambda/${module.shared.lambda-lapsed.function_name}"
  retention_in_days = 60
}
