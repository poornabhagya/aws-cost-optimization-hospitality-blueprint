# Non-Functional Requirements (NFR) Specification

---

### Document Metadata
* **Document Version:** 1.0.0
* **System Name:** Single-Property Unified Hospitality Operating System (Hospitality OS)
* **Target Scope:** 1 Boutique Property (10 Rooms, 30-Seat Restaurant, 20-Seat Bar)
* **Author:** Principal Cloud Solutions Architect / Lead DevOps Engineer
* **Status:** Draft / In-Review
* **Effective Date:** August 19, 2026
* **Classification:** Internal Engineering Baseline & Operational Benchmark

---

## 1. System Scale, Workload & Concurrency Targets

### 1.1 Ingress / Egress Traffic Expectations & Derived Throughput Targets

The workload profile for a single boutique property is derived directly from the operational domain flows defined in the Business Requirements Document ([`docs/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/BRD_SPECIFICATION.md)). Operational metrics account for standard daily cycles, meal service rushes, check-in flushes, and external web query patterns.

#### A. Business Operational Baseline (BRD Input)

| Operational Domain / Flow | Daily Target Volume | Peak Rush Windows | Peak Load Multiplier | Peak Operational Trigger Events |
| :--- | :--- | :--- | :--- | :--- |
| **Restaurant & Bar Live Orders** | 75 – 100 checks / day (3.2 items / check) | 12:00–14:00 (Lunch)<br>19:00–21:30 (Dinner) | **4.5x** | Simultaneous dining table turnover, bar rush, happy hour drink ordering. |
| **Front Desk Check-in / Out** | 8 – 10 room operations / day | 11:00–12:00 (Check-out)<br>15:00–17:00 (Check-in) | **6.0x** | Group arrivals, weekend tourist check-ins, bulk folio settlements. |
| **Direct Web Booking Searches** | 1,200 – 1,800 room queries / day | 18:00–22:00 (Evening booking surge) | **3.0x** | Marketing campaign drops, seasonal rate lookups, organic search clicks. |
| **POS Offline Batch Sync** | 0 – 3 network outage reconciliations / mo | Immediate network reconnection | **10.0x** (Replay burst) | Uplink restoration after ISP drop; flushing up to 100 buffered receipts. |
| **Kitchen KDS / KOT Dispatch** | 240 – 320 digital tickets / day | 12:30–13:30 (Lunch peak)<br>19:30–20:30 (Dinner peak) | **5.0x** | Simultaneous course fires ("Hold/Fire" release), multi-course tasting menus. |

#### B. Derived Technical Throughput & Throttling Targets (Calculated RPS)

| Operation / Endpoint Category | Average Throughput (RPS) | Peak Burst Throughput (RPS) | Peak Multiplier | Ingress Rate-Limit / Throttling Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Direct Web Booking Engine** (`/api/v1/booking/*`) | 0.02 – 0.05 RPS | 0.25 – 0.50 RPS | 10.0x | 30 requests / minute per IP (Burst: 10 req) |
| **POS Order & Folio Operations** (`/api/v1/pos/*`) | 0.05 – 0.10 RPS | 0.80 – 1.20 RPS | 12.0x | 120 requests / minute per Terminal (Burst: 30 req) |
| **Front Desk & PMS Operations** (`/api/v1/pms/*`) | 0.01 – 0.03 RPS | 0.30 – 0.50 RPS | 15.0x | 60 requests / minute per Workstation (Burst: 15 req) |
| **Kitchen KDS Station WebSocket / Poll** | 0.04 – 0.08 RPS | 0.40 – 0.80 RPS | 10.0x | 120 requests / minute per Station |
| **POS Offline Batch Synchronization** (`/api/v1/sync/*`) | 0.00 RPS (Idle) | 5.00 – 10.00 RPS (Replay) | Burst Only | 20 requests / minute per Terminal (Max 5 concurrent) |
| **Health Checks & Telemetry** (`/health/`, `/metrics`) | 0.10 – 0.20 RPS | 0.20 – 0.40 RPS | 2.0x | Unthrottled for internal VPC CIDRs |

```
+----------------------------------------------------------------------------------------------------+
|                               THROUGHPUT & RATE LIMITING TOPOLOGY                                  |
|                                                                                                    |
|  [ Public Internet (Guests) ] ----(Rate Limit: 30 req/min)----> [ Traefik Ingress Gateway ]       |
|                                                                          |                         |
|  [ Local LAN (POS/Front Desk)] ---(Rate Limit: 120 req/min)---> [ Ingress Controller / TLS Term ]  |
|                                                                          |                         |
|                                                                          v                         |
|                                                     [ Django Modular Application Stack ]           |
|                                                                          |                         |
|                                                                          v                         |
|                                                     [ PgBouncer Connection Pool (Max 30) ]         |
|                                                                          |                         |
|                                                                          v                         |
|                                                     [ PostgreSQL 17 Dedicated Database ]           |
+----------------------------------------------------------------------------------------------------+
```

---

### 1.2 Concurrency & Connection Capacities

```
+----------------------------------------------------------------------------------------------------+
|                              CONCURRENT CLIENT HARDWARE TOPOLOGY                                   |
|                                                                                                    |
|  +--------------------------+  +--------------------------+  +----------------------------------+  |
|  |     FIXED POS NODES      |  |   MANAGEMENT DEVICES     |  |       AUTHENTICATED SESSIONS     |  |
|  | * 1 Front Desk PC        |  | * 1 Owner Laptop / Phone |  | * 1 Owner                        |  |
|  | * 1 Restaurant POS       |  | * 1 GM Tablet            |  | * 1 GM                           |  |
|  | * 1 Bar POS Terminal     |  | * 1 Auditor Workstation  |  | * 1 Front Desk Agent             |  |
|  | * 1 Kitchen KDS / Print  |  |                          |  | * 1 Restaurant Cashier           |  |
|  |                          |  |                          |  | * 1 Bartender                    |  |
|  |                          |  |                          |  | * 1 Head Chef                    |  |
|  |                          |  |                          |  | * 1 Financial Auditor            |  |
|  +--------------------------+  +--------------------------+  +----------------------------------+  |
|               |                             |                                 |                    |
|               +-----------------------------+---------------------------------+                    |
|                                             |                                                      |
|                                             v                                                      |
|                         [ Max 30 Active Database Connections (PgBouncer) ]                         |
+----------------------------------------------------------------------------------------------------+
```

1. **Active POS Hardware Nodes:**
   * **4 Fixed Nodes:** 
     - 1x Front Desk Workstation PC (Windows 11 / Edge + Desktop Service).
     - 1x Main Dining Room POS Terminal (Touchscreen Tauri + Thermal Printer + Cash Drawer).
     - 1x Bar Speed POS Terminal (Touchscreen Tauri + Thermal Printer + Cash Drawer).
     - 1x Kitchen Display Station (KDS) & ESC/POS Kitchen Ticket Printer Bridge.
2. **Active Management & Back-Office Client Devices:**
   * **Up to 3 Devices:**
     - 1x Property Owner Mobile / Laptop (Executive BI & SaaS Subscription Console).
     - 1x General Manager Tablet (Operational Floor Management & Overrides).
     - 1x Night Auditor / Financial Controller Workstation (GL Reconciliation & Tax Engine).
3. **Max Concurrent Staff Sessions:**
   * **7 Authenticated Staff Sessions:** Encompassing Owner, GM, Front Desk Agent, Cashier, Bartender, Chef, and Night Auditor.
4. **Max Concurrent Direct Booking / Guest Sessions:**
   * **20 – 30 Active Web Sessions:** Concurrent table QR digital menu viewers, mobile guest portal users, and direct web booking engine search sessions.
5. **Database Connection Pool Limit:**
   * **Max 30 Active Client Connections:** Governed strictly via PgBouncer connection pooler in transaction pooling mode, preventing backend connection exhaustion on the single-tenant PostgreSQL instance.

---

### 1.3 Expected Payload Constraints

* **Standard API JSON Request / Response:** Maximum **128 KB** (e.g., standard POS cart payload, room availability calendar slice, user authentication payload).
* **Receipt / Invoice PDF Download:** Maximum **2 MB** (e.g., multi-page consolidated guest folio PDF, full monthly VAT tax ledger report).
* **Offline POS Batch Sync Payload:** Maximum **1 MB** (supporting up to 100 queued offline checks and receipts with cryptographic signatures).

---

## 2. Performance & Latency Service Level Objectives (SLOs)

### 2.1 Critical Path API Latency Thresholds

All API latency thresholds are measured at the outer Ingress/Load Balancer layer under standard and peak operational conditions.

| Endpoint / Critical Operation | p50 (Median) | p95 (SLO Target) | p99 (Worst Case) | Max SLA Ceiling | Operational Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Health Check (`/health/`, `/ready/`)** | < 5 ms | < 15 ms | < 30 ms | 100 ms | Infrastructure load balancer probe routing. |
| **POS Order Placement & Folio Post** | < 45 ms | < 120 ms | < 250 ms | 500 ms | Immediate server check creation & order firing. |
| **Room Availability Search (Single Day)** | < 35 ms | < 90 ms | < 180 ms | 400 ms | Direct booking engine room calendar lookup. |
| **Payment Gateway Capture (Stripe/Bank)** | < 650 ms | < 1,500 ms | < 2,800 ms | 5,000 ms | Third-party payment pre-auth and capture. |
| **Hardware Receipt Print & Drawer Kick** | < 20 ms | < 60 ms | < 120 ms | 250 ms | Native desktop ESC/POS driver byte transmission. |
| **Kitchen KDS Bump / State Transition** | < 25 ms | < 75 ms | < 150 ms | 300 ms | Line cook stage change (`In Prep` -> `Ready`). |
| **Night Audit Financial Batch Step** | < 120 ms | < 450 ms | < 900 ms | 2,500 ms | Daily room charge posting & GL journal balance. |

---

### 2.2 Network, Proxy & Container Timeouts

```
+----------------------------------------------------------------------------------------------------+
|                                    TIMEOUT CASCADE ENFORCEMENT                                     |
|                                                                                                    |
|  [ Ingress / ALB Timeout: 60.0s ]                                                                  |
|       |                                                                                            |
|       +---> [ WSGI / Gunicorn Worker Timeout: 30.0s ]                                              |
|                  |                                                                                 |
|                  +---> [ Database Statement Timeout: 5.0s ]                                        |
|                  |                                                                                 |
|                  +---> [ Third-Party Payment Gateway HTTP Timeout: 5.0s ]                          |
+----------------------------------------------------------------------------------------------------+
```

1. **Load Balancer (ALB) Idle Timeout:** **60.0 Seconds** (terminates hanging or orphaned HTTP connections at the gateway).
2. **Application WSGI / Gunicorn Worker Timeout:** **30.0 Seconds** (worker is terminated and restarted if request execution exceeds 30s).
3. **Database Statement Timeout (`statement_timeout`):** **5,000 ms (5.0 Seconds)** (aborts runaway SQL queries to preserve database capacity).
4. **Third-Party Payment Gateway Timeout:** **5.0 Seconds** (hard HTTP connection/read timeout for external payment gateway API calls).

---

## 3. Availability, Reliability & Fault Tolerance

### 3.1 Availability SLA Commitments

| Component / Subsystem | Availability SLA | Max Allowed Unplanned Downtime | Continuity Mechanism |
| :--- | :--- | :--- | :--- |
| **Core Hospitality Hub API** | **99.9% Uptime** | ≤ 43.8 minutes / calendar month | Multi-AZ container deployment with auto-restart. |
| **Local POS Terminal Execution** | **99.999% Continuity** | ≤ 26.3 seconds / calendar month | Local-first embedded database (72-hour offline mode). |
| **Direct Web Booking Engine** | **99.9% Uptime** | ≤ 43.8 minutes / calendar month | Edge CDN caching for static assets & multi-AZ backend. |
| **Kitchen Display System (KDS)** | **99.99% Continuity** | ≤ 4.38 minutes / calendar month | Local LAN fallback & instant WebSocket reconnection. |

---

### 3.2 Redundancy & Self-Healing

```
+----------------------------------------------------------------------------------------------------+
|                                 HIGH-AVAILABILITY ARCHITECTURE                                     |
|                                                                                                    |
|                         [ AWS Application Load Balancer (ALB) ]                                    |
|                                     |                     |                                        |
|                    +----------------+                     +----------------+                       |
|                    |                                                       |                       |
|                    v                                                       v                       |
|     +------------------------------+                       +------------------------------+        |
|     |     AVAILABILITY ZONE A      |                       |     AVAILABILITY ZONE B      |        |
|     |  [ Container Task 1 (App) ]  |                       |  [ Container Task 2 (App) ]  |        |
|     |  [ Redis Broker (Primary) ]  |                       |  [ Redis Standby (Replica) ] |        |
|     |  [ RDS PostgreSQL (Primary)] |                       |  [ RDS Multi-AZ (Standby) ]  |        |
|     +------------------------------+                       +------------------------------+        |
+----------------------------------------------------------------------------------------------------+
```

1. **Container Redundancy:**
   * Application plane runs a **minimum of 2 container tasks** distributed across **2 distinct Availability Zones (Multi-AZ)** behind the Application Load Balancer.
2. **Health Check & Auto-Restart Specifications:**
   * **ALB Health Check Endpoint:** `GET /health/`
   * **Health Check Interval:** 10 Seconds
   * **Unhealthy Threshold:** 2 consecutive failures (triggers immediate container deregistration).
   * **Healthy Threshold:** 2 consecutive successes.
   * **Container Replacement SLA:** Crashed or non-responsive application containers are terminated and replaced by orchestrator tasks in **< 30 seconds**.
3. **Database High Availability:**
   * Managed Multi-AZ PostgreSQL deployment with automatic synchronous standby replication and automated failover in **< 60 seconds**.

---

## 4. Disaster Recovery (DR) & Data Resilience

### 4.1 Recovery Metrics (RPO & RTO)

| Metric | Target SLA | Implementation Architecture |
| :--- | :--- | :--- |
| **Recovery Point Objective (RPO)** | **≤ 1.0 Second** | Synchronous Multi-AZ database commit replication with continuous PostgreSQL Write-Ahead Log (WAL) streaming. |
| **Recovery Time Objective (RTO) — AZ Failure / Container Crash** | **≤ 60 Seconds** | Automatic load balancer container task redistribution and RDS automated standby promotion. |
| **Recovery Time Objective (RTO) — Full Catastrophic Restore** | **≤ 15 Minutes** | Automated OpenTofu/Terraform infrastructure re-hydration and snapshot point-in-time restore. |

---

### 4.2 Backup & Snapshot Schedules

```
+----------------------------------------------------------------------------------------------------+
|                                DATA BACKUP & SNAPSHOT PIPELINE                                     |
|                                                                                                    |
|  [ Live PostgreSQL 17 ] ---(Continuous WAL Streaming)---> [ AWS S3 / RDS PITR Window (7-35 Days) ]|
|            |                                                                                       |
|            +---(Daily 02:00 UTC Snapshot)---------------> [ Encrypted Snapshot Vault (30 Days) ]   |
|                                                                                                    |
|  [ Invoices & Ledger PDFs ] ---(WORM / Object Lock)-----> [ S3 Glacier Compliance Vault (7 Years) ]|
+----------------------------------------------------------------------------------------------------+
```

1. **Database Point-in-Time Recovery (PITR):**
   * Continuous Write-Ahead Log (WAL) archiving to encrypted object storage.
   * Granular point-in-time recovery window configurable between **7 and 35 Days**.
2. **Daily Full Database Snapshots:**
   * Automated full database volume snapshot taken daily at **02:00 UTC** (post-Night Audit).
   * Snapshots retained with rolling **30-Day retention policy**.
3. **Invoice & Legal Document Storage:**
   * All generated fiscal receipts, folio statements, and tax invoices stored in AWS S3 with **Object Lock (WORM - Write Once, Read Many)** and bucket versioning enabled to prevent deletion or overwriting.

---

## 5. Security, Privacy & Data Isolation

### 5.1 Data Isolation & Multi-Tenancy

* **Siloed Multi-Instance Architecture:** The boutique property operates with its own isolated database schema and application runtime, preventing noisy-neighbor resource contention and cross-tenant data leaks.
* **Domain Decoupling:** Cross-module queries between Property Management (PMS), Point of Sale (POS), and General Ledger (GL) are strictly decoupled. Cross-domain data propagation is mediated via standard asynchronous event messaging.

---

### 5.2 Encryption Standards

```
+----------------------------------------------------------------------------------------------------+
|                                    ENCRYPTION ARCHITECTURE                                         |
|                                                                                                    |
|  [ Client Browser / POS ] ----(TLS 1.3 / HTTPS / HSTS: max-age=31536000)----> [ Cloud Ingress ]   |
|                                                                                      |             |
|  [ Local SQLite / RxDB ]  <---(SQLCipher / AES-256 at-rest)                          |             |
|                                                                                      v             |
|  [ RDS PostgreSQL ]       <---(AWS KMS AES-256 Storage & Tablespace Encryption)------+             |
|                                                                                                    |
|  [ S3 Document Vault ]    <---(SSE-KMS AES-256 Object Encryption)-------------------+             |
+----------------------------------------------------------------------------------------------------+
```

1. **Data In-Transit:**
   * Strict enforcement of **TLS 1.3** across all public and internal ingress endpoints.
   * HTTP Strict Transport Security (HSTS) enabled with `max-age=31536000; includeSubDomains; preload`.
   * Insecure ciphers disabled; only forward-secret AEAD cipher suites permitted.
2. **Data At-Rest:**
   * **Relational Database (RDS PostgreSQL):** Encrypted using **AES-256** with customer-managed keys via AWS Key Management Service (AWS KMS).
   * **Object Storage (AWS S3):** Encrypted via Server-Side Encryption with AWS KMS (SSE-KMS).
   * **Local POS Terminals:** Local embedded storage (RxDB / SQLite) encrypted at-rest using **SQLCipher / AES-256** on client storage disks.

---

### 5.3 Authentication & Session Lifecycle

1. **Access Token Lifespan:**
   * Short-lived cryptographically signed JSON Web Tokens (JWT) with **30-Minute expiration**.
   * Embedded claims: `tenant_id`, `user_id`, `role`, `permissions`, `token_version`, and `active_modules`.
2. **Refresh Token Lifespan & Security:**
   * **14-Day validity** stored in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie.
   * Single-use token rotation enabled: using a refresh token issues a new token pair and invalidates the prior token.
   * Instant session revocation: bumping the user's `token_version` immediately invalidates all active tokens across all property terminals.
3. **PCI-DSS Scope & Cardholder Data Boundary:**
   * **Strict Zero Raw Card Storage Policy:** The platform never ingests, transmits, or stores Primary Account Numbers (PANs), cardholder PINs, or CVV/CVC codes.
   * All card transactions operate via iframe/SDK tokenization directly with certified payment orchestrators (e.g., Stripe, Hyperswitch).

---

## 6. Data Retention, Archiving & Storage Growth

### 6.1 Database Growth Projections

Capacity projections for a single boutique property (10 Rooms, 30-Seat Dining, 20-Seat Bar) over a 3-year operating horizon:

```
+----------------------------------------------------------------------------------------------------+
|                                 DATABASE STORAGE GROWTH TRAJECTORY                                 |
|                                                                                                    |
|   TIME HORIZON        DAILY CHECKS      DAILY DB GROWTH       CUMULATIVE DB VOLUME                 |
|   -----------------   ---------------   -------------------   ---------------------------------    |
|   Day 1 (Scaffold)    --                --                    ~ 85 MB (Base Schema & Seeds)        |
|   Year 1              75 - 100 / day    ~ 2.5 MB / day        ~ 1.00 GB                            |
|   Year 2              75 - 100 / day    ~ 2.5 MB / day        ~ 1.91 GB                            |
|   Year 3              75 - 100 / day    ~ 2.5 MB / day        ~ 2.82 GB                            |
+----------------------------------------------------------------------------------------------------+
```

* **Estimated Daily Checks:** 75 – 100 checks / day (averaging 3.2 line items per check).
* **Estimated Daily DB Storage Growth:** **~2.0 – 5.0 MB / day** (encompassing POS receipts, outbox events, inventory stock ledger rows, and immutable GL entries).
* **Estimated Annual DB Growth:** **~1.5 – 2.0 GB / year**.
* **3-Year Total DB Provisioning Target:** Allocate a baseline 20 GB gp3 SSD storage volume with auto-scaling storage enabled up to 100 GB.

---

### 6.2 Audit Log & File Retention Policies

| Log / Data Category | Storage Target | Hot Retention Window | Long-Term Compliance Policy | Deletion / Purge Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Application JSON Access Logs** | CloudWatch Logs / Grafana Loki | 30 Days | 90 Days (Cold S3 Glacier) | Automated lifecycle purge after 90 days. |
| **Security & RBAC Audit Trails** | Append-Only DB Table / S3 Log | 365 Days | 3 Years (Encrypted Archive) | Retained for 3 years; immutable. |
| **Closed Invoices & Guest Folios** | AWS S3 Object Lock (WORM) | 180 Days | **7 Years** (S3 Glacier Vault) | Regulatory fiscal compliance; no premature purge. |
| **General Ledger Journal Entries** | PostgreSQL Immutable Tables | Live Active DB | **Permanent** (Append-Only) | **Never deleted or purged.** |
| **Processed Outbox Events** | PostgreSQL `outbox_events` | 14 Days | -- | Pruned weekly for records with status `PUBLISHED`. |
