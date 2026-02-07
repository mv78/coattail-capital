# Uncomment after running scripts/bootstrap-state.sh
# terraform {
#   backend "s3" {
#     bucket         = "coattail-capital-tfstate"
#     key            = "infrastructure/terraform.tfstate"
#     region         = "us-west-2"
#     dynamodb_table = "coattail-capital-tflock"
#     encrypt        = true
#   }
# }
