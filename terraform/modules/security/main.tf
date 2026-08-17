locals {
  name = "${var.project_name}-${var.environment}"
}

# ---------------------------------------------------------------------------
# Security Group applicatif — destine aux pods EKS (futurs nodes/pods)
# ---------------------------------------------------------------------------

resource "aws_security_group" "app" {
  name        = "${local.name}-app-sg"
  description = "Security group applicatif pour les pods EKS de l app DGSSI"
  vpc_id      = var.vpc_id

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Autorise le trafic entrant HTTP/HTTPS interne (depuis l ALB, ajoute plus tard)
resource "aws_security_group_rule" "app_ingress_http" {
  type              = "ingress"
  from_port         = 8080
  to_port           = 8080
  protocol          = "tcp"
  security_group_id = aws_security_group.app.id
  cidr_blocks       = [var.vpc_cidr]
  description       = "Trafic HTTP interne depuis le VPC (app Flask, port 8080)"
}

# Aucune regle egress explicite : AWS autorise tout le trafic sortant par
# defaut sur un Security Group. Suffisant tant qu il n y a pas de NAT Gateway
# (les pods restent de toute facon sans acces internet direct).

# ---------------------------------------------------------------------------
# Security Group pour le futur ALB (public, HTTPS uniquement)
# ---------------------------------------------------------------------------

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb-sg"
  description = "Security group pour l Application Load Balancer public"
  vpc_id      = var.vpc_id

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_security_group_rule" "alb_ingress_https" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = aws_security_group.alb.id
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "HTTPS public"
}

resource "aws_security_group_rule" "alb_egress_to_app" {
  type                     = "egress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  security_group_id        = aws_security_group.alb.id
  source_security_group_id = aws_security_group.app.id
  description               = "Vers les pods applicatifs uniquement"
}

resource "aws_security_group_rule" "app_ingress_from_alb" {
  type                     = "ingress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  security_group_id        = aws_security_group.app.id
  source_security_group_id = aws_security_group.alb.id
  description               = "Depuis l ALB uniquement"
}