# Low-Level Design (LLD) Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Production Cloud Low-Level Design (LLD) & Subsystem Topology Specification
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 1.0.0 (Production Engineering Baseline)
* **Status:** Approved / Architecture-Ready Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Cloud Provider:** Amazon Web Services (AWS) — Primary Region: `us-east-1` (Dual-AZ: `us-east-1a`, `us-east-1b`)
* **Classification:** Highly Confidential / Enterprise Low-Level Architecture Blueprint
* **Aligned Specifications:**
  - [`docs/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/BRD_SPECIFICATION.md) (Domain Rules, 72h POS Autonomy, Append-Only GL, Recipe BOM)
  - [`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md) (Multi-AZ 99.9% Uptime, $p_{95} \le 120\text{ ms}$, TLS 1.3, Rate Limits, 30 DB Sockets)
  - [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md) (0.50 vCPU / 1GB RAM Compute, 512MB Redis, 0.50 vCPU / 2GB / 20GB gp3 PostgreSQL)
  - [`docs/HLA_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/HLA_SPECIFICATION.md) (7-Tier Platform Topology)
  - [`docs/ADR_COLLECTION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/ADR_COLLECTION.md) (ADR-001 through ADR-011 Master ADR Baseline)
  - [`docs/NETWORK_AND_SECURITY_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NETWORK_AND_SECURITY_SPECIFICATION.md) (VPC 10.0.0.0/20, 6 Subnets, Route Tables, Security Groups)
  - [`docs/DATABASE_AND_STORAGE_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/DATABASE_AND_STORAGE_SPECIFICATION.md) (PostgreSQL 17 Multi-AZ, PgBouncer, Redis 7.2 AOF, 3x S3 Buckets)
  - [`docs/SECURITY_AND_COMPLIANCE_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/SECURITY_AND_COMPLIANCE_SPECIFICATION.md) (WAF WebACL, KMS CMK, SSM Parameter Hierarchy, IAM Dual-Roles, OIDC)

---

## 1. Executive Architectural Overview & Master Topology

Hospitality OS is an integrated, cloud-native hospitality platform architected to unify property lodging, multi-station point-of-sale dining, real-time kitchen orchestration, automated recipe inventory depletion, and append-only financial accounting into a single resilient operating system.

The cloud implementation is deployed inside a dedicated Amazon Virtual Private Cloud (VPC) spanning two Availability Zones (`us-east-1a` and `us-east-1b`) in `us-east-1`.

```
+==================================================================================================================+
|                                    HOSPITALITY OS 7-TIER ARCHITECTURAL TOPOLOGY                                   |
+==================================================================================================================+
|                                                                                                                  |
|  [ TIER 1: CLIENT & ON-PREMISE HARDWARE ]                                                                        |
|    • Public Web & Mobile Guest Booking SPA | Guest QR Self-Service Menu (CloudFront CDN Edge)                    |
|    • Front Desk PMS PC (Tauri Desktop App + Receipt Bridge)                                                      |
|    • Dining Room & Bar Touchscreen POS Terminals (Tauri + SQLite Local Buffer + ESC/POS Network Driver)           |
|    • Kitchen Display Station (KDS) & ESC/POS Ticket Printer Bridge                                               |
|                                                                                                                  |
|  [ TIER 2: EDGE INGRESS & ROUTING PLANE ]                                                                        |
|    • Amazon Route 53 (DNS Anycast with Health Checks)                                                            |
|    • AWS WAF (Web Application Firewall: Core Rule Set, SQLi filters, Rate Limits: 30/60/120 req/min)             |
|    • AWS Application Load Balancer (ALB: TLS 1.3 Termination, Path Routing, Multi-AZ Health Probing)             |
|                                                                                                                  |
|  [ TIER 3: STATELESS COMPUTE PLANE (DUAL-AZ) ]                                                                   |
|    • AWS ECS Fargate Cluster (2x Tasks, 0.25 vCPU / 512MB RAM per task)                                          |
|    • Container 1: Django Modular Monolith API Worker (Gunicorn Pre-Fork Model, Port 8000)                        |
|    • Container 2: Asynchronous Celery Outbox Worker (Recipe BOM depletion, GL Journal Balancing)                 |
|    • Container 3: PgBouncer Sidecar (Transaction Pooling Mode, capping DB connections to 5-10 sockets)          |
|                                                                                                                  |
|  [ TIER 4: EPHEMERAL STATE PLANE ]                                                                               |
|    • AWS ElastiCache for Redis 7.2 (cache.t4g.micro / 512 MB RAM, AOF Disk Persistence)                          |
|    • Namespaces: Distributed Locks (pms:lock:* 10s), Idempotency Replay (idemp:pos:* 72h), Room Search Cache (60s)|
|                                                                                                                  |
|  [ TIER 5: RELATIONAL PERSISTENCE PLANE ]                                                                       |
|    • AWS RDS PostgreSQL 17 Multi-AZ (db.t4g.micro / db.t4g.small, 20GB gp3 SSD, 3,000 IOPS, 125 MB/s)           |
|    • Schema-per-Tenant isolation, Double-Entry Append-Only General Ledger, Effective-Dated Tax Models            |
|    • Maximum Connection Ceiling: 25 Backend Connections (Governed strictly by PgBouncer)                         |
|                                                                                                                  |
|  [ TIER 6: DURABLE OBJECT VAULT PLANE ]                                                                          |
|    • s3-hospitality-web-prod (CloudFront OAC Private Origin for Web SPAs)                                        |
|    • s3-hospitality-financial-archive-prod (S3 Object Lock COMPLIANCE Mode: 7-Year WORM Vault, Glacier Deep Tier) |
|    • s3-hospitality-wal-backups-prod (Continuous PostgreSQL 17 WAL Streaming for Point-in-Time Recovery <= 1.0s)  |
|                                                                                                                  |
|  [ TIER 7: OBSERVABILITY, TELEMETRY & SECURITY CONTROL PLANE ]                                                   |
|    • Amazon CloudWatch (Container Insights, p95 Latency Alarms, 30d Log Retention) + AWS SNS                     |
|    • AWS KMS (Customer Managed Key Envelope Encryption) + AWS SSM Parameter Store (Dynamic Secret Injection)    |
|    • GitHub Actions CI/CD (OIDC Federated IAM Authentication without Static AWS Keys)                            |
+==================================================================================================================+
```

---

## 2. Master Network & Component Topology Table

The following master matrix details all infrastructure components, network addressing, port bindings, security associations, and hardware allocations across the platform:

| Tier | Component / Service | Subnet & CIDR | Network Interface / Protocol | Security Group ID | Resource Sizing & Limits | Scaling / Redundancy Model |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | Local POS Terminals (Dining/Bar) | On-Premise LAN (`192.168.1.0/24`) | HTTPS (`TCP 443`) / ESC/POS (`TCP 9100`) | Native Firewall | 15" Touchscreen PC, SQLite 3.45 WAL | Dual Fixed Terminals + Local Offline Autonomy |
| **Tier 1** | Front Desk PMS Workstation | On-Premise LAN (`192.168.1.0/24`) | HTTPS (`TCP 443`) / RJ12 Drawer Kick | Native Firewall | Windows 11 / Edge Browser / Tauri Bridge | Fixed Workstation Node |
| **Tier 2** | Amazon CloudFront CDN | Global Edge Network (600+ PoPs) | HTTPS (`TCP 443`) / TLS 1.3 | AWS Managed Edge | Unlimited Global Anycast Edge Delivery | Global Edge Multi-PoP Caching |
| **Tier 2** | AWS WAF WebACL | Ingress to ALB | Layer 7 HTTP/S Inspection | AWS Managed WAF | 3 Managed Rule Sets + 3 Custom Rate Limits | Integrated with ALB Ingress |
| **Tier 2** | AWS ALB (Node A) | `subnet-pub-a` (`10.0.0.0/24`) | In: `TCP 443/80` $\rightarrow$ Out: `TCP 8000` | `sg-alb-ingress` | Managed L7 ALB (Idle Timeout: 60s) | Multi-AZ Cross-Zone Load Balancing |
| **Tier 2** | AWS ALB (Node B) | `subnet-pub-b` (`10.0.1.0/24`) | In: `TCP 443/80` $\rightarrow$ Out: `TCP 8000` | `sg-alb-ingress` | Managed L7 ALB (Idle Timeout: 60s) | Multi-AZ Cross-Zone Load Balancing |
| **Tier 2** | NAT Gateway A | `subnet-pub-a` (`10.0.0.0/24`) | In: `10.0.2.0/23` $\rightarrow$ Out: `0.0.0.0/0` | Managed EIP | Managed NAT (Elastic IP: 54.x.x.x) | Outbound Egress for Payment Gateways |
| **Tier 3** | ECS Task 1 (App + Celery + PgB) | `subnet-priv-app-a` (`10.0.2.0/23`)| In: `TCP 8000` $\rightarrow$ Out: `5432,6379,443` | `sg-ecs-compute` | $0.25\text{ vCPU} / 512\text{ MB RAM}$ | Active-Active Dual-AZ Task Placement |
| **Tier 3** | ECS Task 2 (App + Celery + PgB) | `subnet-priv-app-b` (`10.0.4.0/23`)| In: `TCP 8000` $\rightarrow$ Out: `5432,6379,443` | `sg-ecs-compute` | $0.25\text{ vCPU} / 512\text{ MB RAM}$ | Active-Active Dual-AZ Task Placement |
| **Tier 4** | ElastiCache Redis 7.2 Primary | `subnet-iso-db-a` (`10.0.6.0/24`) | Inbound: `TCP 6379` (TLS + AUTH) | `sg-redis-cache` | `cache.t4g.micro` (512 MB RAM) | AOF Disk Sync + Daily S3 Snapshots |
| **Tier 5** | RDS PostgreSQL 17 Primary | `subnet-iso-db-a` (`10.0.6.0/24`) | Inbound: `TCP 5432` (SCRAM-SHA-256) | `sg-rds-postgres` | `db.t4g.micro` / `small`, 20GB gp3 SSD | Multi-AZ Synchronous Physical Mirror |
| **Tier 5** | RDS PostgreSQL 17 Standby | `subnet-iso-db-b` (`10.0.7.0/24`) | Synchronous Mirroring (`TCP 5432`) | `sg-rds-postgres` | `db.t4g.micro` / `small`, 20GB gp3 SSD | Automated Standby Failover ($< 60\text{s}$) |
| **Tier 6** | `s3-hospitality-web-prod` | AWS S3 Regional Fabric | HTTPS (SigV4 via CloudFront OAC) | S3 Bucket Policy | Scalable Object Storage | 99.999999999% (11 9s) Durability |
| **Tier 6** | `s3-financial-archive-prod` | AWS S3 Regional Fabric | HTTPS (SigV4 via App Role) | S3 Object Lock | 7-Year WORM Compliance Vault | Glacier Flexible $\rightarrow$ Deep Archive Lifecycle |
| **Tier 6** | `s3-wal-backups-prod` | AWS S3 Regional Fabric | HTTPS (Continuous WAL Stream) | S3 Bucket Policy | Streaming WAL Archive | Point-in-Time Recovery $\le 1.0\text{s}$ RPO |
| **Tier 7** | AWS KMS Master CMK | AWS KMS Security Module | Cryptographic Envelope Calls | KMS Key Policy | FIPS 140-2 Level 2 HSM Origin | Automated Annual Key Rotation (365d) |
| **Tier 7** | AWS SSM Parameter Store | AWS Systems Manager Fabric | HTTPS (`TCP 443` via PrivateLink) | IAM Policy | Standard Parameter Store (Free Tier) | Encrypted `SecureString` Hierarchy |
| **Tier 7** | Amazon CloudWatch | AWS Observability Fabric | HTTPS (`TCP 443` via PrivateLink) | IAM Policy | 30-Day Container Log Retention | Multi-Channel SNS Alarms (Slack/Email) |

---

## 3. End-to-End Operational Request Flows

### 3.1 Flow 1: Direct Web Guest Booking & Payment Settlement

This sequence details a public guest searching room availability, selecting dates, submitting credit card payment via Stripe Elements (PCI SAQ-A), acquiring distributed reservation locks, executing double-entry ledger settlement, and archiving the finalized booking folio in the S3 WORM Vault.

```
+========================================================================================================================+
|                                    FLOW 1: DIRECT GUEST BOOKING & PAYMENT SETTLEMENT                                   |
+========================================================================================================================+
|                                                                                                                        |
|  [ GUEST BROWSER ]     [ CLOUDFRONT/S3 ]     [ WAF / ALB ]     [ ECS GUNICORN ]     [ REDIS 7.2 ]     [ PG17 / PGB ]   |
|         |                     |                    |                  |                   |                  |     |
|  1. Get Booking SPA --------->|                    |                  |                   |                  |     |
|     (Index.html + JS) <-------| (Cached Edge PoP)  |                  |                   |                  |     |
|         |                                          |                  |                   |                  |     |
|  2. Search Room Availability: GET /api/v1/booking/availability?start=2026-09-01&end=2026-09-05                     |
|         |----------------------------------------->|                  |                   |                  |     |
|         | (WAF: Passes Rate Limit < 30 req/min)    |                  |                   |                  |     |
|         |                                          |--- Forward 8000->|                   |                  |     |
|         |                                          |                  |-- Check Cache --->|                  |     |
|         |                                          |                  |   (pms:avail:*)   |                  |     |
|         |                                          |                  |<-- Cache Hit -----|                  |     |
|         |<--------------------- Return JSON Availability (35ms) ------|                   |                  |     |
|         |                                                                                 |                  |     |
|  3. Guest Submits Credit Card via Stripe Elements (Direct Browser-to-Stripe Tokenization)                          |
|         |---- Tokenize PAN / CVV directly to Stripe CDN (https://api.stripe.com) --------> [ Stripe Vault ]         |
|         |<--- Returns PaymentMethod Token: pm_1P987654321 --------------------------------- [ Stripe Vault ]         |
|         |                                                                                                    |     |
|  4. Confirm Booking: POST /api/v1/booking/settle { room_id: "RM-101", token: "pm_1P98...", dates: "..." }           |
|         |----------------------------------------->|                  |                   |                  |     |
|         |                                          |--- Forward 8000->|                   |                  |     |
|         |                                          |                  |-- Acquire Lock -->|                  |     |
|         |                                          |                  | (pms:lock:RM101)  |                  |     |
|         |                                          |                  | (SET NX EX 10s)   |                  |     |
|         |                                          |                  |<-- Lock ACQUIRED -|                  |     |
|         |                                          |                  |                                      |     |
|         |                                          |                  |-- Execute Stripe PaymentIntent API ->|     |
|         |                                          |                  |<-- Payment Confirmed (ch_123) -------|     |
|         |                                          |                  |                                      |     |
|         |                                          |                  |-- Begin ACID DB Transaction -------->|     |
|         |                                          |                  |   (Insert Reservation & Guest)       |     |
|         |                                          |                  |   (Append-Only GL: Cash / Revenue)   |     |
|         |                                          |                  |   (Insert OutboxEvent: booking.conf) |     |
|         |                                          |                  |<-- COMMIT Transaction (8ms) ---------|     |
|         |                                          |                  |                                      |     |
|         |                                          |                  |-- Release Lock -->|                  |     |
|         |                                          |                  |   (DEL pms:lock)  |                  |     |
|         |<--------------------- Return HTTP 201 Created (115ms) ------|                   |                  |     |
|                                                                                                                    |
|  5. Asynchronous Background Folio Archival (Celery Worker)                                                          |
|     Celery consumes `booking.confirmed` outbox event -> Generates PDF/A-3 Folio Invoice ->                         |
|     Uploads to S3 Compliance Vault (`s3-hospitality-financial-archive-prod`) with 7-Year WORM Lock.                |
+========================================================================================================================+
```

---

### 3.2 Flow 2: POS Offline Batch Synchronization & Replay Engine

This sequence demonstrates the local-first autonomy of on-premise POS terminals during a 72-hour WAN internet outage, followed by network restoration and high-burst batch synchronization ($5.00–10.00\text{ RPS}$) against cloud idempotency deduplication buffers.

```
+========================================================================================================================+
|                                    FLOW 2: POS OFFLINE BATCH SYNC & IDEMPOTENCY REPLAY                                 |
+========================================================================================================================+
|                                                                                                                        |
|  [ TAURI POS TERMINAL ]      [ LOCAL SQLITE ]     [ AWS WAF / ALB ]     [ ECS GUNICORN ]     [ REDIS IDEMP ]     [ PG17 ]  |
|         |                          |                     |                     |                    |               |  |
|  ==== PHASE A: WAN OUTAGE ACTIVE (72-HOUR LOCAL-FIRST AUTONOMY) =====================================================  |
|  1. Cashier enters table order ->  |                     |                     |                    |               |  |
|  2. Settles cash / Split bill ---> |                     |                     |                    |               |  |
|  3. Writes local receipt journal ->| Insert SQLite (WAL) |                     |                    |               |  |
|  4. Native Rust ESC/POS bridge kicks drawer & prints receipt (p99 < 15ms)      |                    |               |  |
|  5. Queues payload in `offline_receipt_events` (sync_status = PENDING)          |                    |               |  |
|         |                          |                     |                     |                    |               |  |
|  ==== PHASE B: WAN NETWORK RESTORATION & BATCH REPLAY FLUSH =========================================================  |
|  6. Background thread detects WAN uplink active (HEAD /health/ returns 200 OK)  |                    |               |  |
|  7. POS Batch Sync: POST /api/v1/pos/sync/batch                                 |                    |               |  |
|     Headers: { "X-Idempotency-Key": "idemp_pos_tx_8899aabbcc" }                 |                    |               |  |
|     Payload: 100 Buffered Signed Receipt Events (1MB compressed JSON)           |                    |               |  |
|         |----------------------------------------------->|                     |                    |               |  |
|         |                                                |--- Forward 8000 --->|                    |               |  |
|         |                                                |                     |-- Check Idempotency|               |  |
|         |                                                |                     |   (GET idemp:pos:*)                |
|         |                                                |                     |<-- Key NOT FOUND --|               |  |
|         |                                                |                     |                    |               |  |
|         |                                                |                     |-- Set Buffer (72h)->|              |  |
|         |                                                |                     |   (SET EX 259200s) |               |  |
|         |                                                |                     |                    |               |  |
|         |                                                |                     |-- Batch SQL Insert --------------->|  |
|         |                                                |                     |   (Reconcile Receipts to GL)       |  |
|         |                                                |                     |   (Trigger BOM Stock Depletions)   |  |
|         |                                                |                     |<-- Batch COMMIT (12ms) ------------|  |
|         |<--------------------- Return HTTP 200 OK (Batch Reconciled) ---------|                                    |  |
|         |                          |                                                                                |  |
|  8. Update Local SQLite: Set sync_status = 'RECONCILED' for all 100 buffered receipts.                              |
+========================================================================================================================+
```

---

### 3.3 Flow 3: Night Audit Financial Ledger Balancing & Day-Close Batch

This sequence details the automated end-of-day financial reconciliation executed at `02:00 UTC`:

```
+========================================================================================================================+
|                                    FLOW 3: NIGHT AUDIT FINANCIAL BALANCING & BATCH CLOSE                               |
+========================================================================================================================+
|                                                                                                                        |
|  [ AWS CLOUDWATCH CRON ]     [ CELERY AUDIT WORKER ]     [ PG17 / PGBOUNCER ]     [ S3 WORM VAULT ]     [ AWS SNS ]    |
|             |                           |                         |                       |                  |         |
|  1. Trigger 02:00 UTC Event ----------->|                         |                       |                  |         |
|     (events.night_audit_trigger)        |                         |                       |                  |         |
|             |                           |-- Acquire Exclusive Lock|                       |                  |         |
|             |                           |   (audit:lock:20260823) |                       |                  |         |
|             |                           |                         |                       |                  |         |
|             |                           |-- Step A: Post Room Charges to Active Folios -> |                  |         |
|             |                           |   (Daily Room Rate + Effective Taxes)           |                  |         |
|             |                           |<-- 10 Room Folios Posted (15ms) ----------------|                  |         |
|             |                           |                         |                       |                  |         |
|             |                           |-- Step B: Validate Double-Entry GL Ledger ----->|                  |         |
|             |                           |   SELECT SUM(debit) - SUM(credit) FROM gl_entry;|                  |         |
|             |                           |<-- Variance = 0.00000 (Balanced Ledger) --------|                  |         |
|             |                           |                         |                       |                  |         |
|             |                           |-- Step C: Freeze Financial Day (Close Date) --->|                  |         |
|             |                           |<-- Fiscal Day Closed (COMMIT) ------------------|                  |         |
|             |                           |                         |                       |                  |         |
|             |                           |-- Step D: Generate Consolidated Audit Report -> |                  |         |
|             |                           |   (PDF/A-3 Audit Report & VAT Export Package)   |                  |         |
|             |                           |   Upload to S3 WORM Vault --------------------->| (Object Lock)    |         |
|             |                           |                                                 | (7-Year Hold)    |         |
|             |                           |<-- 200 S3 PutObject Confirmed ------------------|                  |         |
|             |                           |                                                                    |         |
|             |                           |-- Step E: Publish Night Audit Completion Summary ----------------->|         |
|             |                           |   (Dispatches Executive KPI Report to GM/Owner Slack & Email)      |         |
+========================================================================================================================+
```

---

### 3.4 Flow 4: OIDC Federated CI/CD Deployment & Zero-Downtime ECS Rolling Rollout

This sequence details the automated delivery pipeline from Git commit to production container replacement with zero downtime:

```
+========================================================================================================================+
|                               FLOW 4: OIDC FEDERATED CI/CD & ZERO-DOWNTIME ROLLING DEPLOYMENT                          |
+========================================================================================================================+
|                                                                                                                        |
|  [ GITHUB ACTIONS ]    [ AWS STS (OIDC) ]    [ TERRAFORM S3/DDB ]    [ AMAZON ECR ]    [ ECS FARGATE ]    [ AWS ALB ]  |
|         |                      |                     |                     |                  |                |       |
|  1. Git Push to main --------->|                     |                     |                  |                |       |
|     (repo: The-Code-Consortium/hospitality-saas-monorepo)                  |                  |                |       |
|         |                      |                     |                     |                  |                |       |
|  2. Exchange OIDC JWT -------->|                     |                     |                  |                |       |
|     (sts:AssumeRoleWithWebIdentity)                  |                     |                  |                |       |
|         |<-- Ephemeral 15m STS Credentials ----------|                     |                  |                |       |
|         |                                            |                     |                  |                |       |
|  3. Run Automated Tests: pytest --cov (>80%), mypy, flake8                 |                  |                |       |
|         |                                            |                     |                  |                |       |
|  4. Terraform Apply (HCL Modules) ------------------>|                     |                  |                |       |
|     (Acquires DynamoDB lock -> Applies VPC/RDS/ECS -> Releases Lock)       |                  |                |       |
|         |<-- Infrastructure Converged ---------------|                     |                  |                |       |
|         |                                                                  |                  |                |       |
|  5. Build & Push Multi-Stage Docker Image -------------------------------->|                  |                |       |
|     (Tag: SHA-256 Digest; PrivateLink Transfer com.amazonaws.ecr.dkr)     |                  |                |       |
|         |<-- Image Layer Digest Confirmed ---------------------------------|                  |                |       |
|         |                                                                                     |                |       |
|  6. Trigger Zero-Downtime ECS Rolling Update ------------------------------------------------>|                |       |
|     (aws ecs update-service --service hospitality-web-app --force-new-deployment)             |                |       |
|         |                                                                                     |                |       |
|         | ==== PHASE A: SPAWN NEW CONTAINER TASKS (Max 200% Capacity) ========================|                |       |
|         | • Spawns Task 1 (v2) in us-east-1a (10.0.2.x) and Task 2 (v2) in us-east-1b (10.0.4.x)|              |       |
|         | • ECS Agent retrieves SSM secrets & KMS data keys (DATABASE_URL, REDIS_URL)        |                |       |
|         | • Gunicorn web server initializes on Port 8000 (Warm ORM Cache)                     |                |       |
|         |                                                                                     |                |       |
|         | ==== PHASE B: ALB HEALTH PROBE VALIDATION ==========================================|                |       |
|         |                                                                                     |-- Register ENI |       |
|         |                                                                                     |<-- Target Group|       |
|         |                                                                                     |                |       |
|         |                                                                                     |<-- GET /health/ (10s)--|
|         |                                                                                     |--- 200 OK (5ms) ------>|
|         |                                                                                     |                |       |
|         | ==== PHASE C: TRAFFIC SHIFT & DEREGISTRATION (Min 100% Healthy) ====================|                |       |
|         | • ALB shifts new HTTP/S requests to Task 1 (v2) and Task 2 (v2)                     |                |       |
|         | • ALB initiates Connection Draining on old v1 tasks (Deregistration Delay: 30s)     |                |       |
|         | • In-flight transactions complete; old tasks receive SIGTERM and gracefully exit    |                |       |
|         |<--------------------- Deployment Succeeded (Zero Dropped Requests) -----------------|                |       |
|                                                                                                                        |
|  7. Continuous Telemetry & Anomaly Rollback Watchdog (Amazon CloudWatch)                                               |
|     CloudWatch monitors TargetResponseTime (p95 <= 120ms) and 5XX error rates. If thresholds breached within 3 mins,    |
|     CloudWatch Alarm dispatches SNS rollback trigger to automatically revert to previous Task Definition.              |
+========================================================================================================================+
```

---

## 4. Failure Recovery & Disaster Domains

| Failure Scenario | Impacted Component | Detection Mechanism | Automated Recovery Action | RTO | RPO |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ECS Container Crash / OOM** | Application Web Task | ALB Target Group 10s Health Probe | ECS Fargate automatically destroys failed container and provisions replacement task. ALB routes to surviving AZ task. | $< 15\text{ Seconds}$ | $0.0\text{ Seconds}$ |
| **Primary RDS Database Node Failure** | PostgreSQL Primary in `us-east-1a` | RDS Multi-AZ Synchronous Heartbeat Probe | AWS RDS initiates automatic DNS failover to Standby Replica in `us-east-1b`. PgBouncer reconnects upon DNS propagation. | $< 60\text{ Seconds}$ | $0.0\text{ Seconds}$ (Synchronous) |
| **Complete Availability Zone Outage** | AZ `us-east-1a` | AWS Global Control Plane Alarm | ALB routes 100% of ingress to `us-east-1b`. ECS tasks scale in surviving AZ. RDS Standby in `us-east-1b` promoted to Primary. | $< 60\text{ Seconds}$ | $0.0\text{ Seconds}$ |
| **Total Property WAN Internet Outage**| On-Premise LAN Terminals | Native POS Rust Heartbeat Probe | POS terminals enter Local-First Autonomous Mode. Orders written to SQLite WAL. Sync engine pauses until WAN restoration. | $0.0\text{ Seconds}$ (Zero Downtime) | $0.0\text{ Seconds}$ (Buffered locally) |
| **Accidental Data Corruption / Truncation**| Production Database | DBA / Security Incident Report | Execute Point-in-Time Recovery (PITR) CLI Runbook to restore database to exact second prior to corruption. | $\le 15\text{ Minutes}$ | $\le 1.0\text{ Second}$ |

---

## 5. Architectural Verification Checklist

- [ ] **Verification 1 (Multi-AZ Path):** Traffic dispatched through ALB reaches both `us-east-1a` and `us-east-1b` compute tasks.
- [ ] **Verification 2 (Connection Capping):** PgBouncer enforces transaction pooling; active PostgreSQL connections remain $\le 20$.
- [ ] **Verification 3 (Redis Ephemeral TTLs):** Distributed reservation locks expire strictly within 10 seconds; idempotency keys persist for 72 hours.
- [ ] **Verification 4 (WORM Immutability):** Finalized audit PDFs in `s3-hospitality-financial-archive-prod` cannot be deleted via AWS CLI or Console.
- [ ] **Verification 5 (OIDC CI/CD):** Deployments execute with short-lived STS credentials without static AWS secrets in GitHub Actions.
