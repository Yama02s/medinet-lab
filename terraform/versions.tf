terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# Las credenciales NO van en el codigo: se leen de las variables de entorno
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY y AWS_SESSION_TOKEN (Learner Lab).
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.project
      Module    = "LAB"
      ManagedBy = "terraform"
    }
  }
}
