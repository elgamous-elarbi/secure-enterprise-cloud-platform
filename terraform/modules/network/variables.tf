variable "project_name" {
  description = "Nom du projet, utilisé comme préfixe pour les tags/noms de ressources"
  type        = string
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}

variable "vpc_cidr" {
  description = "Bloc CIDR du VPC"
  type        = string
}

variable "azs" {
  description = "Liste des AZ à utiliser (2 minimum, requis pour RDS Subnet Group / ALB)"
  type        = list(string)
}

variable "tags" {
  description = "Tags communs additionnels"
  type        = map(string)
  default     = {}
}
