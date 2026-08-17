output "vpc_id" {
  description = "ID du VPC"
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "Bloc CIDR du VPC"
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "IDs des subnets publics (un par AZ) — pour EC2 / futur ALB"
  value       = aws_subnet.public[*].id
}

output "private_data_subnet_ids" {
  description = "IDs des subnets privés data (un par AZ) — pour RDS Subnet Group"
  value       = aws_subnet.private_data[*].id
}

output "public_route_table_id" {
  description = "ID de la route table publique"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "IDs des route tables privées (un par AZ)"
  value       = aws_route_table.private[*].id
}

output "internet_gateway_id" {
  description = "ID de l'Internet Gateway"
  value       = aws_internet_gateway.this.id
}
output "private_app_subnet_ids" {
  description = "IDs des subnets privés app (destinés aux nodes/pods EKS)"
  value       = aws_subnet.private_app[*].id
}
