locals {
  name = "${var.project_name}-${var.environment}"
}

# ---------------------------------------------------------------------------
# AMI Amazon Linux 2023 la plus recente, via le parametre SSM public AWS
# (evite de coder un ID d AMI en dur, qui devient obsolete avec le temps)
# ---------------------------------------------------------------------------

data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# ---------------------------------------------------------------------------
# Autorise HTTPS public sur le Security Group applicatif existant
# (reutilise du module security, pas de nouveau SG cree)
# ---------------------------------------------------------------------------

resource "aws_security_group_rule" "app_ingress_https_public" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = var.app_security_group_id
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "HTTPS public direct vers l instance EC2 (pas d ALB)"
}

# ---------------------------------------------------------------------------
# Instance EC2 : Docker + pull de l image ECR + connexion RDS
# ---------------------------------------------------------------------------

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.al2023_ami.value
  instance_type          = var.instance_type
  subnet_id              = var.public_subnet_id
  vpc_security_group_ids = [var.app_security_group_id]
  iam_instance_profile   = var.instance_profile_name
  key_name               = var.key_name

  associate_public_ip_address = true

   user_data = templatefile("${path.module}/user_data.sh.tpl", {
    ecr_repository_url = var.ecr_repository_url
    aws_region         = data.aws_region.current.name
    db_secret_arn      = var.db_secret_arn
    db_address         = var.db_address
    project_name       = var.project_name
    flask_secret_arn   = var.flask_secret_arn
  })

  tags = {
    Name        = "${local.name}-app"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

data "aws_region" "current" {}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = {
    Name = "${local.name}-app-eip"
  }
}