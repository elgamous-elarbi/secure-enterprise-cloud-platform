variable "project_name" {
  description = "Nom du projet, utilisé comme préfixe"
  type        = string
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}