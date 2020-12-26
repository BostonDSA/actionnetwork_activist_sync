provider "aws" {
  profile = "bostondsa"
  region  = "us-east-1"
}

locals {
  email = format("%s@%s", var.project, var.domain)
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
  name          = "${var.project}_incoming"
  rule_set_name = aws_ses_receipt_rule_set.default.rule_set_name
  recipients    = [local.email]
  enabled       = true

  s3_action {
    bucket_name = aws_s3_bucket.an-sync-bucket.bucket
    position    = 1
  }
}

# S3 Bucket to deposit incoming emails into

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

resource "aws_s3_bucket_public_access_block" "an-sync-bucket-policy" {
  # This makes sure we don't accidentally put anything in the bucket publically
  bucket = aws_s3_bucket.an-sync-bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "an-sync-bucket" {
  bucket = format("%s.%s", var.bucket, var.domain)
  acl    = "private"
}

resource "aws_s3_bucket_notification" "an-sync-bucket-notification" {
  bucket = aws_s3_bucket.an-sync-bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.an-sync-incoming-lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.an-sync-incoming-lambda-permission]
}

# Lambda to process incoming messages

data "aws_iam_policy_document" "an-sync-lambda-policy-assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

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
}

resource "aws_iam_policy" "an-sync-lambda-policy-attach" {
  policy = data.aws_iam_policy_document.an-sync-lambda-policy-attach.json
}

resource "aws_iam_role" "an-sync-incoming-lambda-role" {
  name               = "an-sync-incoming-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.an-sync-lambda-policy-assume.json
}

resource "aws_iam_role_policy_attachment" "an-sync-lambda-policy-attach" {
  role       = aws_iam_role.an-sync-incoming-lambda-role.name
  policy_arn = aws_iam_policy.an-sync-lambda-policy-attach.arn
}

resource "aws_lambda_permission" "an-sync-incoming-lambda-permission" {
  # Let the S3 bucket trigger the lambda
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.an-sync-incoming-lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.an-sync-bucket.arn
}

resource "aws_lambda_function" "an-sync-incoming-lambda" {
  filename         = "../function.zip"
  source_code_hash = data.archive_file.function.output_base64sha256
  function_name    = "an-sync-incoming-lambda"
  role             = aws_iam_role.an-sync-incoming-lambda-role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.7"
}

data "archive_file" "function" {
  # TODO replace with actual build process
  type        = "zip"
  source_file = "../lambda_function.py"
  output_path = "../function.zip"
}