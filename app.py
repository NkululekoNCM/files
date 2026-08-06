"""
Mid-Level Cloud Engineering Project - Week 1
Simple Flask CRUD application backed by PostgreSQL.

Resource: "items" (id, name, description, created_at)

Endpoints:
  GET    /health          -> health check (used by ALB target group later)
  GET    /items            -> list all items
  GET    /items/<id>       -> get one item
  POST   /items            -> create item
  PUT    /items/<id>       -> update item
  DELETE /items/<id>       -> delete item
"""

import os
import time
from datetime import datetime

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "appdb"),
    "user": os.environ.get("DB_USER", "appuser"),
    "password": os.environ.get("DB_PASSWORD", "apppassword"),
}


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
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
        conn.commit()
    finally:
        conn.close()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()}), 200


@app.route("/items", methods=["GET"])
def list_items():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, name, description, created_at FROM items ORDER BY id;")
            rows = cur.fetchall()
        return jsonify([dict(r) for r in rows]), 200
    finally:
        conn.close()


@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, name, description, created_at FROM items WHERE id = %s;", (item_id,))
            row = cur.fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(dict(row)), 200
    finally:
        conn.close()


@app.route("/items", methods=["POST"])
def create_item():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    description = data.get("description", "")

    if not name:
        return jsonify({"error": "'name' is required"}), 400

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO items (name, description) VALUES (%s, %s) RETURNING id, name, description, created_at;",
                (name, description),
            )
            row = cur.fetchone()
        conn.commit()
        return jsonify(dict(row)), 201
    finally:
        conn.close()


@app.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    description = data.get("description")

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id FROM items WHERE id = %s;", (item_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "not found"}), 404

            cur.execute(
                """
                UPDATE items
                SET name = COALESCE(%s, name),
                    description = COALESCE(%s, description)
                WHERE id = %s
                RETURNING id, name, description, created_at;
                """,
                (name, description, item_id),
            )
            row = cur.fetchone()
        conn.commit()
        return jsonify(dict(row)), 200
    finally:
        conn.close()


@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM items WHERE id = %s RETURNING id;", (item_id,))
            deleted = cur.fetchone()
        conn.commit()
        if deleted is None:
            return jsonify({"error": "not found"}), 404
        return jsonify({"deleted_id": item_id}), 200
    finally:
        conn.close()


# Initialize the DB schema on import so this works both under
# `python app.py` (dev) and `gunicorn app:app` (container/prod).
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
