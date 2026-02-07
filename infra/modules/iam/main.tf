variable "prefix" {
  type = string
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "kinesis_stream_arn" {
  type = string
}

variable "raw_bucket_arn" {
  type = string
}

variable "processed_bucket_arn" {
  type = string
}

variable "checkpoint_bucket_arn" {
  type = string
}

variable "athena_results_bucket_arn" {
  type = string
}

variable "dynamodb_table_arn" {
  type = string
}

variable "glue_database_name" {
  type = string
}

variable "emr_application_arn" {
  type = string
}

# ---------- EMR Serverless Execution Role ----------
resource "aws_iam_role" "emr_execution" {
  name = "${var.prefix}-emr-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "emr-serverless.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = var.account_id
          }
        }
      }
    ]
  })
}

# S3 access for EMR (lakehouse buckets)
resource "aws_iam_role_policy" "emr_s3" {
  name = "s3-lakehouse-access"
  role = aws_iam_role.emr_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadWriteLakehouse"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          var.raw_bucket_arn,
          "${var.raw_bucket_arn}/*",
          var.processed_bucket_arn,
          "${var.processed_bucket_arn}/*",
          var.checkpoint_bucket_arn,
          "${var.checkpoint_bucket_arn}/*"
        ]
      }
    ]
  })
}

# Kinesis read access for EMR
resource "aws_iam_role_policy" "emr_kinesis" {
  name = "kinesis-read-access"
  role = aws_iam_role.emr_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadKinesis"
        Effect = "Allow"
        Action = [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:DescribeStream",
          "kinesis:DescribeStreamSummary",
          "kinesis:ListShards",
          "kinesis:SubscribeToShard"
        ]
        Resource = var.kinesis_stream_arn
      }
    ]
  })
}

# DynamoDB write access for EMR (alerts)
resource "aws_iam_role_policy" "emr_dynamodb" {
  name = "dynamodb-alerts-access"
  role = aws_iam_role.emr_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "WriteAlerts"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          var.dynamodb_table_arn,
          "${var.dynamodb_table_arn}/index/*"
        ]
      }
    ]
  })
}

# Glue catalog access for EMR (Iceberg)
resource "aws_iam_role_policy" "emr_glue" {
  name = "glue-catalog-access"
  role = aws_iam_role.emr_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GlueCatalog"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetTables",
          "glue:CreateTable",
          "glue:UpdateTable",
          "glue:DeleteTable",
          "glue:GetPartitions",
          "glue:BatchCreatePartition",
          "glue:BatchDeletePartition"
        ]
        Resource = [
          "arn:aws:glue:${var.region}:${var.account_id}:catalog",
          "arn:aws:glue:${var.region}:${var.account_id}:database/${var.glue_database_name}",
          "arn:aws:glue:${var.region}:${var.account_id}:table/${var.glue_database_name}/*"
        ]
      }
    ]
  })
}

# CloudWatch metrics for EMR
resource "aws_iam_role_policy" "emr_cloudwatch" {
  name = "cloudwatch-metrics"
  role = aws_iam_role.emr_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "PublishMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "CryptoPulse"
          }
        }
      },
      {
        Sid    = "EmrLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws/emr-serverless/*"
      }
    ]
  })
}

# ---------- Kinesis Producer Role ----------
resource "aws_iam_role" "producer" {
  name = "${var.prefix}-producer"

  # Allow EC2, ECS, or Lambda to assume this role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = [
            "ec2.amazonaws.com",
            "ecs-tasks.amazonaws.com",
            "lambda.amazonaws.com"
          ]
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "producer_kinesis" {
  name = "kinesis-write-access"
  role = aws_iam_role.producer.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "WriteKinesis"
        Effect = "Allow"
        Action = [
          "kinesis:PutRecord",
          "kinesis:PutRecords",
          "kinesis:DescribeStream"
        ]
        Resource = var.kinesis_stream_arn
      }
    ]
  })
}

# ---------- Lambda API Role ----------
resource "aws_iam_role" "lambda_api" {
  name = "${var.prefix}-lambda-api"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "dynamodb-read-access"
  role = aws_iam_role.lambda_api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadAlerts"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          var.dynamodb_table_arn,
          "${var.dynamodb_table_arn}/index/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ---------- Outputs ----------
output "emr_execution_role_arn" {
  value = aws_iam_role.emr_execution.arn
}

output "producer_role_arn" {
  value = aws_iam_role.producer.arn
}

output "lambda_api_role_arn" {
  value = aws_iam_role.lambda_api.arn
}
