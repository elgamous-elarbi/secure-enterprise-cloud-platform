variable "aws_region" {
  description = "Région AWS cible"
  type        = string
  default     = "eu-north-1"
}

variable "project_name" {
  type    = string
  default = "secip"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "azs" {
  description = "2 AZ minimum, requis par les DB Subnet Groups RDS et par un futur ALB"
  type        = list(string)
  default     = ["eu-north-1a", "eu-north-1b"]
}

variable "github_org" {
  description = "Organisation/compte GitHub hébergeant le repo (pour le rôle OIDC)"
  type        = string
  default     = "elgamous-elarbi"
}

variable "github_repo" {
  description = "Nom du repo GitHub contenant le pipeline CI/CD (pour le rôle OIDC)"
  type        = string
  default     = "secure-enterprise-cloud-platform"
}

variable "github_branch" {
  description = "Branche autorisée à assumer le rôle OIDC GitHub Actions"
  type        = string
  default     = "main"
}
