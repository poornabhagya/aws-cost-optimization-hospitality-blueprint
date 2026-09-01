# Architecture Decision Records (ADR) Collection
## Single-Property Zero-Cost Free-Tier Hospitality OS Deployment (< $0.50 USD / Month)

---

### Document Metadata
* **Document Title:** Master Architecture Decision Records (ADR) Collection: 100% AWS Free-Tier Target Architecture
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 2.0.0 (Free-Tier Architecture Baseline)
* **Status:** Accepted / Production-Ready Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Budget Ceiling:** **< $0.50 USD / month ($6.00 USD / year)** total cloud spend
* **Target Cloud Provider & Region:** Amazon Web Services (AWS) — Primary Region: Asia Pacific (Mumbai) `ap-south-1` / `us-east-1`
* **Aligned Specifications:**
  - [`docs/Enterprise Baseline/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/BRD_SPECIFICATION.md) (Domain Rules, 72h POS Autonomy, Append-Only GL, Recipe BOM)
  - [`docs/Enterprise Baseline/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/NFR_SPECIFICATION.md) ($p_{95} \le 120\text{ ms}$, TLS 1.3, Rate Limits, 30 DB Sockets)
  - [`docs/Enterprise Baseline/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/CAPACITY_SIZING.md) (0.50 vCPU / 1GB RAM Compute, 512MB Redis, 0.50 vCPU / 2GB / 20GB gp3 PostgreSQL)

---

## Master ADR Index

| ADR ID | Decision Title | Status | Free-Tier Technology / Approach | Target Cost |
| :--- | :--- | :--- | :--- | :--- |
| [**ADR-001**](#adr-001-cloud-provider-ecosystem-selection) | Cloud Provider Ecosystem Selection | Accepted | Amazon Web Services (AWS Free Tier) | **$0.00 / mo** |
| [**ADR-002**](#adr-002-single-host-containerized-compute-plane) | Single-Host Containerized Compute Plane | Accepted | 1x `t4g.micro` EC2 + Docker Compose (ARM64) | **$0.00 / mo** |
| [**ADR-003**](#adr-003-edge-ingress-reverse-proxy--ssl-termination) | Edge Ingress, Reverse Proxy & SSL Termination | Accepted | In-Container NGINX + Let's Encrypt (Certbot) | **$0.00 / mo** |
| [**ADR-004**](#adr-004-relational-persistence-plane) | Relational Persistence Plane | Accepted | AWS RDS PostgreSQL 17 Single-AZ (`db.t4g.micro`) | **$0.00 / mo** |
| [**ADR-005**](#adr-005-embedded-ephemeral-state--task-broker) | Embedded Ephemeral State & Task Broker | Accepted | In-Container Redis 7.2 Alpine (Docker Compose) | **$0.00 / mo** |
| [**ADR-006**](#adr-006-client-web-delivery--storage-archival) | Client Web Delivery & Storage Archival | Accepted | AWS S3 (5GB Free) + Amazon CloudFront (1TB Free) | **$0.00 / mo** |
| [**ADR-007**](#adr-007-zero-cost-lean-vpc--subnet-isolation) | Zero-Cost Lean VPC & Subnet Isolation | Accepted | Public/Private Subnets + Security Groups (0 NAT GW) | **$0.00 / mo** |
| [**ADR-008**](#adr-008-secrets-management--runtime-configuration) | Secrets Management & Runtime Configuration | Accepted | Docker Env Injection + GitHub Secrets + IAM Profile | **$0.00 / mo** |
| [**ADR-009**](#adr-009-infrastructure-as-code--automation) | Infrastructure as Code & Automation | Accepted | HashiCorp Terraform + Local / Free S3 Backend | **$0.00 / mo** |
| [**ADR-010**](#adr-010-cicd-pipeline--automated-deployment) | CI/CD Pipeline & Automated Deployment | Accepted | GitHub Actions (OIDC) + Amazon ECR + Remote Deploy | **$0.00 / mo** |
| [**ADR-011**](#adr-011-telemetry--cost-governance-guardrails) | Telemetry & Cost Governance Guardrails | Accepted | CloudWatch Free Metrics + $0.50 Billing Alarms | **$0.00 / mo** |
| **TOTAL** | **Consolidated Monthly Infrastructure Spend** | **Active** | **100% Free-Tier & Always-Free Tier Alignment** | **< $0.50 / mo** |

---

```
+==================================================================================================================+
|                               HOSPITALITY OS ZERO-COST FREE-TIER ARCHITECTURE TOPOLOGY                           |
|                                            (Target Monthly Spend: $0.00 USD)                                     |
+==================================================================================================================+
|                                                                                                                  |
|  [ GLOBAL EDGE & STATIC WEB DELIVERY ] (ADR-006)                                                                 |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | Amazon CloudFront CDN (Global Edge PoPs: 1 TB/mo Free Perpetual)                                       |    |
|    | • Serves React SPA & Guest QR Menus directly from Private Amazon S3 (5 GB Free Tier)                   |    |
|    +--------------------------------------------------------------------------------------------------------+    |
|                                                     | (Dynamic API Requests: api.platform.com)                   |
|                                                     v                                                            |
|  [ ZERO-COST LEAN VPC: 10.0.0.0/16 (0 NAT GATEWAYS, 0 PRIVATE LINK) ] (ADR-007)                                 |
|                                                                                                                  |
|    [ PUBLIC SUBNET (10.0.1.0/24) ]                                                                               |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | Amazon EC2 Instance: 1x t4g.micro (ARM64 Graviton2, 2 vCPUs, 1.0 GB RAM, 30GB gp3) — (ADR-002)         |    |
|    | (750 Hours / Month Free Tier)                                                                          |    |
|    |                                                                                                        |    |
|    |  +--------------------------------------------------------------------------------------------------+  |    |
|    |  | DOCKER COMPOSE MULTI-CONTAINER ENGINE (Single Host Network Stack)                                |  |    |
|    |  |                                                                                                  |  |    |
|    |  |  +---------------------------+     +--------------------------------+     +-------------------+  |  |    |
|    |  |  | NGINX Ingress Proxy       | --> | Django Modular Monolith API    | --> | Redis 7.2 Cache   |  |  |    |
|    |  |  | • Let's Encrypt (Certbot) |     | • Gunicorn WSGI (Port 8000)    |     | • AOF Persistence |  |  |    |
|    |  |  | • TLS 1.3 / Rate Limiting |     | • 2x Prefork Worker Processes  |     | • Celery Broker   |  |  |    |
|    |  |  | • Port 80 / 443 (ADR-003) |     | • Low Memory Heap (<250MB)     |     | • Port 6379(ADR-005)|  |
|    |  |  +---------------------------+     +--------------------------------+     +-------------------+  |  |    |
|    |  |                                                    |                                             |  |    |
|    |  |                                                    +-----> [ Celery Async Outbox Worker ]        |  |    |
|    |  |                                                            • Recipe BOM & GL Journal Balancing   |  |    |
|    |  +--------------------------------------------------------------------------------------------------+  |    |
|    +--------------------------------------------------------------------------------------------------------+    |
|                                                     |                                                            |
|                                                     | Private SQL Queries (TCP Port 5432)                        |
|                                                     v                                                            |
|    [ PRIVATE DATABASE SUBNET (10.0.2.0/24) ]                                                                     |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | Amazon RDS PostgreSQL 17 Single-AZ (Instance Class: db.t4g.micro / 2 vCPU / 1.0 GB RAM) — (ADR-004)    |    |
|    | (750 Hours / Month Free Tier + 20 GB gp3 SSD Storage + 7-Day Automated Snapshot Backups)               |    |
|    | • Security Group: Inbound TCP 5432 permitted solely from EC2 Security Group                            |    |
|    | • 0 Public Access / 0 Internet Routing                                                                  |    |
|    +--------------------------------------------------------------------------------------------------------+    |
|                                                                                                                  |
|  [ CI/CD & TELEMETRY CONTROL PLANE ] (ADR-008, ADR-009, ADR-010, ADR-011)                                        |
|    • GitHub Actions (OIDC STS Auth) -> Amazon ECR (500MB Free) -> SSH/SSM Deployment Trigger                    |
|    • CloudWatch Basic Metrics + Billing Alarm ($0.50 Threshold) -> Email Notification                            |
+==================================================================================================================+
```

---

## ADR-001: Cloud Provider Ecosystem Selection

### Status
**Accepted**

### Context & Problem Statement
Hospitality OS requires a resilient, cloud-hosted backbone to run its modular monolith API, background event workers, relational persistence, in-memory cache, and static client web SPAs for a single boutique client property (10 rooms, 30 dining seats, 20 bar stools).

The overarching operational constraint is **Zero Cloud Expenditure (< $0.50 USD / month total spend)** while retaining production-grade security, automated database backups, automated deployment pipelines, and meeting the performance requirement of $p_{95} \le 120\text{ ms}$.

### Decision Outcome
**Adopt Amazon Web Services (AWS)** under strict Free-Tier architectural parameters:
- 12-Month Free Tier: 750 hours/month `t4g.micro`/`t3.micro` EC2, 750 hours/month `db.t4g.micro`/`db.t3.micro` RDS PostgreSQL, 5 GB S3 Standard storage, 500 MB Amazon ECR private repository storage.
- Perpetual Always-Free Tier: Amazon CloudFront (1 TB/month data transfer out + 10,000,000 HTTP/S requests), 10 CloudWatch custom metrics, 3 CloudWatch metric alarms, AWS IAM, and AWS STS.

### Considered Options
1. **Option 1: Amazon Web Services (AWS Free Tier)** — 750h compute + 750h managed RDS + 1TB CloudFront CDN.
2. **Option 2: Google Cloud Platform (GCP Free Tier)** — e2-micro compute instance, but Cloud SQL has zero permanent free tier (incurs ~$35/mo minimum database cost).
3. **Option 3: Oracle Cloud Infrastructure (OCI Always Free)** — 4 OCPU Ampere ARM instances + 24GB RAM, but lacks managed open-source PostgreSQL 17 in the free tier and has lower regional availability.
4. **Option 4: Low-Cost VPS (Hetzner / DigitalOcean)** — Flat €4–€6/month, but lacks managed automated RDS backups, IAM OIDC federation, and native S3/CDN integrations.

### Pros and Cons Matrix

| Evaluation Criteria | Option 1: AWS Free Tier (Selected) | Option 2: GCP Free Tier | Option 3: OCI Always Free | Option 4: Low-Cost VPS |
| :--- | :--- | :--- | :--- | :--- |
| **Monthly Net Cost** | **$0.00 / month** (100% within Free-Tier limits) | **~$35.00 / month** (Cloud SQL is paid) | **$0.00 / month** | **€4.00 – €6.00 / month** |
| **Managed Relational DB** | **Included:** AWS RDS PostgreSQL 17 (750h free/mo with automated snapshots). | **None:** Must self-host Postgres on a tiny e2-micro instance. | **None:** Must self-host Postgres on VM. | **None:** Must manage raw Postgres on Linux. |
| **Global CDN & Edge** | **Included:** CloudFront (1 TB/mo free perpetual with TLS 1.3). | **Paid:** Cloud CDN requires Cloud Storage / LB. | **Limited:** OCI edge CDN has smaller PoP footprint. | **Requires 3rd Party:** Requires Cloudflare configuration. |
| **CI/CD Security** | **Native OIDC:** Zero static IAM keys needed for GitHub Actions. | **Native:** Workload Identity Federation. | **Complex:** OCI token management. | **High Risk:** Storing static SSH private keys in CI. |

### Consequences
* **Positive:** Complete cloud infrastructure spend remains $0.00/month; enterprise-grade RDS automated snapshots; native GitHub Actions OIDC integration.
* **Negative / Mitigation:** AWS 12-month free tier for EC2 and RDS expires after year 1.
  - *Mitigation:* After 12 months, migration to 3-year Savings Plans or switching to an OCI Always-Free standby or reserved instance (~$6.00/mo) is straightforward due to 100% containerized Docker Compose packaging.

---

## ADR-002: Single-Host Containerized Compute Plane

### Status
**Accepted**

### Context & Problem Statement
The enterprise baseline utilized AWS ECS Fargate serverless containers across Dual Availability Zones. However, ECS Fargate incurs baseline hourly vCPU and memory charges (~$10.61/mo) and requires an Application Load Balancer (~$17.68/mo) for traffic ingress.

Per [`docs/Enterprise Baseline/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/CAPACITY_SIZING.md), the workload for a single boutique property is:
- Baseline traffic: $0.28\text{ RPS}$, peak sustained traffic: $2.50\text{ RPS}$, offline burst replay: $10.00\text{ RPS}$.
- Little's Law concurrency: $0.1125$ concurrent worker processes at peak sustained load.
- Memory requirement: Django API + Gunicorn consumes ~180MB RAM; Celery worker consumes ~120MB RAM; total compute memory footprint is < 400MB.

### Decision Outcome
**Adopt 1x Amazon EC2 `t4g.micro` (ARM64 Graviton2, 2 vCPUs, 1.0 GB RAM, 30 GB gp3 Root Disk) running Docker Compose** to host the Django modular monolith, Celery background worker, in-container Redis, and NGINX reverse proxy on a single unified host.

### Considered Options
1. **Option 1: 1x EC2 `t4g.micro` with Docker Compose (Selected)** — 750 hours/month free tier, 2 vCPUs, 1GB RAM, ARM64 energy efficiency, sub-millisecond local container IPC.
2. **Option 2: AWS ECS Fargate** — Serverless tasks with dedicated network interfaces, but introduces $28.29/month in compute and ALB costs.
3. **Option 3: AWS Lambda + Amazon API Gateway** — Serverless functions, but cold starts ($800–2,500ms) violate the $p_{95} \le 120\text{ ms}$ SLO and complicate long-running Celery outbox loops.

### Pros and Cons Matrix

| Evaluation Criteria | Option 1: EC2 `t4g.micro` + Docker Compose (Selected) | Option 2: AWS ECS Fargate | Option 3: AWS Lambda + API Gateway |
| :--- | :--- | :--- | :--- |
| **Monthly Compute Cost** | **$0.00 / month** (750 hours Free Tier eligible) | **$10.61 / month** (Compute only) | **$0.00 – $2.00 / month** (Variable) |
| **Cold Start Latency** | **Zero Cold Starts:** Warm Gunicorn pre-fork processes deliver $p_{50} < 45\text{ ms}$. | **Zero Cold Starts:** Tasks run continuously. | **High Cold Starts:** 800ms–2,500ms on Python/Django cold invocations. |
| **Background Processing** | **Native:** Celery worker runs alongside Django connected to local Redis. | **Native:** Dedicated worker task. | **Unnatural:** Requires SQS / EventBridge event refactoring. |
| **Operational Overhead** | **Low:** Single `docker-compose.yml` file defines all services and volumes. | **Low:** Managed container tasks. | **Low:** Serverless abstraction. |

### Exact Implementation Directives (`docker-compose.yml` Blueprint)
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: hospitality_nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - web

  web:
    image: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/hospitality-os:latest
    container_name: hospitality_api
    restart: always
    command: gunicorn core_hub.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 2 --timeout 30
    env_file: .env.production
    depends_on:
      - redis

  celery:
    image: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/hospitality-os:latest
    container_name: hospitality_celery
    restart: always
    command: celery -A core_hub worker -l INFO -c 2
    env_file: .env.production
    depends_on:
      - redis

  redis:
    image: redis:7.2-alpine
    container_name: hospitality_redis
    restart: always
    command: redis-server --appendonly yes --maxmemory 128mb --maxmemory-policy volatile-lru
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### Consequences
* **Positive:** Fits entirely within the 750-hour AWS EC2 Free Tier; eliminates ALB and NAT Gateway costs; sub-millisecond local network latency between Django, Redis, and NGINX.
* **Negative / Mitigation:** Single point of failure (Single-AZ EC2).
  - *Mitigation:* The on-premise POS terminals operate with **72-Hour Local-First Autonomy** (SQLite WAL mode). If the EC2 host reboots, local property operations are unaffected. Automated EC2 Auto-Recovery automatically restarts the instance if underlying hardware degrades.

---

## ADR-003: Edge Ingress, Reverse Proxy & SSL Termination

### Status
**Accepted**

### Context & Problem Statement
The enterprise baseline utilized an AWS Application Load Balancer (ALB, $17.68/mo) integrated with AWS WAF ($11.06/mo) and ACM certificates. To achieve a $0.00/month cost baseline, ingress routing, TLS termination, and application security must be handled without managed AWS load balancers.

Requirements:
- Enforce TLS 1.3 encryption for all incoming API traffic.
- Automated, zero-touch SSL certificate provisioning and renewal.
- Layer 7 rate limiting (30 req/min for booking, 120 req/min for POS, 60 req/min for PMS).
- Path-based routing and static asset compression (Gzip/Brotli).

### Decision Outcome
**Deploy an In-Container NGINX Reverse Proxy with Let's Encrypt (Certbot Automated Renewal Sidecar)** running inside the Docker Compose network on the EC2 host.

### Considered Options
1. **Option 1: In-Container NGINX + Let's Encrypt (Certbot) (Selected)** — Open-source NGINX container handling TLS 1.3 termination, HTTP/2, Let's Encrypt SSL auto-renewal, and `limit_req_zone` rate limiting at $0.00 cost.
2. **Option 2: AWS Application Load Balancer (ALB) + AWS WAF** — Managed load balancer with ACM, but costs $28.74/month minimum.
3. **Option 3: Traefik Proxy with Let's Encrypt** — Dynamic reverse proxy, but slightly higher memory footprint (~60MB) compared to NGINX Alpine (~15MB).

### Pros and Cons Matrix

| Evaluation Criteria | Option 1: In-Container NGINX + Certbot (Selected) | Option 2: AWS ALB + AWS WAF | Option 3: Traefik Proxy |
| :--- | :--- | :--- | :--- |
| **Monthly Fixed Cost** | **$0.00 / month** | **$28.74 / month** ($17.68 ALB + $11.06 WAF) | **$0.00 / month** |
| **Memory Footprint** | **Ultra-Light:** ~12–18 MB RAM (NGINX Alpine). | **0 MB on host:** Offloaded to AWS managed infrastructure. | **Moderate:** ~50–70 MB RAM. |
| **Rate Limiting** | **Granular:** Native `limit_req_zone` enforces exact 30/60/120 req/min limits. | **Managed:** AWS WAF rate-based rules. | **Granular:** Native Traefik middleware. |
| **SSL Certificate Renewal**| **Automated:** Certbot cron container checks and renews certificates automatically every 60 days. | **Automated:** AWS ACM handles renewals seamlessly. | **Automated:** Built-in ACME challenge resolver. |

### Exact Implementation Directives (`nginx.conf` Rate Limiting & SSL Blueprint)
```nginx
# Rate Limiting Zones
limit_req_zone $binary_remote_addr zone=booking_limit:10m rate=30r/m;
limit_req_zone $binary_remote_addr zone=pos_limit:10m rate=120r/m;
limit_req_zone $binary_remote_addr zone=pms_limit:10m rate=60r/m;

server {
    listen 80;
    server_name api.platform.com;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name api.platform.com;

    ssl_certificate /etc/letsencrypt/live/api.platform.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.platform.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    # Booking Engine API Rate Limit
    location /api/v1/booking/ {
        limit_req zone=booking_limit burst=10 nodelay;
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # POS Terminal API Rate Limit
    location /api/v1/pos/ {
        limit_req zone=pos_limit burst=30 nodelay;
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Default API Gateway Route
    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### Consequences
* **Positive:** Completely eliminates $28.74/month in ALB/WAF fees; provides microsecond reverse proxy latency; automated Let's Encrypt TLS 1.3 encryption.
* **Negative / Mitigation:** NGINX configuration must be version-controlled and maintained inside the repository.
  - *Mitigation:* NGINX configuration files are stored under `/infrastructure/nginx/` and mounted as read-only volumes.

---

## ADR-004: Relational Persistence Plane

### Status
**Accepted**

### Context & Problem Statement
The persistence plane stores the authoritative business ledger, room reservations, and inventory data.

Per [`docs/Enterprise Baseline/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/CAPACITY_SIZING.md#section-4):
- 3-year relational data growth for a single property is **2.82 GB**.
- Transaction commit latency must satisfy $p_{50} \le 12\text{ ms}$.
- Hard connection cap: Maximum **30 active database client sockets**.
- Multi-AZ RDS doubles database compute and storage costs ($37.80/mo).

### Decision Outcome
**Adopt Amazon RDS PostgreSQL 17 Single-AZ (`db.t4g.micro` or `db.t3.micro`, 20 GB gp3 SSD Storage) with automated 7-day snapshot retention**, fitting 100% within the AWS 12-Month Free Tier.

### Considered Options
1. **Option 1: AWS RDS PostgreSQL 17 Single-AZ (`db.t4g.micro`, 20GB gp3) (Selected)** — 750 hours/month free tier, managed PostgreSQL 17 engine, automated daily backups with 7-day retention, 3,000 baseline IOPS.
2. **Option 2: AWS RDS PostgreSQL 17 Multi-AZ** — Synchronous standby replica across 2 AZs, but incurs $37.80/month (not free-tier eligible).
3. **Option 3: Self-Hosted PostgreSQL 17 Container on EC2** — Running PostgreSQL inside Docker Compose on the `t4g.micro` instance, but risks out-of-memory (OOM) host crashes and lacks automated cloud snapshots.

### Pros and Cons Matrix

| Evaluation Criteria | Option 1: RDS PostgreSQL Single-AZ (Selected) | Option 2: RDS PostgreSQL Multi-AZ | Option 3: Self-Hosted Postgres on EC2 |
| :--- | :--- | :--- | :--- |
| **Monthly Database Cost** | **$0.00 / month** (750h Free Tier + 20GB gp3 included) | **$37.80 / month** | **$0.00 / month** |
| **Memory Isolation** | **Dedicated 1.0 GB RAM:** PostgreSQL has its own isolated kernel memory; zero CPU/RAM contention with app containers. | **Dedicated 1.0 GB RAM:** Isolated memory. | **Severe Contention:** Competes with Django, Celery, Redis, and NGINX for 1.0 GB host RAM. |
| **Automated Backups** | **Turnkey Managed:** Daily physical snapshots with point-in-time recovery retained for 7 days at $0.00. | **Turnkey Managed:** Point-in-time recovery across AZs. | **Fragile:** Requires custom `pg_dump` cron scripts; risk of silent backup failures. |
| **Commit Latency ($p_{50}$)** | **Optimal:** Local gp3 SSD caching delivers $p_{50} < 12\text{ ms}$ commit latency. | **Good:** Slightly higher commit latency due to synchronous inter-AZ write. | **Variable:** Dependent on host disk I/O contention. |

### Exact Configuration Directives
* **RDS Engine:** PostgreSQL 17.x
* **Instance Sizing:** `db.t4g.micro` (ARM Graviton2, 2 vCPUs, 1.0 GB RAM)
* **Allocated Storage:** 20 GB General Purpose SSD (gp3)
* **Backup Retention:** 7 Days (Automated snapshot window: `02:00–02:30 UTC`)
* **Parameter Group Directives:**
  - `max_connections = 25`
  - `shared_buffers = 256MB`
  - `work_mem = 8MB`
  - `statement_timeout = 5000` (5.0s)
  - `idle_in_transaction_session_timeout = 10000` (10.0s)

### Consequences
* **Positive:** Zero database hosting cost; 100% isolated database memory plane; automated daily backups managed by AWS.
* **Negative / Mitigation:** Single-AZ deployment lacks automatic multi-AZ hardware failover.
  - *Mitigation:* Single-property boutique operations tolerate a 15-minute RTO snapshot restoration in catastrophic AWS hardware failures; local POS terminals continue operating autonomously via SQLite WAL mode for up to 72 hours.

---

## ADR-005: Embedded Ephemeral State & Task Broker

### Status
**Accepted**

### Context & Problem Statement
Hospitality OS requires an in-memory caching and message queuing layer for:
1. Distributed reservation locks (`pms:lock:*` with 10s TTL).
2. Idempotency replay de-duplication buffers (`idemp:pos:*` with 72h TTL).
3. Celery asynchronous task broker queue (recipe BOM depletion, night audit ledger balancing).

Standalone AWS ElastiCache for Redis costs **$14.60/month** and is not covered under the perpetual free tier.

### Decision Outcome
**Deploy an Embedded In-Container Redis 7.2 Alpine instance via Docker Compose on the EC2 host with Append-Only File (AOF) persistence enabled and a 128 MB RAM boundary.**

### Considered Options
1. **Option 1: In-Container Redis 7.2 Alpine on EC2 (Selected)** — Lightweight containerized Redis (~15MB base memory) configured with `maxmemory 128mb`, `volatile-lru` eviction, and AOF disk persistence. Cost: $0.00/mo.
2. **Option 2: Amazon ElastiCache for Redis (`cache.t4g.micro`)** — Managed standalone Redis node, but costs $14.60/month.
3. **Option 3: PostgreSQL-Based Celery Broker (django-db / kombu)** — Using relational database as message queue, but causes unnecessary database write locks and table bloat.

### Pros and Cons Matrix

| Evaluation Criteria | Option 1: In-Container Redis 7.2 (Selected) | Option 2: Amazon ElastiCache Redis | Option 3: PostgreSQL Database Queue |
| :--- | :--- | :--- | :--- |
| **Monthly Cache Cost** | **$0.00 / month** | **$14.60 / month** | **$0.00 / month** |
| **Latency & Performance** | **Sub-Millisecond (< 0.2ms):** In-memory localhost TCP/Unix socket communication. | **Sub-Millisecond (< 1.0ms):** Network transit over private VPC subnet. | **Slow (10–25ms):** Disk-bound relational table polling. |
| **Memory Footprint** | **Strictly Bounded:** Capped at 128 MB RAM via `maxmemory` parameter. | **Dedicated:** 0.5 GB RAM. | **Shared DB Buffers:** Consumes Postgres shared memory. |
| **Durability** | **High:** Append-Only File (`appendfsync everysec`) persisted to named Docker volume. | **High:** AOF persistence with automated node replacement. | **High:** ACID relational table durability. |

### Exact Implementation Parameters
```text
# Redis Command Arguments in Docker Compose
redis-server \
    --appendonly yes \
    --appendfsync everysec \
    --maxmemory 128mb \
    --maxmemory-policy volatile-lru \
    --save 900 1 \
    --save 300 10
```

### Consequences
* **Positive:** Completely eliminates $14.60/month ElastiCache fee; delivers ultra-fast sub-millisecond lock acquisition; bounded memory consumption protects host stability.
* **Negative / Mitigation:** Ephemeral container storage could be lost if host filesystem is deleted.
  - *Mitigation:* Named Docker volume `redis_data` is mounted to persistent host gp3 EBS storage, preserving AOF logs across container restarts.

---

## ADR-006: Client Web Delivery & Storage Archival

### Status
**Accepted**

### Context & Problem Statement
The platform must serve public booking single-page applications (React SPAs), mobile QR code menus, staff consoles, and archive finalized PDF folios and daily night audit ledgers.

Requirements:
- Global edge caching with sub-second page load times ($< 800\text{ ms}$).
- Offload static asset delivery completely from the EC2 compute host.
- Zero data transfer egress costs.

### Decision Outcome
**Adopt Amazon S3 (5 GB Free Tier) fronted by Amazon CloudFront CDN (1 TB/month Perpetual Free Tier) with Origin Access Control (OAC) and TLS 1.3.**

### Considered Options
1. **Option 1: Amazon S3 + Amazon CloudFront (OAC) (Selected)** — 5 GB free S3 storage + 1 TB/month free CloudFront CDN edge transfer. 100% private S3 bucket with SigV4 OAC.
2. **Option 2: Serving Static Files Directly from EC2 NGINX** — Packing React builds inside the NGINX container on EC2, but consumes EC2 network bandwidth and disk storage.
3. **Option 3: Cloudflare Pages + External Storage** — Multi-vendor configuration separating edge hosting from AWS.

### Pros and Cons Matrix

| Evaluation Criteria | Option 1: S3 + CloudFront (Selected) | Option 2: EC2 NGINX Static Hosting | Option 3: Cloudflare Pages |
| :--- | :--- | :--- | :--- |
| **Monthly Storage & CDN Cost** | **$0.00 / month** (5GB S3 + 1TB CloudFront Free) | **$0.00 / month** (Uses EC2 EBS disk) | **$0.00 / month** |
| **Global TTFB Latency** | **< 20 ms:** Cached at 600+ Global Anycast edge PoPs. | **80–250 ms:** Routed across WAN to single EC2 host. | **< 20 ms:** Global Anycast edge. |
| **Host Compute Offload** | **100% Offload:** 0% CPU, 0% RAM, 0% bandwidth consumed on EC2. | **Contention:** NGINX worker threads serve static assets instead of proxying APIs. | **100% Offload.** |
| **Security & Privacy** | **Private Origin:** S3 public access completely blocked; restricted strictly to CloudFront OAC. | **Public Port:** Exposed directly via NGINX port 443. | **Dual Vendor:** Requires cross-cloud API token management. |

### Consequences
* **Positive:** 100% free static web delivery; sub-20ms asset loading worldwide; complete compute offload for the EC2 host.
* **Negative / Mitigation:** Deploying frontend updates requires invalidating CloudFront cache.
  - *Mitigation:* CI/CD pipeline issues an automated `aws cloudfront create-invalidation --paths "/*"` command upon frontend merges.

---

## ADR-007: Zero-Cost Lean VPC & Subnet Isolation

### Status
**Accepted**

### Context & Problem Statement
Enterprise AWS VPC architectures provision NAT Gateways ($32.85/month each) and VPC Interface Endpoints ($7.20/month per endpoint $\times 6 = $43.20/month). Together, network isolation services account for over **$75.50/month**, which completely violates our zero-cost requirement.

Security requirements:
- Relational database (RDS) must **never** be directly reachable from the public internet.
- EC2 host must only expose ports `80` (HTTP) and `443` (HTTPS).
- Achieve strict network isolation with **0 NAT Gateways and 0 VPC PrivateLink Endpoints ($0.00 spend)**.

### Decision Outcome
**Implement a 2-Tier Lean VPC Architecture (`10.0.0.0/16`) comprising 1 Public Subnet and 2 Isolated Private Database Subnets, governed strictly by AWS Security Groups with 0 NAT Gateways and 0 PrivateLink Endpoints.**

```
+==================================================================================================================+
|                                    LEAN VPC ARCHITECTURE & SECURITY GROUP ISOLATION                              |
+==================================================================================================================+
|                                                                                                                  |
|  [ PUBLIC SUBNET (10.0.1.0/24) ]                                                                                 |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | SECURITY GROUP: sg_hospitality_ec2                                                                       |    |
|  | • Inbound: TCP 80 (0.0.0.0/0), TCP 443 (0.0.0.0/0)                                                       |    |
|  | • Outbound: ALL Traffic (0.0.0.0/0 via Internet Gateway - Free Egress for Package Updates & Stripe API)  |    |
|  |                                                                                                          |    |
|  |   [ Amazon EC2 Instance: t4g.micro (10.0.1.50) ]                                                         |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|                                                     |                                                            |
|                                                     | Inbound TCP 5432 permitted ONLY from sg_hospitality_ec2    |
|                                                     v                                                            |
|  [ PRIVATE DATABASE SUBNET GROUP (10.0.2.0/24 & 10.0.3.0/24) ]                                                  |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | SECURITY GROUP: sg_hospitality_rds                                                                       |    |
|  | • Inbound: TCP 5432 <- Strictly restricted to sg_hospitality_ec2 (ZERO Public Access)                    |    |
|  | • Outbound: NONE (Implicit Deny)                                                                         |    |
|  | • Routing Table: Local Only (10.0.0.0/16 -> local). Zero Internet Gateway / Zero NAT Gateway             |    |
|  |                                                                                                          |    |
|  |   [ Amazon RDS PostgreSQL 17 Single-AZ (10.0.2.100) ]                                                    |    |
|  +----------------------------------------------------------------------------------------------------------+    |
+==================================================================================================================+
```

### Considered Options
1. **Option 1: Lean VPC with Public EC2 + Private Isolated RDS (Selected)** — Free Internet Gateway attached to Public Subnet; EC2 connects to RDS over private AWS backbone; RDS has no route to internet. Cost: $0.00/mo.
2. **Option 2: Enterprise Multi-AZ VPC with NAT Gateways & PrivateLink** — Private subnets for all compute, but incurs $75.50/month in networking fees.
3. **Option 3: Public RDS with IP Whitelisting** — RDS placed in public subnet with public IP, but introduces severe external attack surface risks.

### Pros and Cons Matrix

| Evaluation Criteria | Option 1: Lean VPC (Selected) | Option 2: Enterprise NAT VPC | Option 3: Public RDS |
| :--- | :--- | :--- | :--- |
| **Monthly Network Cost** | **$0.00 / month** (0 NAT GW, 0 PrivateLink) | **$75.50 / month** | **$0.00 / month** |
| **Database Security** | **100% Private:** RDS has `PubliclyAccessible = false` and no route to internet; reachable only via EC2 SG. | **100% Private:** Complete private subnet isolation. | **High Risk:** Publicly accessible endpoint exposed to automated brute-force attacks. |
| **Outbound Internet Access** | **Direct via IGW:** EC2 has public IP for package updates and Stripe API calls at zero cost. | **Via NAT Gateway:** Secure, but expensive data processing fees. | **Direct via IGW.** |

### Consequences
* **Positive:** Saves $75.50/month in VPC infrastructure costs; enforces complete network-level isolation for the PostgreSQL database.
* **Negative / Mitigation:** EC2 instance resides in a public subnet.
  - *Mitigation:* Security group `sg_hospitality_ec2` allows inbound connections strictly on ports `80` and `443`. SSH port `22` is closed by default; remote management is conducted via AWS Systems Manager (SSM) Session Manager (Free Tier).

---

## ADR-008: Secrets Management & Runtime Configuration

### Status
**Accepted**

### Context & Problem Statement
The enterprise baseline utilized AWS Secrets Manager ($0.40/secret/mo) and AWS KMS Customer Managed Keys ($1.00/mo) for secret rotation and envelope encryption.

Requirements:
- Secure injection of database passwords, Stripe API keys, and JWT RSA signing keys.
- Zero plaintext secrets stored in source control.
- Zero monthly spend on KMS CMKs or Secrets Manager.

### Decision Outcome
**Inject environment secrets at runtime via host-level `.env.production` files managed securely through GitHub Actions Repository Secrets and AWS IAM Instance Profiles with Amazon SSM Session Manager.**

### Considered Options
1. **Option 1: GitHub Secrets + Host-Level Encrypted Environment Files (Selected)** — CI/CD deploys secrets securely to the EC2 host during deployment or via AWS SSM Parameter Store Standard Tier ($0.00 free tier).
2. **Option 2: AWS Secrets Manager + KMS Customer Managed Key** — Managed secret rotation, but incurs $1.40–$3.00/month.
3. **Option 3: Hardcoded Environment Variables in Docker Image** — Plaintext secrets baked into container image (Strictly Prohibited).

### Pros and Cons Matrix

| Evaluation Criteria | Option 1: GitHub Secrets / Host Env (Selected) | Option 2: AWS Secrets Manager + KMS | Option 3: Hardcoded in Image |
| :--- | :--- | :--- | :--- |
| **Monthly Secrets Cost** | **$0.00 / month** | **~$2.50 / month** | **$0.00 / month** |
| **Security Posture** | **High:** Encrypted in GitHub Actions; stored with `chmod 600` root permissions on EC2; never committed to Git. | **Maximum:** Automated rotation and KMS envelope encryption. | **Critical Vulnerability:** Credentials exposed in image layers and Git history. |
| **Deployment Complexity**| **Simple:** Standard Docker Compose `.env` injection. | **Moderate:** Requires AWS SDK / entrypoint secret fetching. | **Trivial.** |

### Consequences
* **Positive:** $0.00/month secrets management; full compliance with Git security standards; zero secret leakage.
* **Negative / Mitigation:** Rotating a secret requires updating GitHub Repository Secrets and triggering a deployment.
  - *Mitigation:* Handled via automated CI/CD redeployment workflow.

---

## ADR-009: Infrastructure as Code & Automation

### Status
**Accepted**

### Context & Problem Statement
To guarantee environment reproducibility, eliminate configuration drift, and enable one-click disaster recovery, the entire lean cloud footprint (VPC, Subnets, Security Groups, EC2, RDS, S3, CloudFront) must be defined as declarative code.

### Decision Outcome
**Adopt HashiCorp Terraform with Local or Free-Tier S3 Remote State Backend to provision and manage the entire AWS Free-Tier infrastructure deterministically.**

### Considered Options
1. **Option 1: HashiCorp Terraform (Selected)** — Open-source declarative HCL configuration managing AWS provider resources with precise state tracking. Cost: $0.00/mo.
2. **Option 2: AWS CloudFormation** — AWS native JSON/YAML templates.
3. **Option 3: Manual AWS Management Console Provisioning** — ClickOps configuration (Prohibited due to lack of traceability).

### Pros and Cons Matrix

| Evaluation Criteria | Option 1: HashiCorp Terraform (Selected) | Option 2: AWS CloudFormation | Option 3: Manual Console (ClickOps) |
| :--- | :--- | :--- | :--- |
| **Tooling Cost** | **$0.00 / month** | **$0.00 / month** | **$0.00 / month** |
| **Modularity & Reusability**| **Superior:** Clean reusable modules (`vpc`, `ec2`, `rds`, `s3`, `cloudfront`). | **Moderate:** Verbose YAML stacks. | **Zero:** Cannot be replicated or versioned. |
| **State Drift Detection** | **Native:** `terraform plan` compares active cloud state with declared configuration. | **Moderate:** CloudFormation drift detection. | **None:** Impossible to detect silent changes. |

### Exact Implementation Directives
```hcl
# Terraform Root Configuration for Free-Tier Deployment
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  backend "s3" {
    bucket  = "hospitality-os-terraform-state-free-tier"
    key     = "production/terraform.tfstate"
    region  = "ap-south-1"
    encrypt = true
  }
}
```

### Consequences
* **Positive:** 100% reproducible single-property infrastructure; zero configuration drift; instant environment recreation in any AWS region in < 10 minutes.
* **Negative / Mitigation:** State file concurrency must be managed.
  - *Mitigation:* Single-developer / automated CI deployment model avoids concurrency collisions; S3 native versioning protects state file history.

---

## ADR-010: CI/CD Pipeline & Automated Deployment

### Status
**Accepted**

### Context & Problem Statement
Deploying container updates, database migrations, and frontend assets must occur through a fully automated, secure Continuous Integration and Continuous Delivery (CI/CD) pipeline without persistent AWS root credentials or paid runner instances.

### Decision Outcome
**Adopt GitHub Actions utilizing AWS IAM OpenID Connect (OIDC) Federated Authentication to build ARM64 container images, push to Amazon ECR (500 MB Free Tier), and trigger automated `docker compose pull && docker compose up -d` deployments via AWS SSM Session Manager or SSH.**

### Considered Options
1. **Option 1: GitHub Actions + AWS IAM OIDC + Amazon ECR (Selected)** — Ephemeral STS token exchange (zero static AWS keys), free GitHub Actions hosted runners, 500 MB free ECR storage, automated remote container restart. Cost: $0.00/mo.
2. **Option 2: Dedicated Self-Hosted CI/CD Server (Jenkins on EC2)** — Requires dedicated VM ($15–$25/mo).
3. **Option 3: Manual SSH Deployments by Engineers** — Fragile and error-prone manual procedure.

### Pros and Cons Matrix

| Evaluation Criteria | Option 1: GitHub Actions + OIDC (Selected) | Option 2: Self-Hosted Jenkins | Option 3: Manual SSH Deploy |
| :--- | :--- | :--- | :--- |
| **Monthly Pipeline Cost** | **$0.00 / month** (2,000 Free Actions Minutes + 500MB ECR Free) | **$15.00 – $25.00 / month** | **$0.00 / month** |
| **Credential Security** | **Maximum:** Short-lived 15-minute STS session tokens; zero static AWS keys stored in GitHub. | **Moderate:** IAM instance profiles on Jenkins host. | **Critical Risk:** Static SSH private keys shared among engineers. |
| **Automation & Speed** | **Fully Automated:** Builds ARM64 Docker images, runs `pytest`, pushes to ECR, and updates EC2 in < 4 minutes. | **Fully Automated.** | **Manual & Slow:** 15–30 minutes per release. |

### Exact Implementation Directives (Deployment Pipeline Step)
```yaml
name: Production Deployment Pipeline

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4

      - name: Configure AWS Credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/HospitalityGitHubDeployRole
          aws-region: ap-south-1

      - name: Log in to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build & Push ARM64 Container Image
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/arm64
          push: true
          tags: ${{ steps.login-ecr.outputs.registry }}/hospitality-os:latest

      - name: Deploy to EC2 via AWS SSM
        run: |
          aws ssm send-command \
            --instance-ids "${{ secrets.EC2_INSTANCE_ID }}" \
            --document-name "AWS-RunShellScript" \
            --parameters 'commands=[
              "aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin ${{ steps.login-ecr.outputs.registry }}",
              "cd /opt/hospitality-os && docker compose pull && docker compose up -d --remove-orphans",
              "docker system prune -af --volumes"
            ]'
```

### Consequences
* **Positive:** 100% automated zero-cost CI/CD pipeline; zero static AWS credentials in GitHub; automated Docker layer pruning prevents disk exhaustion on EC2.
* **Negative / Mitigation:** Single-host container restart incurs ~2–5 seconds of transient API interruption during `docker compose up -d`.
  - *Mitigation:* Deployments are scheduled during low-traffic maintenance windows (e.g., `03:00 UTC`); on-premise POS terminals buffer transactions locally during the brief restart window.

---

## ADR-011: Telemetry & Cost Governance Guardrails

### Status
**Accepted**

### Context & Problem Statement
Operating within a strict **< $0.50 USD / month** budget requires active, continuous cost guardrails to detect and prevent accidental provisioning of paid AWS resources or runaway metric ingestion fees.

Requirements:
- Immediate alerting if monthly AWS spend exceeds **$0.50 USD**.
- Free-tier system health monitoring (CPU, RAM, Disk Space, RDS Storage).
- Zero paid monitoring agent licenses.

### Decision Outcome
**Leverage Amazon CloudWatch Free Tier (10 Free Metrics, 3 Free Alarms, 5 GB Free Log Ingestion) paired with an AWS Billing Alarm set to $0.50 USD and an in-container `/health/` endpoint.**

### Considered Options
1. **Option 1: CloudWatch Free Tier + $0.50 Billing Alarm (Selected)** — 10 free metrics, 3 free metric alarms, AWS Billing budget alert notifying DevOps email via SNS at $0.50 spend. Cost: $0.00/mo.
2. **Option 2: Third-Party SaaS APM (Datadog / New Relic)** — Commercial APM agents, but incur $15–$30/month per host.
3. **Option 3: Self-Hosted Prometheus + Grafana Container on EC2** — Open-source TSDB, but consumes ~250MB of the 1GB EC2 RAM, causing memory pressure.

### Pros and Cons Matrix

| Evaluation Criteria | Option 1: CloudWatch Free Tier (Selected) | Option 2: Third-Party APM (Datadog) | Option 3: Prometheus on EC2 |
| :--- | :--- | :--- | :--- |
| **Monthly Telemetry Cost** | **$0.00 / month** | **$15.00 – $30.00 / month** | **$0.00 / month** |
| **Host Resource Overhead** | **0% Host Overhead:** Managed AWS metrics emitted agentless by hypervisor. | **Moderate:** Agent consumes 50–80 MB RAM. | **Heavy:** Consumes 200–300 MB RAM and disk IOPS. |
| **Cost Protection Guarantee** | **Active:** Billing alarm triggers immediate email notification at $0.50 spend threshold. | **None:** External tool cannot track AWS billing metrics. | **None.** |

### Exact Implementation Directives
```hcl
# CloudWatch Billing Alarm for $0.50 Threshold
resource "aws_cloudwatch_metric_alarm" "billing_alarm_free_tier" {
  alarm_name          = "hospitality-os-free-tier-budget-breach"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600 # 6 Hours
  statistic           = "Maximum"
  threshold           = 0.50
  alarm_description   = "CRITICAL ALERT: Monthly AWS spend has exceeded $0.50 USD!"
  alarm_actions       = [aws_sns_topic.billing_alerts.arn]

  dimensions = {
    Currency = "USD"
  }
}
```

### Consequences
* **Positive:** Guaranteed financial safety with immediate alert if any billable resource is created; 0% compute overhead on the EC2 host; 100% free monitoring.
* **Negative / Mitigation:** CloudWatch billing metrics update every 6 hours rather than instantaneously.
  - *Mitigation:* Infrastructure is provisioned strictly via Terraform, preventing accidental manual creation of expensive resources.

---

## Master Free-Tier Architecture Governance & Verification

All decisions recorded in this collection (ADR-001 through ADR-011) establish the immutable baseline for Hospitality OS Single-Property **Zero-Cost Free-Tier Deployments**. 

### Final Verification Checklist
- [x] **Compute:** 1x `t4g.micro` EC2 instance (750 hours/month Free Tier eligible).
- [x] **Ingress & SSL:** In-Container NGINX + Let's Encrypt Certbot ($0.00 spend; 0 ALB / 0 WAF).
- [x] **Database:** RDS PostgreSQL 17 Single-AZ `db.t4g.micro`, 20GB gp3 (750 hours/month Free Tier eligible).
- [x] **Cache & Queue:** In-Container Redis 7.2 Alpine on EC2 with AOF persistence ($0.00 spend; 0 ElastiCache).
- [x] **Web Delivery:** S3 (5GB Free) + CloudFront (1TB Free perpetual).
- [x] **Networking:** Lean VPC with 0 NAT Gateways and 0 PrivateLink Endpoints ($0.00 spend).
- [x] **Secrets & CI/CD:** Docker environment injection + GitHub Actions OIDC + ECR (500MB Free).
- [x] **Billing Guardrail:** CloudWatch Billing Alarm active at **$0.50 USD threshold**.
- [x] **Consolidated Monthly Cost:** **$0.00 USD / month (< $0.50 USD ceiling)**.
