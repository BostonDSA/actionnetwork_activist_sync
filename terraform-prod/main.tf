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
    lambda_function_arn = aws_lambda_function.an-sync-ingester-lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.an-sync-ingester-lambda-permission]
}

# Lambda to process ingester messages

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
  statement {
    actions = [
      "dynamodb:*"
    ]
    resources = [module.shared.db-table.arn, module.shared.db-table.stream_arn]
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

resource "aws_iam_role" "an-sync-lambda-role" {
  name               = "an-sync-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.an-sync-lambda-policy-assume.json
}

resource "aws_iam_role_policy_attachment" "an-sync-lambda-policy-attach" {
  role       = aws_iam_role.an-sync-lambda-role.name
  policy_arn = aws_iam_policy.an-sync-lambda-policy-attach.arn
}

resource "aws_lambda_permission" "an-sync-ingester-lambda-permission" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.an-sync-ingester-lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.an-sync-bucket.arn
}

resource "aws_lambda_function" "an-sync-ingester-lambda" {
  description      = "Action Network Sync S3 Ingester (Step 1)"
  filename         = "../dist/sync.zip"
  source_code_hash = filebase64sha256("../dist/sync.zip")
  function_name    = "an-sync-ingester-lambda"
  role             = aws_iam_role.an-sync-lambda-role.arn
  handler          = "lambda_ingester.lambda_handler"
  runtime          = "python3.7"

  environment {
    variables = {
      DRY_RUN   = module.shared.dry-run-ingester
      DSA_KEY   = aws_secretsmanager_secret.an-sync-secrets.arn
      LOG_LEVEL = "INFO"
    }
  }

}

resource "aws_cloudwatch_log_group" "an-sync-ingester-lambda" {
  name              = "/aws/lambda/${aws_lambda_function.an-sync-ingester-lambda.function_name}"
  retention_in_days = 60
}

# Lambda to process the DynamoDB items

resource "aws_lambda_event_source_mapping" "processor" {
  event_source_arn       = module.shared.db-table.stream_arn
  function_name          = aws_lambda_function.an-sync-processor-lambda.arn
  starting_position      = "LATEST"
  maximum_retry_attempts = 3
  batch_size             = 10
}

resource "aws_lambda_function" "an-sync-processor-lambda" {
  description      = "Action Network Sync DynamoDB Processor (Step 2)"
  filename         = "../dist/sync.zip"
  source_code_hash = filebase64sha256("../dist/sync.zip")
  function_name    = "an-sync-processor-lambda"
  role             = aws_iam_role.an-sync-lambda-role.arn
  handler          = "lambda_processor.lambda_handler"
  runtime          = "python3.7"
  timeout          = 60

  environment {
    variables = {
      ACTIONNETWORK_API_KEY = aws_secretsmanager_secret.an-sync-secrets.arn
      DRY_RUN               = module.shared.dry-run-processor
      LOG_LEVEL             = "INFO"
    }
  }
}

resource "aws_cloudwatch_log_group" "an-sync-processor-lambda" {
  name              = "/aws/lambda/${aws_lambda_function.an-sync-processor-lambda.function_name}"
  retention_in_days = 60
}

# Lambda to process membership lapses

resource "aws_cloudwatch_event_rule" "an-sync-lapsed" {
  name        = "an-sync-lapsed"
  description = "Weekly job to trigger lapsed lambda"
  # Tuesday 7pm
  schedule_expression = "cron(0 19 ? * 2 *)"
}

resource "aws_cloudwatch_event_target" "an-sync-lapsed" {
  rule      = aws_cloudwatch_event_rule.an-sync-lapsed.name
  target_id = "an-sync-trigger-lambda"
  arn       = aws_lambda_function.an-sync-lapsed-lambda.arn
}

resource "aws_lambda_function" "an-sync-lapsed-lambda" {
  description      = "Action Network Sync Lapsed Memberships (Step 3)"
  filename         = "../dist/sync.zip"
  source_code_hash = filebase64sha256("../dist/sync.zip")
  function_name    = "an-sync-lapsed-lambda"
  role             = aws_iam_role.an-sync-lambda-role.arn
  handler          = "lambda_lapsed.lambda_handler"
  runtime          = "python3.7"
  timeout          = 600

  environment {
    variables = {
      ACTIONNETWORK_API_KEY = aws_secretsmanager_secret.an-sync-secrets.arn
      DRY_RUN               = module.shared.dry-run-lapsed
      LOG_LEVEL             = "INFO"
    }
  }
}

resource "aws_cloudwatch_log_group" "an-sync-lapsed-lambda" {
  name              = "/aws/lambda/${aws_lambda_function.an-sync-lapsed-lambda.function_name}"
  retention_in_days = 60
}

# Misc

resource "aws_secretsmanager_secret" "an-sync-secrets" {
  name = module.shared.project
}