"""
Mid-Level Cloud Engineering Project - Week 1
Project Tracker - a simple Flask CRUD app backed by PostgreSQL.

Scenario: a startup needs an internal tool to track projects across teams -
what they're called, their budget, current status, and deadline.

Resource: "projects" (id, title, budget, status, deadline, created_at)

Endpoints:
  GET    /health             -> health check (used by ALB target group later)
  GET    /projects            -> list all projects
  GET    /projects/<id>       -> get one project
  POST   /projects            -> create project
  PUT    /projects/<id>       -> update project
  DELETE /projects/<id>       -> delete project
"""

import os
import time
from datetime import datetime

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "appdb"),
    "user": os.environ.get("DB_USER", "appuser"),
    "password": os.environ.get("DB_PASSWORD", "apppassword"),
}

# Allowed project statuses
VALID_STATUSES = ("open", "in-progress", "completed")


def get_connection(retries=10, delay=3):
    """Connect to Postgres, retrying while the DB container is still starting."""
    last_err = None
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except psycopg2.OperationalError as e:
            last_err = e
            print(f"[db] connection attempt {attempt + 1}/{retries} failed, retrying in {delay}s...")
            time.sleep(delay)
    raise last_err


def init_db():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    budget NUMERIC(12, 2),
                    status VARCHAR(20) NOT NULL DEFAULT 'open',
                    deadline DATE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
        conn.commit()
    finally:
        conn.close()


@app.route("/", methods=["GET"])
def index():
    """Serve the styled web UI."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()}), 200


@app.route("/projects", methods=["GET"])
def list_projects():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, title, budget, status, deadline, created_at FROM projects ORDER BY id;"
            )
            rows = cur.fetchall()
        return jsonify([dict(r) for r in rows]), 200
    finally:
        conn.close()


@app.route("/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, title, budget, status, deadline, created_at FROM projects WHERE id = %s;",
                (project_id,),
            )
            row = cur.fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(dict(row)), 200
    finally:
        conn.close()


@app.route("/projects", methods=["POST"])
def create_project():
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    budget = data.get("budget")
    status = data.get("status", "open")
    deadline = data.get("deadline")  # expected format: "YYYY-MM-DD"

    if not title:
        return jsonify({"error": "'title' is required"}), 400

    if status not in VALID_STATUSES:
        return jsonify({"error": f"'status' must be one of {VALID_STATUSES}"}), 400

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO projects (title, budget, status, deadline)
                VALUES (%s, %s, %s, %s)
                RETURNING id, title, budget, status, deadline, created_at;
                """,
                (title, budget, status, deadline),
            )
            row = cur.fetchone()
        conn.commit()
        return jsonify(dict(row)), 201
    finally:
        conn.close()


@app.route("/projects/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    budget = data.get("budget")
    status = data.get("status")
    deadline = data.get("deadline")

    if status is not None and status not in VALID_STATUSES:
        return jsonify({"error": f"'status' must be one of {VALID_STATUSES}"}), 400

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id FROM projects WHERE id = %s;", (project_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "not found"}), 404

            cur.execute(
                """
                UPDATE projects
                SET title = COALESCE(%s, title),
                    budget = COALESCE(%s, budget),
                    status = COALESCE(%s, status),
                    deadline = COALESCE(%s, deadline)
                WHERE id = %s
                RETURNING id, title, budget, status, deadline, created_at;
                """,
                (title, budget, status, deadline, project_id),
            )
            row = cur.fetchone()
        conn.commit()
        return jsonify(dict(row)), 200
    finally:
        conn.close()


@app.route("/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM projects WHERE id = %s RETURNING id;", (project_id,))
            deleted = cur.fetchone()
        conn.commit()
        if deleted is None:
            return jsonify({"error": "not found"}), 404
        return jsonify({"deleted_id": project_id}), 200
    finally:
        conn.close()


# Initialize the DB schema on import so this works both under
# `python app.py` (dev) and `gunicorn app:app` (container/prod).
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
