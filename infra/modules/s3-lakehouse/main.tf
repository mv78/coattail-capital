variable "prefix" {
  type = string
}

variable "account_id" {
  type = string
}

variable "transition_to_ia_days" {
  type    = number
  default = 30
}

variable "expiration_days" {
  type    = number
  default = 90
}

locals {
  buckets = {
    raw        = "${var.prefix}-raw-${var.account_id}"
    processed  = "${var.prefix}-processed-${var.account_id}"
    checkpoint = "${var.prefix}-checkpoint-${var.account_id}"
    athena     = "${var.prefix}-athena-results-${var.account_id}"
  }
}

# --- Raw Data Landing Zone ---
resource "aws_s3_bucket" "raw" {
  bucket        = local.buckets.raw
  force_destroy = true # Portfolio project — easy teardown

  tags = { Component = "lakehouse-raw" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    id     = "archive-and-expire"
    status = "Enabled"
    transition {
      days          = var.transition_to_ia_days
      storage_class = "STANDARD_IA"
    }
    expiration {
      days = var.expiration_days
    }
  }
}

# --- Processed Data (Iceberg Tables) ---
resource "aws_s3_bucket" "processed" {
  bucket        = local.buckets.processed
  force_destroy = true

  tags = { Component = "lakehouse-processed" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed" {
  bucket = aws_s3_bucket.processed.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "processed" {
  bucket                  = aws_s3_bucket.processed.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "processed" {
  bucket = aws_s3_bucket.processed.id
  versioning_configuration {
    status = "Enabled" # Protect Iceberg metadata
  }
}

# --- Spark Checkpoints ---
resource "aws_s3_bucket" "checkpoint" {
  bucket        = local.buckets.checkpoint
  force_destroy = true

  tags = { Component = "spark-checkpoints" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "checkpoint" {
  bucket = aws_s3_bucket.checkpoint.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "checkpoint" {
  bucket                  = aws_s3_bucket.checkpoint.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "checkpoint" {
  bucket = aws_s3_bucket.checkpoint.id
  rule {
    id     = "expire-old-checkpoints"
    status = "Enabled"
    expiration {
      days = 7 # Checkpoints only needed for recovery
    }
  }
}

# --- Athena Query Results ---
resource "aws_s3_bucket" "athena" {
  bucket        = local.buckets.athena
  force_destroy = true

  tags = { Component = "athena-results" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "athena" {
  bucket = aws_s3_bucket.athena.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "athena" {
  bucket                  = aws_s3_bucket.athena.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "athena" {
  bucket = aws_s3_bucket.athena.id
  rule {
    id     = "expire-query-results"
    status = "Enabled"
    expiration {
      days = 7
    }
  }
}

# --- Outputs ---
output "raw_bucket_id" {
  value = aws_s3_bucket.raw.id
}

output "raw_bucket_arn" {
  value = aws_s3_bucket.raw.arn
}

output "processed_bucket_id" {
  value = aws_s3_bucket.processed.id
}

output "processed_bucket_arn" {
  value = aws_s3_bucket.processed.arn
}

output "checkpoint_bucket_id" {
  value = aws_s3_bucket.checkpoint.id
}

output "checkpoint_bucket_arn" {
  value = aws_s3_bucket.checkpoint.arn
}

output "athena_results_bucket_id" {
  value = aws_s3_bucket.athena.id
}

output "athena_results_bucket_arn" {
  value = aws_s3_bucket.athena.arn
}
