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

# Week 3 – CI/CD & Deployment Automation

Part of the **Mid-Level Cloud Engineering Project (4 Weeks)**.
Week 3 goal: automatically build, push, and deploy the app whenever code is pushed to `main`, by SSH-ing into the running EC2 instances and restarting the container - as specified in the brief.

## What changed in Week 2's infrastructure to support this

Week 2 originally placed app instances in **private subnets** with no SSH access at all (Systems Manager only). To literally SSH in from GitHub Actions, two things had to change:

1. **App instances moved to public subnets** with a public IP, since GitHub-hosted runners connect over the public internet and can't reach a private-subnet-only instance.
2. **Port 22 opened** on the app security group, from `0.0.0.0/0`.

### The tradeoff, stated plainly

GitHub-hosted runners don't publish a fixed IP range, so there is no way to restrict port 22 to "just GitHub" - it has to accept SSH from anywhere. This is a real reduction in the security posture built in Week 2, done deliberately to satisfy the brief's literal SSH requirement.

**The more locked-down alternative** (worth mentioning in your Week 4 write-up as the production-grade approach): keep app instances in private subnets, add a small **bastion host** in the public subnet with SSH restricted to specific IPs, and have the pipeline SSH into the bastion first, then hop to the private instances from there. That keeps the app tier fully unreachable from the internet while still allowing controlled SSH access. This project uses the simpler direct-SSH version to match the brief exactly, with this tradeoff documented rather than hidden.

## What the pipeline does

On every push to `main` that touches the app code (`app.py`, `requirements.txt`, `Dockerfile`, or `static/`):

1. **Build & push job**
   - Checks out the repo, logs in to Docker Hub, builds the image
   - Pushes it tagged both `:latest` and `:<commit-sha>`

2. **Deploy job** (runs only if the build succeeds)
   - Looks up the public IP of every running instance in the Auto Scaling Group
   - Sets up the SSH private key from a GitHub secret
   - SSHes into each instance and runs `/opt/app/redeploy.sh` - a script written to each instance at boot time (see Week 2's `user_data.sh.tpl`) that pulls the latest image and restarts the container

Keeping the redeploy logic in a script on the instance (rather than inline in the pipeline) means the pipeline never needs to know the database credentials - it just triggers a script that already has them.

## Required GitHub secrets

Go to your GitHub repo -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**:

| Secret name | Value |
|---|---|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | A Docker Hub **access token** (see below) |
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `SSH_PRIVATE_KEY` | The private key Terraform generated (see below) |

### Getting the SSH private key
Terraform generated an SSH key pair for you in Week 2. Retrieve the private key with:
```bash
terraform output -raw ssh_private_key
```
Copy the **entire output**, including the `-----BEGIN ... PRIVATE KEY-----` and `-----END ... PRIVATE KEY-----` lines, and paste it as the `SSH_PRIVATE_KEY` secret exactly as shown - don't add or remove any lines.

### Creating a Docker Hub access token
1. hub.docker.com -> avatar -> Account Settings -> Personal access tokens -> Generate new token
2. Permission: Read & Write. Copy the token immediately - it's shown once.

## Applying the updated infrastructure

Before the pipeline will work, you need to apply the updated Week 2 Terraform (moves instances to public subnets, opens port 22, generates the key pair):

```bash
cd terraform
terraform apply
```

Type `yes` when prompted. This will replace your existing EC2 instances (Terraform will show `~` or `-/+` next to the launch template and ASG) - a short blip in availability while the new instances come up, same as any deployment.

## Trying it out

1. Make sure all 5 secrets are added and `terraform apply` has been run
2. Make a small, visible change to the app (e.g. tweak text in `static/index.html`)
3. Commit and push to `main`
4. GitHub repo -> **Actions** tab - watch the workflow run
5. Once both jobs are green, reload your app's Load Balancer URL - the change should be live

## Files

| File | Purpose |
|---|---|
| `.github/workflows/deploy.yml` | The GitHub Actions pipeline - build, push, SSH deploy |


# Week 4 – Monitoring, Scaling & Security

Part of the **Mid-Level Cloud Engineering Project (4 Weeks)**.

## What's new this week

1. **Secrets moved to AWS Systems Manager Parameter Store.** The database
   password is stored as a `SecureString` parameter (`/week1-crud-app/db_password`)
   instead of being written into the launch template or EC2 user data. Each
   instance fetches it at boot/deploy time via the AWS CLI, using an IAM
   permission scoped to that one parameter only.
2. **CloudWatch Logs.** The app container now ships its logs to CloudWatch
   (`/week1-crud-app/app` log group, 14-day retention) using Docker's built-in
   `awslogs` log driver - no separate logging agent to install or manage.
3. **Least-privilege IAM**, reviewed end to end (see below).
4. **Auto Scaling verification** - the scale-up/scale-down alarms built in
   Week 2 are now tested under real load (see "Testing the scaling policy").

## Security decisions - the full picture

| Requirement | Status | Notes |
|---|---|---|
| IAM roles, no access keys in code | ✅ Done | EC2 instances use an IAM instance role. No AWS credentials are ever written into Terraform files, user data, or the app. |
| Restrict SSH access | ⚠️ **Partial - documented tradeoff** | See below. |
| Encrypt RDS | ✅ Done | `storage_encrypted = true` on the RDS instance. |
| Secrets in Parameter Store | ✅ Done | DB password is a SecureString parameter, fetched at runtime, not embedded anywhere static. |
| Least privilege | ✅ Done | See IAM breakdown below. |

### The SSH tradeoff, stated plainly

Week 3's CI/CD pipeline SSHes into the EC2 instances directly from GitHub-hosted
Actions runners. Those runners don't publish a fixed IP range, so there is no
CIDR block that means "just GitHub" - the app security group's SSH rule has to
stay open to `0.0.0.0/0` for the pipeline to keep working. This is a real,
intentional reduction in security posture, kept because the project brief asks
for a literal SSH-based deploy pipeline.

**The production-grade fix**, worth naming even though it isn't implemented
here: either (a) put the app instances back in private subnets behind a small
bastion host with SSH restricted to specific IPs, and have the pipeline hop
through the bastion, or (b) switch the deploy step from SSH to AWS Systems
Manager `send-command` (which the IAM role already supports as break-glass
access) - eliminating the need for port 22 to be open at all. Both are
reasonable next steps for a real production system; this project keeps the
simpler direct-SSH version to match the brief, with the tradeoff documented
rather than hidden.

### IAM least-privilege breakdown

The EC2 instance role (`week1-crud-app-app-instance-role`) has exactly three
permissions, each scoped as tightly as possible:

| Policy | Scope | Why |
|---|---|---|
| `AmazonSSMManagedInstanceCore` | AWS managed policy | Break-glass console access via Session Manager, independent of the SSH path - useful if the SSH key is ever lost. |
| `ssm:GetParameter` | Only `/week1-crud-app/db_password` (one specific ARN) | Nothing else in Parameter Store is readable, even other parameters in the same account. |
| `logs:CreateLogStream`, `logs:PutLogEvents` | Only the `/week1-crud-app/app` log group | Can't write to or read any other log group. |

No policy uses a wildcard `Resource: "*"`.

## Testing the Auto Scaling policy

The scale-up/scale-down CloudWatch alarms were created in Week 2. To actually
trigger and screenshot a scaling event:

1. Connect to a running instance (Session Manager: EC2 Console → select an
   instance → **Connect** → **Session Manager** tab → **Connect**)
2. Generate CPU load to cross the 70% threshold:
   ```bash
   sudo dnf install -y stress
   stress --cpu 2 --timeout 300
   ```
3. In the AWS Console, go to **CloudWatch → Alarms** and watch
   `week1-crud-app-cpu-high` move from OK to ALARM (takes ~2-4 minutes,
   since the alarm needs 2 consecutive 60-second periods above 70%)
4. Go to **EC2 → Auto Scaling Groups → week1-crud-app-asg → Activity** and
   watch a new instance launch
5. Screenshot both the alarm state and the scaling activity - these are your
   Week 4 deliverables ("screenshot of scaling activity", "CloudWatch alarm
   screenshot")
6. Let the `stress` command finish (or Ctrl+C it) - CPU drops, and after a
   few minutes `week1-crud-app-cpu-low` fires and scales back down

## Viewing logs

AWS Console → **CloudWatch → Log groups → /week1-crud-app/app** → click into
a log stream (one per instance) to see live application output.

## Files changed this week

| File | What changed |
|---|---|
| `main.tf` | Added `aws_ssm_parameter`, `aws_cloudwatch_log_group`, two scoped IAM policies |
| `variables.tf` | Added `ssh_allowed_cidr`, `log_retention_days` |
| `outputs.tf` | Added `cloudwatch_log_group`, `db_password_parameter` |
| `user_data.sh.tpl` | Fetches DB password from Parameter Store at runtime instead of receiving it directly; added `awslogs` log driver to the `docker run` command |


