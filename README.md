# Week 1 – Project Tracker (Flask + PostgreSQL, Dockerized)

Part of the **Mid-Level Cloud Engineering Project (4 Weeks)**.
Week 1 goal: build a CRUD app, containerize it, connect it to PostgreSQL, and get it ready to push to Docker Hub.

## Scenario
A startup needs a simple internal tool to track projects across teams —
what each project is called, its budget, current status, and deadline.

## Stack
- Python 3.12 / Flask
- PostgreSQL 16
- Docker + Docker Compose
- Gunicorn (production WSGI server inside the container)

## Resource: `projects`
| field       | type                                |
|-------------|--------------------------------------|
| id          | serial pk                           |
| title       | string                              |
| budget      | numeric                             |
| status      | string (`open` / `in-progress` / `completed`) |
| deadline    | date (`YYYY-MM-DD`)                 |
| created_at  | timestamp                           |

## API Endpoints
| Method | Path             | Description         |
|--------|------------------|----------------------|
| GET    | /health          | Health check         |
| GET    | /projects        | List all projects    |
| GET    | /projects/<id>   | Get one project      |
| POST   | /projects        | Create a project     |
| PUT    | /projects/<id>   | Update a project     |
| DELETE | /projects/<id>   | Delete a project     |

## Run locally with Docker Compose (recommended)
This spins up the app **and** a Postgres database together:

```bash
docker compose up --build
```

App will be available at `http://localhost:5000`.

Test it:
```bash
curl http://localhost:5000/health

curl -X POST http://localhost:5000/projects \
  -H "Content-Type: application/json" \
  -d '{"title": "Website Redesign", "budget": 15000, "status": "open", "deadline": "2026-12-01"}'

curl http://localhost:5000/projects
```

Stop and remove containers:
```bash
docker compose down
```

Stop and also wipe the database volume:
```bash
docker compose down -v
```

## Run the app container standalone (against an external Postgres)
```bash
docker build -t week1-crud-app .

docker run -d -p 5000:5000 \
  -e DB_HOST=<your-db-host> \
  -e DB_PORT=5432 \
  -e DB_NAME=appdb \
  -e DB_USER=appuser \
  -e DB_PASSWORD=apppassword \
  --name week1_app \
  week1-crud-app
```

## Push image to Docker Hub
```bash
docker login
docker tag week1-crud-app <your-dockerhub-username>/week1-crud-app:latest
docker push <your-dockerhub-username>/week1-crud-app:latest
```

## Project Structure
```
.
├── app.py                # Flask CRUD application
├── requirements.txt    
├── Dockerfile             # App container image definition
├── docker-compose.yml     # Local app + Postgres stack
├── .env.example           # Sample environment variables
├── .dockerignore
├── .gitignore
└── README.md
```

## Notes for Week 2 (Terraform / AWS)
# Week 2 – Infrastructure as Code (Terraform)

Part of the **Mid-Level Cloud Engineering Project (4 Weeks)**.
Week 2 goal: provision the AWS infrastructure that the Week 1 Project Tracker app runs on, entirely through Terraform.

## What this builds

A production-style 3-tier AWS environment inside a custom VPC:

- **Networking:** 1 VPC, 2 public subnets, 2 private subnets (across 2 Availability Zones), 1 Internet Gateway, 1 NAT Gateway, public + private route tables
- **Compute:** Application Load Balancer (public subnets) → Auto Scaling Group of EC2 instances (private subnets), running the Week 1 app container pulled from Docker Hub
- **Data:** RDS PostgreSQL instance in the private subnets, reachable only from the app instances
- **Security:** three-tier security groups (ALB → App → DB, each locked to only the layer next to it), IAM role with AWS Systems Manager access instead of SSH keys
- **Scaling:** CloudWatch alarms that scale the Auto Scaling Group up at 70% CPU and down at 30% CPU

See `architecture-diagram.svg` for a visual of how these pieces connect.
<img width="792" height="581" alt="Project Diagram3 drawio" src="https://github.com/user-attachments/assets/e8afa54a-0ff0-49cd-9fff-8ded8ff8b81a" />


## Files

| File | Purpose |
|---|---|
| `main.tf` | All AWS resources: VPC, subnets, gateways, security groups, RDS, ALB, launch template, ASG, scaling policies |
| `variables.tf` | Input variables with sensible defaults (region, CIDR blocks, instance sizes, etc.) |
| `outputs.tf` | Values printed after `apply` — ALB DNS name, RDS endpoint, VPC ID, etc. |
| `terraform.tfvars.example` | Template for your own variable values — copy to `terraform.tfvars` and fill in |
| `user_data.sh.tpl` | Script each EC2 instance runs on boot: installs Docker, pulls the app image, starts the container |
| `.gitignore` | Keeps `terraform.tfvars`, state files, and the `.terraform/` cache out of GitHub |

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) installed
- [AWS CLI](https://aws.amazon.com/cli/) installed and configured (`aws configure`) with valid credentials
- An AWS account (Free Tier eligible sizes are used throughout, but the NAT Gateway and ALB are **not** Free Tier — see Cost notes below)

## How to deploy

```bash
# 1. Copy the example vars file and fill in your own values
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: set docker_image to your Docker Hub image, and a db_password
# (avoid the characters / @ " and spaces - AWS RDS rejects them)

# 2. Initialize Terraform (downloads the AWS provider)
terraform init

# 3. Preview what will be created - nothing is built yet
terraform plan

# 4. Build it for real
terraform apply
# type "yes" when prompted
```

After `apply` finishes, Terraform prints the outputs, including the load balancer's public address:

```
alb_dns_name = "week1-crud-app-alb-xxxxxxxxxx.us-east-1.elb.amazonaws.com"
```

Open that URL in a browser (`http://`, not `https://`) to reach the app. It can take a couple of minutes after `apply` finishes for the EC2 instances to finish booting, installing Docker, and pulling the image.

## How to tear it down

```bash
terraform destroy
# type "yes" when prompted
```

**Run this after you're done testing or taking screenshots.** The NAT Gateway and Application Load Balancer bill by the hour even when idle — leaving them running unnecessarily costs money for no benefit during a learning project.

## Security decisions

- App and database instances live in **private subnets** with no direct internet route — only reachable through the ALB (app) or from the app instances (database)
- Security groups are scoped tightly: the database only accepts traffic from the app security group, not from any IP range
- EC2 instances use an **IAM instance role with AWS Systems Manager** for remote access instead of SSH key pairs, so no port 22 is open anywhere
- RDS storage is encrypted at rest
- No credentials are hardcoded in `main.tf` — the database password is supplied via `terraform.tfvars`, which is gitignored and never committed

## Notes for Week 3 (CI/CD)

- The Auto Scaling Group's launch template already knows how to pull and run `var.docker_image` on boot, so a CI/CD pipeline just needs to build and push a new image to Docker Hub, then trigger an instance refresh on the ASG (or replace instances) to roll out the update.

