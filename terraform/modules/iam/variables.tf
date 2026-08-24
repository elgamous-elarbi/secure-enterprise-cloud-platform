variable "project_name" {
  description = "Nom du projet, utilisé comme préfixe pour les tags/noms de ressources"
  type        = string
}

variable "environment" {
  description = "Environnement (dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "Région AWS cible (pour scoper les ARN dans les policies)"
  type        = string
}

variable "ecr_repository_arns" {
  description = "ARNs des repos ECR sur lesquels donner pull/push (vide = pas encore créés, on scope large sur le compte/région en attendant le module ecr)"
  type        = list(string)
  default     = []
}

variable "github_org" {
  description = "Organisation ou compte GitHub (ex: ton-pseudo)"
  type        = string
}

variable "github_repo" {
  description = "Nom du repo GitHub contenant le pipeline CI/CD"
  type        = string
}

variable "github_branch" {
  description = "Branche autorisée à assumer le rôle OIDC (ex: main)"
  type        = string
  default     = "main"
}

variable "tags" {
  description = "Tags communs additionnels"
  type        = map(string)
  default     = {}
}
variable "secret_arns" {
  description = "ARNs des secrets Secrets Manager que le rôle EC2 peut lire"
  type        = list(string)
  default     = []
}
