"""Employee Operations Lab.

A small classroom application that makes the complete request path visible:
browser UI -> Flask REST API -> relational database -> API response.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Text, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from werkzeug.exceptions import HTTPException


load_dotenv()


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
REQUEST_ID_PATTERN = re.compile(r"[^A-Za-z0-9._:-]")
ALLOWED_STATUSES = {"Active", "On Leave", "Inactive"}


class Employee(db.Model):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    department: Mapped[str] = mapped_column(String(80), index=True)
    role: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="Active", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "employee_code": self.employee_code,
            "name": self.name,
            "email": self.email,
            "department": self.department,
            "role": self.role,
            "status": self.status,
            "notes": self.notes or "",
            "created_at": _isoformat(self.created_at),
            "updated_at": _isoformat(self.updated_at),
        }


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _as_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalise_database_url(raw_url: str) -> str:
    """Select Psycopg 3 explicitly for PostgreSQL connection strings."""
    if raw_url.startswith("postgres://"):
        return "postgresql+psycopg://" + raw_url[len("postgres://") :]
    if raw_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw_url[len("postgresql://") :]
    return raw_url


def _database_label(database_url: str) -> str:
    backend = make_url(database_url).get_backend_name()
    return "PostgreSQL" if backend == "postgresql" else "SQLite"


def _request_id() -> str:
    incoming = request.headers.get("X-Request-ID", "").strip()
    if incoming:
        cleaned = REQUEST_ID_PATTERN.sub("-", incoming)[:80]
        if cleaned:
            return cleaned
    return f"REQ-{uuid.uuid4().hex[:12].upper()}"


def _json_error(message: str, code: str, status: int):
    return (
        jsonify(
            {
                "success": False,
                "error": {"code": code, "message": message},
                "request_id": getattr(g, "request_id", None),
            }
        ),
        status,
    )


def _clean_text(value: Any, maximum: int) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())[:maximum]


def _validate_employee(payload: Any) -> tuple[dict[str, str], dict[str, str]]:
    if not isinstance(payload, dict):
        return {}, {"body": "Send employee details as a JSON object."}

    values = {
        "employee_code": _clean_text(payload.get("employee_code"), 20).upper(),
        "name": _clean_text(payload.get("name"), 100),
        "email": _clean_text(payload.get("email"), 150).lower(),
        "department": _clean_text(payload.get("department"), 80),
        "role": _clean_text(payload.get("role"), 100),
        "status": _clean_text(payload.get("status"), 20) or "Active",
        "notes": _clean_text(payload.get("notes"), 500),
    }

    errors: dict[str, str] = {}
    for field in ("employee_code", "name", "email", "department", "role"):
        if not values[field]:
            errors[field] = "This field is required."

    if values["email"] and not EMAIL_PATTERN.match(values["email"]):
        errors["email"] = "Enter a valid email address."
    if values["status"] not in ALLOWED_STATUSES:
        errors["status"] = "Choose Active, On Leave, or Inactive."

    return values, errors


def _seed_if_empty() -> None:
    if db.session.scalar(select(func.count(Employee.id))) != 0:
        return
    db.session.add_all(
        [
            Employee(
                employee_code="EMP1001",
                name="Ananya Rao",
                email="ananya.rao@example.com",
                department="Application Support",
                role="Production Support Analyst",
                status="Active",
                notes="Monitors payment services and incident queues.",
            ),
            Employee(
                employee_code="EMP1002",
                name="Arun Kumar",
                email="arun.kumar@example.com",
                department="Database Operations",
                role="Database Support Engineer",
                status="Active",
                notes="Supports PostgreSQL health and query troubleshooting.",
            ),
            Employee(
                employee_code="EMP1003",
                name="Meera Joseph",
                email="meera.joseph@example.com",
                department="Service Management",
                role="Incident Coordinator",
                status="On Leave",
                notes="Coordinates major incidents and stakeholder updates.",
            ),
            Employee(
                employee_code="EMP1004",
                name="Vijay Singh",
                email="vijay.singh@example.com",
                department="Platform Engineering",
                role="Linux Administrator",
                status="Active",
                notes="Maintains Linux hosts and deployment automation.",
            ),
        ]
    )
    db.session.commit()


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)

    default_database_url = "sqlite:///employee_demo.db"
    configured_url = _normalise_database_url(
        os.getenv("DATABASE_URL") or default_database_url
    )
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=configured_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 300},
        AUTO_CREATE_TABLES=_as_bool(os.getenv("AUTO_CREATE_TABLES"), True),
        SEED_DEMO_DATA=_as_bool(
            os.getenv("SEED_DEMO_DATA"), configured_url.startswith("sqlite")
        ),
        DEMO_MODE=_as_bool(os.getenv("DEMO_MODE"), True),
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    app.logger.setLevel(logging.INFO)

    with app.app_context():
        try:
            if app.config["AUTO_CREATE_TABLES"]:
                db.create_all()
            if app.config["SEED_DEMO_DATA"]:
                _seed_if_empty()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception(
                "Database initialization failed; the service will start in degraded mode"
            )

    @app.before_request
    def start_request_trace() -> None:
        g.request_id = _request_id()
        g.request_started = time.perf_counter()

    @app.after_request
    def finish_request_trace(response):
        duration_ms = round((time.perf_counter() - g.request_started) * 1000, 2)
        response.headers["X-Request-ID"] = g.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        )
        app.logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": g.request_id,
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "remote_addr": request.headers.get(
                        "X-Forwarded-For", request.remote_addr
                    ),
                },
                separators=(",", ":"),
            )
        )
        return response

    @app.get("/")
    def index():
        return render_template("index.html", demo_mode=app.config["DEMO_MODE"])

    @app.get("/api/health")
    def health():
        started = time.perf_counter()
        try:
            db.session.execute(text("SELECT 1"))
            db.session.commit()
            database_status = "connected"
            status_code = 200
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception(
                "Database health check failed request_id=%s", g.request_id
            )
            database_status = "unavailable"
            status_code = 503

        return (
            jsonify(
                {
                    "success": status_code == 200,
                    "service": "employee-operations-lab",
                    "api": "healthy" if status_code == 200 else "degraded",
                    "database": database_status,
                    "database_type": _database_label(
                        app.config["SQLALCHEMY_DATABASE_URI"]
                    ),
                    "response_time_ms": round(
                        (time.perf_counter() - started) * 1000, 2
                    ),
                    "request_id": g.request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            status_code,
        )

    @app.get("/api/employees")
    def list_employees():
        query = _clean_text(request.args.get("q"), 100)
        statement = select(Employee)
        if query:
            pattern = f"%{query}%"
            statement = statement.where(
                Employee.name.ilike(pattern)
                | Employee.employee_code.ilike(pattern)
                | Employee.department.ilike(pattern)
                | Employee.role.ilike(pattern)
            )
        employees = db.session.scalars(
            statement.order_by(Employee.id.desc())
        ).all()
        return jsonify(
            {
                "success": True,
                "count": len(employees),
                "data": [employee.to_dict() for employee in employees],
                "request_id": g.request_id,
            }
        )

    @app.post("/api/employees")
    def create_employee():
        values, errors = _validate_employee(request.get_json(silent=True))
        if errors:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Please correct the highlighted employee details.",
                            "fields": errors,
                        },
                        "request_id": g.request_id,
                    }
                ),
                400,
            )

        employee = Employee(**values)
        db.session.add(employee)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return _json_error(
                "Employee code or email already exists.",
                "DUPLICATE_EMPLOYEE",
                409,
            )

        app.logger.info(
            "employee_created request_id=%s employee_id=%s employee_code=%s",
            g.request_id,
            employee.id,
            employee.employee_code,
        )
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Employee created successfully.",
                    "data": employee.to_dict(),
                    "request_id": g.request_id,
                }
            ),
            201,
        )

    @app.put("/api/employees/<int:employee_id>")
    def update_employee(employee_id: int):
        employee = db.session.get(Employee, employee_id)
        if employee is None:
            return _json_error("Employee not found.", "EMPLOYEE_NOT_FOUND", 404)

        values, errors = _validate_employee(request.get_json(silent=True))
        if errors:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Please correct the highlighted employee details.",
                            "fields": errors,
                        },
                        "request_id": g.request_id,
                    }
                ),
                400,
            )

        for key, value in values.items():
            setattr(employee, key, value)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return _json_error(
                "Employee code or email already exists.",
                "DUPLICATE_EMPLOYEE",
                409,
            )

        app.logger.info(
            "employee_updated request_id=%s employee_id=%s",
            g.request_id,
            employee.id,
        )
        return jsonify(
            {
                "success": True,
                "message": "Employee updated successfully.",
                "data": employee.to_dict(),
                "request_id": g.request_id,
            }
        )

    @app.delete("/api/employees/<int:employee_id>")
    def delete_employee(employee_id: int):
        employee = db.session.get(Employee, employee_id)
        if employee is None:
            return _json_error("Employee not found.", "EMPLOYEE_NOT_FOUND", 404)

        employee_code = employee.employee_code
        db.session.delete(employee)
        db.session.commit()
        app.logger.warning(
            "employee_deleted request_id=%s employee_id=%s employee_code=%s",
            g.request_id,
            employee_id,
            employee_code,
        )
        return jsonify(
            {
                "success": True,
                "message": f"Employee {employee_code} deleted.",
                "request_id": g.request_id,
            }
        )

    @app.get("/api/demo/error")
    def demo_error():
        if not app.config["DEMO_MODE"]:
            return _json_error("Endpoint not found.", "NOT_FOUND", 404)
        app.logger.error(
            "Intentional classroom error request_id=%s", g.request_id
        )
        return _json_error(
            "Intentional classroom error. Use the request ID to find this call in the logs.",
            "DEMO_INTERNAL_ERROR",
            500,
        )

    @app.get("/api/demo/slow")
    def demo_slow():
        if not app.config["DEMO_MODE"]:
            return _json_error("Endpoint not found.", "NOT_FOUND", 404)
        try:
            seconds = max(1.0, min(float(request.args.get("seconds", "3")), 5.0))
        except ValueError:
            seconds = 3.0
        time.sleep(seconds)
        return jsonify(
            {
                "success": True,
                "message": f"The API intentionally waited {seconds:.1f} seconds.",
                "request_id": g.request_id,
            }
        )

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return _json_error("Endpoint not found.", "NOT_FOUND", 404)
        return render_template("index.html", demo_mode=app.config["DEMO_MODE"]), 404

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        app.logger.exception(
            "Unhandled database error request_id=%s error=%s", g.request_id, error
        )
        return _json_error(
            "The database operation could not be completed. Check the application logs.",
            "DATABASE_ERROR",
            503,
        )

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            return _json_error(
                error.description or "The request could not be completed.",
                error.name.upper().replace(" ", "_"),
                error.code or 500,
            )
        return error

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception(
            "Unhandled application error request_id=%s error=%s", g.request_id, error
        )
        return _json_error(
            "An unexpected application error occurred. Check the application logs.",
            "INTERNAL_ERROR",
            500,
        )

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
