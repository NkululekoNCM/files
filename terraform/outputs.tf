output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "alb_dns_name" {
  description = "Public DNS name of the load balancer - open this in a browser to reach the app"
  value       = aws_lb.app.dns_name
}

output "rds_endpoint" {
  description = "Connection endpoint for the RDS PostgreSQL instance"
  value       = aws_db_instance.app_db.address
}

output "asg_name" {
  description = "Name of the Auto Scaling Group"
  value       = aws_autoscaling_group.app.name
}

output "ssh_private_key" {
  description = "Private key for SSH access to app instances. Retrieve with: terraform output -raw ssh_private_key"
  value       = tls_private_key.app.private_key_pem
  sensitive   = true
}

output "cloudwatch_log_group" {
  description = "CloudWatch Logs group receiving application container logs"
  value       = aws_cloudwatch_log_group.app.name
}

output "db_password_parameter" {
  description = "Parameter Store name holding the DB password"
  value       = aws_ssm_parameter.db_password.name
}
