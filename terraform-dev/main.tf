provider "aws" {
  access_key                  = "mock_access_key"
  secret_key                  = "mock_secret_key"
  region                      = "us-east-1"
  s3_force_path_style         = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  skip_get_ec2_platforms      = true


  endpoints {
    dynamodb       = "http://localhost:4566"
    s3             = "http://localhost:4566"
    secretsmanager = "http://localhost:4566"
    stepfunctions  = "http://localhost:4566"
    iam            = "http://localhost:4566"
    lambda         = "http://localhost:4566"
  }
}

module "shared" {
  source     = "../terraform-shared"
  bucket_arn = aws_s3_bucket.an-sync-bucket.arn
}

resource "aws_s3_bucket" "an-sync-bucket" {
  bucket = format("%s.%s", module.shared.bucket, module.shared.domain)
  acl    = "public-read-write"
}

# Populates fake secrets

resource "aws_secretsmanager_secret_version" "an-sync" {
  secret_id     = module.shared.secrets.id
  secret_string = jsonencode(var.secrets)
}

variable "secrets" {
  default = {
    DSA_KEY               = "TESTKEY"
    ACTIONNETWORK_API_KEY = "TESTKEY"
  }

  type = map(string)
}
