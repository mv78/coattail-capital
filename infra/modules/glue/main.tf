variable "prefix" {
  type = string
}

variable "lakehouse_bucket_id" {
  type = string
}

resource "aws_glue_catalog_database" "crypto_pulse" {
  name        = replace("${var.prefix}_lakehouse", "-", "_")
  description = "Crypto Pulse Analytics Iceberg lakehouse catalog"
}

# Note: Iceberg tables are created by Spark at runtime via Glue catalog.
# The database just needs to exist. Table schemas are managed by the
# PySpark jobs using CREATE TABLE IF NOT EXISTS statements.
#
# This is the recommended pattern for Iceberg + Glue:
# Spark creates/manages table metadata, Glue stores the catalog.

output "database_name" {
  value = aws_glue_catalog_database.crypto_pulse.name
}

output "database_arn" {
  value = aws_glue_catalog_database.crypto_pulse.arn
}
