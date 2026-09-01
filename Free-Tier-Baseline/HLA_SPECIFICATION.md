# High-Level Architecture (HLA) Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Production High-Level Architecture (HLA) Specification: Single-Environment, Platform-Neutral & Local-First Topology
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 2.0.0 (Platform-Neutral Production Architecture Baseline)
* **Status:** Approved / Architecture-Ready Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Architectural Stance:** 100% Platform-Neutral, Cloud-Agnostic & Open-Source Standards (Linux, Docker Engine, Docker Compose, Nginx, Python 3.12, Gunicorn, Celery, Redis 7.2, PostgreSQL 17, S3-Compatible Storage API)
* **Aligned Specifications:**
  - [`docs/Enterprise Baseline/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/BRD_SPECIFICATION.md) (Domain Rules, 72h POS Autonomy, Append-Only GL, Recipe BOM)
  - [`docs/Enterprise Baseline/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/NFR_SPECIFICATION.md) ($p_{95} \le 120\text{ ms}$, TLS 1.3, Rate Limits, 30 DB Sockets)
  - [`docs/Enterprise Baseline/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/CAPACITY_SIZING.md) (0.50 vCPU / 1GB RAM Compute, 512MB Redis, 0.50 vCPU / 2GB / 20GB gp3 PostgreSQL)
  - [`docs/Free Tier Baseline/ADR_COLLECTION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/ADR_COLLECTION.md) (Master ADR Architecture Decision Baseline)

---

## 1. Executive Architectural Scope & System Vision

### 1.1 Architectural Vision
Hospitality OS is an integrated, modular, platform-neutral hospitality platform engineered to unify hotel property management, multi-station point-of-sale dining, real-time kitchen orchestration, automated recipe Bill-of-Materials (BOM) inventory depletion, and append-only financial accounting into a single resilient operating system.

The platform architecture resolves the fundamental operational vulnerability of traditional hospitality software—catastrophic failure during Wide Area Network (WAN) outages—by pairing a containerized, cloud-agnostic application and persistence plane with local-first, offline-autonomous desktop terminals capable of maintaining continuous property operations for up to 72 hours without internet connectivity.

```
+==================================================================================================================+
|                                    HOSPITALITY OS 7-TIER ARCHITECTURAL TOPOLOGY                                   |
+==================================================================================================================+
|                                                                                                                  |
|  [ TIER 1: CLIENT & ON-PREMISE HARDWARE PLANE ]                                                                  |
|    +-----------------------------+   +-----------------------------+   +------------------------------------+    |
|    | Public Web Booking / Mobile |   | Front Desk PMS Workstation  |   | Local POS Terminals (Dining & Bar) |    |
|    | Guest QR Self-Service Menu  |   | Visual Booking Grid / Folio |   | Embedded SQLite + ESC/POS Bridge   |    |
|    +-----------------------------+   +-----------------------------+   +------------------------------------+    |
|                   |                                 |                                     |                      |
|                   +---------------------------------+-------------------------------------+                      |
|                                                     | HTTPS / TLS 1.3                                            |
|                                                     v                                                            |
|  [ TIER 2: EDGE INGRESS & REVERSE PROXY PLANE ]                                                                  |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | Nginx Reverse Proxy: TLS 1.3 Termination (ACME / Let's Encrypt) | Rate Limiting (30-120 req/min) | Gzip    |    |
|    +--------------------------------------------------------------------------------------------------------+    |
|                                                     | Local Container Socket (HTTP Port 8000)                    |
|                                                     v                                                            |
|  [ TIER 3: STATELESS APPLICATION & COMPUTE PLANE (SINGLE HOST RUNTIME) ]                                         |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | Docker Engine & Docker Compose Network Stack                                                           |    |
|    |  +----------------------------------------------------+   +------------------------------------------+  |    |
|    |  | Web API Worker (Python 3.12 / Django / Gunicorn)   |   | Async Background Worker (Python / Celery)|  |    |
|    |  | • Modular Monolith Domain Logic (PMS, POS, Taxes)  |   | • Outbox Consumer & Recipe BOM Explosion |  |    |
|    |  | • 2x Pre-fork Workers (< 250 MB RAM Heap)          |   | • Double-Entry GL Journal Balancing      |  |    |
|    |  +----------------------------------------------------+   +------------------------------------------+  |    |
|    +--------------------------------------------------------------------------------------------------------+    |
|                         |                                                         |                              |
|                         v (Local Unix/TCP 6379)                                   v (Private TCP 5432)           |
|  [ TIER 4: EPHEMERAL STATE ]                                             [ TIER 5: PERSISTENCE PLANE ]           |
|    +-----------------------------------------+                             +----------------------------------+  |
|    | In-Container Redis 7.2 Alpine           |                             | PostgreSQL 17 Relational Engine  |  |
|    | • Distributed Pessimistic Locks (10s)   |                             | • Schema-per-Tenant Isolation    |  |
|    | • Idempotency Replay Buffers (72h)      |                             | • Double-Entry Append-Only GL    |  |
|    | • Room Availability Search Cache (60s)  |                             | • Effective-Dated Tax Models     |  |
|    | • Celery Task Broker (AOF Disk Sync)    |                             | • Dedicated Memory & Disk Buffer |  |
|    +-----------------------------------------+                             +----------------------------------+  |
|                                                                                           |                      |
|                                                                                           v Continuous WAL Stream|
|  [ TIER 6: DURABLE OBJECT VAULT PLANE ]                                                                          |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | S3-Compatible Object Store API                                                                         |    |
|    | • Public Web Assets Bucket: Compiled React SPAs, Web Client Bundles, Tenant Logos                       |    |
|    | • Compliance Vault Bucket: 7-Year WORM-Locked Folios, VAT Invoices, Night Audit Reports (SEC 17a-4)    |    |
|    | • WAL Backup Bucket: Continuous PostgreSQL Write-Ahead Logs for Point-in-Time Recovery (RPO <= 1.0s)   |    |
|    +--------------------------------------------------------------------------------------------------------+    |
|                                                                                                                  |
|  [ TIER 7: OBSERVABILITY & CI/CD CONTROL PLANE ]                                                                 |
|    • Automated CI/CD: Git Push -> OIDC Token Auth -> Automated Testing -> Private Registry -> Zero-Downtime Deploy|
|    • Health & Telemetry: In-Container `/health/` Probes, Structured JSON Access Logs, Budget & Metric Alerts    |
+==================================================================================================================+
```

---

## 2. 7-Tier Subsystem Decomposition

The platform is decomposed into seven discrete architectural planes to enforce failure containment, portability, and zero cross-domain state corruption:

| Subsystem Layer | Architectural Role | Core Technology | SLA / Latency Objective | Redundancy & Recovery Model |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Client & Hardware** | Guest digital booking, POS touchscreen orders, physical receipt generation, kitchen ticket display. | Modern Web / Tauri (Rust) / SQLite 3.45 / ESC/POS | $p_{50} < 10\text{ ms}$ (Local UI)<br>$p_{99} < 250\text{ ms}$ (KDS Bump) | Dual On-Premise POS Hardware Nodes with 72-Hour Local-First Autonomy |
| **Tier 2: Edge Ingress** | TLS 1.3 termination, ACME automated certificate renewal, reverse proxying, Layer 7 rate limiting. | Nginx 1.26 (Alpine) + Certbot Sidecar | $p_{99} < 5\text{ ms}$ (Proxy Overhead) | In-Container Edge Proxy with Automated Auto-Restart |
| **Tier 3: Stateless Compute** | Modular monolith business logic (PMS, POS, Inventory, Ledger), JWT auth, outbox event publishing. | Python 3.12 / Gunicorn / Celery in Docker | $p_{50} \le 45\text{ ms}$<br>$p_{95} \le 120\text{ ms}$ | Pre-fork Worker Process Pool (< 400 MB RAM Budget) |
| **Tier 4: Ephemeral State** | Distributed room lock management, idempotency replay dedup, room availability search caching, task broker. | Redis 7.2 Alpine (AOF Disk Sync) | $p_{99} < 1\text{ ms}$ (Local IPC Read/Write) | In-Memory with Host Block Storage Volume Mounting |
| **Tier 5: Relational Persistence** | Schema-per-tenant ACID storage, double-entry append-only accounting ledger, transactional outbox log. | PostgreSQL 17 (Dedicated Memory) | $p_{50} \le 12\text{ ms}$ (Transaction Commit) | Automated Daily Snapshots + Continuous WAL Stream (< 60s RTO, $\le 1.0\text{s}$ RPO) |
| **Tier 6: Durable Object Vault** | WORM-locked compliance invoice PDFs, fiscal audit export packages, historical database WAL segments. | S3-Compatible Object Store API | 99.999999999% (11 9s) Durability | 7-Year Non-Rewritable Non-Erasable Compliance Hold |
| **Tier 7: Observability & CI/CD** | Centralized structured logging, health probes, automated delivery pipelines, cost guardrails. | OpenTelemetry / OIDC / Docker Compose | Continuous 10-Second Health Probing | Automated Image Build, Test, and Container Restart |

---

## 3. Component-by-Component Technical Specification

### 3.1 Tier 1: Client & On-Premise Hardware Layer

```
+--------------------------------------------------------------------------------------------------+
|                               LOCAL-FIRST POS ARCHITECTURAL BLUEPRINT                             |
|                                                                                                  |
|  +--------------------------------------------------------------------------------------------+  |
|  |                             TAURI (RUST) DESKTOP POS CONTAINER                             |  |
|  |                                                                                            |  |
|  |  +-------------------------------------+      +-----------------------------------------+  |  |
|  |  |          REACT POS WEB UI           |      |           NATIVE RUST BRIDGE            |  |  |
|  |  | • Touchscreen Dining Floorplan       | ---> | • USB / Network ESC/POS Thermal Driver  |  |  |
|  |  | • Fast Bar Speed Ordering           |      | • Serial Cash Drawer Kick Relay (RJ12)  |  |  |
|  |  | • Course Hold / Fire (<100ms)       |      | • Offline Hardware Heartbeat Probe      |  |  |
|  |  +-------------------------------------+      +-----------------------------------------+  |  |
|  |                     |                                              |                       |  |
|  |                     v                                              v                       |  |
|  |  +-------------------------------------+      +-----------------------------------------+  |  |
|  |  |    EMBEDDED STORAGE (SQLITE / RXDB) |      |          SYNC & REPLAY ENGINE           |  |  |
|  |  | • Local Menu & Price Catalog Cache |      | • Replay Queue (`sync_status = PENDING`)|  |  |
|  |  | • Immutable Local Receipt Journals  | ---> | • Exponential Backoff Jitter (1s->60s)  |  |  |
|  |  | • 72-Hour Offline Transaction Buffer|      | • Idempotency Key Injection (`idemp_*`) |  |  |
|  |  +-------------------------------------+      +-----------------------------------------+  |  |
|  +--------------------------------------------------------------------------------------------+  |
|                                                |                                                 |
|                                                | WAN Uplink (HTTPS POST /api/v1/pos/sync/batch)  |
|                                                v                                                 |
|                                     [ Nginx Ingress Gateway ]                                    |
+--------------------------------------------------------------------------------------------------+
```

#### A. Local Point-of-Sale (POS) Engine Specification
1. **Application Wrapper:** Tauri 2.0 (Rust native core with embedded WebView2 / WebKit frontend).
2. **Local Database Engine:** SQLite 3.45 with Write-Ahead Logging (WAL) mode enabled.
3. **Local Storage Allocation:** 500 MB reserved disk space per terminal (sufficient for $> 50,000$ local transactions).
4. **Hardware Interface Drivers:** Native Rust direct-to-device bindings:
   - Thermal Receipt Printers: Raw ESC/POS bytecode over TCP (Port 9100) or USB `/dev/usb/lp0`.
   - Cash Drawers: RJ12 24V pulse command (`ESC p 0 25 250`) triggered on cash settlement.
   - Barcode & QR Scanners: HID keyboard emulation mode with 10ms debounce filtering.
5. **72-Hour Local-First Autonomy Guarantees:**
   - Terminals cache complete active menu catalogs, modifiers, table floorplans, and effective tax tables.
   - All order creation, check splitting, cash settling, and receipt printing execute against local SQLite with $p_{99} < 15\text{ ms}$ latency regardless of internet connectivity.

---

### 3.2 Tier 2: Edge Ingress & Reverse Proxy Plane (Nginx + ACME)

1. **Ingress Engine:** Nginx 1.26 Alpine running as the frontmost container exposing Ports `80` (HTTP redirect) and `443` (HTTPS TLS 1.3).
2. **Automated SSL/TLS Lifecycle:** Integrated ACME (Let's Encrypt / Certbot) container validating HTTP-01 challenges and automatically renewing X.509 certificates every 60 days.
3. **Cryptographic Standards:** Enforces TLS 1.3 and TLS 1.2 with secure cipher suites (`ECDHE-ECDSA-AES128-GCM-SHA256`, `ECDHE-RSA-AES128-GCM-SHA256`).
4. **Layer 7 Rate Limiting:**
   - Public Booking Engine (`/api/v1/booking/*`): Capped at **30 requests / minute** per IP (Burst: 10).
   - POS Terminal Synchronization (`/api/v1/pos/*`): Capped at **120 requests / minute** per Terminal (Burst: 30).
   - Front Desk PMS API (`/api/v1/pms/*`): Capped at **60 requests / minute** per Workstation (Burst: 15).

---

### 3.3 Tier 3: Stateless Application & Compute Plane (Django + Gunicorn + Celery)

```
+----------------------------------------------------------------------------------------------------+
|                                STATELESS COMPUTE PLANE MEMORY ALLOCATION                           |
|                                                                                                    |
|  [ GUNICORN WEB WORKER CONTAINER: ~180 MB ]                                                        |
|  • Base OS & Python 3.12 Runtime: 42 MB                                                            |
|  • Django Core & Domain Frameworks (PMS, POS, Taxes, GL): 110 MB                                    |
|  • Client Sockets & Connection Buffers: 15 MB                                                      |
|  • Request Heap & Serialization: 13 MB                                                             |
|                                                                                                    |
|  [ ASYNC CELERY WORKER CONTAINER: ~120 MB ]                                                        |
|  • Base OS & Python 3.12 Runtime: 42 MB                                                            |
|  • Celery Process & Kombu Transport: 48 MB                                                         |
|  • Task Execution Buffer (BOM Explosion & Ledger Balance): 30 MB                                    |
|                                                                                                    |
|  TOTAL COMPUTE MEMORY BOUNDARY: < 400 MB RAM (Well within 1.0 GB Host Footprint)                   |
+----------------------------------------------------------------------------------------------------+
```

1. **Web Runtime:** Python 3.12 executing Django under Gunicorn with a pre-fork worker model (2 worker processes $\times$ 2 threads = 4 concurrent execution threads).
2. **Domain Architecture:** Modular Monolith architecture strictly organized by domain boundaries (`/modules/pos-system`, `/modules/hotel-pms`, `/modules/kitchen-inventory`, `/core-hub`).
3. **Outbox Pattern Enforcement:** All cross-domain side effects (e.g., deducting inventory after meal sales) are written to the database `OutboxEvent` table inside the primary ACID transaction. Zero cross-module direct SQL mutations permitted.
4. **Asynchronous Processing:** Celery worker daemon continuously polls and consumes outbox event streams, performing dynamic recipe Bill-of-Materials (BOM) explosion, stock deduction, and ledger verification in the background.

---

### 3.4 Tier 4: Ephemeral State & In-Memory Plane (Redis 7.2 Alpine)

1. **Engine:** Redis 7.2 Alpine running in-container on the internal Docker network (Port `6379`).
2. **Durability & Persistence:** Configured with Append-Only File (`appendonly yes`, `appendfsync everysec`) mounted to persistent host storage.
3. **Memory Boundary & Eviction:** Strictly capped at **128 MB RAM** using `maxmemory-policy volatile-lru`.
4. **Operational Key Namespaces:**
   - Distributed Locks: `pms:lock:<room_id>:<date>` (10s TTL, pessimistic lock preventing double-booking).
   - Idempotency Deduplication: `idemp:pos:<client_tx_uuid>` (72h TTL, prevents duplicate replay settlement).
   - Search Availability Cache: `pms:avail:slice:<month>` (60s TTL, high-frequency booking engine cache).
   - Celery Task Queue: `celery:queue:default` (Persistent task queue for outbox workers).

---

### 3.5 Tier 5: Relational Persistence Plane (PostgreSQL 17)

1. **Engine:** PostgreSQL 17.x executing in an isolated database environment with dedicated kernel memory.
2. **Storage Allocation:** 20 GB block storage with Write-Ahead Logging (WAL) enabled (`wal_level = replica`).
3. **Multi-Tenancy Isolation:** Strict **Schema-per-Tenant** architecture. Each tenant property operates in an isolated schema namespace (`tenant_prop_01.*`) with zero cross-tenant query leakage.
4. **Append-Only Financial Ledger:** General Ledger tables enforce `NO UPDATE` and `NO DELETE` PostgreSQL database trigger constraints. All financial adjustments must be posted as new offsetting journal entries.
5. **Connection Disciplines:** Hard ceiling of **25 maximum database connections** (`max_connections = 25`, `statement_timeout = 5000ms`, `idle_in_transaction_session_timeout = 10000ms`).

---

### 3.6 Tier 6: Durable Object Storage & Compliance Vault (S3-Compatible API)

1. **Storage Protocol:** S3-Compatible Object Storage REST API.
2. **Bucket Architecture:**
   - `hospitality-web-assets`: Stores compiled React Single Page Applications, Vite bundles, and tenant branding.
   - `hospitality-financial-archive`: Immutable compliance vault storing finalized guest folios, VAT tax export packages, and daily night audit reports under a **7-Year (2,555-Day) WORM (Write-Once-Read-Many)** non-repudiation lock (SEC 17a-4 / European VAT compliant).
   - `hospitality-wal-backups`: Continuous PostgreSQL WAL streaming repository enabling Point-in-Time Recovery ($\text{RPO} \le 1.0\text{s}$).

---

## 4. End-to-End Operational Sequences

### 4.1 Flow 1: Synchronous Dining Folio Charge & Settlement

This sequence details a dining guest settling a restaurant check charged directly to their hotel room folio:

```
+========================================================================================================================+
|                               FLOW 1: SYNCHRONOUS DINING FOLIO CHARGE & ROOM POSTING                                  |
+========================================================================================================================+
|                                                                                                                        |
|  [ POS TERMINAL ]      [ NGINX PROXY ]      [ GUNICORN CORE ]      [ REDIS LOCK ]      [ POSTGRESQL 17 ]     [ KDS ]   |
|         |                     |                    |                     |                     |                |      |
|  1. Server selects "Charge to Room 101"            |                     |                     |                |      |
|  2. POST /api/v1/pos/checks/settle_room ---------->|                     |                     |                |      |
|         |                     |--- Forward 8000--->|                     |                     |                |      |
|         |                     |                    |-- Acquire Lock ---->|                     |                |      |
|         |                     |                    |   (pms:lock:RM101)  |                     |                |      |
|         |                     |                    |<-- Lock GRANTED ----|                     |                |      |
|         |                     |                    |                                           |                |      |
|         |                     |                    |-- Begin ACID DB Transaction ------------->|                |      |
|         |                     |                    |   (Assert Room 101 Status == 'OCCUPIED')  |                |      |
|         |                     |                    |   (Post Folio Transaction Line Item)      |                |      |
|         |                     |                    |   (Close POS Check: status = 'SETTLED')   |                |      |
|         |                     |                    |   (Insert OutboxEvent: pos.meal_sold)     |                |      |
|         |                     |                    |<-- COMMIT Transaction (8ms) --------------|                |      |
|         |                     |                    |                                           |                |      |
|         |                     |                    |-- Release Lock ---->|                     |                |      |
|         |<-------------------- Return HTTP 200 OK -|                     |                     |                |      |
|         |                                                                                                       |      |
|  3. Local Hardware ESC/POS bridge prints receipt & kicks cash drawer (p99 < 15ms).                              |      |
|  4. Kitchen Display Station (KDS) receives live WebSocket notification: status -> 'FIRED'. ------------------->|      |
+========================================================================================================================+
```

---

### 4.2 Flow 2: Asynchronous Outbox BOM Explosion & Append-Only General Ledger

This sequence demonstrates the decoupling of financial accounting and inventory depletion from user-facing API threads:

```
+========================================================================================================================+
|                               FLOW 2: ASYNCHRONOUS BOM EXPLOSION & APPEND-ONLY GL                                     |
+========================================================================================================================+
|                                                                                                                        |
|  [ OUTBOX TABLE (PG17) ]     [ CELERY WORKER ]     [ INVENTORY MODULE ]     [ GL ACCOUNTING ]     [ S3 OBJECT VAULT ]  |
|             |                        |                     |                        |                     |            |
|  1. Event: `pos.meal_sold`           |                     |                        |                     |            |
|     Payload: { check_id: "chk_99", items: [ { recipe_id: "rcp_steak_frites", qty: 2 } ] }                             |
|             |                        |                     |                        |                     |            |
|             |<-- Poll Event Stream --|                     |                        |                     |            |
|             |                        |-- Lookup Recipe BOM |                        |                     |            |
|             |                        |   (2x 250g Ribeye, 2x 150g Potatoes, 2x 50g Butter)        |            |
|             |                        |-------------------->|                        |                     |            |
|             |                        |                     |-- Deduct Stock Units ->| (Postgres Update)   |            |
|             |                        |                                                                    |            |
|             |                        |-- Post Double-Entry Journal Entry -------------------------------->|            |
|             |                        |   Debit: 1020-Guest-Ledger-Receivable ($90.00)                     |            |
|             |                        |   Credit: 4020-F&B-Food-Revenue ($75.00)                           |            |
|             |                        |   Credit: 2020-VAT-Output-Tax ($15.00)                             |            |
|             |                        |   (Trigger asserts Debit == Credit & NO-UPDATE/NO-DELETE)          |            |
|             |                        |                                                                    |            |
|             |                        |-- Mark Outbox Event `PROCESSED` in Database ---------------------->|            |
+========================================================================================================================+
```

---

### 4.3 Flow 3: 72-Hour Offline POS Batch Replay Synchronization

This sequence details how on-premise terminals flush locally buffered transactions upon internet restoration:

```
+========================================================================================================================+
|                               FLOW 3: 72-HOUR OFFLINE POS REPLAY SYNCHRONIZATION                                      |
+========================================================================================================================+
|                                                                                                                        |
|  [ TAURI POS TERMINAL ]      [ LOCAL SQLITE ]      [ NGINX PROXY ]      [ GUNICORN CORE ]      [ REDIS IDEMP BUFFER ]  |
|         |                          |                      |                    |                         |             |
|  1. Background thread detects WAN uplink active (HEAD /health/ returns 200 OK)    |                         |             |
|  2. POST /api/v1/pos/sync/batch ------------------------->|                    |                         |             |
|     Headers: { "X-Idempotency-Key": "idemp_pos_batch_998877" }                 |                         |             |
|     Payload: 100 Buffered Signed Receipt Events (1MB compressed JSON)          |                         |             |
|         |                          |                      |--- Forward 8000--->|                         |             |
|         |                          |                      |                    |-- Check Idempotency --->|             |
|         |                          |                      |                    |<-- Key NOT FOUND -------|             |
|         |                          |                      |                    |                         |             |
|         |                          |                      |                    |-- Set Buffer (72h) ---->|             |
|         |                          |                      |                    |   (SET EX 259200s)      |             |
|         |                          |                      |                    |                         |             |
|         |                          |                      |                    |-- Batch SQL Insert (PG17) ------------>|
|         |                          |                      |                    |   (Reconcile Receipts to GL)          |
|         |                          |                      |                    |   (Emit Outbox Events for BOM)        |
|         |                          |                      |                    |<-- Batch COMMIT (12ms) ----------------|
|         |<------------------------- Return HTTP 200 OK (Batch Reconciled) -----|                                       |
|         |                          |                                                                                   |
|  3. Update Local SQLite: Set sync_status = 'RECONCILED' for all 100 buffered receipts.                                 |
+========================================================================================================================+
```

---

## 5. Security, Zero-Trust & Single-Environment Governance

### 5.1 Defense-in-Depth Security Matrix
1. **Network Layer Isolation:** 
   - Public Ingress: Ports `80` and `443` open strictly on the Nginx reverse proxy.
   - Private Database: PostgreSQL port `5432` bound strictly to the internal container bridge network; **zero public internet routing**.
2. **Container Process Hardening:**
   - Containers execute under unprivileged non-root user accounts (`USER 1000:1000`).
   - Read-only container root filesystems with temporary writable mounts restricted to `/tmp` and `/var/run`.
3. **Payment Isolation (PCI-DSS SAQ-A):**
   - Credit card Primary Account Numbers (PAN) and CVVs are tokenized directly in the guest browser via Stripe Elements. Raw card numbers never touch the host network or database.
4. **GDPR Data Privacy & Accounting Preservation:**
   - Guest personal data is pseudonymized using cryptographic salt-shredding upon deletion requests, preserving immutable financial ledger entries without violating data privacy regulations.

---

### 5.2 Single-Environment Automated CI/CD Delivery Flow

The deployment lifecycle is 100% automated from source code commit to production container rollout:

```
+========================================================================================================================+
|                               SINGLE-ENVIRONMENT CONTINUOUS DELIVERY PIPELINE                                          |
+========================================================================================================================+
|                                                                                                                        |
|  [ GIT REPOSITORY ] ---> [ CI RUNNER (GitHub Actions) ] ---> [ CONTAINER REGISTRY ] ---> [ PRODUCTION CONTAINER HOST ] |
|         |                              |                               |                              |                |
|  1. Push `main` branch                 |                               |                              |                |
|         |----------------------------->|                               |                              |                |
|                                        | 2. Run Test Suite:            |                              |                |
|                                        |    • pytest --cov (>80%)      |                              |                |
|                                        |    • mypy static typing       |                              |                |
|                                        |    • flake8 linting           |                              |                |
|                                        |                               |                              |                |
|                                        | 3. Build Docker Image (ARM64) |                              |                |
|                                        | 4. Push Image with SHA Tag -->|                              |                |
|                                        |                               |                              |                |
|                                        | 5. Trigger Remote Deploy (SSH / SSM Session) --------------->|                |
|                                        |                                                              | 6. Pull Layers |
|                                        |                                                              | 7. Rolling Up: |
|                                        |                                                              |    docker      |
|                                        |                                                              |    compose     |
|                                        |                                                              |    up -d       |
|                                        |<--------------------- Deployment Complete (200 OK) ----------|                |
+========================================================================================================================+
```

---

## 6. High-Level Architecture Verification Checklist

- [x] **Platform Neutrality:** 100% cloud-agnostic architecture based strictly on open-source Linux, Docker, Nginx, Python, Redis, and PostgreSQL standards.
- [x] **Resource Sizing:** Compute and cache planes operate within < 500 MB RAM, meeting single-host execution constraints.
- [x] **Local-First POS Autonomy:** Full 72-hour offline operation guaranteed via embedded SQLite WAL and native ESC/POS hardware drivers.
- [x] **Persistence Integrity:** Schema-per-tenant isolation, append-only general ledger constraints, and automated continuous WAL archiving ($\text{RPO} \le 1.0\text{s}$).
- [x] **Zero-Downtime Delivery:** Automated CI/CD pipeline triggers container builds, tests, and rolling updates upon `git push main`.
