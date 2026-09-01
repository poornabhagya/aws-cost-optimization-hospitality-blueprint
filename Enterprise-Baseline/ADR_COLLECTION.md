# Architecture Decision Records (ADR) Collection
## Single-Property Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Enterprise Architecture Decision Records (ADR) Master Collection
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 1.0.0 (Production Architecture Baseline)
* **Status:** Accepted / Approved Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Environment:** Amazon Web Services (AWS) Cloud Infrastructure + On-Premise Edge Terminals
* **Aligned Specifications:**
  - [`docs/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/BRD_SPECIFICATION.md) (Business Rules, 72h POS Offline Autonomy, Append-Only GL, Recipe BOM)
  - [`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md) ($p_{95} \le 120\text{ ms}$, 99.9% Availability, TLS 1.3, Rate Limits, 30 DB Sockets)
  - [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md) (0.50 vCPU / 1GB RAM Compute, 512MB Redis, 0.50 vCPU / 2GB / 20GB PostgreSQL)
  - [`docs/HLA_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/HLA_SPECIFICATION.md) (7-Tier Architectural Topology Reference)

---

## Master ADR Index

| ADR ID | Decision Title | Status | Primary AWS Service / Tech | Tier Alignment |
| :--- | :--- | :--- | :--- | :--- |
| [**ADR-001**](#adr-001-cloud-provider-ecosystem-selection) | Cloud Provider Ecosystem Selection | Accepted | Amazon Web Services (AWS) | Global Infrastructure |
| [**ADR-002**](#adr-002-stateless-compute-execution-plane) | Stateless Compute Execution Plane | Accepted | AWS ECS Fargate (Serverless Containers) | Tier 3: Stateless Compute |
| [**ADR-003**](#adr-003-client-asset-delivery--global-edge-caching) | Client Asset Delivery & Global Edge Caching | Accepted | AWS S3 + Amazon CloudFront (OAC) | Tier 1 & Tier 2: Edge Delivery |
| [**ADR-004**](#adr-004-relational-persistence--connection-multiplexing) | Relational Persistence & Connection Multiplexing | Accepted | AWS RDS PostgreSQL + PgBouncer | Tier 5: Persistence Plane |
| [**ADR-005**](#adr-005-in-memory-ephemeral-state--event-streaming) | In-Memory Ephemeral State & Event Streaming | Accepted | AWS ElastiCache for Redis (AOF) | Tier 4: Ephemeral State |
| [**ADR-006**](#adr-006-immutable-compliance--long-term-financial-archival) | Immutable Compliance & Long-Term Financial Archival | Accepted | AWS S3 Glacier Vault (Object Lock WORM) | Tier 6: Durable Object Vault |
| [**ADR-007**](#adr-007-edge-routing-tls-termination--application-security) | Edge Routing, TLS Termination & Application Security | Accepted | AWS Application Load Balancer (ALB) + AWS WAF | Tier 2: Edge Ingress & Routing |
| [**ADR-008**](#adr-008-secrets-management-parameter-configuration--cryptography) | Secrets Management, Parameter Configuration & Cryptography | Accepted | AWS KMS + SSM Parameter Store + ACM | Security & Governance Plane |
| [**ADR-009**](#adr-009-infrastructure-as-code--state-management) | Infrastructure as Code & State Management | Accepted | HashiCorp Terraform + S3 & DynamoDB Lock | Infrastructure Automation |
| [**ADR-010**](#adr-010-cicd-pipeline--automated-cloud-authentication) | CI/CD Pipeline & Automated Cloud Authentication | Accepted | GitHub Actions + AWS IAM OIDC Federation | DevOps & Delivery Plane |
| [**ADR-011**](#adr-011-telemetry-observability--operational-alerting) | Telemetry, Observability & Operational Alerting | Accepted | Amazon CloudWatch (Logs, Metrics, Alarms) + SNS | Tier 7: Observability Plane |

---

```
+==================================================================================================================+
|                                  AWS CLOUD INFRASTRUCTURE ARCHITECTURE MAPPING                                   |
+==================================================================================================================+
|                                                                                                                  |
|  [ CI/CD & AUTOMATION ] (ADR-009, ADR-010)                                                                       |
|    +------------------------------------+          +--------------------------------------------------------+    |
|    | GitHub Actions CI/CD (OIDC Auth)   | -------> | Terraform Remote State (S3 Bucket + DynamoDB Lock Table)|    |
|    +------------------------------------+          +--------------------------------------------------------+    |
|                                                                                                                  |
|  [ EDGE INGRESS & CONTENT DELIVERY ] (ADR-003, ADR-007, ADR-008)                                                 |
|    +------------------------------------+          +--------------------------------------------------------+    |
|    | Amazon CloudFront CDN + S3 Origin  |          | AWS ALB (TLS 1.3 via ACM) + AWS WAF (Core Rule Set)    |    |
|    | (Public Booking SPA & POS Shell)   |          | (Rate Limiting: 30-120 req/min, DDoS Mitigation)       |    |
|    +------------------------------------+          +--------------------------------------------------------+    |
|                                                                    |                                             |
|                                                                    v                                             |
|  [ STATELESS COMPUTE PLANE ] (ADR-002, ADR-008)                                                                  |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | AWS ECS Fargate Cluster (Dual-AZ: 2x Tasks, 0.25 vCPU / 512MB RAM each)                                 |    |
|    | - Modular Monolith Django Web Worker (Gunicorn)                                                         |    |
|    | - Asynchronous Celery Outbox Event Worker                                                               |    |
|    | - Secrets & Config Injected via AWS SSM Parameter Store + KMS Encryption                                |    |
|    +--------------------------------------------------------------------------------------------------------+    |
|                         |                                           |                         |                  |
|                         v                                           v                         v                  |
|  [ EPHEMERAL STATE ] (ADR-005)           [ PERSISTENCE PLANE ] (ADR-004)       [ DURABLE VAULT ] (ADR-006)       |
|    +----------------------------+          +-----------------------------+       +-------------------------+     |
|    | AWS ElastiCache for Redis  |          | PgBouncer Connection Pool   |       | AWS S3 Glacier Vault    |     |
|    | - In-Memory Distributed Lock|          | (Transaction Mode, Max 30)  |       | - Object Lock (WORM)    |     |
|    | - Celery Task Broker       |          +-----------------------------+       | - 7-Year Tax Compliance |     |
|    | - Idempotency Replay Buffer|                         |                      | - Database WAL Archives |     |
|    +----------------------------+                         v                      +-------------------------+     |
|                                            +-----------------------------+                                       |
|                                            | AWS RDS PostgreSQL 17       |                                       |
|                                            | (0.50 vCPU / 2GB / 20GB gp3)|                                       |
|                                            | - Append-Only Ledger        |                                       |
|                                            | - Schema-per-Tenant         |                                       |
|                                            +-----------------------------+                                       |
|                                                           |                                                      |
|  [ OBSERVABILITY PLANE ] (ADR-011)                        |                                                      |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | Amazon CloudWatch: Container Insights, Metric Alarms (p95 > 120ms), Log Retention (30d), SNS Alerts   |    |
|    +--------------------------------------------------------------------------------------------------------+    |
+==================================================================================================================+
```

---

## ADR-001: Cloud Provider Ecosystem Selection

### Status
**Accepted**

### Context & Problem Statement
Hospitality OS requires a unified, high-availability cloud infrastructure foundation to host its stateless application containers, managed relational persistence, ephemeral caching, immutable compliance storage, and automated deployment pipelines. 

Per the Non-Functional Requirements ([`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md)), the platform must satisfy:
- Multi-Availability Zone (Multi-AZ) active-active redundancy with a target availability SLA of $\ge 99.9\%$ ($\le 43.8$ minutes unscheduled downtime/year).
- Strict API responsiveness ($p_{95} \le 120\text{ ms}$ for core operational paths).
- Zero long-lived static credentials across delivery automation.
- Maximum cost efficiency for a single boutique property (10 rooms, 30 dining seats, 20 bar stools) capable of fitting inside cloud Free-Tier allocations or low-overhead baseline budgets ($\le \$50/\text{month}$).

### Decision Outcome
**Adopt Amazon Web Services (AWS)** as the primary cloud infrastructure provider.

All core compute, persistence, edge routing, storage, security, and telemetry subsystems will be standardized on native AWS managed services orchestrated via HashiCorp Terraform.

### Considered Options
1. **Option 1: Amazon Web Services (AWS)** — Comprehensive managed serverless container (ECS Fargate), managed database (RDS PostgreSQL), edge CDN (CloudFront), and IAM OIDC primitives with robust Free-Tier eligibility.
2. **Option 2: Google Cloud Platform (GCP)** — Managed Kubernetes (GKE Autopilot) / Cloud Run, Cloud SQL for PostgreSQL, and Cloud Storage.
3. **Option 3: Microsoft Azure** — Azure Container Apps (ACA), Azure Database for PostgreSQL Flexible Server, and Azure Blob Storage.
4. **Option 4: Self-Hosted Bare Metal / Unmanaged VPS (Hetzner / DigitalOcean)** — Co-located or VPS Linux hosts running raw Docker Compose and self-managed Postgres.

### Pros and Cons Matrix

| Criteria / Dimension | Option 1: AWS (Selected) | Option 2: GCP | Option 3: Microsoft Azure | Option 4: Bare Metal / VPS |
| :--- | :--- | :--- | :--- | :--- |
| **Free-Tier & Baseline Cost** | **High:** 12-month free tier covers RDS (750h `db.t4g.micro`), S3 (5GB), CloudFront (1TB/mo free perpetual), DynamoDB (25 RCU/WCU free). | **Moderate:** $300 credit; Cloud Run generous free tier, but Cloud SQL has no permanent free tier. | **Moderate:** 12-month free tier; higher minimum cost floor for container apps and managed Postgres. | **Highest Raw Cost Efficiency:** Flat €10–€30/month for dedicated hardware, but zero managed SLA. |
| **Multi-AZ Availability** | **Superior:** 3+ physical AZs per region with $<1.5\text{ ms}$ inter-AZ latency and isolated fault domains. | **High:** Multi-region and regional zones available globally. | **High:** Availability Zones standard across primary regions. | **Poor:** Single point of failure; requires complex manual multi-datacenter clustering. |
| **Managed Serverless Containers** | **ECS Fargate:** Ultra-lightweight ($0.25\text{ vCPU} / 512\text{ MB}$), zero cluster management overhead, sub-second auto-recovery. | **Cloud Run:** Excellent HTTP request scaling, but complex background Celery worker persistence. | **Container Apps:** Good KEDA scaling, but slower cold-start profiles and higher minimum memory sizing. | **Manual Docker:** Requires self-managed systemd daemon, zero automated health healing without k8s. |
| **Enterprise Security & Compliance** | **Industry Benchmark:** KMS envelope encryption, S3 Object Lock (SEC 17a-4/FINRA WORM compliance), native IAM OIDC. | **High:** Google Cloud KMS, Object Retention Lock, Workload Identity Federation. | **High:** Azure Key Vault, Immutable Blob Storage, Managed Identities. | **High Risk:** Manual disk encryption, self-managed certificate rotation, high operational vulnerability. |
| **DevOps & Terraform Maturity** | **Gold Standard:** `hashicorp/aws` provider is the most widely adopted and tested IaC module library. | **High:** `hashicorp/google` provider is mature and feature-complete. | **Moderate:** `hashicorp/azurerm` provider has frequent breaking schema updates. | **Poor:** Relies on imperative Ansible/SSH scripts; state drift is difficult to prevent. |

### Consequences
* **Positive:** Complete alignment with modern infrastructure-as-code automation; zero server management overhead for OS patching; seamless integration between IAM, KMS, RDS, and ECS; 100% cloud-native Multi-AZ resilience.
* **Negative / Mitigation:** Vendor lock-in to AWS proprietary APIs (e.g., Parameter Store, CloudWatch).
  - *Mitigation:* The application layer is built strictly as a platform-neutral Docker container (Python 3.12, PostgreSQL 17 standard SQL, Redis 7 standard protocol), enabling zero-code-change portability to any cloud or on-premise Kubernetes cluster.

---

## ADR-002: Stateless Compute Execution Plane

### Status
**Accepted**

### Context & Problem Statement
The application execution plane must host both synchronous REST API workloads (Django modular monolith serving POS, PMS, and Booking endpoints) and asynchronous background tasks (Celery workers processing outbox events, recipe BOM depletion, and GL balance verifications).

Per [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md#section-2):
- The baseline traffic is $0.28\text{ RPS}$, peak sustained traffic is $2.50\text{ RPS}$, and maximum burst traffic during offline POS batch replay is $10.00\text{ RPS}$.
- Little's Law concurrency calculations demonstrate that peak sustained load requires only $0.1125$ concurrent worker processes.
- Memory budget per application instance is strictly capped at **512 MB RAM** (Base OS: 48MB, Python runtime: 42MB, Django framework/ORM: 110MB, Sockets: 35MB, Heap: 64MB, Dynamic Headroom: 213MB).
- Total compute allocation across the property footprint: **0.50 vCPU / 1GB RAM aggregate** (divided into 2x $0.25\text{ vCPU} / 512\text{ MB}$ tasks across Dual Availability Zones).
- Sub-millisecond container startup and instant request processing without cold starts are required to satisfy the $p_{95} \le 120\text{ ms}$ SLO.

### Decision Outcome
**Adopt AWS ECS Fargate (Serverless Containers)** configured with Active-Active Dual-AZ deployment (2 container tasks, each allocated $0.25\text{ vCPU}$ and $512\text{ MB RAM}$).

### Considered Options
1. **Option 1: AWS ECS Fargate** — Fully managed serverless container execution with task-level CPU/memory isolation, zero underlying EC2 instance maintenance, and native dual-AZ task placement.
2. **Option 2: AWS Lambda + Amazon API Gateway** — Function-as-a-Service (FaaS) event-driven execution.
3. **Option 3: Amazon EKS (Managed Kubernetes)** — Kubernetes cluster managing small node pools or Fargate profiles.
4. **Option 4: Standalone Amazon EC2 Instance (`t4g.nano` / `t4g.micro`)** — Traditional virtual machine running Docker daemon directly.

### Pros and Cons Matrix

| Evaluation Dimension | Option 1: AWS ECS Fargate (Selected) | Option 2: AWS Lambda | Option 3: Amazon EKS | Option 4: Standalone EC2 |
| :--- | :--- | :--- | :--- | :--- |
| **Cold Start & Latency** | **Zero Cold Starts:** Long-running Gunicorn pre-fork workers maintain hot connections and warm ORM cache ($p_{50} < 45\text{ ms}$). | **Poor Cold Starts:** Python Django cold starts range from $800\text{ ms}$ to $2,500\text{ ms}$, violating the $120\text{ ms}$ $p_{95}$ SLO. | **Zero Cold Starts:** Pods remain continuously warm. | **Zero Cold Starts:** Container runs continuously on the VM. |
| **Background Worker Compatibility** | **Native:** Celery worker runs as a dedicated or shared ECS task with continuous Redis socket streaming. | **Complex / Unnatural:** Requires AWS SQS/EventBridge refactoring; cannot run long-lived Celery outbox loops. | **Native:** Kubernetes Deployments natively support async Celery worker pods. | **Native:** Systemd or Docker Compose runs Celery worker alongside Gunicorn. |
| **Operational Overhead** | **Zero OS Patching:** AWS manages underlying Linux AMI, security patches, and container isolation. | **Zero Infrastructure:** Complete serverless abstraction. | **Extreme Overhead:** Managing k8s control plane upgrades, ingress controllers, CNI plugins, and RBAC. | **High Overhead:** Manual Linux kernel updates, security patching, Docker daemon monitoring. |
| **Cost Profile** | **Ultra-Low:** 2x tasks ($0.25\text{ vCPU} / 512\text{ MB}$) running $24/7 \approx \$7.20 / \text{month}$ per task ($\approx \$14.40/\text{mo}$ total). | **Pay-per-Request:** Free under low traffic, but API Gateway ingress fees accumulate on high burst polls. | **Prohibitive:** EKS control plane fixed cost alone is **\$73.00/month** before any compute nodes. | **Lowest Fixed Cost:** 1x `t4g.micro` ($\approx \$6.00/\text{mo}$), but lacks Multi-AZ failover and auto-healing. |

### Consequences
* **Positive:** Predictable sub-millisecond compute response; exact memory boundary enforcement (512MB hard limit); zero cold-start latency; automatic container health recovery within 15 seconds; seamless horizontal scaling if property expands.
* **Negative / Mitigation:** ECS task startup/deployment time takes 45–90 seconds during CI/CD rolling releases.
  - *Mitigation:* Configure ECS rolling update parameters with `minimum_healthy_percent = 100` and `maximum_percent = 200`, ensuring zero downtime and graceful traffic draining during updates.

---

## ADR-003: Client Asset Delivery & Global Edge Caching

### Status
**Accepted**

### Context & Problem Statement
Hospitality OS serves multiple client-facing frontends:
1. Public Direct Booking Engine & Guest Portal (Responsive React SPA).
2. Digital QR Code Table & Room Menus (Mobile-optimized web application).
3. POS & Front Desk Application Shells (HTML/CSS/JS bundles loaded by Tauri desktop wrappers and browser workstations).

Per [`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md), client web asset loading must achieve:
- First Contentful Paint (FCP) $< 800\text{ ms}$ globally.
- $> 95\%$ edge cache hit ratio for all static JavaScript, CSS, fonts, and image assets.
- Strict security isolation preventing direct public exposure of static storage buckets.
- Zero compute utilization on the primary application container (ECS Fargate) for serving static files.

### Decision Outcome
**Adopt AWS S3 Static Bucket paired with Amazon CloudFront CDN using Origin Access Control (OAC)** for all frontend static bundles, media assets, and compiled React applications.

### Considered Options
1. **Option 1: AWS S3 + Amazon CloudFront (with Origin Access Control)** — Distributed Edge CDN caching across 600+ Global Points of Presence (PoPs) fronting a private encrypted S3 origin.
2. **Option 2: Containerized Nginx Sidecar in ECS Fargate** — Static files packaged inside the application Docker container and served directly via Gunicorn/WhiteNoise or an Nginx sidecar container.
3. **Option 3: Cloudflare Pages / CDN with External Origin** — Frontend hosted on Cloudflare edge network proxying backend API requests to AWS.

### Pros and Cons Matrix

| Evaluation Dimension | Option 1: S3 + CloudFront (Selected) | Option 2: Container Nginx / WhiteNoise | Option 3: Cloudflare Pages |
| :--- | :--- | :--- | :--- |
| **Edge Latency & Delivery** | **Ultra-Low:** Global Anycast edge caching delivers static assets with $< 20\text{ ms}$ TTFB worldwide. | **High Latency:** Static files routed through ALB to regional ECS containers; adds load to compute workers. | **Ultra-Low:** Global Anycast edge caching on Cloudflare network. |
| **Compute Plane Offload** | **100% Offload:** 0% CPU and 0% RAM consumed on ECS Fargate for static web asset delivery. | **Compute Contention:** Consumes container memory heap and worker threads needed for transactional APIs. | **100% Offload:** Static assets served completely independently of backend compute. |
| **Security & Access Control** | **Maximum:** S3 bucket has public access completely blocked; access restricted strictly to CloudFront via SigV4 OAC. | **Moderate:** Nginx container exposed via ALB; requires container attack surface management. | **Moderate:** Requires managing cross-vendor API tokens and dual security configurations. |
| **Cost Profile** | **Free Tier:** CloudFront perpetual free tier includes **1 TB data transfer out/month** and **10,000,000 HTTP requests/month**. | **Hidden Cost:** Increases required ECS Fargate container sizing and ALB processed byte charges. | **Generous Free Tier:** Free tier for static pages, but bifurcates infrastructure across multiple vendors. |

### Exact Implementation Parameters
```hcl
# CloudFront Origin Access Control (OAC) Configuration
resource "aws_cloudfront_origin_access_control" "spa_oac" {
  name                              = "hospitality-os-spa-oac"
  description                       = "OAC for Private S3 Static Web Assets"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Cache Behavior Optimization
# Min TTL: 0s, Default TTL: 86400s (24h), Max TTL: 31536000s (1yr) with gzip/brotli compression
```

### Consequences
* **Positive:** Sub-20ms asset load times worldwide; zero impact on ECS backend capacity; 100% free under normal property traffic volumes; automatic HTTPS with TLS 1.3 edge termination.
* **Negative / Mitigation:** SPA client-side routing requires rewriting 404/403 errors to `/index.html`.
  - *Mitigation:* Configure CloudFront Custom Error Responses to return `/index.html` with HTTP 200 status code for all single-page application routes.

---

## ADR-004: Relational Persistence & Connection Multiplexing

### Status
**Accepted**

### Context & Problem Statement
The persistence layer represents the authoritative financial, operational, and inventory record of the property.

Per [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md#section-4) and [`docs/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/BRD_SPECIFICATION.md):
- **Data Workload:** Strict ACID persistence for Schema-per-Tenant isolation, Double-Entry Append-Only General Ledger, Effective-Dated Tax Models, and Transactional Outbox event queues.
- **Hardware Boundary:** Sized for 1 property: **0.50 vCPU / 2GB RAM / 20GB gp3 SSD Storage**.
- **Connection Boundary:** Maximum **30 active database client sockets** permitted across all application workers, background tasks, and management sessions to prevent connection starvation and memory exhaustion.
- **Commit Latency SLO:** $p_{50} \le 12\text{ ms}$ commit latency with automated continuous WAL archiving for Point-In-Time Recovery (PITR).

### Decision Outcome
**Adopt AWS RDS PostgreSQL 17 (Instance Class: `db.t4g.micro` / `db.t4g.small`) coupled with PgBouncer connection multiplexer in Transaction Pooling Mode.**

### Considered Options
1. **Option 1: AWS RDS PostgreSQL 17 + PgBouncer (Transaction Pooling Mode)** — Dedicated managed PostgreSQL instance with gp3 storage, automated daily snapshots, automated WAL streaming to S3, fronted by PgBouncer to cap database connections to 5–10 backend sockets.
2. **Option 2: AWS Aurora Serverless v2 PostgreSQL + RDS Proxy** — Cloud-native auto-scaling multi-AZ distributed relational database.
3. **Option 3: Self-Managed PostgreSQL 17 on Amazon EC2** — PostgreSQL installed directly on an EC2 virtual machine with custom cron backup scripts.

### Pros and Cons Matrix

| Evaluation Dimension | Option 1: RDS PostgreSQL + PgBouncer (Selected) | Option 2: Aurora Serverless v2 + RDS Proxy | Option 3: Self-Managed EC2 PostgreSQL |
| :--- | :--- | :--- | :--- |
| **Performance & Latency** | **Optimal:** Dedicated vCPU and memory; local gp3 SSD caching; PgBouncer eliminates connection handshake latency ($p_{50} < 12\text{ ms}$). | **Excellent:** Sub-10ms latency, but cold scale-up latency can introduce sporadic $p_{99}$ spikes. | **Variable:** Dependent on EC2 noisy neighbors and EBS burst balance. |
| **Connection Pooling & Capping** | **Strict Guarantee:** PgBouncer in transaction mode multiplexes hundreds of frontend client queries across **5–10 rigid backend Postgres connections**, strictly respecting the 30-socket cap. | **RDS Proxy:** Provides connection multiplexing, but minimum charge is **\$0.015/proxy-hour ($\approx \$11/mo$)** plus Aurora overhead. | **Manual PgBouncer:** Requires maintaining local unix sockets, systemd services, and custom user auth configs. |
| **Backup & Disaster Recovery** | **Turnkey Automated:** Automated 7-day snapshot retention, automated WAL archiving enabling sub-60 second RPO Point-in-Time Recovery. | **Turnkey Automated:** Continuous back-up to S3 with 1-second recovery granularity. | **High Risk:** Fragile custom bash scripts (`pg_dump`); risk of silent backup failures and corrupted WAL replay. |
| **Cost Profile** | **Free-Tier / Low Cost:** Eligible for AWS Free Tier (750 hours/month `db.t4g.micro` for 12 months); ongoing standard cost is $\approx \$12.50/\text{month}$ ($+ \$2.30$ for 20GB gp3 storage). | **Prohibitive:** Aurora Serverless v2 has a minimum capacity floor of 0.5 ACUs = **$\approx \$43.80/\text{month}$** minimum database spend. | **Lowest Raw Cost:** Included in EC2 VM cost, but high maintenance labor cost. |

### Exact Configuration Directives
* **PostgreSQL Version:** 17.x (ARM64 Graviton2/Graviton3 architecture).
* **Storage Configuration:** 20 GB gp3 SSD, 3,000 Baseline IOPS, 125 MB/s Baseline Throughput, Storage Auto-scaling enabled up to 100 GB.
* **PgBouncer Configuration:**
  - `pool_mode = transaction`
  - `max_client_conn = 100`
  - `default_pool_size = 10`
  - `reserve_pool_size = 2`
  - `max_db_connections = 25` (Well beneath the 30 hard ceiling).
  - `server_idle_timeout = 60.0`
  - `query_timeout = 5.0`

### Consequences
* **Positive:** Complete ACID transactional safety; guaranteed protection against connection exhaustion during traffic spikes; zero maintenance automated backups; fits within initial Free-Tier budget.
* **Negative / Mitigation:** PgBouncer `transaction` pool mode does not support session-level PostgreSQL features (e.g., `LISTEN/NOTIFY`, session-level `SET` commands, temporary tables).
  - *Mitigation:* Celery and transactional outbox polling are used instead of `LISTEN/NOTIFY`; all application database queries are strictly stateless and transaction-scoped.

---

## ADR-005: In-Memory Ephemeral State & Event Streaming

### Status
**Accepted**

### Context & Problem Statement
The application architecture requires a high-throughput, sub-millisecond in-memory data store to manage:
1. Distributed concurrency locks (e.g., `pms:lock:<room_id>:<date_range>` with 10s TTL preventing simultaneous double-booking).
2. Idempotency replay buffers (`idemp:pos:<client_tx_uuid>` with 72h TTL to deduplicate POS offline sync replay events).
3. Room availability search slice caching (60s TTL).
4. Celery asynchronous task broker and outbox event publishing queue.

Per [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md#section-3), the in-memory footprint for a single property requires **512 MB RAM** with $p_{99} < 2\text{ ms}$ read/write latency.

### Decision Outcome
**Adopt AWS ElastiCache for Redis (Standalone Node, Engine Version 7.2, Node Type: `cache.t4g.micro`) with Append-Only File (AOF) persistence enabled.**

### Considered Options
1. **Option 1: AWS ElastiCache for Redis 7.2 (`cache.t4g.micro`)** — Managed in-memory Redis service with automated node replacement, parameter group tuning, and in-transit/at-rest encryption.
2. **Option 2: AWS MemoryDB for Redis** — Redis-compatible database with a multi-AZ transactional log for primary durable persistence.
3. **Option 3: Self-Hosted Redis 7 Container on ECS Fargate** — Running a standard `redis:7.2-alpine` container alongside the application tasks.

### Pros and Cons Matrix

| Evaluation Dimension | Option 1: AWS ElastiCache Redis (Selected) | Option 2: AWS MemoryDB | Option 3: Container Redis on ECS |
| :--- | :--- | :--- | :--- |
| **Latency & Performance** | **Ultra-Low:** Dedicated kernel memory allocation delivers sub-millisecond ($< 1\text{ ms}$) response times for lock acquisition and token checks. | **Low:** Sub-millisecond reads, but write latency is slightly higher ($2–4\text{ ms}$) due to multi-AZ synchronous transaction logging. | **Moderate:** Shared container network stack; potential CPU contention with application worker. |
| **Durability & Recovery** | **High:** AOF persistence with daily snapshot backups to S3; automatic node recovery and parameter re-initialization. | **Maximum:** Multi-AZ transactional write durability across 3 AZs. | **Volatile:** Ephemeral container storage; container restart loses in-flight distributed locks and task queues unless EBS is attached. |
| **Operational Simplicity** | **Turnkey Managed:** Zero Redis engine patching, built-in CloudWatch metric integration (CPU, Evictions, Memory Usage). | **Turnkey Managed:** High availability cluster, but excessive complexity for single-property scale. | **Manual:** Requires custom health checking, memory limit configuration, and manual snapshot scripting. |
| **Cost Profile** | **Low Cost:** `cache.t4g.micro` costs **$\approx \$11.50/\text{month}$** ($0.50\text{ GB RAM}$, 2 vCPUs). | **Prohibitive:** Minimum node size is `db.t4g.small` starting at **$\approx \$45.00/\text{month}$** plus write payload fees. | **Lowest Cost:** Included in ECS compute budget, but sacrifices durability and Multi-AZ decoupling. |

### Exact Configuration Directives
* **Parameter Group Configuration:**
  - `maxmemory-policy = volatile-lru` (Evicts expiring keys first if memory pressure occurs).
  - `appendonly = yes` (AOF persistence enabled).
  - `appendfsync = everysec` (Balances disk I/O performance with data durability).
* **Security:** In-transit TLS encryption enabled, Auth Token authentication required, deployed inside private Database Subnet with ingress restricted to Application Security Group (Port 6379).

### Consequences
* **Positive:** Guaranteed sub-millisecond execution for distributed locking and room search caching; reliable Celery task transport; fully isolated memory plane preventing OOM crashes on the compute tier.
* **Negative / Mitigation:** Standalone single-node Redis does not provide multi-master high availability during AWS hardware failure.
  - *Mitigation:* Redis stores strictly ephemeral state; if the node restarts, distributed locks expire gracefully within 10 seconds, and Celery tasks are regenerated from the immutable database `OutboxEvent` table.

---

## ADR-006: Immutable Compliance & Long-Term Financial Archival

### Status
**Accepted**

### Context & Problem Statement
Hospitality OS enforces strict double-entry, append-only financial accounting ([`docs/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/BRD_SPECIFICATION.md#section-4)). 

The platform must satisfy:
1. Long-term archival for finalized guest folios, fiscal VAT receipts, and end-of-day night audit ledger balance exports.
2. Regulatory compliance (SEC Rule 17a-4, FINRA Rule 4511, European VAT audit directives) mandating a **7-Year Retention Period** during which financial documents cannot be overwritten, modified, or deleted by any user—including AWS root accounts.
3. Continuous archiving of PostgreSQL Write-Ahead Log (WAL) segments for Point-in-Time Recovery.
4. Minimal storage expenditure for historical cold data.

### Decision Outcome
**Adopt AWS S3 with Object Lock in Compliance Mode paired with S3 Glacier Flexible / Deep Archive Lifecycle Rules.**

### Considered Options
1. **Option 1: AWS S3 Object Lock (Compliance Mode WORM) + S3 Glacier Lifecycle** — Write-Once-Read-Many (WORM) storage where files are locked against deletion or modification for 7 years (2,555 days), transitioning automatically to Glacier Flexible Archive after 90 days and Glacier Deep Archive after 365 days.
2. **Option 2: Standard S3 Bucket with Versioning & IAM Deny Policies** — Standard S3 bucket with IAM policies blocking `s3:DeleteObject`.
3. **Option 3: AWS Backup Vault with Vault Lock** — Centralized backup management service managing compliance recovery points.

### Pros and Cons Matrix

| Evaluation Dimension | Option 1: S3 Glacier Object Lock (Selected) | Option 2: S3 + IAM Deny Policies | Option 3: AWS Backup Vault Lock |
| :--- | :--- | :--- | :--- |
| **Regulatory Immutability (WORM)** | **Cryptographic Guarantee:** Object Lock in **Compliance Mode** strictly prevents modification or deletion by ANY entity, including AWS account root, until the retention period expires. | **Bypassable Risk:** AWS root credentials or compromised administrator IAM roles can modify bucket policies and delete objects. | **Cryptographic Guarantee:** Vault Lock enforces immutable recovery points. |
| **Storage Cost Efficiency** | **Lowest Tier:** Standard S3 ($0.023/GB) for first 90 days $\rightarrow$ Glacier Flexible ($0.0036/GB) $\rightarrow$ Glacier Deep Archive (**\$0.00099/GB/month**). | **High Cost:** Objects remain in Standard S3 indefinitely unless manual lifecycle rules are configured without WORM validation. | **Moderate Cost:** Backup storage fees are $\approx \$0.05/GB/\text{month}$ for warm recovery points. |
| **Audit & Legal Readiness** | **Certified:** Compliant with SEC 17a-4(f), FINRA 4511(c), and CFTC 1.31(c)-(d); supports Legal Hold overrides for tax disputes. | **Fails Compliance Audits:** Cannot produce cryptographic WORM non-rewritable non-erasable certification. | **Certified:** Supports compliance audit logging. |
| **WAL & Invoice Compatibility** | **Native:** Seamless integration with `pg_dump`, WAL archiving tools (`pgBackRest` / `wal-g`), and PDF generation pipelines. | **Native:** Direct S3 API compatibility. | **Complex:** Intended for block-level volume snapshots rather than fine-grained individual invoice PDF storage. |

### Exact Implementation Directives
```hcl
# S3 Bucket Object Lock Configuration (Compliance Mode)
resource "aws_s3_bucket" "financial_archive" {
  bucket        = "hospitality-os-financial-archive-prod"
  force_destroy = false
}

resource "aws_s3_bucket_object_lock_configuration" "worm_lock" {
  bucket = aws_s3_bucket.financial_archive.id

  rule {
    default_retention {
      mode  = "COMPLIANCE"
      years = 7
    }
  }
}

# Lifecycle Transition: 90 Days -> Glacier Flexible, 365 Days -> Glacier Deep Archive
```

### Consequences
* **Positive:** Cryptographically unassailable financial compliance; complete protection against accidental or malicious ledger tampering; storage cost for 7 years of property records remains under **\$0.50/month**.
* **Negative / Mitigation:** If corrupted or test data is uploaded to the Compliance-locked bucket, it cannot be deleted under any circumstances until the 7-year retention expires.
  - *Mitigation:* Enforce strict automated staging tests and separate testing buckets (`test-hospitality-archive`) with short 1-day Governance retention policies for non-production environments.

---

## ADR-007: Edge Routing, TLS Termination & Application Security

### Status
**Accepted**

### Context & Problem Statement
The platform ingress layer handles heterogeneous traffic flows:
1. Public internet guest booking queries and mobile QR scans.
2. High-frequency local POS orders and kitchen KDS bump operations.
3. Offline POS batch synchronization replays ($5.00–10.00\text{ RPS}$ burst).
4. Automated telemetry and health probes.

Per [`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md):
- Enforce **TLS 1.3** cryptographic termination with HSTS.
- Implement strict rate limiting: **30 req/min** for booking endpoints, **120 req/min** for POS endpoints, and **60 req/min** for PMS endpoints.
- Protect against common web vulnerabilities (OWASP Top 10, SQL Injection, Cross-Site Scripting, DDoS flood attacks).
- Ensure multi-AZ health probe load balancing across active ECS Fargate containers.

### Decision Outcome
**Adopt AWS Application Load Balancer (ALB) integrated with AWS WAF (Web Application Firewall) and AWS Certificate Manager (ACM).**

### Considered Options
1. **Option 1: AWS Application Load Balancer (ALB) + AWS WAF** — Fully managed Layer 7 reverse proxy with native dual-AZ target health routing, automatic ACM SSL/TLS certificate renewal, and managed WAF Core Rule Sets (CRS).
2. **Option 2: In-Cluster Traefik / Nginx Proxy on EC2** — Self-managed reverse proxy instance handling TLS termination and rate limiting via local configuration files.
3. **Option 3: Cloudflare Enterprise Edge WAF** — Third-party DNS and edge security proxy fronting an origin load balancer.

### Pros and Cons Matrix

| Evaluation Dimension | Option 1: AWS ALB + AWS WAF (Selected) | Option 2: Self-Managed Traefik / Nginx | Option 3: Cloudflare Edge WAF |
| :--- | :--- | :--- | :--- |
| **High Availability & Health Probing** | **Turnkey Multi-AZ:** Scales automatically across AZs; conducts active 10-second health probes to `/health/`; routes traffic only to healthy ECS tasks. | **Single Point of Failure:** Unless deployed across multiple redundant EC2 nodes with Keepalived/VRRP, proxy host is a SPOF. | **External Edge Routing:** Excellent global routing, but requires origin ALB behind it anyway for AWS container routing. |
| **Security & WAF Protection** | **AWS Managed Rules:** Pre-configured protection against OWASP Top 10, SQLi, XSS, Bad Bot traffic; native Rate-Based Rules. | **Manual Rules:** Requires maintaining ModSecurity / OWASP Coraza rules and manual IP blocklist maintenance. | **Superior WAF:** Advanced bot management, but introduces extra billing and vendor hop. |
| **TLS Certificate Lifecycle** | **Automated Zero-Touch:** AWS Certificate Manager (ACM) provisions and auto-renews free public SSL certificates every 12 months. | **Manual Certbot:** Requires Let's Encrypt Certbot cron renewals; risk of service disruption on renewal failure. | **Automated:** Cloudflare Universal SSL. |
| **Cost Profile** | **Predictable:** ALB is $\approx \$16.20/\text{month}$ ($+ \$0.008/\text{LCU-hour}$); AWS WAF is $\$5.00/\text{web-ACL} + \$1.00/\text{rule}$. | **Low Fixed Cost:** Uses existing EC2 VM capacity, but high maintenance and monitoring overhead. | **High Cost:** Free/Pro tiers lack advanced custom rate limits; Enterprise tier starts at $> \$2,000/\text{month}$. |

### Exact Configuration Directives
* **Security Policy:** `ELBSecurityPolicy-TLS13-1-2-2021-06` (Restricted strictly to modern, secure ciphers: TLS 1.3 / TLS 1.2; SSLv3, TLS 1.0, and TLS 1.1 strictly disabled).
* **ALB Timeouts:** `idle_timeout.timeout_seconds = 60` (Matches timeout cascade: ALB 60s $\rightarrow$ Gunicorn 30s $\rightarrow$ DB 5s).
* **AWS WAF Rate-Limiting Rules:**
  - `RateLimit-Booking`: 30 requests / minute per IP on `/api/v1/booking/*`.
  - `RateLimit-POS`: 120 requests / minute per IP on `/api/v1/pos/*`.
  - `RateLimit-PMS`: 60 requests / minute per IP on `/api/v1/pms/*`.
  - `AWSManagedRulesCommonRuleSet`: Enabled (Blocks generic web exploit patterns).
  - `AWSManagedRulesSQLiRuleSet`: Enabled (Blocks SQL injection attempts).

### Consequences
* **Positive:** Complete elimination of proxy maintenance; automated zero-downtime certificate renewal; instantaneous DDoS mitigation via AWS Shield Standard; robust Layer 7 rate limiting protecting backend database sockets.
* **Negative / Mitigation:** ALB introduces a fixed baseline cost of $\approx \$16–\$25/\text{month}$ regardless of property traffic volume.
  - *Mitigation:* The architectural stability, Multi-AZ high availability SLA (99.99%), and automated certificate management justify this minimal operational expenditure for a revenue-critical hospitality property.

---

## ADR-008: Secrets Management, Parameter Configuration & Cryptography

### Status
**Accepted**

### Context & Problem Statement
Hospitality OS handles highly sensitive operational and financial credentials:
1. PostgreSQL master database credentials and connection strings.
2. Redis AUTH tokens.
3. Stripe API secret keys and webhook signing secrets.
4. JWT asymmetric signing keys (RSA-2048 / Ed25519 private keys) for tenant auth tokens and Metabase dashboard embedding.
5. ESC/POS hardware encryption tokens.

Per security governance:
- Zero plaintext secrets or environmental configuration files (`.env`) permitted in Git repositories.
- Least-privilege role-based access control (RBAC) enforced via IAM.
- All secrets encrypted at rest using envelope encryption with automated key rotation.
- Secrets must be injected dynamically into ECS Fargate containers at task launch without baking values into Docker container images.

### Decision Outcome
**Adopt AWS Systems Manager (SSM) Parameter Store (SecureString) and AWS Secrets Manager encrypted with AWS Key Management Service (AWS KMS) Customer Managed Keys (CMK), paired with AWS Certificate Manager (ACM) for public PKI.**

### Considered Options
1. **Option 1: AWS KMS + SSM Parameter Store / Secrets Manager + ACM** — Native AWS cryptographic fabric with IAM-integrated secret injection at container runtime via ECS Task Execution Roles.
2. **Option 2: HashiCorp Vault Cluster** — Dedicated enterprise secrets management and dynamic credential engine.
3. **Option 3: Encrypted `.env` Files (Git-Crypt / SOPS) Baked into Container Image** — File-based encrypted secrets decrypted during container entrypoint execution.

### Pros and Cons Matrix

| Evaluation Dimension | Option 1: AWS SSM + Secrets Manager + KMS (Selected) | Option 2: HashiCorp Vault | Option 3: Encrypted `.env` / Git-Crypt |
| :--- | :--- | :--- | :--- |
| **AWS Native IAM Integration** | **Seamless:** ECS Task Definitions natively reference SSM Parameter ARNs; ECS agent securely injects them as environment variables at task initialization. | **Complex:** Requires running Vault sidecar agent, AppRole authentication, or external webhook orchestrators. | **Poor:** Secret decryption key must be passed via CI/CD, creating a key-distribution bootstrap dilemma. |
| **Encryption at Rest & Key Rotation** | **Automated Envelope Encryption:** KMS Customer Managed Keys provide FIPS 140-2 Level 2 cryptographic hardware validation and annual key rotation. | **Enterprise Grade:** Excellent Shamir secret sharing and cryptographic key management. | **Manual:** Key rotation requires re-encrypting all repository files and rebuilding container images. |
| **Audit Logging & Access Tracking** | **Full Audit Trail:** Every secret decryption event is immutably logged in AWS CloudTrail with caller IAM identity, timestamp, and IP. | **Full Audit Trail:** Vault internal audit logs. | **Zero Auditability:** Cannot audit when a local `.env` file is read or extracted from a running host. |
| **Cost Profile** | **Free / Minimal Cost:** SSM Parameter Store Standard Tier is **\$0.00 (Free)**; KMS key costs **\$1.00/month**; Secrets Manager (if used for auto-rotating DB credentials) is **\$0.40/secret/month**. | **Prohibitive:** Running a resilient 3-node Vault cluster requires dedicated compute nodes costing **$> \$100/month**. | **Free:** Zero direct financial cost, but extreme risk of accidental credential leakage. |

### Exact Implementation Directives
* **ECS Task Execution Role:** Granted `kms:Decrypt` and `ssm:GetParameters` on `arn:aws:ssm:region:account:parameter/hospitality-os/prod/*`.
* **ECS Task Definition Secret Injection:**
```json
"secrets": [
  {
    "name": "DATABASE_URL",
    "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/hospitality-os/prod/database_url"
  },
  {
    "name": "REDIS_URL",
    "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/hospitality-os/prod/redis_url"
  },
  {
    "name": "STRIPE_SECRET_KEY",
    "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/hospitality-os/prod/stripe_secret_key"
  },
  {
    "name": "JWT_PRIVATE_KEY",
    "valueFrom": "arn:aws:ssm:us-east-1:123456789012:parameter/hospitality-os/prod/jwt_private_key"
  }
]
```

### Consequences
* **Positive:** Absolute elimination of hardcoded secrets; seamless compliance with PCI-DSS and SOC 2 credential storage standards; zero cost for standard parameter storage; instant revocation of compromised credentials without redeploying code.
* **Negative / Mitigation:** Updating a parameter in SSM requires restarting the ECS Fargate task to ingest the new environment value.
  - *Mitigation:* Issue an automated `aws ecs update-service --force-new-deployment` command via CI/CD whenever sensitive parameters are rotated.

---

## ADR-009: Infrastructure as Code & State Management

### Status
**Accepted**

### Context & Problem Statement
To enforce deterministic deployments, environment reproducibility, disaster recovery automation, and zero configuration drift across all cloud tiers, the entire AWS infrastructure must be defined strictly as declarative code.

Key requirements:
1. Version-controlled infrastructure definitions stored inside the monorepo under `/infrastructure/terraform`.
2. Secure, centralized remote state storage with atomic state locking to prevent concurrent deployment collisions and state corruption.
3. Modular design separating networking (VPC), security groups, database (RDS), cache (ElastiCache), compute (ECS), edge delivery (CloudFront/ALB), and observability (CloudWatch).
4. Automated linting, static security analysis, and speculative execution plan generation in CI/CD before applying changes.

### Decision Outcome
**Adopt HashiCorp Terraform with S3 Remote State Backend and Amazon DynamoDB Distributed State Locking.**

### Considered Options
1. **Option 1: HashiCorp Terraform (with S3 Backend + DynamoDB Lock Table)** — Industry-standard declarative HCL (HashiCorp Configuration Language) infrastructure-as-code engine with an S3 state bucket and DynamoDB table for distributed atomic locking.
2. **Option 2: AWS CloudFormation / AWS Cloud Development Kit (CDK)** — AWS-native JSON/YAML templates or imperative TypeScript/Python wrapper constructing CloudFormation stacks.
3. **Option 3: Pulumi** — General-purpose programming language infrastructure-as-code tool (TypeScript/Python).

### Pros and Cons Matrix

| Evaluation Dimension | Option 1: Terraform + S3/DynamoDB (Selected) | Option 2: AWS CDK / CloudFormation | Option 3: Pulumi |
| :--- | :--- | :--- | :--- |
| **Ecosystem & Provider Breadth** | **Industry Leader:** The `hashicorp/aws` provider is the most mature, rapidly updated, and thoroughly documented cloud provider in the software industry. | **AWS Centric:** Tied directly to CloudFormation engine; non-AWS resources require custom resource handlers. | **Moderate:** Relies on bridged Terraform providers or native SDKs; smaller community module ecosystem. |
| **State Management & Locking** | **Robust & Proven:** S3 stores encrypted state versions; DynamoDB provides sub-second atomic locking preventing simultaneous `apply` operations. | **Managed by AWS:** CloudFormation engine manages state internally, but rollback failures can leave stacks in `UPDATE_ROLLBACK_FAILED` lockups. | **SaaS Backend:** Requires Pulumi Service account or self-managed backend storage. |
| **Modularity & Monorepo Structure** | **Clean Directory Structure:** Clean separation of reusable root and child modules (`vpc`, `rds`, `ecs`, `alb`, `security`). | **Code Complexity:** Requires compiling TypeScript/Python code into CloudFormation synthesis templates before deployment. | **Code Complexity:** High language runtime dependencies in CI/CD runners. |
| **Cost Profile** | **Free:** Terraform CLI is open-source; S3 state storage ($< \$0.01/mo) and DynamoDB Free Tier (25 RCU/WCU free perpetual) cost **\$0.00/month**. | **Free:** CloudFormation has no direct management fee. | **SaaS Billing:** Free for individuals, but team collaboration tiers introduce monthly per-seat licensing fees. |

### Exact Implementation Directives
```hcl
# Terraform Remote State & Lock Configuration
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  backend "s3" {
    bucket         = "hospitality-os-terraform-state-prod"
    key            = "core/production.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "hospitality-os-terraform-locks"
  }
}
```

### Consequences
* **Positive:** 100% reproducible single-property infrastructure; zero configuration drift; instant disaster recovery recreation in an alternate AWS region in $< 15$ minutes; automated `terraform plan` PR comments in CI/CD.
* **Negative / Mitigation:** Manual modifications in the AWS Management Console can cause state drift.
  - *Mitigation:* Strict policy: all console write permissions are revoked in production; all infrastructure mutations must pass through GitHub Actions Terraform CI/CD pipelines.

---

## ADR-010: CI/CD Pipeline & Automated Cloud Authentication

### Status
**Accepted**

### Context & Problem Statement
Deploying code, executing database migrations, and provisioning cloud resources must occur through an automated, secure Continuous Integration and Continuous Delivery (CI/CD) pipeline.

Security and operational constraints:
1. Eliminate all long-lived AWS IAM Access Keys and Secret Access Keys from GitHub repository secrets to eliminate credential theft attack vectors.
2. Enforce automated pull request validation: code formatting (`black`, `flake8`), static typing (`mypy`), unit tests (`pytest` with $> 80\%$ coverage), and Terraform linting (`tflint`, `terraform fmt`).
3. Automated zero-downtime rolling container deployments to AWS ECS Fargate upon merging to the `main` branch.
4. Native monorepo path filtering so that changes to `/modules/pos-system` do not trigger redundant rebuilds of `/core-hub`.

### Decision Outcome
**Adopt GitHub Actions utilizing AWS IAM OpenID Connect (OIDC) Federated Identity Authentication.**

### Considered Options
1. **Option 1: GitHub Actions with IAM OpenID Connect (OIDC)** — Ephemeral cryptographic authentication using GitHub's OIDC token exchange with AWS Security Token Service (STS) to obtain temporary 15-minute IAM session credentials without storing static secrets.
2. **Option 2: GitLab CI / CircleCI with Static AWS IAM Secret Keys** — Third-party CI runner configured with long-lived `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` stored as encrypted environment secrets.
3. **Option 3: Dedicated Jenkins Master/Worker Cluster on Amazon EC2** — Self-managed Jenkins server running inside the VPC with an IAM Instance Profile.

### Pros and Cons Matrix

| Evaluation Dimension | Option 1: GitHub Actions + OIDC (Selected) | Option 2: CI with Static IAM Keys | Option 3: Dedicated Jenkins EC2 |
| :--- | :--- | :--- | :--- |
| **Credential Security & Posture** | **Zero Static Credentials:** No secret keys stored in GitHub; uses cryptographic JWT token exchange with AWS STS for temporary, scoped 15-minute credentials. | **Critical Risk:** Long-lived static keys stored in CI settings; compromised repository secrets grant persistent AWS account access. | **Secure:** Uses EC2 Instance Profiles, but Jenkins server itself is an exposed high-value attack target. |
| **Monorepo Integration** | **Native:** `paths` and `paths-ignore` filter workflow triggers based on modified directory boundaries (`/core-hub/**`, `/modules/**`). | **Requires Tooling:** Requires custom script wrappers or monorepo tools (e.g., Turborepo, Nx). | **Complex:** Requires configuring multi-branch pipeline path triggers and webhook filters. |
| **Operational Overhead** | **Zero Maintenance:** Hosted GitHub runners execute builds in ephemeral, isolated container environments. | **Zero Maintenance:** Managed runners. | **Heavy Maintenance:** Managing Jenkins OS updates, JVM memory tuning, plugin security patches, and runner disk space. |
| **Cost Profile** | **Free Tier:** 2,000 free GitHub Actions build minutes/month for private repositories; sufficient for property deployment cadence. | **Tiered:** Free tier limits, then paid runner minutes. | **High Fixed Cost:** Dedicated `t4g.small` EC2 instance costs **$\approx \$15–\$25/\text{month}$** continuous spend. |

### Exact Implementation Directives
* **AWS IAM OIDC Trust Policy Configuration:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:The-Code-Consortium/hospitality-saas-monorepo:*"
        }
      }
    }
  ]
}
```

### Consequences
* **Positive:** Complete elimination of AWS credential leakage risks; full compliance with modern zero-trust enterprise security baselines; automated end-to-end testing and deployment without manual intervention.
* **Negative / Mitigation:** GitHub Actions outages could temporarily block emergency hotfix deployments.
  - *Mitigation:* Break-glass emergency AWS IAM administrator roles can be assumed directly via AWS Management Console SSO with multi-factor authentication (MFA) in catastrophic scenarios.

---

## ADR-011: Telemetry, Observability & Operational Alerting

### Status
**Accepted**

### Context & Problem Statement
Operating a production hospitality platform requires comprehensive real-time visibility across all 7 architectural tiers to detect and remediate anomalies before they impact guest experience or financial reconciliation.

Per [`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md#section-4):
- Real-time tracking of critical SLOs: API latency ($p_{95} \le 120\text{ ms}$), container CPU utilization ($< 80\%$), memory utilization ($< 85\%$), and active database connection pool saturation ($\le 30$ connections).
- Centralized structured logging for all application containers, Gunicorn access logs, Celery workers, and database query logs with a **30-Day Retention Policy**.
- Immediate automated alerting dispatched via Amazon Simple Notification Service (SNS) to management email/Slack channels whenever an SLO threshold is breached.

### Decision Outcome
**Adopt Amazon CloudWatch (CloudWatch Logs, CloudWatch Container Insights, Metric Alarms, and Metric Filters) integrated with Amazon Simple Notification Service (SNS).**

### Considered Options
1. **Option 1: Amazon CloudWatch + CloudWatch Alarms & SNS** — AWS-native observability suite with automated metric collection for ECS, RDS, ALB, and ElastiCache, log group retention management, and anomaly alarms.
2. **Option 2: Self-Hosted Prometheus + Grafana + Loki Stack on EC2** — Open-source metrics and log aggregation cluster.
3. **Option 3: Third-Party SaaS APM (Datadog / New Relic)** — Commercial monitoring agent and cloud observability platform.

### Pros and Cons Matrix

| Evaluation Dimension | Option 1: Amazon CloudWatch + SNS (Selected) | Option 2: Prometheus + Grafana + Loki | Option 3: Datadog / New Relic |
| :--- | :--- | :--- | :--- |
| **Infrastructure Overhead** | **Zero Overhead:** Managed agentless metrics emitted directly by AWS services (ALB, ECS, RDS, Redis); zero compute servers to maintain. | **Heavy Overhead:** Requires provisioning 1–2 dedicated EC2 instances with persistent EBS volumes for TSDB time-series storage and PromQL queries. | **Zero Overhead:** SaaS platform with lightweight daemon, but requires managing external agent keys. |
| **AWS Metric Integration** | **Native:** Instant out-of-the-box visibility into ALB Target Response Times, ECS CPU/Memory, RDS DatabaseConnections, and ElastiCache CacheHits. | **Requires Exporters:** Must deploy and manage `node_exporter`, `postgres_exporter`, `redis_exporter`, and `cloudwatch_exporter`. | **Excellent:** Comprehensive AWS integration, but metric collection latency can be delayed by 1–5 minutes. |
| **Log Management & Lifecycle** | **Automated Retention:** CloudWatch Log Groups enforce a strict 30-day automatic expiration lifecycle, preventing runaway disk accumulation. | **Manual Pruning:** Requires configuring Loki retention chunk cleaners and disk volume thresholds. | **Managed:** SaaS log ingestion with custom indexing rules. |
| **Cost Profile** | **Free / Ultra-Low:** Includes 10 free metrics, 5GB log ingestion, and 3 free alarms; ongoing property telemetry spend is **$\approx \$3.50–\$7.00/\text{month}$**. | **Moderate Fixed Spend:** Compute and EBS storage for the Prometheus/Grafana instance costs **$\approx \$25–\$45/\text{month}$**. | **Prohibitive:** APM host licenses start at **\$15/host/month** plus \$0.10/GB log indexing, scaling rapidly. |

### Exact Metric Alarm Baselines

```
+----------------------------------------------------------------------------------------------------+
|                                    CLOUDWATCH TELEMETRY & ALARM MATRIX                             |
|                                                                                                    |
|  [ ALB TargetResponseTime ] -----> Alarm if p95 > 120ms for 3 consecutive 1-min periods            |
|                                                                                                    |
|  [ ECS Fargate Memory ] ---------> Alarm if RAM Utilization > 85% for 2 consecutive 1-min periods   |
|                                                                                                    |
|  [ RDS DatabaseConnections ] ----> Alarm if Active Connections > 25 (Approaching 30 socket cap)   |
|                                                                                                    |
|  [ Outbox Lag / Age ] -----------> Metric Filter: Log events older than 60s without dispatch       |
|                                                                                                    |
|                         +-----------------------------------------------+                          |
|                         |  AWS SNS Topic: hospitality-alerts-production |                          |
|                         +-----------------------------------------------+                          |
|                                         |                       |                                  |
|                                         v                       v                                  |
|                              [ DevOps Slack Webhook ]  [ On-Call SMS/Email ]                       |
+----------------------------------------------------------------------------------------------------+
```

| CloudWatch Metric Name | Monitored Resource | Metric Threshold | Evaluation Window | Severity | Action Triggered |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `TargetResponseTime` (p95) | AWS ALB Target Group | $> 120\text{ ms}$ | 3 data points within 3 minutes | **High** | SNS Alert: Latency SLO Breach |
| `MemoryUtilization` | ECS Fargate Task | $> 85\%$ ($> 435\text{ MB}$) | 2 data points within 2 minutes | **Critical** | SNS Alert: Container Memory Risk |
| `CPUUtilization` | ECS Fargate Task | $> 80\%$ | 3 data points within 3 minutes | **Medium** | SNS Alert: High Compute Load |
| `DatabaseConnections` | RDS PostgreSQL 17 | $> 25\text{ Sockets}$ | 2 data points within 2 minutes | **Critical** | SNS Alert: DB Socket Exhaustion |
| `FreeStorageSpace` | RDS PostgreSQL gp3 | $< 5\text{ GB}$ ($< 25\%$) | 1 data point within 5 minutes | **High** | SNS Alert: Storage Depletion |
| `5XXErrorRate` | AWS ALB Ingress | $> 1.0\%$ of requests | 2 data points within 2 minutes | **Critical** | SNS Alert: Elevated Error Rate |

### Consequences
* **Positive:** Complete visibility into all critical SLOs; zero infrastructure maintenance overhead; turnkey integration with AWS services; predictable low cost; immediate proactive notification of operational degradation.
* **Negative / Mitigation:** CloudWatch Dashboards and custom metric queries have basic visual fidelity compared to advanced Grafana dashboards.
  - *Mitigation:* CloudWatch Metrics are exported via CloudWatch Metric Streams to OpenTelemetry / Grafana when multi-property fleet visualization is required in future growth phases.

---

## Architecture Governance & Evolution Framework

All decisions recorded in this collection (ADR-001 through ADR-011) represent the immutable baseline for Hospitality OS Single-Property production deployments. Any architectural modification, service replacement, or threshold revision must be submitted as a new ADR (e.g., ADR-012) following the standard MADR specification, referencing mathematical models from [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md) and SLO baselines from [`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md).
