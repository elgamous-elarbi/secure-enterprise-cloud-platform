variable "project_name" {
  description = "Nom du projet (prefixe des ressources)"
  type        = string
}

variable "environment" {
  description = "Nom de l'environnement (dev, prod...)"
  type        = string
}

variable "aws_region" {
  description = "Region AWS"
  type        = string
}