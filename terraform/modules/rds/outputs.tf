output "db_instance_endpoint" {
  description = "Endpoint de connexion RDS (host:port)"
  value       = aws_db_instance.this.endpoint
}

output "db_instance_address" {
  description = "Adresse (host seul) de l'instance RDS"
  value       = aws_db_instance.this.address
}

output "secret_arn" {
  description = "ARN du secret Secrets Manager contenant les identifiants RDS"
  value       = aws_secretsmanager_secret.db.arn
}

output "security_group_id" {
  description = "ID du Security Group RDS (à référencer pour autoriser l'accès depuis EKS)"
  value       = aws_security_group.rds.id
}