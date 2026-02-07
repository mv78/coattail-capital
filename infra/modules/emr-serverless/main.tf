variable "prefix" {
  type = string
}

variable "max_vcpu" {
  type    = number
  default = 4
}

variable "max_memory" {
  type    = string
  default = "8 GB"
}

variable "auto_stop_idle_minutes" {
  type    = number
  default = 15
}

resource "aws_emrserverless_application" "spark" {
  name          = "${var.prefix}-spark"
  release_label = "emr-7.0.0" # Spark 3.4.x runtime
  type          = "SPARK"

  maximum_capacity {
    cpu    = "${var.max_vcpu} vCPU"
    memory = var.max_memory
  }

  auto_start_configuration {
    enabled = true
  }

  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = var.auto_stop_idle_minutes
  }

  # Spark defaults for streaming jobs
  initial_capacity {
    initial_capacity_type = "Driver"
    initial_capacity_config {
      worker_count = 1
      worker_configuration {
        cpu    = "2 vCPU"
        memory = "4 GB"
      }
    }
  }

  tags = {
    Component = "spark-processing"
  }
}

output "application_id" {
  value = aws_emrserverless_application.spark.id
}

output "application_arn" {
  value = aws_emrserverless_application.spark.arn
}
