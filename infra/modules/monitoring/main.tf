variable "prefix" {
  type = string
}

variable "kinesis_stream_name" {
  type = string
}

variable "emr_application_id" {
  type = string
}

variable "dynamodb_table_name" {
  type = string
}

variable "billing_alarm_threshold" {
  type    = number
  default = 25
}

variable "alarm_email" {
  type    = string
  default = ""
}

# ---------- SNS Topic for Alarms ----------
resource "aws_sns_topic" "alarms" {
  name = "${var.prefix}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# ---------- Billing Alarm ----------
resource "aws_cloudwatch_metric_alarm" "billing" {
  alarm_name          = "${var.prefix}-billing-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600 # 6 hours
  statistic           = "Maximum"
  threshold           = var.billing_alarm_threshold
  alarm_description   = "Billing alarm: estimated charges exceed $${var.billing_alarm_threshold}"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    Currency = "USD"
  }

  tags = {
    Component = "cost-control"
  }
}

# ---------- Kinesis Iterator Age Alarm ----------
resource "aws_cloudwatch_metric_alarm" "kinesis_iterator_age" {
  alarm_name          = "${var.prefix}-kinesis-lag"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "GetRecords.IteratorAgeMilliseconds"
  namespace           = "AWS/Kinesis"
  period              = 300
  statistic           = "Maximum"
  threshold           = 300000 # 5 minutes — consumer is falling behind
  alarm_description   = "Kinesis consumer lag exceeds 5 minutes"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    StreamName = var.kinesis_stream_name
  }
}

# ---------- DynamoDB Throttle Alarm ----------
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttle" {
  alarm_name          = "${var.prefix}-dynamodb-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "DynamoDB write throttling detected"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    TableName = var.dynamodb_table_name
  }
}

# ---------- CloudWatch Dashboard ----------
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Kinesis - Incoming Records"
          metrics = [["AWS/Kinesis", "IncomingRecords", "StreamName", var.kinesis_stream_name, { stat = "Sum", period = 60 }]]
          view    = "timeSeries"
          region  = "us-west-2"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Kinesis - Iterator Age (Consumer Lag)"
          metrics = [["AWS/Kinesis", "GetRecords.IteratorAgeMilliseconds", "StreamName", var.kinesis_stream_name, { stat = "Maximum", period = 60 }]]
          view    = "timeSeries"
          region  = "us-west-2"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "DynamoDB - Write Capacity"
          metrics = [["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", var.dynamodb_table_name, { stat = "Sum", period = 60 }]]
          view    = "timeSeries"
          region  = "us-west-2"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title = "Estimated Charges"
          metrics = [["AWS/Billing", "EstimatedCharges", "Currency", "USD", { stat = "Maximum", period = 21600 }]]
          view  = "singleValue"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        properties = {
          title = "Custom - Anomaly Alerts Published"
          metrics = [["CryptoPulse", "AnomalyAlerts", { stat = "Sum", period = 300 }]]
          view  = "timeSeries"
          region = "us-west-2"
        }
      }
    ]
  })
}

# ---------- Outputs ----------
output "dashboard_url" {
  value = "https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "sns_topic_arn" {
  value = aws_sns_topic.alarms.arn
}
