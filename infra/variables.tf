variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name used in resource naming"
  type        = string
  default     = "coattail"
}

# ---------- Kinesis ----------
variable "kinesis_stream_name" {
  description = "Name of the Kinesis data stream"
  type        = string
  default     = "coattail-trades"
}

variable "kinesis_retention_hours" {
  description = "Kinesis data retention period in hours"
  type        = number
  default     = 24
}

# ---------- EMR Serverless ----------
variable "emr_max_vcpu" {
  description = "Maximum vCPUs for EMR Serverless application (cost control)"
  type        = number
  default     = 4
}

variable "emr_max_memory_gb" {
  description = "Maximum memory in GB for EMR Serverless (cost control)"
  type        = string
  default     = "8 GB"
}

variable "emr_auto_stop_idle_minutes" {
  description = "Minutes of idle time before EMR Serverless auto-stops"
  type        = number
  default     = 15
}

# ---------- DynamoDB ----------
variable "dynamodb_ttl_hours" {
  description = "Hours to retain alerts in DynamoDB before TTL expiry"
  type        = number
  default     = 24
}

# ---------- Monitoring ----------
variable "billing_alarm_threshold_usd" {
  description = "USD threshold for billing alarm"
  type        = number
  default     = 25
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
  default     = ""
}

# ---------- S3 Lifecycle ----------
variable "s3_transition_to_ia_days" {
  description = "Days before transitioning S3 objects to Infrequent Access"
  type        = number
  default     = 30
}

variable "s3_expiration_days" {
  description = "Days before deleting S3 objects"
  type        = number
  default     = 90
}

# ---------- Feature Module System ----------
variable "feature_tier" {
  description = "Feature tier: controls which modules are active and EMR sizing (small/medium/large)"
  type        = string
  default     = "small"

  validation {
    condition     = contains(["small", "medium", "large"], var.feature_tier)
    error_message = "feature_tier must be one of: small, medium, large"
  }
}

variable "enabled_modules" {
  description = "Override map to enable/disable individual modules regardless of tier. Keys are module IDs (e.g., MOD-001), values are booleans."
  type        = map(bool)
  default     = {}
}

variable "symbols" {
  description = "List of trading pair symbols to track"
  type        = list(string)
  default     = ["btcusdt", "ethusdt", "solusdt"]
}

variable "exchange_connectors" {
  description = "List of CEX exchange connectors to activate"
  type        = list(string)
  default     = ["binance-ws", "coinbase-ws"]
}

variable "blockchain_connectors" {
  description = "List of blockchain connectors to activate (Large tier)"
  type        = list(string)
  default     = []
}
