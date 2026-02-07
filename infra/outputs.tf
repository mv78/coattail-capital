output "kinesis_stream_arn" {
  description = "ARN of the Kinesis data stream"
  value       = module.kinesis.stream_arn
}

output "kinesis_stream_name" {
  description = "Name of the Kinesis data stream"
  value       = module.kinesis.stream_name
}

output "raw_bucket" {
  description = "S3 bucket for raw data landing zone"
  value       = module.s3_lakehouse.raw_bucket_id
}

output "processed_bucket" {
  description = "S3 bucket for Iceberg tables"
  value       = module.s3_lakehouse.processed_bucket_id
}

output "checkpoint_bucket" {
  description = "S3 bucket for Spark checkpoints"
  value       = module.s3_lakehouse.checkpoint_bucket_id
}

output "emr_application_id" {
  description = "EMR Serverless application ID"
  value       = module.emr_serverless.application_id
}

output "emr_execution_role_arn" {
  description = "IAM role ARN for EMR Serverless job execution"
  value       = module.iam.emr_execution_role_arn
}

output "dynamodb_alerts_table" {
  description = "DynamoDB alerts table name"
  value       = aws_dynamodb_table.alerts.name
}

output "glue_database" {
  description = "Glue Data Catalog database name"
  value       = module.glue.database_name
}

output "cloudwatch_dashboard_url" {
  description = "URL to CloudWatch dashboard"
  value       = module.monitoring.dashboard_url
}

output "step_functions_arn" {
  description = "ARN of the batch workflow state machine"
  value       = module.step_functions.state_machine_arn
}

output "step_functions_name" {
  description = "Name of the batch workflow state machine"
  value       = module.step_functions.state_machine_name
}

output "analyst_role_arn" {
  description = "ARN of the analyst role for Athena queries"
  value       = module.lake_formation.analyst_role_arn
}
