#!/bin/bash
# Runs once when each EC2 instance boots (Amazon Linux 2023).
set -e

# ---- Install Docker ----
dnf update -y
dnf install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# ---- Pull and run the app container ----
docker pull ${docker_image}

docker run -d \
  --name app \
  --restart unless-stopped \
  -p ${app_port}:${app_port} \
  -e DB_HOST="${db_host}" \
  -e DB_PORT="${db_port}" \
  -e DB_NAME="${db_name}" \
  -e DB_USER="${db_user}" \
  -e DB_PASSWORD="${db_password}" \
  ${docker_image}
