variable "bucket_arn" {
  type = string
}

resource "aws_dynamodb_table" "an-sync" {
  name           = var.project
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "batch"
  range_key      = "email"
  stream_enabled = false

  attribute {
    name = "email"
    type = "S"
  }

  attribute {
    name = "batch"
    type = "S"
  }

}

data "aws_iam_policy_document" "an-sync-lambda-policy-assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "an-sync-lambda-role" {
  name               = "an-sync-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.an-sync-lambda-policy-assume.json
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
    resources = ["${var.bucket_arn}/*"]
  }
  statement {
    actions = [
      "dynamodb:*"
    ]
    resources = [aws_dynamodb_table.an-sync.arn]
  }
  statement {
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = [aws_secretsmanager_secret.an-sync-secrets.arn]
  }
}

resource "aws_iam_policy" "an-sync-lambda-policy-attach" {
  name   = "an-sync-lambda-policy-attach"
  policy = data.aws_iam_policy_document.an-sync-lambda-policy-attach.json
}

resource "aws_iam_role_policy_attachment" "an-sync-lambda-policy-attach" {
  role       = aws_iam_role.an-sync-lambda-role.id
  policy_arn = aws_iam_policy.an-sync-lambda-policy-attach.arn
}


resource "aws_lambda_function" "an-sync-ingester-lambda" {
  description      = "Action Network Sync S3 Ingester (Step 1)"
  filename         = "../dist/sync.zip"
  source_code_hash = filebase64sha256("../dist/sync.zip")
  function_name    = "an-sync-ingester-lambda"
  role             = aws_iam_role.an-sync-lambda-role.arn
  handler          = "lambda_ingester.lambda_handler"
  runtime          = "python3.7"
  timeout          = 300

  environment {
    variables = {
      DSA_KEY   = aws_secretsmanager_secret.an-sync-secrets.arn
      LOG_LEVEL = "INFO"
    }
  }

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
      DRY_RUN               = var.dry-run-processor
      LOG_LEVEL             = "INFO"
    }
  }

  lifecycle {
    ignore_changes = [environment]
  }
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
      DRY_RUN               = var.dry-run-lapsed
      LOG_LEVEL             = "INFO"
    }
  }

  lifecycle {
    ignore_changes = [environment]
  }
}

data "aws_iam_policy_document" "an-sync-step-policy-assume" {
  policy_id = "an-sync-step-policy-assume"
  statement {
    sid = "StateMachineAssume"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = [
        "states.amazonaws.com",
        "events.amazonaws.com"
        ]
    }
  }
}

data "aws_iam_policy_document" "an-sync-step-invoke" {
  policy_id = "an-sync-step-invoke"
  statement {
    sid = "StateMachineInvokeLambda"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = [
      aws_lambda_function.an-sync-ingester-lambda.arn,
      aws_lambda_function.an-sync-processor-lambda.arn,
      aws_lambda_function.an-sync-lapsed-lambda.arn
    ]
  }
  statement {
    sid = "StateMachineStartExecution"
    actions = [
      "states:StartExecution"
    ]
    resources = [
      aws_sfn_state_machine.an-sync-state-machine.arn
    ]
  }
}

resource "aws_iam_policy" "an-sync-step" {
  policy = data.aws_iam_policy_document.an-sync-step-invoke.json
}

resource "aws_iam_role_policy_attachment" "an-sync-step" {
  role       = aws_iam_role.an-sync-step.name
  policy_arn = aws_iam_policy.an-sync-step.arn
}

resource "aws_iam_role" "an-sync-step" {
  name               = "an-sync-step"
  assume_role_policy = data.aws_iam_policy_document.an-sync-step-policy-assume.json
}

resource "aws_sfn_state_machine" "an-sync-state-machine" {
  name       = var.project
  role_arn   = aws_iam_role.an-sync-step.arn
  definition = <<EOF
{
  "StartAt": "Ingester",
  "States": {
    "Ingester": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.an-sync-ingester-lambda.arn}",
      "InputPath": "$.detail.requestParameters",
      "Next": "Processor"
    },

    "Processor": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.an-sync-processor-lambda.arn}",
      "Next": "MoreToProcess"
    },

    "MoreToProcess": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.hasMore",
          "BooleanEquals": true,
          "Next": "Processor"
        }
      ],
      "Default": "Lapsed"
    },

    "Lapsed": {
      "Type": "Task",
      "Resource": "${aws_lambda_function.an-sync-lapsed-lambda.arn}",
      "Next": "Succeed"
    },

    "Succeed": {
      "Type": "Succeed"
    }
  }
}
EOF
}

resource "aws_secretsmanager_secret" "an-sync-secrets" {
  name = var.project
}