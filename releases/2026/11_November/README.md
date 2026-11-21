# November 2026 Student Release

Student changes are submitted through feature branches and pull requests, not by direct commits to SIT or main.

## Release folders
- `python_code/backend/` — Python API and service change submissions
- `python_code/frontend/` — template, CSS, and JavaScript submissions
- `db_code/ddl/` — schema migrations
- `db_code/dml/` — data migrations
- `db_code/rollback/` — reviewed rollback scripts
- `test_cases/` — unit and integration tests
- `deployment/` — deployment instructions and evidence

Create folders when adding their first file; Git does not track empty directories. Production code must be integrated into the actual app and migrations, reviewed, tested, and approved before promotion. Never put database passwords or production data here.
