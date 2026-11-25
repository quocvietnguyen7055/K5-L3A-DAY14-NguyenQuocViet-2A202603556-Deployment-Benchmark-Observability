# Day 14 Lab — Mission Answers

> Written answers below are based on the supplied source. Measurements and actions that require Docker or a cloud account are explicitly marked pending; no output is fabricated.

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns in the basic app

1. API/database credentials are embedded in source and can leak through Git.
2. The app logs the API key, exposing a secret in plain text logs.
3. Debug mode and reload are enabled, which are inappropriate for production.
4. It binds to `localhost` and a fixed port, so a container/platform cannot reach it through an injected port.
5. Configuration is hard-coded instead of read from environment variables.
6. There are no liveness/readiness endpoints or structured logs.
7. There is no controlled startup/shutdown lifecycle.

### Exercises 1.2–1.3: Comparison

| Feature | Basic | Production example | Why it matters |
|---|---|---|---|
| Configuration | Hard-coded | Environment-backed settings | Same image can run in dev, staging, and production without embedding secrets. |
| Binding | Localhost / fixed port | `0.0.0.0` / platform port | Makes the service reachable inside containers and on cloud platforms. |
| Health | No health endpoint | `/health` and `/ready` | Separates process liveness from dependency readiness. |
| Logs | `print`, including secret | Structured JSON without secret | Enables search/aggregation and avoids credential leaks. |
| Shutdown | Abrupt | Lifespan cleanup; server drains requests | Reduces dropped in-flight work during deploys. |

The basic endpoint works locally but is not production-ready because it assumes the developer's machine and exposes credentials.

## Part 2: Docker

### Exercise 2.1: Dockerfile concepts

1. The basic Dockerfile uses `python:3.11-slim`.
2. Its working directory is `/app`.
3. Copying `requirements.txt` and installing dependencies before application source allows Docker to reuse the dependency layer when only source changes.
4. `CMD` supplies the default process/arguments and is readily replaced at runtime. `ENTRYPOINT` defines the container's main executable; `CMD` commonly supplies its default arguments.

### Exercises 2.2–2.4: Results and architecture

- Built and ran the basic image from `02-docker/develop/Dockerfile`; `/health` returned 200. The image is 1,667,779,889 bytes (about 1.55 GiB), reflecting the full `python:3.11` base. The Go single-stage image was 1,246 MiB; its multi-stage counterpart was 21.6 MiB. Both Go images served `/` successfully. Part 6's production image was 273 MB. Measurements are in `reports/docker_images.txt` and `reports/production_readiness.txt`.
- Multi-stage build: the builder installs dependencies; the runtime stage copies only the environment and app files, uses a slim base and non-root user. This reduces shipped build tools and image size.
- Compose stack: agent connects to Redis on the private Compose network; Redis health gates agent startup. Nginx, Redis, vector database, and agent services in the supplied advanced example communicate over the internal network, with Nginx as the public entry point.

## Part 3: Cloud Deployment

### Deployment status

Public deployment and URL: **pending**. No cloud account/session is connected to this workspace. Do not treat the local Docker config as a deployed service.

### Railway vs Render; Cloud Run pipeline

Railway's `railway.toml` declares the Dockerfile builder and `/health` health check. Render's `render.yaml` describes a web service, Docker runtime, health check, and environment variables; secrets are generated or entered through the dashboard. Cloud Build's sample pipeline runs tests, builds and pushes an image, then deploys it to Cloud Run. The service manifest sets scaling, resources, environment/Secret Manager references, and probes.

## Part 4: API Security

### Exercises 4.1–4.3: Implementation notes

- The develop API checks `X-API-Key` against its configured key; missing or invalid credentials should be rejected. Rotate by creating a new secret in the hosting environment, updating clients, then revoking the old value; never commit it.
- JWT flow: authenticate credentials at a token endpoint, issue a signed token with identity/role/expiry claims, and verify signature and expiry on protected calls. Unlike a static API key, a JWT can expire and carry signed claims; a signed JWT is not automatically encrypted.
- The production example uses a sliding window with a default user limit of 10 requests per 60 seconds and a separate admin tier (100/minute). Admin bypass/tier selection is based on authenticated role; do not trust a client-supplied user ID. The supplied example keeps counters in process memory, so it is not shared across workers/restarts; Part 6 moves limiter state to Redis.
- The Part 6 production checker exercised the corresponding runtime cases: missing/invalid API keys returned 401, a valid key returned 200, excess requests returned 429 with limiter state surviving an agent restart, and an exhausted budget returned 402. Full output: `reports/production_readiness.txt`.

### Exercise 4.4: Cost guard

Track token-derived spend by user and period in Redis. Before a model call, compare current spend plus an estimate against the user's budget and reject an exhausted budget with HTTP 402. After the call, atomically add actual spend and set an expiry through the budget period. The supplied Part 4 example uses a $1 per-user daily and $10 global daily limit; the exercise prompt separately asks for a $10 monthly per-user implementation. Those periods/limits should not be conflated.

## Part 5: Scaling & Reliability

### Exercises 5.1–5.3: Design notes

- `/health` is a liveness check: return 200 while the process runs. `/ready` checks dependencies and returns 503 when the instance must not receive traffic. Redis failure should affect readiness, not liveness.
- On SIGTERM, stop accepting new work, let in-flight requests finish, close resources, and exit cleanly. Uvicorn handles the server drain when its signal handler is retained; app lifespan is the place for cleanup.
- Store conversation/session state in Redis rather than a process-local dictionary so any replica can serve the next request and state survives instance replacement.

### Exercises 5.4–5.5: Load balancing and evidence

Nginx distributed five requests for one session across three agent instances; Redis preserved all 10 user/assistant messages. Captured output is in `reports/part5_stateless.txt`.

## Part 6: Final Project

Implemented in `06-lab-complete/`: environment configuration, API key dependency, Redis health/readiness, Redis sliding-window rate limiting, daily cost tracking, JSON logs, FastAPI lifespan shutdown, multi-stage Dockerfile, Compose Redis service, and Railway/Render configs.

Checker result: **PASS 12/12 criteria; 43/43 checks passed**. Docker Desktop and the WSL2 backend were installed on D: to run the complete checker, including container health/readiness, auth and limiter behavior, graceful in-flight shutdown, and `docker stop` timing. The measured image size was 273 MB. The full output is in `reports/production_readiness.txt`.

## Part 7: Benchmark & Observability

Local eval/load JSON and observability evidence are in `reports/`; the two Locust runs are in `benchmark-results/`, and screenshots are in `screenshots/`. The KB changes fixed the two misses in `security-02` and `scaling-03`; final v2 quality gate was 23/23 (100%) with no regressions. The one- and three-replica 100-user runs each lasted two minutes. Fault injection fired `AgentHighErrorRate`, `AgentHighLatencyP95`, and `LLMCostBurnRateHigh`; alert observations and error/slow trace IDs are recorded in `reports/`.

### CI quality gate

Run `python eval/run_eval.py --url <agent-url> --min-accuracy 1.0 --baseline reports/eval_v2.json`. Preserve and check its process exit code: zero allows the CI job to proceed; nonzero fails the job and blocks merge.

## AI log

- Asked AI to inspect and implement the unfinished Part 6 agent. AI proposed code for config, auth, Redis rate/cost guards, routes/logging/lifespan, Docker, Compose, and deployment config. I reviewed the source changes, installed Docker Desktop/WSL2 on D:, and ran the full production checker (12/12; 43/43).
- Asked AI what is required for submission and to complete available deliverables. AI summarized the checklist, generated local Part 7 eval/load reports, added the two KB entries identified by eval, and drafted these written explanations and report. The fixed v2 eval passed 23/23 without regressions; the local load p95 SLO passed at concurrency 1/10 and failed at 50/100. The Docker observability stack, scale benchmarks, alert evidence, and local screenshots were captured. Public cloud deployment and its three deployment screenshots remain pending because an account/session is not connected.
