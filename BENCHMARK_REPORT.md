# Benchmark & Observability Report — Day 14

**Student:** Nguyen Quoc Viet (from repository name)
**Run date:** 2026-11-25
**Environment:** Windows 11, Python 3.11; local eval/load runs and Docker Desktop/WSL2 observability stack.
**Note:** Values below are from generated JSON and Locust CSV reports. Locust `/ask` metrics are used for the replica comparison; 503s were returned by Nginx under sustained load.

## 1. SLOs

| SLI | SLO | Reason |
|---|---:|---|
| p95 latency `/ask` | ≤ 500 ms | Keeps typical tail latency responsive while allowing occasional simulated slow calls. |
| Error rate `/ask` | ≤ 2% | Allows rare simulated upstream failures without masking sustained failure. |
| Golden set accuracy | ≥ 100% for fixed v2 | The lab's final quality gate explicitly requests 1.0 accuracy with no regression. |

## 2. Performance benchmark

### 2.1 Concurrency vs latency (v2, 300 requests per run)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | p95 SLO |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 4.01 | 204.2 | 237.3 | 1710.1 | 0.33% | PASS |
| 10 | 34.17 | 190.8 | 430.0 | 1709.0 | 0.67% | PASS |
| 50 | 96.12 | 210.7 | 556.8 | 1739.2 | 0.33% | FAIL |
| 100 | 40.96 | 980.2 | 5280.0 | 5916.8 | 0.67% | FAIL |

Throughput rose through 50 concurrent clients, then fell at 100 as latency and contention increased. It did not scale linearly; this local single-process mock workload and host became saturated. Occasional slow requests strongly affected p99 even when p50 remained near 200 ms.

### 2.2 Slow-request rate (300 requests, concurrency 20)

| `MOCK_SLOW_RATE` | Average (ms) | p95 (ms) | p99 (ms) |
|---:|---:|---:|---:|
| 0 | 211.4 | 466.9 | 512.0 |
| 0.03 | 267.7 | 494.2 | 1715.7 |
| 0.1 | 314.4 | 1666.1 | 1732.9 |

p99 responds sharply to a small number of slow requests. Average latency hides the experience of the slowest users, so an SLO should use a percentile such as p95 or p99.

## 3. Quality benchmark

| Metric | v1 | v2 baseline | v2 after KB fix |
|---|---:|---:|---:|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100% (23/23) |
| Average tokens/question | 57.0 | 109.3 | 114.9 |
| Total cost | $0.000402 | $0.000764 | $0.000801 |
| Cost/correct answer | $0.00040215 | $0.00003639 | $0.00003484 |
| Quality gate | FAIL | PASS (≥80%, no regression) | PASS (≥100%, no regression) |

The initial v2 misses were `security-02` (JWT vs API key) and `scaling-03` (Kubernetes HPA metrics). Added corresponding knowledge base entries in `develop/utils/mock_llm.py`. Accuracy reached 100%, with no regressions; cost per correct answer fell because all answers scored correctly.

## 4. Production observability

The Docker Compose stack was exercised with 100 users and temporary fault injection (`MOCK_ERROR_RATE=0.25`, `MOCK_SLOW_RATE=0.30`). Captured evidence is in `screenshots/` and `reports/`.

| Evidence | Observation |
|---|---|
| Grafana | Dashboard shows request/latency/cost panels under load; 3 agent instances were up. |
| Error trace | Jaeger trace `7fb31bf9a44269365ab06766d430afdc`, `/ask` returned 503; request span duration 114 ms. |
| Slow trace | Jaeger trace `23b5d87da021f26289d9ab881996fa92`, `/ask` completed in 1,674.1 ms. |
| Prometheus alerts | `AgentHighErrorRate`, `AgentHighLatencyP95`, and `LLMCostBurnRateHigh` were firing together. Observation at 2026-11-25 10:21:20 UTC; both SLO alerts became active at 10:19:17 UTC and fired after their configured 1-minute and 2-minute hold times. |

Fault injection was restored by stopping the temporary Compose stack after evidence capture. Raw alert snapshots and trace JSON are in `reports/`.

## 5. Production scaling benchmark

Both rows use the Locust `POST /ask` statistics from headless 100-user, two-minute runs. CSVs are in `benchmark-results/`.

| Agent replicas | Requests | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failed | Failure rate |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 7,008 | 59.04 | 200 | 690 | 1,700 | 67 | 0.96% |
| 3 | 7,051 | 59.41 | 190 | 230 | 1,700 | 72 | 1.02% |

Three replicas improved `/ask` p95 by about 67% while throughput stayed nearly flat (+0.6%). p99 remained dominated by the injected slow-call tail. Failures were HTTP 503 responses from Nginx; replica scaling did not remove this failure mode on the local host.

## 6. Conclusions

1. Increasing concurrency improved local mock throughput only until host saturation; at 100 clients, p95 and throughput both degraded.
2. Tail latency and p99 make rare slow calls visible when the average does not.
3. Retrieval improved this golden set from 4.3% (v1) to 100% (fixed v2); eval catches answer-quality problems that infrastructure dashboards cannot.

For a real deployment, add alerts for Redis availability, sustained 5xx rates, budget burn, queue depth, and per-model latency/cost. Validate thresholds against production traffic.
