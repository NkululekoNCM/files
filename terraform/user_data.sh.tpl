#!/bin/bash
# Runs once when each EC2 instance boots (Amazon Linux 2023).
set -e

# ---- Install Docker and the AWS CLI ----
dnf update -y
dnf install -y docker awscli
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# ---- Save a redeploy script the CI/CD pipeline can trigger over SSH ----
# The DB password is fetched from Parameter Store at run time, never
# embedded here - so it never appears in the launch template or the
# EC2 instance metadata that anyone with instance/API access could read.
mkdir -p /opt/app
cat > /opt/app/redeploy.sh << 'REDEPLOY'
#!/bin/bash
set -e

DB_PASSWORD=$(aws ssm get-parameter \
  --name "${db_password_ssm}" \
  --with-decryption \
  --region "${aws_region}" \
  --query "Parameter.Value" \
  --output text)

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
  -e DB_PASSWORD="$DB_PASSWORD" \
  --log-driver=awslogs \
  --log-opt awslogs-region=${aws_region} \
  --log-opt awslogs-group=${log_group} \
  --log-opt awslogs-stream=app-$(TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60"); curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id) \
  ${docker_image}
REDEPLOY
chmod +x /opt/app/redeploy.sh

# ---- Run it once now, at boot ----
bash /opt/app/redeploy.sh
