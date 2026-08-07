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
├── requirements.txt      # Python dependencies
├── Dockerfile             # App container image definition
├── docker-compose.yml     # Local app + Postgres stack
├── .env.example           # Sample environment variables
├── .dockerignore
├── .gitignore
└── README.md
```

## Notes for Week 2 (Terraform / AWS)
- The container reads DB connection info from environment variables
  (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`), so in AWS these
  will point at the RDS PostgreSQL endpoint instead of the local `db` container.
- `/health` is already implemented and ready to be used as the
  Application Load Balancer target group health check path.
- No secrets are hardcoded in the image — they're injected at runtime,
  which lines up with the Week 4 requirement to use IAM roles / Parameter Store
  instead of credentials in code.
