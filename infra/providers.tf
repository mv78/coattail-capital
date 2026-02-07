terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "coattail-capital"
      Environment = var.environment
      ManagedBy   = "terraform"
      CostCenter  = "portfolio"
      Owners      = "mike-frank"
    }
  }
}
