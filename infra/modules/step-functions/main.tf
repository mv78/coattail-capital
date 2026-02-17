variable "prefix" {
  type = string
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "emr_application_id" {
  type = string
}

variable "emr_execution_role_arn" {
  type = string
}

variable "raw_bucket" {
  type = string
}

variable "processed_bucket" {
  type = string
}

variable "sns_topic_arn" {
  type = string
}

variable "glue_database" {
  type = string
}

# ---------- IAM Role for Step Functions ----------
resource "aws_iam_role" "step_functions" {
  name = "${var.prefix}-step-functions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "step_functions_emr" {
  name = "emr-serverless-access"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EMRServerless"
        Effect = "Allow"
        Action = [
          "emr-serverless:StartJobRun",
          "emr-serverless:GetJobRun",
          "emr-serverless:CancelJobRun"
        ]
        Resource = "arn:aws:emr-serverless:${var.region}:${var.account_id}:/applications/${var.emr_application_id}/*"
      },
      {
        Sid      = "PassRole"
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = var.emr_execution_role_arn
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "emr-serverless.amazonaws.com"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "step_functions_lambda" {
  name = "lambda-invoke"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeLambda"
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = [
          aws_lambda_function.historical_loader.arn,
          aws_lambda_function.quality_validator.arn,
          aws_lambda_function.catalog_updater.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "step_functions_sns" {
  name = "sns-publish"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "PublishSNS"
        Effect   = "Allow"
        Action   = "sns:Publish"
        Resource = var.sns_topic_arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "step_functions_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

# ---------- Lambda: Historical Loader ----------
resource "aws_iam_role" "historical_loader" {
  name = "${var.prefix}-historical-loader"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "historical_loader_basic" {
  role       = aws_iam_role.historical_loader.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "historical_loader_s3" {
  name = "s3-write"
  role = aws_iam_role.historical_loader.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject"]
      Resource = "arn:aws:s3:::${var.raw_bucket}/*"
    }]
  })
}

resource "aws_lambda_function" "historical_loader" {
  function_name = "${var.prefix}-historical-loader"
  runtime       = "python3.11"
  handler       = "index.handler"
  role          = aws_iam_role.historical_loader.arn
  timeout       = 300
  memory_size   = 512

  filename         = "${path.module}/lambda_placeholder.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_placeholder.zip")

  environment {
    variables = {
      RAW_BUCKET = var.raw_bucket
      SYMBOLS    = "BTCUSDT,ETHUSDT,SOLUSDT"
    }
  }

  tags = { Component = "batch-orchestration" }
}

# ---------- Lambda: Quality Validator ----------
resource "aws_iam_role" "quality_validator" {
  name = "${var.prefix}-quality-validator"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "quality_validator_basic" {
  role       = aws_iam_role.quality_validator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "quality_validator_athena" {
  name = "athena-query"
  role = aws_iam_role.quality_validator.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "arn:aws:s3:::${var.processed_bucket}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["glue:GetTable", "glue:GetPartitions"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "quality_validator" {
  function_name = "${var.prefix}-quality-validator"
  runtime       = "python3.11"
  handler       = "index.handler"
  role          = aws_iam_role.quality_validator.arn
  timeout       = 120
  memory_size   = 256

  filename         = "${path.module}/lambda_placeholder.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_placeholder.zip")

  environment {
    variables = {
      GLUE_DATABASE    = var.glue_database
      PROCESSED_BUCKET = var.processed_bucket
    }
  }

  tags = { Component = "batch-orchestration" }
}

# ---------- Lambda: Catalog Updater ----------
resource "aws_iam_role" "catalog_updater" {
  name = "${var.prefix}-catalog-updater"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "catalog_updater_basic" {
  role       = aws_iam_role.catalog_updater.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "catalog_updater_glue" {
  name = "glue-catalog"
  role = aws_iam_role.catalog_updater.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["glue:UpdateTable", "glue:GetTable", "glue:BatchCreatePartition"]
      Resource = "*"
    }]
  })
}

resource "aws_lambda_function" "catalog_updater" {
  function_name = "${var.prefix}-catalog-updater"
  runtime       = "python3.11"
  handler       = "index.handler"
  role          = aws_iam_role.catalog_updater.arn
  timeout       = 60
  memory_size   = 128

  filename         = "${path.module}/lambda_placeholder.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_placeholder.zip")

  environment {
    variables = {
      GLUE_DATABASE = var.glue_database
    }
  }

  tags = { Component = "batch-orchestration" }
}

# ---------- Step Functions State Machine ----------
resource "aws_sfn_state_machine" "batch_workflow" {
  name     = "${var.prefix}-batch-workflow"
  role_arn = aws_iam_role.step_functions.arn

  definition = jsonencode({
    Comment = "Crypto Pulse Analytics - Daily Batch Processing Workflow"
    StartAt = "HistoricalLoad"
    States = {
      HistoricalLoad = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.historical_loader.arn
          Payload = {
            "date.$"    = "$.date"
            "symbols.$" = "$.symbols"
          }
        }
        ResultPath = "$.loadResult"
        Next       = "SubmitSparkJob"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "SendFailureAlert"
          ResultPath  = "$.error"
        }]
      }

      SubmitSparkJob = {
        Type     = "Task"
        Resource = "arn:aws:states:::emr-serverless:startJobRun.sync"
        Parameters = {
          ApplicationId    = var.emr_application_id
          ExecutionRoleArn = var.emr_execution_role_arn
          JobDriver = {
            SparkSubmit = {
              EntryPoint            = "s3://${var.processed_bucket}/jobs/batch/reprocess_anomalies.py"
              SparkSubmitParameters = "--conf spark.jars.packages=org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.4.2"
            }
          }
        }
        ResultPath = "$.sparkResult"
        Next       = "RunQualityChecks"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "SendFailureAlert"
          ResultPath  = "$.error"
        }]
      }

      RunQualityChecks = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.quality_validator.arn
          Payload = {
            "date.$" = "$.date"
          }
        }
        ResultPath = "$.qualityResult"
        Next       = "CheckQualityPassed"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "SendFailureAlert"
          ResultPath  = "$.error"
        }]
      }

      CheckQualityPassed = {
        Type = "Choice"
        Choices = [{
          Variable      = "$.qualityResult.Payload.passed"
          BooleanEquals = true
          Next          = "UpdateCatalog"
        }]
        Default = "SendQualityFailureAlert"
      }

      UpdateCatalog = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.catalog_updater.arn
          Payload = {
            "date.$" = "$.date"
          }
        }
        ResultPath = "$.catalogResult"
        Next       = "PublishSuccessMetrics"
      }

      PublishSuccessMetrics = {
        Type     = "Task"
        Resource = "arn:aws:states:::cloudwatch:putMetricData"
        Parameters = {
          Namespace = "CryptoPulse/Batch"
          MetricData = [{
            MetricName = "BatchSuccess"
            Value      = 1
            Unit       = "Count"
          }]
        }
        End = true
      }

      SendFailureAlert = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn    = var.sns_topic_arn
          Subject     = "Crypto Pulse Batch Job Failed"
          "Message.$" = "States.Format('Batch job failed: {}', $.error)"
        }
        Next = "PublishFailureMetrics"
      }

      SendQualityFailureAlert = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn    = var.sns_topic_arn
          Subject     = "Crypto Pulse Quality Check Failed"
          "Message.$" = "States.Format('Quality check failed: {}', $.qualityResult)"
        }
        Next = "PublishFailureMetrics"
      }

      PublishFailureMetrics = {
        Type     = "Task"
        Resource = "arn:aws:states:::cloudwatch:putMetricData"
        Parameters = {
          Namespace = "CryptoPulse/Batch"
          MetricData = [{
            MetricName = "BatchFailure"
            Value      = 1
            Unit       = "Count"
          }]
        }
        End = true
      }
    }
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ERROR"
  }

  tags = { Component = "batch-orchestration" }
}

resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/vendedlogs/states/${var.prefix}-batch-workflow"
  retention_in_days = 14
}

# ---------- EventBridge Schedule ----------
resource "aws_scheduler_schedule" "daily_batch" {
  name       = "${var.prefix}-daily-batch"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "cron(0 2 * * ? *)" # Daily at 02:00 UTC

  target {
    arn      = aws_sfn_state_machine.batch_workflow.arn
    role_arn = aws_iam_role.eventbridge_scheduler.arn

    input = jsonencode({
      date    = "yesterday"
      symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    })
  }

  state = "DISABLED" # Enable when ready for production
}

resource "aws_iam_role" "eventbridge_scheduler" {
  name = "${var.prefix}-eventbridge-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_scheduler" {
  name = "start-step-functions"
  role = aws_iam_role.eventbridge_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "states:StartExecution"
      Resource = aws_sfn_state_machine.batch_workflow.arn
    }]
  })
}

# ---------- Outputs ----------
output "state_machine_arn" {
  value = aws_sfn_state_machine.batch_workflow.arn
}

output "state_machine_name" {
  value = aws_sfn_state_machine.batch_workflow.name
}
