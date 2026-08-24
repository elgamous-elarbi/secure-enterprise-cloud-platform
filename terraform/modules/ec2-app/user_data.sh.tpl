#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/user-data.log) 2>&1

echo "=== Mise a jour systeme (Amazon Linux 2023) ==="
dnf update -y
dnf install -y docker jq openssl

echo "=== Demarrage Docker ==="
systemctl enable docker
systemctl start docker

echo "=== Installation Docker Compose (plugin) ==="
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "=== Login ECR ==="
aws ecr get-login-password --region ${aws_region} | docker login --username AWS --password-stdin ${ecr_repository_url}

echo "=== Recuperation credentials RDS depuis Secrets Manager ==="
SECRET_JSON=$(aws secretsmanager get-secret-value --region ${aws_region} --secret-id ${db_secret_arn} --query SecretString --output text)
DB_USER=$(echo "$SECRET_JSON" | jq -r '.username')
DB_PASSWORD=$(echo "$SECRET_JSON" | jq -r '.password')
DB_NAME=$(echo "$SECRET_JSON" | jq -r '.dbname // "${project_name}"')
DB_PORT=$(echo "$SECRET_JSON" | jq -r '.port // "5432"')

echo "=== Recuperation cle Flask depuis Secrets Manager ==="
FLASK_SECRET_JSON=$(aws secretsmanager get-secret-value --region ${aws_region} --secret-id ${flask_secret_arn} --query SecretString --output text)
FLASK_SECRET_KEY=$(echo "$FLASK_SECRET_JSON" | jq -r '.flask_secret_key')

mkdir -p /opt/app
cat > /opt/app/.env <<EOF
DB_HOST=${db_address}
DB_PORT=$${DB_PORT}
DB_NAME=$${DB_NAME}
DB_USER=$${DB_USER}
DB_PASSWORD=$${DB_PASSWORD}
FLASK_SECRET_KEY=$${FLASK_SECRET_KEY}
APP_ENV=production
LOG_LEVEL=INFO
EOF
chmod 600 /opt/app/.env

echo "=== Certificat auto-signe (pas de domaine) ==="
mkdir -p /opt/app/nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /opt/app/nginx/certs/selfsigned.key \
  -out /opt/app/nginx/certs/selfsigned.crt \
  -subj "/C=MA/ST=Tanger/L=Tanger/O=${project_name}/CN=app.local"

cat > /opt/app/nginx/nginx.conf <<EOF
events {}
http {
    server {
        listen 80;
        return 301 https://\$host\$request_uri;
    }
    server {
        listen 443 ssl;
        ssl_certificate     /etc/nginx/certs/selfsigned.crt;
        ssl_certificate_key /etc/nginx/certs/selfsigned.key;

        location / {
            proxy_pass http://app:5000;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
EOF

cat > /opt/app/docker-compose.yml <<EOF
services:
  app:
    image: ${ecr_repository_url}:latest
    env_file: .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/health/live')"]
      interval: 30s
      timeout: 5s
      retries: 3

  nginx:
    image: nginx:1.27-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - app
EOF

echo "=== Lancement des conteneurs ==="
cd /opt/app
docker compose up -d

echo "=== user-data termine ==="