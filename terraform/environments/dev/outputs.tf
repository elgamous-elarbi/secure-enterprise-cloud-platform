output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "private_data_subnet_ids" {
  value = module.network.private_data_subnet_ids
}

output "ec2_role_arn" {
  description = "ARN du rôle IAM à attacher à l'instance EC2 (module ec2, à venir)"
  value       = module.iam.ec2_role_arn
}

output "ec2_instance_profile_name" {
  description = "Instance profile à référencer dans le module ec2 (aws_instance.iam_instance_profile)"
  value       = module.iam.ec2_instance_profile_name
}

output "github_actions_role_arn" {
  description = "ARN à mettre dans le workflow GitHub Actions (aws-actions/configure-aws-credentials → role-to-assume)"
  value       = module.iam.github_actions_role_arn
}

output "github_oidc_provider_arn" {
  description = "ARN du provider OIDC GitHub (utile si vous ajoutez d'autres rôles fédérés plus tard)"
  value       = module.iam.github_oidc_provider_arn
}
output "ecr_repository_url" {
  description = "URL du dépôt ECR pour l'app DGSSI"
  value       = module.ecr.repository_url
}
output "private_app_subnet_ids" {
  description = "IDs des subnets privés app"
  value       = module.network.private_app_subnet_ids
}