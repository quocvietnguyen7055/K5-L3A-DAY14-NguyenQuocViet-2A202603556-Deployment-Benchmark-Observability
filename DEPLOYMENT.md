# Deployment Information

## Status

Local Docker installation and Part 6 container validation are complete. Public deployment is pending: no Railway or Render account is connected to this workspace, so no public URL or platform screenshots are available yet.

## Planned deployment

Use the `06-lab-complete/` service with Railway (`railway.toml`) or Render (`render.yaml`). Provision Redis and set `REDIS_URL` to the provider's private Redis URL. Set `AGENT_API_KEY` as a provider secret. Do not put either value in this file or commit them.

## Record after deployment

- Public service URL: pending account connection
- Platform: Railway or Render, to be selected when account access is available
- Redis provisioned and connected: pending
- `/health`, `/ready`, unauthenticated `/ask`, authenticated `/ask` status codes: pending
- Dashboard, running service, and API test screenshots under `screenshots/`: pending

To finish deployment, connect a Railway or Render account (and choose the platform). Then provision Redis, set `REDIS_URL` and `AGENT_API_KEY` in the provider's secret settings, and use the public URL plus a locally stored API key to run the four checks in `CHECKPOINTS.md` CP6. Record status codes only; do not paste the key into this file or screenshots.
