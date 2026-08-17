locals {
  name = "${var.project_name}-${var.environment}"
}

# ---------------------------------------------------------------------------
# Mot de passe généré aléatoirement (jamais écrit en clair dans le code)
# ---------------------------------------------------------------------------

resource "random_password" "db" {
  length  = 24
  special = false # évite les problèmes d'échappement dans les connection strings
}

resource "aws_secretsmanager_secret" "db" {
  name        = "${local.name}-rds-credentials"
  description = "Identifiants PostgreSQL RDS pour l'app DGSSI"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db.result
    dbname   = var.db_name
    engine   = "postgres"
    host     = aws_db_instance.this.address
    port     = 5432
  })
}

# ---------------------------------------------------------------------------
# Subnet group RDS (subnets privés data uniquement)
# ---------------------------------------------------------------------------

resource "aws_db_subnet_group" "this" {
  name       = "${local.name}-rds-subnet-group"
  subnet_ids = var.private_data_subnet_ids

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ---------------------------------------------------------------------------
# Security Group RDS — accès restreint aux SG autorisés uniquement
# ---------------------------------------------------------------------------

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds-sg"
  description = "Autorise uniquement les connexions PostgreSQL depuis les SG applicatifs autorises"
  vpc_id      = var.vpc_id

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_security_group_rule" "rds_ingress" {
  count = length(var.allowed_security_group_ids)

  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = var.allowed_security_group_ids[count.index]
  description               = "PostgreSQL depuis SG applicatif autorise"
}

# Aucune règle egress explicite nécessaire : AWS autorise tout le trafic
# sortant par défaut sur un Security Group, ce qui est suffisant pour RDS.

# ---------------------------------------------------------------------------
# Instance RDS PostgreSQL — configuration free tier
# ---------------------------------------------------------------------------

resource "aws_db_instance" "this" {
  identifier     = "${local.name}-postgres"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  storage_type           = "gp2"
  storage_encrypted      = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Free tier : single-AZ obligatoire (multi-AZ sort du free tier)
  multi_az = false

  # Pas d'accès public : RDS reste dans les subnets privés data uniquement
  publicly_accessible = false

  # Snapshot final au lieu de suppression sèche (sécurité)
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-postgres-final-snapshot"

  backup_retention_period = 7

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}