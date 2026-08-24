variable "project_name" {
  description = "Nom du projet (prefixe des ressources)"
  type        = string
}

variable "environment" {
  description = "Nom de l'environnement (dev, prod...)"
  type        = string
}

variable "instance_type" {
  description = "Type d'instance EC2"
  type        = string
  default     = "t3.micro"
}

variable "public_subnet_id" {
  description = "ID du subnet public où déployer l'instance"
  type        = string
}

variable "app_security_group_id" {
  description = "ID du security group applicatif existant"
  type        = string
}

variable "instance_profile_name" {
  description = "Nom de l'instance profile IAM"
  type        = string
}

variable "key_name" {
  description = "Nom de la keypair EC2 (optionnel, SSM suffit)"
  type        = string
  default     = null
}

variable "ecr_repository_url" {
  description = "URL du dépôt ECR contenant l'image de l'app"
  type        = string
}

variable "db_secret_arn" {
  description = "ARN du secret Secrets Manager contenant les identifiants RDS"
  type        = string
}

variable "db_address" {
  description = "Adresse (host) de l'instance RDS"
  type        = string
}
variable "flask_secret_arn" {
  description = "ARN du secret Secrets Manager contenant la clé Flask"
  type        = string
}