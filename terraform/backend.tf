# Terraform Backend Configuration
# Uncomment and configure for remote state storage

# AWS S3 Backend
# terraform {
#   backend "s3" {
#     bucket         = "apex-os-terraform-state"
#     key            = "infrastructure/terraform.tfstate"
#     region         = "us-east-1"
#     encrypt        = true
#     dynamodb_table = "apex-os-terraform-locks"
#   }
# }

# Azure Backend
# terraform {
#   backend "azurerm" {
#     resource_group_name  = "apex-os-terraform-rg"
#     storage_account_name = "apexostfstate"
#     container_name       = "tfstate"
#     key                  = "infrastructure.terraform.tfstate"
#   }
# }

# GCP Backend
# terraform {
#   backend "gcs" {
#     bucket = "apex-os-terraform-state"
#     prefix = "infrastructure"
#   }
# }

# Local Backend (default for development)
terraform {
  backend "local" {
    path = "./terraform.tfstate"
  }
}
