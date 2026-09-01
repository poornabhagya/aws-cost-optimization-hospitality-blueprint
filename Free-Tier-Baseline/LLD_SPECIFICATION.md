# Cloud Low-Level Design (LLD) & Subsystem Topology Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Production Cloud Low-Level Design (LLD) & Subsystem Topology Specification
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 2.0.0 (Free-Tier Production Baseline)
* **Status:** Approved / Production-Ready Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Budget Ceiling:** **< $0.50 USD / month ($0.00 USD / month net spend)**
* **Target Cloud Provider & Region:** Amazon Web Services (AWS) — Primary Region: Asia Pacific (Mumbai) `ap-south-1`
* **Classification:** Highly Confidential / Enterprise Free-Tier Low-Level Design Baseline
* **Aligned Specifications:**
  - [`docs/Free Tier Baseline/ADR_COLLECTION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/ADR_COLLECTION.md) (Master Free-Tier ADR Decisions: ADR-001 through ADR-011)
  - [`docs/Free Tier Baseline/HLA_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/HLA_SPECIFICATION.md) (Platform-Neutral High-Level Architecture Topology)
  - [`docs/Free Tier Baseline/NETWORK_AND_SECURITY_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/NETWORK_AND_SECURITY_SPECIFICATION.md) (Zero-Cost Lean VPC & Subnet Security Rules)
  - [`docs/Free Tier Baseline/DATABASE_AND_STORAGE_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/DATABASE_AND_STORAGE_SPECIFICATION.md) (Single-AZ RDS, Redis Container, SQLite WAL, S3)
  - [`docs/Free Tier Baseline/SECURITY_AND_COMPLIANCE_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/SECURITY_AND_COMPLIANCE_SPECIFICATION.md) (OIDC, SSM, PCI SAQ-A, GDPR Salt-Shredding)
  - [`docs/Free Tier Baseline/CICD_AND_DEPLOYMENT_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/CICD_AND_DEPLOYMENT_SPECIFICATION.md) (GitHub Actions & ECR Automation)
  - [`docs/Enterprise Baseline/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/CAPACITY_SIZING.md) (0.50 vCPU / 1GB RAM Compute, 512MB Redis, 20GB gp3 PostgreSQL)
  - [`docs/Enterprise Baseline/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/NFR_SPECIFICATION.md) ($p_{95} \le 120\text{ ms}$, TLS 1.3, Rate Limits, 30 DB Sockets)

---

## 1. Executive Architectural Overview & Master Topology

Hospitality OS establishes a **Zero-Cost, High-Performance Production Low-Level Design (LLD)** tailored specifically for a single boutique hospitality property (10 rooms, 30 dining seats, 20 bar stools).

The system integrates a **Single-Host Container Runtime Engine** (`t4g.micro` EC2 in `ap-south-1a`), an **Isolated Relational Persistence Boundary** (Single-AZ RDS PostgreSQL 17 in `ap-south-1a`), a **Durable Object Storage Vault** (Amazon S3 + CloudFront), and **Local-First On-Premise POS Terminals** with 72-hour offline operational autonomy.

```
+==================================================================================================================+
|                               HOSPITALITY OS PRODUCTION LOW-LEVEL TOPOLOGY (LLD)                                 |
|                                            (Target Spend: $0.00 / Month)                                         |
+==================================================================================================================+
|                                                                                                                  |
|  [ TIER 1: CLIENT & ON-PREMISE EDGE HARDWARE ]                                                                   |
|    +-----------------------------+   +-----------------------------+   +------------------------------------+    |
|    | Public Booking / Mobile QR  |   | Front Desk PMS Desktop      |   | Local POS Terminals (Dining & Bar) |    |
|    | Browser / Stripe Elements   |   | Tauri 2.0 (Rust) + React    |   | Tauri + SQLite 3.45 WAL + ESC/POS  |    |
|    +-----------------------------+   +-----------------------------+   +------------------------------------+    |
|                   |                                 |                                     |                      |
|                   | HTTPS / TLS 1.3                 | HTTPS / Folio API                   | HTTPS Sync (72h Buff)|
|                   +---------------------------------+-------------------------------------+                      |
|                                                     |                                                            |
|                                                     v                                                            |
|  [ LEAN VPC: 10.0.0.0/16 (0 NAT GATEWAYS / 0 PRIVATELINK ENDPOINTS) ]                                            |
|                                                                                                                  |
|    [ PUBLIC SUBNET (10.0.1.0/24 - ap-south-1a) ]                                                                |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | Amazon EC2 Instance: 1x t4g.micro (ARM64 Graviton2, 2 vCPUs, 1.0 GB RAM, 30GB gp3 Root) — (10.0.1.50)  |    |
|    | Attached to: Internet Gateway (igw-hospitality-prod) | Security Group: sg_hospitality_ec2              |    |
|    |                                                                                                        |    |
|    |  +--------------------------------------------------------------------------------------------------+  |    |
|    |  | DOCKER COMPOSE MULTI-CONTAINER NETWORK (hospitality_internal: 172.28.0.0/16)                     |  |    |
|    |  |                                                                                                  |  |    |
|    |  |  +---------------------------+     +--------------------------------+     +-------------------+  |  |    |
|    |  |  | NGINX Ingress Proxy       | --> | Gunicorn Django Web API        | --> | Redis 7.2 Alpine  |  |  |    |
|    |  |  | • Let's Encrypt (Certbot) |     | • 2x Pre-fork Workers (<250MB) |     | • 128 MB Hard Cap |  |  |    |
|    |  |  | • TLS 1.3 / Rate Limiting |     | • Gunicorn WSGI (Port 8000)    |     | • AOF Disk Sync   |  |  |    |
|    |  |  | • Ports 80 / 443          |     | • Modular Monolith Domain Hub  |     | • Port 6379       |  |  |    |
|    |  |  +---------------------------+     +--------------------------------+     +-------------------+  |  |    |
|    |  |                                                    |                                             |  |    |
|    |  |                                                    +-----> [ Celery Async Background Worker ]    |  |    |
|    |  |                                                            • Recipe BOM Depletion & GL Balancing |  |    |
|    |  +--------------------------------------------------------------------------------------------------+  |    |
|    +--------------------------------------------------------------------------------------------------------+    |
|                                                     |                                                            |
|                                                     | Private ACID SQL Queries (TCP Port 5432)                   |
|                                                     v                                                            |
|    [ PRIVATE DATABASE SUBNET GROUP (10.0.2.0/24 - ap-south-1a & 10.0.3.0/24 - ap-south-1b) ]                    |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | Amazon RDS PostgreSQL 17 Single-AZ (Instance: db.t4g.micro / 1.0 GB RAM / 20 GB gp3 SSD) — (10.0.2.100)|    |
|    | • Security Group: sg_hospitality_rds (Inbound: TCP 5432 strictly from sg_hospitality_ec2 ID)           |    |
|    | • Schema-per-Tenant Isolation (tenant_<uuid>.*) | Append-Only General Ledger Database Triggers          |    |
|    | • Max Connections: 25 | Shared Buffers: 256MB | Automated 7-Day Snapshot Backups ($0.00 Free Tier)     |    |
|    +--------------------------------------------------------------------------------------------------------+    |
|                                                                                                                  |
|  [ TIER 6: DURABLE OBJECT STORAGE & EDGE DELIVERY (AMAZON S3 & CLOUDFRONT) ]                                     |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | 1. hospitality-web-assets-prod        : React SPAs fronted by CloudFront CDN (1 TB/mo Free Perpetual)  |    |
|    | 2. hospitality-financial-archive-prod : 7-Year WORM Compliance Vault (SEC 17a-4 / European VAT Compliant)|    |
|    | 3. hospitality-wal-backups-prod       : Continuous WAL Log Stream for Point-in-Time Recovery (RPO<=1.0s)|   |
|    +--------------------------------------------------------------------------------------------------------+    |
|                                                                                                                  |
|  [ TIER 7: CI/CD & TELEMETRY CONTROL PLANE ]                                                                    |
|    • GitHub Actions OIDC Auth -> Amazon ECR (500MB Free) -> AWS SSM Session Manager Deploy Hook                  |
|    • CloudWatch Free Tier Billing Alarm ($0.50 Threshold) -> Instant SNS Email Alert                             |
+==================================================================================================================+
```

---

## 2. Master Network & Component Topology Matrix

| Tier | Component / Service | Subnet & CIDR | Network Interface & Port | Security Group ID | Resource Sizing & Limits | Scaling & Redundancy Model |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | **POS Touchscreens (x4)** | On-Premise LAN | TCP 443 (Outbound WAN) | Local LAN Firewall | Local Hardware / 500MB Disk | 4 Independent Nodes; 72-Hour SQLite WAL Autonomy |
| **Tier 1** | **Kitchen Display (KDS)** | On-Premise Kitchen | WSS (WebSocket Port 443)| Local LAN Firewall | Embedded Browser / Micro-PC | Real-time WebSocket station order push |
| **Tier 2** | **NGINX Ingress Proxy** | `subnet-public-a` (`10.0.1.0/24`) | `eth0:80`, `eth0:443` | `sg_hospitality_ec2` | In-Container Alpine (~15 MB RAM) | Auto-Restart container; Let's Encrypt TLS 1.3 |
| **Tier 3** | **Django Gunicorn API** | Container Bridge (`172.28.0.10`)| TCP `8000` (Internal Socket) | `sg_hospitality_ec2` | 2 Workers / 2 Threads (~180 MB RAM)| Pre-fork worker pool (< 250MB heap budget) |
| **Tier 3** | **Celery Outbox Worker**| Container Bridge (`172.28.0.11`)| Internal IPC | `sg_hospitality_ec2` | 2 Concurrency (~120 MB RAM) | Auto-Restart worker daemon; outbox polling |
| **Tier 4** | **Redis 7.2 Alpine** | Container Bridge (`172.28.0.12`)| TCP `6379` (Internal Socket) | `sg_hospitality_ec2` | `maxmemory 128mb` (AOF Sync) | In-Memory cache mounted to persistent host EBS |
| **Tier 5** | **RDS PostgreSQL 17** | `subnet-private-db-a` (`10.0.2.0/24`)| TCP `5432` (Private VPC IP) | `sg_hospitality_rds` | `db.t4g.micro` (1GB RAM, 20GB gp3) | Single-AZ; 7-Day Snapshots; Continuous WAL |
| **Tier 6** | **Static Web Bucket** | AWS S3 Global | HTTPS / REST API | S3 Bucket Policy (OAC) | 5 GB Free Tier Allocation | Fronted by CloudFront Global Anycast Edge (1 TB/mo) |
| **Tier 6** | **WORM Compliance Vault**| AWS S3 Global | HTTPS / REST API | S3 Object Lock Policy | 5 GB Free Tier Allocation | 7-Year Immutable Compliance Lock (2,555 Days) |
| **Tier 7** | **GitHub Actions CI/CD**| GitHub Hosted Runner | HTTPS / AWS STS OIDC | IAM Role Assumption | 2,000 Free Minutes / Month | Passwordless STS federation; Automated SSM Deploy |

---

## 3. End-to-End Low-Level Operational Sequences

### 3.1 Sequence 1: Direct Web Guest Booking & Payment Settlement

This sequence details a guest booking a room via the public booking engine, tokenizing credit card credentials via Stripe Elements, securing room availability via Redis pessimistic locks, and finalizing financial records in PostgreSQL:

```
+========================================================================================================================+
|                               SEQUENCE 1: DIRECT GUEST BOOKING & PAYMENT SETTLEMENT                                    |
+========================================================================================================================+
|                                                                                                                        |
|  [ GUEST BROWSER ]   [ STRIPE VAULT ]   [ NGINX PROXY ]   [ GUNICORN API ]   [ REDIS LOCK ]   [ RDS PG17 ]   [ S3 VAULT ]|
|         |                   |                  |                 |                  |              |              |    |
|  1. Guest submits room booking form with date range: 2026-09-01 to 2026-09-05                                          |
|  2. Direct Tokenization via Stripe Elements (PCI-DSS SAQ-A):                                                           |
|         |--- Card Details ->|                  |                 |                  |              |              |    |
|         |<-- Token: pm_9988-|                  |                 |                  |              |              |    |
|         |                                      |                 |                  |              |              |    |
|  3. Submit Booking Request:                    |                 |                  |              |              |    |
|     POST /api/v1/booking/reservations -------->|                 |                  |              |              |    |
|         |                   |                  |--- Pass 8000 -->|                  |              |              |    |
|         |                   |                  |                 |-- Acquire Lock ->|              |              |    |
|         |                   |                  |                 |   (pms:lock:101) |              |              |    |
|         |                   |                  |                 |<-- GRANTED ------|              |              |    |
|         |                   |                  |                 |                                 |              |    |
|         |                   |                  |                 |-- Charge Token via Stripe API ->| (Stripe API) |    |
|         |                   |                  |                 |<-- Charge Confirmed (ch_123) ---|              |    |
|         |                   |                  |                 |                                                |    |
|         |                   |                  |                 |-- Begin ACID DB Transaction --->|              |    |
|         |                   |                  |                 |   (Insert Reservation Record)   |              |    |
|         |                   |                  |                 |   (Post Balanced GL Entries)    |              |    |
|         |                   |                  |                 |   (Insert Outbox: booking_done) |              |    |
|         |                   |                  |                 |<-- COMMIT Transaction (9ms) ----|              |    |
|         |                   |                  |                 |                                                |    |
|         |                   |                  |                 |-- Release Lock ->|                             |    |
|         |<------------------ HTTP 201 Created -|                 |                  |                             |    |
|         |                                                                                                         |    |
|  4. Asynchronous Outbox Worker:                                                                                   |    |
|     Celery consumes `booking_done` -> Generates Folio PDF/A-3 -> Uploads to S3 Compliance Vault ----------------->|    |
+========================================================================================================================+
```

---

### 3.2 Sequence 2: POS Offline Batch Synchronization & Idempotency Replay

This sequence details how an on-premise dining POS terminal buffers transactions locally during a 72-hour WAN outage and reconciles state with the cloud once network connectivity is restored:

```
+========================================================================================================================+
|                               SEQUENCE 2: 72-HOUR POS OFFLINE BATCH REPLAY SYNCHRONIZATION                             |
+========================================================================================================================+
|                                                                                                                        |
|  [ TAURI POS TOUCHSCREEN ]   [ LOCAL SQLITE WAL ]   [ NGINX PROXY ]   [ GUNICORN API ]   [ REDIS DEDUP ]   [ RDS PG17 ]|
|              |                       |                     |                 |                  |               |      |
|  1. WAN Disconnected: 100 Transactions settled against Local SQLite with p99 < 15ms latency.                           |
|     (Receipts stored in `offline_receipt_events` with SHA-256 state hashes and sync_status = 'PENDING').               |
|              |                       |                     |                 |                  |               |      |
|  2. Network Health Probe restores WAN Uplink:                                                                          |
|     Tauri background sync thread detects HTTP 200 OK on HEAD /health/                                                  |
|              |                       |                     |                 |                  |               |      |
|  3. Submit Offline Batch Replay:                                                                                       |
|     POST /api/v1/pos/sync/batch -------------------------->|                 |                  |               |      |
|     Headers: { "X-Idempotency-Key": "idemp_pos_batch_998877" }               |                  |               |      |
|     Payload: 100 Signed JSON Settlement Events (1 MB gzip payload)           |                  |               |      |
|              |                       |                     |--- Pass 8000 -->|                  |               |      |
|              |                       |                     |                 |-- Check Idemp -->|               |      |
|              |                       |                     |                 |<-- Key NOT FOUND |               |      |
|              |                       |                     |                 |                                  |      |
|              |                       |                     |                 |-- Set Idemp Lock (72h TTL) ----->|      |
|              |                       |                     |                 |                                  |      |
|              |                       |                     |                 |-- Begin Batch Transaction ------>|      |
|              |                       |                     |                 |   (Reconcile Receipts to GL)     |      |
|              |                       |                     |                 |   (Emit Outbox BOM Events)       |      |
|              |                       |                     |                 |<-- Batch COMMIT (14ms) ----------|      |
|              |<-------------------------------------------- HTTP 200 OK -----|                                         |
|              |                                                                                                         |
|  4. Local SQLite State Transition: Update `offline_receipt_events` SET sync_status = 'RECONCILED'.                     |
+========================================================================================================================+
```

---

### 3.3 Sequence 3: Automated Night Audit Financial Balancing & Day-Close

This sequence details the automated fiscal close executed at `02:00 UTC` by Celery Beat to post room revenues, balance the double-entry ledger, and export compliance reports:

```
+========================================================================================================================+
|                               SEQUENCE 3: AUTOMATED NIGHT AUDIT FINANCIAL DAY-CLOSE                                    |
+========================================================================================================================+
|                                                                                                                        |
|  [ CELERY BEAT (02:00 UTC) ]   [ GUNICORN CORE ]   [ RDS POSTGRESQL 17 ]   [ IMMUTABLE LEDGER ]   [ S3 COMPLIANCE ]    |
|              |                         |                     |                      |                     |            |
|  1. Scheduled Cron triggers `night_audit_close_task`         |                      |                     |            |
|              |------------------------>|                     |                      |                     |            |
|                                        |-- Step A: Post Room Charges (Room Rate + VAT) ---------->|            |
|                                        |   (For all Active Checked-In Folios)                     |            |
|                                        |                                                          |            |
|                                        |-- Step B: Execute Double-Entry GL Ledger Validation ---->|            |
|                                        |   Assert: SUM(Debits) == SUM(Credits) ($0.00 Variance)   |            |
|                                        |                                                          |            |
|                                        |-- Step C: Advance Fiscal Business Date (Day-Close Lock)->|            |
|                                        |   (Freezes previous day transactions as read-only)       |            |
|                                        |                                                                       |            |
|                                        |-- Step D: Generate PDF/A-3 Consolidated Fiscal Audit Report --------->|            |
|                                        |   (Uploads to S3 Object Lock WORM Vault with 7-Year Retention Hold)   |            |
|                                        |<-- Upload Confirmed (SEC 17a-4 / European VAT Compliant) -------------|            |
+========================================================================================================================+
```

---

### 3.4 Sequence 4: Single-Environment CI/CD Rolling Deployment

This sequence details the automated deployment workflow from Git commit to production container rolling replacement:

```
+========================================================================================================================+
|                               SEQUENCE 4: SINGLE-ENVIRONMENT CI/CD ROLLING DEPLOYMENT                                  |
+========================================================================================================================+
|                                                                                                                        |
|  [ GIT PUSH MAIN ]   [ GITHUB ACTIONS RUNNER ]   [ AMAZON ECR ]   [ AWS SSM SESSION ]   [ EC2 DOCKER HOST ]   [ /HEALTH/ ]|
|         |                       |                      |                 |                       |                 |   |
|  1. Push code to `main` branch  |                      |                 |                       |                 |   |
|         |---------------------->|                      |                 |                       |                 |   |
|                                 | 2. Quality Gates:    |                 |                       |                 |   |
|                                 |    • Pytest (>80%)   |                 |                       |                 |   |
|                                 |    • Mypy strict     |                 |                       |                 |   |
|                                 |    • Bandit scan     |                 |                       |                 |   |
|                                 |                                        |                       |                 |   |
|                                 | 3. OIDC STS Exchange |                 |                       |                 |   |
|                                 | 4. Buildx ARM64 Img  |                 |                       |                 |   |
|                                 | 5. Push Tagged Img ->|                 |                       |                 |   |
|                                 |    (Prune to last 3) |                 |                       |                 |   |
|                                 |                                        |                       |                 |   |
|                                 | 6. Dispatch Deployment via AWS SSM --->|                       |                 |   |
|                                 |                                        |-- Execute Commands -->|                 |   |
|                                 |                                        |   • docker compose pull                 |   |
|                                 |                                        |   • python manage.py migrate            |   |
|                                 |                                        |   • docker compose up -d                |   |
|                                 |                                        |   • docker system prune -af             |   |
|                                 |                                        |                       |                 |   |
|                                 |                                        |   • Probe Endpoint -------------------->|   |
|                                 |                                        |   <-- HTTP 200 OK ----------------------|   |
|                                 |<-- Deployment Success (200 OK) --------|                                             |   |
+========================================================================================================================+
```

---

## 4. Failure Domains & Recovery SLAs

The platform classifies failure scenarios and enforces strict recovery service level agreements:

| Failure Scenario | Impacted Subsystem | Detection Mechanism | Automated Recovery Action | Target RTO | Target RPO |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **WAN / Internet Cut** | On-Premise POS Terminals | Health probe timeout (`HEAD /health/`) | POS activates **72-Hour Offline Autonomy** against local SQLite WAL. | **$0.0\text{s}$ (Zero Interruption)** | **$\le 0.0\text{s}$ (Local Zero Loss)** |
| **Django API Crash** | Compute Worker Container | Docker Healthcheck probe | Docker Compose restart policy (`restart: always`) restarts container. | **$< 2.0\text{s}$** | **$\le 0.0\text{s}$** |
| **Redis Memory OOM** | In-Memory Ephemeral Cache | Memory boundary threshold | Evicts volatile keys (`volatile-lru`); restarts from AOF file. | **$< 3.0\text{s}$** | **$\le 1.0\text{s}$ (AOF Sync)** |
| **EC2 Hardware Fault** | Cloud Compute Host | AWS EC2 Status Check (1/2) | AWS EC2 Auto-Recovery launches instance on new underlying hardware. | **$< 3.0\text{ minutes}$** | **$\le 0.0\text{s}$ (EBS Preserved)** |
| **Database Corruption**| RDS PostgreSQL 17 | PostgreSQL PANIC / Disk I/O | Execute Single-AZ Point-in-Time Recovery (PITR) CLI runbook from S3 WAL. | **$< 15.0\text{ minutes}$** | **$\le 1.0\text{s}$ (WAL Stream)** |

---

## 5. Low-Level Architectural Verification Checklist

- [ ] **Assertion 1 (Zero Paid Managed Services):** Infrastructure utilizes 1x EC2 `t4g.micro`, 1x RDS `db.t4g.micro` Single-AZ, 0 ALB, 0 WAF, 0 NAT Gateways, and 0 PrivateLink endpoints (< $0.50/mo total spend).
- [ ] **Assertion 2 (Port Micro-Segmentation):** Inbound TCP 80 and 443 are open exclusively on NGINX; internal ports 8000, 6379, and 5432 are isolated within private container and VPC networks.
- [ ] **Assertion 3 (Immutable GL Triggers):** PostgreSQL triggers strictly block `UPDATE` and `DELETE` queries on `general_ledger_entries`.
- [ ] **Assertion 4 (Redis Memory Cap):** Redis memory usage is strictly bounded at 128 MB with `volatile-lru` eviction active.
- [ ] **Assertion 5 (Offline POS Autonomy):** Unplugging the WAN cable allows POS terminals to settle dining checks and print physical receipts with $p_{99} < 15\text{ ms}$.
- [ ] **Assertion 6 (S3 Compliance Retention):** S3 bucket `hospitality-financial-archive-prod` enforces a 2,555-day WORM Object Lock in `COMPLIANCE` mode.
- [ ] **Assertion 7 (Billing Alarm Active):** AWS CloudWatch Billing Alarm `hospitality-os-free-tier-budget-breach` triggers at `$0.50 USD` estimated charges.
