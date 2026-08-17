output "ec2_role_arn" {
  description = "ARN du rôle IAM attaché à l'instance EC2"
  value       = aws_iam_role.ec2.arn
}

output "ec2_instance_profile_name" {
  description = "Nom de l'instance profile à référencer dans le module ec2"
  value       = aws_iam_instance_profile.ec2.name
}

output "github_actions_role_arn" {
  description = "ARN du rôle OIDC à utiliser dans le workflow GitHub Actions (aws-actions/configure-aws-credentials)"
  value       = aws_iam_role.github_actions.arn
}

output "github_oidc_provider_arn" {
  description = "ARN du provider OIDC GitHub"
  value       = aws_iam_openid_connect_provider.github.arn
}
