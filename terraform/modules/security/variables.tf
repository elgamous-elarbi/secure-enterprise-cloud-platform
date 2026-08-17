variable "project_name" {
  description = "Nom du projet, utilise comme prefixe"
  type        = string
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "ID du VPC"
  type        = string
}
variable "vpc_cidr" {
  description = "Bloc CIDR du VPC (pour autoriser le trafic interne)"
  type        = string
}