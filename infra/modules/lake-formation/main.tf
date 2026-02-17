variable "prefix" {
  type = string
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "processed_bucket_arn" {
  type = string
}

variable "glue_database_name" {
  type = string
}

variable "emr_execution_role_arn" {
  type = string
}

variable "lambda_api_role_arn" {
  type = string
}

# ---------- Lake Formation Data Lake Settings ----------
# This makes the current account's IAM principals able to manage Lake Formation
resource "aws_lakeformation_data_lake_settings" "main" {
  admins = [
    "arn:aws:iam::${var.account_id}:role/Admin",
    # Add your admin role ARN here
  ]

  # Allow IAM principals to access newly created databases/tables by default
  # This is the "use only IAM access control" setting - we're enabling hybrid mode
  create_database_default_permissions {
    permissions = ["ALL"]
    principal   = "IAM_ALLOWED_PRINCIPALS"
  }

  create_table_default_permissions {
    permissions = ["ALL"]
    principal   = "IAM_ALLOWED_PRINCIPALS"
  }
}

# ---------- Register S3 Location with Lake Formation ----------
resource "aws_lakeformation_resource" "processed_bucket" {
  arn = var.processed_bucket_arn

  # Use Lake Formation's service-linked role for S3 access
  use_service_linked_role = true
}

# ---------- Database Permissions ----------

# EMR Execution Role - Full access to the database
resource "aws_lakeformation_permissions" "emr_database" {
  principal   = var.emr_execution_role_arn
  permissions = ["CREATE_TABLE", "DESCRIBE", "ALTER", "DROP"]

  database {
    name = var.glue_database_name
  }
}

# EMR Execution Role - Full access to all tables
resource "aws_lakeformation_permissions" "emr_tables" {
  principal   = var.emr_execution_role_arn
  permissions = ["ALL"]

  table {
    database_name = var.glue_database_name
    wildcard      = true # All tables in the database
  }
}

# Lambda API Role - Read-only access to specific tables
resource "aws_lakeformation_permissions" "lambda_alerts_table" {
  principal   = var.lambda_api_role_arn
  permissions = ["SELECT", "DESCRIBE"]

  table {
    database_name = var.glue_database_name
    name          = "alerts"
  }

  # This permission only applies if the table exists
  # For initial deployment, you may need to apply this after tables are created
  depends_on = [aws_lakeformation_permissions.emr_tables]
}

resource "aws_lakeformation_permissions" "lambda_volume_table" {
  principal   = var.lambda_api_role_arn
  permissions = ["SELECT", "DESCRIBE"]

  table {
    database_name = var.glue_database_name
    name          = "volume_aggregates"
  }

  depends_on = [aws_lakeformation_permissions.emr_tables]
}

# ---------- Optional: Create an Analyst Role with Limited Access ----------
resource "aws_iam_role" "analyst" {
  name = "${var.prefix}-analyst"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = "arn:aws:iam::${var.account_id}:root"
      }
      Action = "sts:AssumeRole"
      Condition = {
        Bool = {
          "aws:MultiFactorAuthPresent" = "true"
        }
      }
    }]
  })

  tags = { Component = "governance" }
}

# Analyst - Athena query permissions
resource "aws_iam_role_policy" "analyst_athena" {
  name = "athena-access"
  role = aws_iam_role.analyst.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:GetWorkGroup"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartitions"
        ]
        Resource = [
          "arn:aws:glue:${var.region}:${var.account_id}:catalog",
          "arn:aws:glue:${var.region}:${var.account_id}:database/${var.glue_database_name}",
          "arn:aws:glue:${var.region}:${var.account_id}:table/${var.glue_database_name}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [var.processed_bucket_arn, "${var.processed_bucket_arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = "lakeformation:GetDataAccess"
        Resource = "*"
      }
    ]
  })
}

# Analyst - Lake Formation permissions (read-only, exclude raw_payload column)
resource "aws_lakeformation_permissions" "analyst_tables" {
  principal   = aws_iam_role.analyst.arn
  permissions = ["SELECT", "DESCRIBE"]

  table {
    database_name = var.glue_database_name
    wildcard      = true
  }

  # Note: Column-level filtering would be done via LF-Tags or explicit column lists
  # For this portfolio project, we're showing the pattern without implementing column exclusion
}

# ---------- LF-Tags for Classification (Demonstration) ----------
resource "aws_lakeformation_lf_tag" "data_classification" {
  key    = "DataClassification"
  values = ["Public", "Internal", "Confidential"]
}

resource "aws_lakeformation_lf_tag" "data_domain" {
  key    = "DataDomain"
  values = ["Trading", "Alerts", "Metrics", "Raw"]
}

# ---------- Outputs ----------
output "analyst_role_arn" {
  value = aws_iam_role.analyst.arn
}

output "lf_tags" {
  value = {
    data_classification = aws_lakeformation_lf_tag.data_classification.key
    data_domain         = aws_lakeformation_lf_tag.data_domain.key
  }
}
