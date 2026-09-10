# Employee Operations Lab

Employee Operations Lab is a classroom-ready cloud application that exposes the complete flow from a browser UI to a Flask REST API and a PostgreSQL database. Every response includes a request ID, and the UI records method, endpoint, status, duration, and request ID so students can connect what they see in the browser with the application logs.

## Architecture

```text
Browser UI -> Flask REST API on Render -> PostgreSQL on Supabase
     |               |                         |
DevTools         Render logs              Table Editor / SQL
```

## Features

- Create, read, update, delete, and search employees
- Database and API health check
- Request ID propagation through UI, response headers, JSON, and logs
- Structured HTTP access logs
- Validation errors, duplicate detection, and clear HTTP status codes
- Safe classroom endpoints for 404, 500, and slow-response demonstrations
- Local SQLite mode with sample data
- PostgreSQL mode for Supabase
- Render Blueprint configuration

## Run locally on Ubuntu

```bash
cd employee-cloud-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`.

SQLite is used automatically when `DATABASE_URL` is empty. The local database file is created under the Flask `instance` directory.

## Test

```bash
python -m unittest discover -s tests -v
```

## Deploy

1. Create a free Supabase project.
2. Open SQL Editor and run `schema.sql`, then `seed.sql`.
3. In Supabase, select **Connect > Session pooler** and copy the URI.
4. Replace `[YOUR-PASSWORD]` and add `?sslmode=require` if the URI has no query string.
5. Upload this project to a GitHub repository.
6. In Render, create a new Blueprint and select the repository.
7. Enter the Supabase URI when Render requests the `DATABASE_URL` secret.
8. Wait for deployment, then open the Render URL and select **Check health**.

Do not commit `.env` or database passwords. `DATABASE_URL` is intentionally marked `sync: false` in `render.yaml`.

## API endpoints

| Method | Endpoint | Purpose | Typical status |
| --- | --- | --- | --- |
| GET | `/api/health` | Check API and database | 200 or 503 |
| GET | `/api/employees` | List or search employees | 200 |
| POST | `/api/employees` | Create an employee | 201, 400, or 409 |
| PUT | `/api/employees/{id}` | Update an employee | 200, 400, 404, or 409 |
| DELETE | `/api/employees/{id}` | Delete an employee | 200 or 404 |
| GET | `/api/demo/error` | Produce a controlled 500 | 500 |
| GET | `/api/demo/slow?seconds=3` | Produce a slow response | 200 |

## Classroom flow

1. Open browser Developer Tools and select the Network tab.
2. Create an employee in the UI.
3. Select the `POST /api/employees` request and inspect its payload, status, JSON response, and `X-Request-ID` header.
4. Search the Render logs for the same request ID.
5. Open the Supabase Table Editor and confirm the new database row.
6. Edit and delete the employee to demonstrate `UPDATE` and `DELETE` operations.
7. Use Teaching Tools to demonstrate 404, 500, health checks, and slow responses.

The detailed instructor script is supplied separately in the Word teaching guide.
