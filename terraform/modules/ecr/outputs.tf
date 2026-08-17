output "repository_url" {
  description = "URL du dépôt ECR (à utiliser pour docker push/pull)"
  value       = aws_ecr_repository.this.repository_url
}

output "repository_arn" {
  description = "ARN du dépôt ECR"
  value       = aws_ecr_repository.this.arn
}