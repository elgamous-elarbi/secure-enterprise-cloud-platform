variable "project_name" {
  description = "Nom du projet, utilisé comme préfixe"
  type        = string
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "ID du VPC où déployer RDS"
  type        = string
}

variable "private_data_subnet_ids" {
  description = "IDs des subnets privés data pour le subnet group RDS"
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security Groups autorisés à se connecter à RDS (ex: SG des pods EKS)"
  type        = list(string)
  default     = []
}

variable "db_name" {
  description = "Nom de la base de données PostgreSQL"
  type        = string
  default     = "dgssi"
}

variable "db_username" {
  description = "Nom d'utilisateur admin PostgreSQL"
  type        = string
  default     = "dgssi_admin"
}

variable "instance_class" {
  description = "Classe d'instance RDS (db.t3.micro = free tier 12 mois)"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Stockage en GB (20 GB = limite free tier)"
  type        = number
  default     = 20
}