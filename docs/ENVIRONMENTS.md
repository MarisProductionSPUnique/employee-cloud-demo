# Employee Operations Lab Environments

- `main`: production release branch. Protect it and require approval before merge.
- `develop`: student integration and development branch.
- `sit`: approved integration-testing candidate branch.
- `feature/EMP-<ticket>-<description>`: student work branches from `develop`.

## Deployment prerequisites
1. Configure independent DEV and SIT Render services, each connected to its matching branch.
2. Configure independent DEV and SIT Supabase PostgreSQL databases. Never share production `DATABASE_URL`.
3. Review `render.yaml` and Render dashboard auto-deploy settings before attaching services.
4. Run `python -m unittest discover -s tests -v` and approved database migrations in SIT.
5. Require review, test evidence, backup and rollback plan before merging `sit` release into `main`.

The existence of branches does not create Render services, databases, deployment workflows or automated migration execution.
