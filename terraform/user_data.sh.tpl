#!/bin/bash
# Runs once when each EC2 instance boots (Amazon Linux 2023).
set -e

# ---- Install Docker ----
dnf update -y
dnf install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# ---- Save a redeploy script the CI/CD pipeline can trigger over SSH ----
# Keeps DB credentials out of the pipeline itself - the pipeline just SSHes
# in and runs this script by name, it doesn't need to know the connection details.
mkdir -p /opt/app
cat > /opt/app/redeploy.sh << 'REDEPLOY'
#!/bin/bash
set -e
docker pull ${docker_image}
docker stop app || true
docker rm app || true
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
REDEPLOY
chmod +x /opt/app/redeploy.sh

# ---- Run it once now, at boot ----
bash /opt/app/redeploy.sh
