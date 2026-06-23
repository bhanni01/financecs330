# Tells Terraform which "providers" (cloud plugins) it needs and their versions.
# A provider is the plugin that knows how to talk to a specific cloud's API.
terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure the AWS provider: which region to build everything in.
provider "aws" {
  region = "us-east-1"
}
