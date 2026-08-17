terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # backend "s3" {
  #   bucket         = "secip-terraform-state"       # à créer manuellement avant le 1er apply
  #   key            = "dev/network.tfstate"
  #   region         = "eu-west-1"
  #   dynamodb_table = "secip-terraform-locks"        # verrouillage d'état
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region
}

module "network" {
  source = "../../modules/network"

  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = "10.0.0.0/16"
  azs          = var.azs
}

module "iam" {
  source = "../../modules/iam"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region

  # Vide pour l'instant : le module ecr n'existe pas encore.
  # Une fois créé, passer ses ARNs ici pour restreindre le scope ECR.
  ecr_repository_arns = []

  github_org    = var.github_org
  github_repo   = var.github_repo
  github_branch = var.github_branch
}
