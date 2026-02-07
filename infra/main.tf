data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  prefix     = "${var.project_name}-${var.environment}"
}

# ---------- Kinesis Data Stream ----------
module "kinesis" {
  source = "./modules/kinesis"

  stream_name     = var.kinesis_stream_name
  retention_hours = var.kinesis_retention_hours
  prefix          = local.prefix
}

# ---------- S3 Lakehouse ----------
module "s3_lakehouse" {
  source = "./modules/s3-lakehouse"

  prefix                = local.prefix
  account_id            = local.account_id
  transition_to_ia_days = var.s3_transition_to_ia_days
  expiration_days       = var.s3_expiration_days
}

# ---------- Glue Data Catalog ----------
module "glue" {
  source = "./modules/glue"

  prefix              = local.prefix
  lakehouse_bucket_id = module.s3_lakehouse.processed_bucket_id
}

# ---------- IAM Roles ----------
module "iam" {
  source = "./modules/iam"

  prefix                  = local.prefix
  region                  = local.region
  account_id              = local.account_id
  kinesis_stream_arn      = module.kinesis.stream_arn
  raw_bucket_arn          = module.s3_lakehouse.raw_bucket_arn
  processed_bucket_arn    = module.s3_lakehouse.processed_bucket_arn
  checkpoint_bucket_arn   = module.s3_lakehouse.checkpoint_bucket_arn
  athena_results_bucket_arn = module.s3_lakehouse.athena_results_bucket_arn
  dynamodb_table_arn      = aws_dynamodb_table.alerts.arn
  glue_database_name      = module.glue.database_name
  emr_application_arn     = module.emr_serverless.application_arn
}

# ---------- EMR Serverless ----------
module "emr_serverless" {
  source = "./modules/emr-serverless"

  prefix                 = local.prefix
  max_vcpu               = var.emr_max_vcpu
  max_memory             = var.emr_max_memory_gb
  auto_stop_idle_minutes = var.emr_auto_stop_idle_minutes
}

# ---------- Monitoring ----------
module "monitoring" {
  source = "./modules/monitoring"

  prefix                     = local.prefix
  kinesis_stream_name        = module.kinesis.stream_name
  emr_application_id         = module.emr_serverless.application_id
  billing_alarm_threshold    = var.billing_alarm_threshold_usd
  alarm_email                = var.alarm_email
  dynamodb_table_name        = aws_dynamodb_table.alerts.name
}

# ---------- DynamoDB Alerts Table ----------
resource "aws_dynamodb_table" "alerts" {
  name         = "${local.prefix}-alerts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "alert_id"
  range_key    = "detected_at"

  attribute {
    name = "alert_id"
    type = "S"
  }

  attribute {
    name = "detected_at"
    type = "S"
  }

  attribute {
    name = "alert_type"
    type = "S"
  }

  attribute {
    name = "symbol"
    type = "S"
  }

  global_secondary_index {
    name            = "type-time-index"
    hash_key        = "alert_type"
    range_key       = "detected_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "symbol-time-index"
    hash_key        = "symbol"
    range_key       = "detected_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl_epoch"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = false # Cost savings for portfolio project
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Component = "alerts-store"
  }
}

# ---------- SSM Parameters (Configuration Store) ----------
resource "aws_ssm_parameter" "kinesis_stream_name" {
  name  = "/${local.prefix}/kinesis/stream-name"
  type  = "String"
  value = module.kinesis.stream_name
}

resource "aws_ssm_parameter" "s3_raw_bucket" {
  name  = "/${local.prefix}/s3/raw-bucket"
  type  = "String"
  value = module.s3_lakehouse.raw_bucket_id
}

resource "aws_ssm_parameter" "s3_processed_bucket" {
  name  = "/${local.prefix}/s3/processed-bucket"
  type  = "String"
  value = module.s3_lakehouse.processed_bucket_id
}

resource "aws_ssm_parameter" "s3_checkpoint_bucket" {
  name  = "/${local.prefix}/s3/checkpoint-bucket"
  type  = "String"
  value = module.s3_lakehouse.checkpoint_bucket_id
}

resource "aws_ssm_parameter" "dynamodb_table_name" {
  name  = "/${local.prefix}/dynamodb/alerts-table"
  type  = "String"
  value = aws_dynamodb_table.alerts.name
}

resource "aws_ssm_parameter" "glue_database" {
  name  = "/${local.prefix}/glue/database-name"
  type  = "String"
  value = module.glue.database_name
}

# ---------- Step Functions (Batch Orchestration) ----------
module "step_functions" {
  source = "./modules/step-functions"

  prefix                 = local.prefix
  region                 = local.region
  account_id             = local.account_id
  emr_application_id     = module.emr_serverless.application_id
  emr_execution_role_arn = module.iam.emr_execution_role_arn
  raw_bucket             = module.s3_lakehouse.raw_bucket_id
  processed_bucket       = module.s3_lakehouse.processed_bucket_id
  sns_topic_arn          = module.monitoring.sns_topic_arn
  glue_database          = module.glue.database_name
}

# ---------- Lake Formation (Data Governance) ----------
module "lake_formation" {
  source = "./modules/lake-formation"

  prefix                 = local.prefix
  region                 = local.region
  account_id             = local.account_id
  processed_bucket_arn   = module.s3_lakehouse.processed_bucket_arn
  glue_database_name     = module.glue.database_name
  emr_execution_role_arn = module.iam.emr_execution_role_arn
  lambda_api_role_arn    = module.iam.lambda_api_role_arn
}
