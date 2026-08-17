terraform {
  required_version = ">= 1.6"

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

  backend "s3" {
    bucket         = "secip-terraform-state-523842384893"
    key            = "dev/terraform.tfstate"
    region         = "eu-north-1"
    dynamodb_table = "secip-terraform-locks"
    encrypt        = true
  }
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
module "ecr" {
  source = "../../modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}
module "iam" {
  source = "../../modules/iam"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region

 ecr_repository_arns = [module.ecr.repository_arn]

  github_org    = var.github_org
  github_repo   = var.github_repo
  github_branch = var.github_branch
}
module "rds" {
  source = "../../modules/rds"

  project_name = var.project_name
  environment  = var.environment

  vpc_id                   = module.network.vpc_id
  private_data_subnet_ids  = module.network.private_data_subnet_ids

  # Vide pour l'instant : le module security/eks n'existe pas encore.
  # Une fois créé, passer le SG des pods EKS ici pour autoriser l'accès.
  allowed_security_group_ids = []
}