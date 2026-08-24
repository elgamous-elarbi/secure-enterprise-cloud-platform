locals {
  name = "${var.project_name}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.tags
  )

  account_id = data.aws_caller_identity.current.account_id

  # Tant que le module ecr n'existe pas encore, on scope sur tous les repos
  # du compte/région (encore free tier — aucun coût lié au rôle lui-même).
  # Une fois le module ecr créé, passer ses ARNs réels via ecr_repository_arns.
  ecr_resource_arns = length(var.ecr_repository_arns) > 0 ? var.ecr_repository_arns : [
    "arn:aws:ecr:${var.aws_region}:${local.account_id}:repository/*"
  ]
}

data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# Rôle EC2 : accès SSM (pas de clé SSH) + pull ECR uniquement
# ---------------------------------------------------------------------------

resource "aws_iam_role" "ec2" {
  name = "${local.name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

# Accès SSM (Session Manager) — remplace l'accès SSH direct
resource "aws_iam_role_policy_attachment" "ec2_ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Pull ECR uniquement (pas de push depuis l'instance)
resource "aws_iam_role_policy" "ec2_ecr_pull" {
  name = "${local.name}-ec2-ecr-pull"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EcrAuth"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "EcrPull"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = local.ecr_resource_arns
      }
    ]
  })
}

# Lecture des secrets Secrets Manager (RDS + Flask)
resource "aws_iam_role_policy" "ec2_secrets_read" {
  name = "${local.name}-ec2-secrets-read"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "SecretsRead"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = var.secret_arns
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${local.name}-ec2-instance-profile"
  role = aws_iam_role.ec2.name

  # Pas de tags ici : le user terraform-cli n'a pas la permission
  # iam:TagInstanceProfile. Si cette permission est ajoutée côté AWS,
  # tu peux remettre `tags = local.common_tags`.
}

# ---------------------------------------------------------------------------
# OIDC GitHub Actions : le pipeline assume ce rôle sans clé AWS stockée
# dans les secrets GitHub (federated identity)
# ---------------------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = local.common_tags
}
resource "aws_iam_role" "github_actions" {
  name = "${local.name}-github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/${var.github_branch}"
        }
      }
    }]
  })

  tags = local.common_tags
}

# Push ECR + déclenchement du déploiement via SSM Send-Command (pas de clé SSH)
resource "aws_iam_role_policy" "github_actions_deploy" {
  name = "${local.name}-github-actions-deploy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EcrAuth"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "EcrPush"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = local.ecr_resource_arns
      },
      {
        Sid    = "DeployViaSsm"
        Effect = "Allow"
        Action = [
          "ssm:SendCommand",
          "ssm:GetCommandInvocation"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${local.account_id}:document/AWS-RunShellScript",
          "arn:aws:ec2:${var.aws_region}:${local.account_id}:instance/*"
        ]
      }
    ]
  })
}