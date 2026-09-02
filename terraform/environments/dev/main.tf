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

  secret_arns = [module.rds.secret_arn, aws_secretsmanager_secret.app.arn]
}
module "rds" {
  source = "../../modules/rds"

  project_name = var.project_name
  environment  = var.environment

  vpc_id                   = module.network.vpc_id
  private_data_subnet_ids  = module.network.private_data_subnet_ids

allowed_security_group_ids = [module.security.app_security_group_id]
}
module "security" {
  source = "../../modules/security"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.network.vpc_id
  vpc_cidr     = module.network.vpc_cidr
}
resource "random_password" "flask_secret" {
  length  = 50
  special = true
}

resource "aws_secretsmanager_secret" "app" {
  name = "secip-dev-app-secret"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id     = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    flask_secret_key = random_password.flask_secret.result
  })
}

module "ec2_app" {
  source = "../../modules/ec2-app"

  project_name           = var.project_name
  environment            = var.environment
  public_subnet_id       = module.network.public_subnet_ids[0]
  app_security_group_id  = module.security.app_security_group_id
  instance_profile_name  = module.iam.ec2_instance_profile_name
  ecr_repository_url     = module.ecr.repository_url
  db_secret_arn          = module.rds.secret_arn
  db_address              = module.rds.db_instance_address
  flask_secret_arn       = aws_secretsmanager_secret.app.arn
}
module "cloudtrail" {
  source = "../../modules/cloudtrail"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
}