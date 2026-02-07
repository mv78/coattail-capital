variable "stream_name" {
  type = string
}

variable "retention_hours" {
  type    = number
  default = 24
}

variable "prefix" {
  type = string
}

resource "aws_kinesis_stream" "trades" {
  name             = var.stream_name
  retention_period = var.retention_hours

  stream_mode_details {
    stream_mode = "ON_DEMAND" # Auto-scales, no shard management, cost-effective
  }

  encryption_type = "KMS"
  kms_key_id      = "alias/aws/kinesis" # AWS-managed key (free)

  tags = {
    Component = "ingestion"
  }
}

# Dead letter stream for malformed records
resource "aws_kinesis_stream" "dlq" {
  name             = "${var.stream_name}-dlq"
  retention_period = 48 # Keep DLQ records longer for debugging

  stream_mode_details {
    stream_mode = "ON_DEMAND"
  }

  encryption_type = "KMS"
  kms_key_id      = "alias/aws/kinesis"

  tags = {
    Component = "ingestion-dlq"
  }
}

output "stream_arn" {
  value = aws_kinesis_stream.trades.arn
}

output "stream_name" {
  value = aws_kinesis_stream.trades.name
}

output "dlq_stream_arn" {
  value = aws_kinesis_stream.dlq.arn
}
