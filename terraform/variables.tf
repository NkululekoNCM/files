variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short name used to tag and name resources"
  type        = string
  default     = "week1-crud-app"
}

# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the 2 public subnets (ALB, NAT Gateway)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for the 2 private subnets (app instances, RDS)"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

# ---------------------------------------------------------------------------
# Compute / Auto Scaling
# ---------------------------------------------------------------------------

variable "instance_type" {
  description = "EC2 instance type for the app servers (t3.micro is Free Tier eligible)"
  type        = string
  default     = "t3.micro"
}

variable "docker_image" {
  description = "Docker Hub image (repo:tag) the app instances will pull and run"
  type        = string
  default     = "YOUR_DOCKERHUB_USERNAME/week1-crud-app:latest"
}

variable "app_port" {
  description = "Port the Flask app listens on inside the container"
  type        = number
  default     = 5000
}

variable "asg_min_size" {
  description = "Minimum number of app instances"
  type        = number
  default     = 2
}

variable "asg_max_size" {
  description = "Maximum number of app instances"
  type        = number
  default     = 4
}

variable "asg_desired_capacity" {
  description = "Desired number of app instances at steady state"
  type        = number
  default     = 2
}

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "appdb"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "appuser"
}

variable "db_password" {
  description = "PostgreSQL master password (set this in terraform.tfvars, never commit it)"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class (db.t3.micro is Free Tier eligible)"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS in GB (20 GB is within Free Tier)"
  type        = number
  default     = 20
}
