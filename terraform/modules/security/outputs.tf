output "app_security_group_id" {
  description = "ID du security group applicatif (pods EKS)"
  value       = aws_security_group.app.id
}

output "alb_security_group_id" {
  description = "ID du security group de l'ALB public"
  value       = aws_security_group.alb.id
}