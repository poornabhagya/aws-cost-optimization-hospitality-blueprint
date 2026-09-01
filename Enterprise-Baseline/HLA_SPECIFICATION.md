# High-Level Architecture (HLA) Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Enterprise High-Level Architecture (HLA) Specification: Single-Property Cloud-Agnostic & Local-First Topology
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 1.0.0 (Production Architecture Baseline)
* **Status:** Approved / Architecture-Ready
* **Effective Date:** August 22, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Architectural Stance:** 100% Platform-Neutral & Cloud-Agnostic (Open-Source Standards: Linux, Docker, PostgreSQL 17, Redis 7, PgBouncer, Nginx, HAProxy, Ceph, Prometheus, Grafana)
* **Aligned Specifications:** 
  - [`docs/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/BRD_SPECIFICATION.md) (Business Requirements Baseline)
  - [`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md) (Non-Functional Requirements & SLAs)
  - [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md) (Technical Sizing & First-Principles Math)
* **Visual Topology Reference:** [`hospitality_os_hla_architecture.png`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/hospitality_os_hla_architecture.png)

---

## 1. Executive Architectural Scope & System Overview

### 1.1 Architectural Vision
Hospitality OS is an integrated, modular, cloud-agnostic enterprise hospitality platform designed to unify lodging property management, multi-station point-of-sale dining, real-time kitchen orchestration, dynamic recipe Bill-of-Materials (BOM) inventory depletion, and append-only financial accounting into a single resilient operating system.

The platform architecture resolves the fundamental operational vulnerability of traditional hospitality software—catastrophic failure during Wide Area Network (WAN) outages—by pairing a cloud-native, multi-availability zone (Multi-AZ) stateless application plane with local-first, offline-autonomous desktop terminals capable of maintaining continuous operations for up to 72 hours without internet connectivity.

```
+==================================================================================================================+
|                                    HOSPITALITY OS 7-TIER ARCHITECTURAL TOPOLOGY                                   |
+==================================================================================================================+
|                                                                                                                  |
|  [ TIER 1: CLIENT & ON-PREMISE HARDWARE ]                                                                        |
|    +-----------------------------+   +-----------------------------+   +------------------------------------+    |
|    | Public Web Booking / Mobile |   | Front Desk PMS Workstation  |   | Local POS Terminals (Dining & Bar) |    |
|    | Guest QR Self-Service Menu  |   | Visual Booking Grid / Folio |   | Embedded SQLite + ESC/POS Bridge   |    |
|    +-----------------------------+   +-----------------------------+   +------------------------------------+    |
|                   |                                 |                                     |                      |
|                   +---------------------------------+-------------------------------------+                      |
|                                                     | HTTPS / TLS 1.3                                            |
|                                                     v                                                            |
|  [ TIER 2: EDGE INGRESS & ROUTING PLANE ]                                                                        |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | Edge Reverse Proxy & WAF (Nginx): TLS 1.3 Termination | Rate Limiting (30-120 req/min) | HSTS / CORS    |    |
|    +--------------------------------------------------------------------------------------------------------+    |
|                                                     | Clean HTTP / gRPC Stream                                   |
|                                                     v                                                            |
|    +--------------------------------------------------------------------------------------------------------+    |
|    | Ingress Load Balancer (HAProxy): Round-Robin Dual-AZ Distribution | Multi-AZ Health Probes (10s)       |    |
|    +--------------------------------------------------------------------------------------------------------+    |
|                                                     |                                                            |
|                         +---------------------------+---------------------------+                                |
|                         |                                                       |                                |
|                         v                                                       v                                |
|  [ TIER 3: STATELESS COMPUTE PLANE (DUAL-AZ) ]                                                                   |
|    +-----------------------------------------+             +-----------------------------------------+           |
|    | Availability Zone A (Fault Domain 1)    |             | Availability Zone B (Fault Domain 2)    |           |
|    | Docker: Modular Monolith Instance 1     |             | Docker: Modular Monolith Instance 2     |           |
|    | Python 3.12 / Gunicorn (0.25 vCPU / 512M)|             | Python 3.12 / Gunicorn (0.25 vCPU / 512M)|           |
|    +-----------------------------------------+             +-----------------------------------------+           |
|                         |                                                       |                                |
|                         +---------------------------+---------------------------+                                |
|                                                     |                                                            |
|         +-------------------------------------------+---------------------------------------+                    |
|         |                                           |                                       |                    |
|         v                                           v                                       v                    |
|  [ TIER 4: EPHEMERAL STATE ]             [ TIER 5: PERSISTENCE ]                [ TIER 6: OBJECT VAULT ]         |
|  +----------------------------+          +---------------------------+          +----------------------+         |
|  | Redis 7 In-Memory Cluster  |          | PgBouncer Connection Pool |          | Immutable Ceph / S3  |         |
|  | • Distributed Locks        |          | Transaction Pooling Mode  |          | • WORM Folio Invoices|         |
|  | • Outbox Event Stream      |          | (5-10 Sockets to DB)      |          | • 7-Year Tax Audits  |         |
|  | • Room Slice Search Cache  |          +---------------------------+          | • Continuous WAL PITR|         |
|  +----------------------------+                        |                        +----------------------+         |
|         |                                              v                                       ^                 |
|         | Consume Outbox Stream          +---------------------------+                         |                 |
|         v                                | PostgreSQL 17 Primary DB  |                         |                 |
|  +----------------------------+          | Dedicated Tenant Schema   |                         |                 |
|  | Async Celery Worker        | -------->| Append-Only GL Ledger     |-------------------------+                 |
|  | • BOM Explosion            | (Writes) | Effective-Dated Taxes     |  Streaming WAL Logs                       |
|  | • GL Balancing & Audit     |          | (0.50 vCPU / 2GB / 20GB)  |                                           |
|  +----------------------------+          +---------------------------+                                           |
|                                                        |                                                         |
|  [ TIER 7: OBSERVABILITY & TELEMETRY PLANE ]           |                                                         |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | Prometheus Server (Metrics Scraper) <---- Scrape (App Nodes / PgBouncer / PG / Redis / Host Exporters)   |    |
|  | Grafana Dashboard (Visualizer & Alerts) <---- Query Probes (P50/P95/P99 Latencies, Active DB Sockets)   |    |
|  +----------------------------------------------------------------------------------------------------------+    |
+==================================================================================================================+
```

---

## 2. 7-Tier Subsystem Decomposition

The platform is strictly decomposed into seven discrete architectural planes to enforce failure containment, horizontal scalability, and zero cross-domain state corruption:

| Subsystem Layer | Architectural Role | Core Technology | SLA / Latency Objective | Redundancy Model |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Client & Hardware** | Guest digital access, POS touchscreen orders, physical receipt generation, kitchen ticket display. | Modern Web / Tauri (Rust) / SQLite / ESC/POS | $p_{50} < 10\text{ ms}$ (Local UI)<br>$p_{99} < 250\text{ ms}$ (KDS Bump) | Local Hardware Redundancy (Dual POS Terminals) |
| **Tier 2: Edge & Ingress** | TLS 1.3 termination, Anycast routing, DDoS mitigation, HTTP/gRPC load balancing, health probing. | Nginx 1.26 + HAProxy 3.0 | $p_{99} < 5\text{ ms}$ (Ingress Overhead) | Multi-AZ Proxy Instances with Auto-Failover |
| **Tier 3: Stateless Compute** | Modular monolith business logic (PMS, POS, Inventory, Ledger), JWT auth, outbox event generation. | Python 3.12 / Gunicorn / Celery in Docker | $p_{50} \le 45\text{ ms}$<br>$p_{95} \le 120\text{ ms}$ | Active-Active Dual-AZ (2 Tasks across 2 Fault Domains) |
| **Tier 4: Ephemeral State** | Distributed room lock management, idempotency replay dedup, room availability search caching, Celery broker. | Redis 7.2 (AOF Persistence) | $p_{99} < 2\text{ ms}$ (Read/Write) | In-Memory with Disk Snapshot & Auto-Restart |
| **Tier 5: Relational Persistence** | Schema-per-tenant ACID storage, double-entry append-only accounting ledger, transactional outbox log. | PostgreSQL 17 + PgBouncer 1.23 | $p_{50} \le 12\text{ ms}$ (Transaction Commit) | Daily Snapshots + Continuous WAL Stream (<60s RTO) |
| **Tier 6: Durable Object Vault** | WORM-locked compliance invoice PDFs, fiscal audit export packages, historical database WAL segments. | Ceph Object Storage / S3-Compatible API | 99.999999999% (11 9s) Durability | Multi-Replica Erasure Coding (7-Year Fiscal Lock) |
| **Tier 7: Observability Plane** | Time-series metrics collection, structured trace aggregation, SLO breach alerting, real-time dashboards. | Prometheus 2.53 + Grafana 11.1 | 15-second Scrape Resolution | Dedicated Telemetry Daemon with Disk Buffering |

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
|  |  | • Fast Bar Speed Ordering           |      | • Serial Cash Drawer Kick Relay         |  |  |
|  |  | • Course Hold / Fire (<100ms)       |      | • Offline Hardware Heartbeat Probe      |  |  |
|  |  +-------------------------------------+      +-----------------------------------------+  |  |
|  |                     |                                              |                       |  |
|  |                     v                                              v                       |  |
|  |  +-------------------------------------+      +-----------------------------------------+  |  |
|  |  |    EMBEDDED STORAGE (SQLITE / RXDB) |      |          SYNC & REPLAY ENGINE           |  |  |
|  |  | • Local Menu & Price Catalog Cache |      | • Replay Queue (`sync_status = PENDING`) |  |  |
|  |  | • Immutable Local Receipt Journals  | ---> | • Exponential Backoff Jitter (1s->60s)  |  |  |
|  |  | • 72-Hour Offline Transaction Buffer|      | • Idempotency Key Injection (`idemp_*`) |  |  |
|  |  +-------------------------------------+      +-----------------------------------------+  |  |
|  +--------------------------------------------------------------------------------------------+  |
|                                                |                                                 |
|                                                | WAN Uplink (HTTPS POST /api/v1/pos/sync/batch)  |
|                                                v                                                 |
|                                   [ Cloud Ingress Gateway ]                                      |
+--------------------------------------------------------------------------------------------------+
```

#### A. Local Point-of-Sale (POS) Engine Specification
1. **Host Environment:** Windows 11 Pro / Ubuntu Linux Desktop on 15" Touchscreen Terminals.
2. **Application Wrapper:** Tauri 2.0 (Rust core with embedded WebView2 / WebKit frontend).
3. **Local Database Engine:** SQLite 3.45 / RxDB with WAL (Write-Ahead Logging) mode enabled.
4. **Local Storage Allocation:** 500 MB reserved disk space per terminal (sufficient for $>50,000$ local transactions).
5. **Hardware Interface Drivers:** Native Rust direct-to-device bindings:
   - Thermal Receipt Printers: Raw ESC/POS bytecode over TCP (Port 9100) or USB `/dev/usb/lp0`.
   - Cash Drawers: RJ12 24V pulse command (`ESC p 0 25 250`) triggered on cash settlement.
   - Barcode & QR Scanners: HID keyboard emulation mode with 10ms debounce filtering.
6. **Local-First Autonomy Guarantees:**
   - Terminals cache complete active menu catalogs, modifiers, table floorplans, and effective tax tables.
   - All order creation, check splitting, cash settling, and receipt printing execute against local SQLite with $p_{99} < 15\text{ ms}$ latency regardless of WAN uplink state.

#### B. POS Offline Batch Synchronization Engine
1. **Network Outage Tolerance:** 72 continuous hours of complete WAN isolation ($>1,200$ checks per terminal).
2. **Replay Queue Design:** Local table `offline_receipt_events` storing serialized JSON payloads with cryptographic SHA-256 state hashes.
3. **Replay Trigger & Handshake:**
   - Background thread issues continuous 5-second HTTP `HEAD /health/` ping probes.
   - Upon uplink restoration, the Sync Engine initiates batch ingestion via `POST /api/v1/pos/sync/batch`.
4. **Concurrency & Rate Limit:** Maximum 5 concurrent batch requests per terminal, chunked at 25 receipts per payload, throttled at 20 requests/minute to prevent cloud compute saturation.
5. **Conflict Resolution Strategy:** Deterministic Client-Timestamp Append-Only Ingestion. Offline receipts are never discarded; conflicting room charge postings trigger automatic front desk reconciliation flags.

---

### 3.2 Tier 2: Edge Security & Ingress Routing Plane

```
+--------------------------------------------------------------------------------------------------+
|                                    EDGE INGRESS INFRASTRUCTURE                                   |
|                                                                                                  |
|  Incoming Traffic ──> [ NGINX EDGE WAF & PROXY ] ──> [ HAPROXY INGRESS LOAD BALANCER ]           |
|                       • TLS 1.3 (ECDHE-ECDSA)        • Round-Robin Active-Active LB              |
|                       • HSTS (max-age=31536000)      • Dynamic HTTP & WebSocket Routing          |
|                       • Leaky Bucket Rate Limiter    • Passive TCP Health Probes (10s interval)  |
|                       • HTTP/2 Protocol Multiplex    • Zero-Downtime Socket Handoff              |
+--------------------------------------------------------------------------------------------------+
```

1. **Edge Reverse Proxy & Web Application Firewall (WAF):** Nginx 1.26.
   - **TLS Profile:** Strict TLS 1.3 only; ECDHE-ECDSA-AES256-GCM-SHA384 and ChaCha20-Poly1305 ciphers; automated Let's Encrypt / ACME certificate renewal.
   - **Security Headers:** Enforced `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy: default-src 'self'`.
   - **Rate Limiting Policies:** Leaky-bucket algorithms segmented by source zone:
     - Public Guest Booking & QR APIs: 30 requests/minute per IP (Burst: 10).
     - Authenticated POS & Front Desk LAN: 120 requests/minute per Terminal (Burst: 30).
     - Offline Batch Sync Endpoint: 20 requests/minute per Terminal (Burst: 5).
2. **Ingress Load Balancer:** HAProxy 3.0.
   - **Balancing Algorithm:** Round-robin with sticky session cookies for persistent WebSocket KDS streams (`SERVERID` insertion).
   - **Health Probing:** HTTP active health checks against `/health/ready` at 10-second intervals; 2 consecutive failures mark compute node as DOWN; 3 successful probes restore UP state.
   - **Socket Connection Limit:** Hard limit of 100 concurrent frontend connections per boutique tenant stack.

---

### 3.3 Tier 3: Stateless Compute Execution Plane (Dual-AZ)

1. **Runtime Framework:** Python 3.12 runtime running modular Django 5.1 / FastAPI core inside hardened OCI Docker containers.
2. **Compute Sizing per Tenant:**
   - **Total Compute Allocation:** 0.50 vCPU, 1.0 GB RAM.
   - **Instance 1 (AZ-A / Fault Domain 1):** 0.25 vCPU, 512 MB RAM (Gunicorn with 2 sync worker processes).
   - **Instance 2 (AZ-B / Fault Domain 2):** 0.25 vCPU, 512 MB RAM (Gunicorn with 2 sync worker processes).
   - **Asynchronous Background Pool:** Celery 5.4 worker task running concurrently on shared instance resources.
3. **Application Thread & Concurrency Math:**
   - Per-worker request capacity: $C_{worker} = \frac{1}{T_{req}} \times \eta = \frac{1}{0.045\text{ s}} \times 0.80 \approx 17.78\text{ RPS}$.
   - Aggregate compute capacity (4 active Gunicorn workers across Dual AZs):
     $$\text{Capacity}_{total} = 4 \times 17.78\text{ RPS} = 71.12\text{ RPS}$$
   - Peak property demand ceiling is $2.50\text{ RPS}$ ($10.00\text{ RPS}$ during batch replay), ensuring $>700\%$ compute headroom.

---

### 3.4 Tier 4: Ephemeral State & In-Memory Event Bus

```
+--------------------------------------------------------------------------------------------------+
|                                    REDIS 7 IN-MEMORY DATA ENGINE                                 |
|                                                                                                  |
|  +--------------------------------+  +--------------------------------+  +--------------------+  |
|  |     DISTRIBUTED LOCK MANAGER   |  |     SEARCH & SLICE CACHE       |  |  IDEMPOTENCY STORE |  |
|  | Key: `pms:lock:room:{room_id}` |  | Key: `pms:avail:slice:{date}`  |  | Key: `idemp:{hash}`|  |
|  | TTL: 120s | Redlock Protocol   |  | TTL: 60s | Volatile LRU Eviction|  | TTL: 86400s (24h)  |  |
|  +--------------------------------+  +--------------------------------+  +--------------------+  |
|                                  |                                       |                       |
|                                  v                                       v                       |
|  +--------------------------------------------------------------------------------------------+  |
|  |                           TRANSACTIONAL OUTBOX EVENT STREAM (STREAM)                       |  |
|  | Stream: `events:outbox` | Group: `celery_outbox_workers` | XACK Acknowledgement Pipeline   |  |
|  +--------------------------------------------------------------------------------------------+  |
+--------------------------------------------------------------------------------------------------+
```

1. **Engine:** Redis 7.2 Alpine In-Memory Key-Value Store.
2. **Resource Allocation:** 512 MB RAM, maximum 10,000 keys, AOF (Append-Only File) write policy with `everysec` synchronization.
3. **Primary Logical Data Structures:**
   - **Distributed Concurrency Locks:** String keys with NX/PX flags (`SET pms:lock:room:101 <uuid> NX PX 120000`) preventing double-allocation of rooms during booking checkout.
   - **Room Availability Slices:** Compressed bitfields and sorted sets (`pms:avail:slice:2026-08`) providing sub-millisecond calendar availability searches.
   - **Idempotency Replay Buffers:** Set of transaction hashes (`pos:sync:dedup:<terminal_id>`) with 24-hour TTL preventing duplicate offline receipt processing.
   - **Transactional Outbox Event Bus:** Redis Streams (`events:outbox`) providing guaranteed at-least-once delivery to Celery consumers with consumer groups and `XACK` confirmation.

---

### 3.5 Tier 5: Persistence & Connection Multiplexing Plane

```
+--------------------------------------------------------------------------------------------------+
|                                RELATIONAL PERSISTENCE & POOLING                                  |
|                                                                                                  |
|  [ 4 Compute Workers ] ──(30 Client Sockets)──> [ PGBOUNCER (TRANSACTION POOLING) ]              |
|                                                             │                                    |
|                                                   (5-10 Dedicated Sockets)                       |
|                                                             ▼                                    |
|                                                 [ POSTGRESQL 17 PRIMARY ]                        |
|                                                 • Schema-per-Tenant (`tenant_boutique_01`)       |
|                                                 • Double-Entry Append-Only GL                    |
|                                                 • Effective-Dated Multi-Tax Engine               |
|                                                 • Continuous WAL Archival Stream                 |
+--------------------------------------------------------------------------------------------------+
```

1. **Connection Pooler (PgBouncer 1.23):**
   - **Pooling Mode:** `transaction` mode (client socket released back to pool immediately upon `COMMIT`/`ROLLBACK`).
   - **Client Sockets Allocated:** Up to 30 concurrent application connections.
   - **Server Sockets to DB Engine:** Multiplexed down to 5–10 active PostgreSQL backend connections.
   - **Pool Overhead:** $<2\text{ ms}$ connection acquisition latency; prevents PostgreSQL process fork exhaustion.
2. **Relational Database Engine (PostgreSQL 17):**
   - **Resource Sizing:** 0.50 vCPU, 2.0 GB RAM, 20 GB NVMe SSD Storage.
   - **Isolation Boundary:** Schema-per-tenant (`tenant_<uuid>`) within dedicated PostgreSQL cluster instance.
   - **Storage Engine Tuning:** `shared_buffers = 512MB`, `effective_cache_size = 1536MB`, `work_mem = 16MB`, `wal_level = replica`, `archive_mode = on`.
   - **Append-Only Immutability Enforcements:** Database triggers and user permissions revoke `UPDATE` and `DELETE` privileges on table `general_ledger_entries`. All correcting adjustments require reversing journal entries.

---

### 3.6 Tier 6: Durable Object Vault & Compliance Plane

1. **Storage Technology:** Ceph Object Gateway / S3-Compatible Object Store.
2. **Retention Policies:**
   - **Guest Folios & Invoices:** PDF/A-3 compliant documents stored with Object Lock WORM (Write Once, Read Many) in compliance mode for 7 years (2,555 days).
   - **Fiscal Audit Export Logs:** Cryptographically signed daily JSON exports with 7-year immutable retention.
   - **Database WAL Segments:** Continuous WAL stream shipping enabling Point-in-Time Recovery (PITR) to any second within the past 35 days.

---

### 3.7 Tier 7: Observability & Telemetry Plane

1. **Metrics Aggregation:** Prometheus 2.53 scraping internal endpoints every 15 seconds:
   - Application Runtime: `/metrics` (Django Prometheus Exporter: HTTP request duration histograms, status codes).
   - Database Pool: PgBouncer Prometheus Exporter (Active pool sockets, queued client sockets, transaction rate).
   - PostgreSQL Engine: `postgres_exporter` (Deadlocks, cache hit ratio $>99\%$, active queries, WAL generation rate).
   - In-Memory Cache: `redis_exporter` (Memory fragmentation ratio, evicted keys, connected clients).
2. **Operational Dashboards & Alerts:** Grafana 11.1 visualizing SLO compliance, P50/P95/P99 latency boundaries, and triggering automated alert notifications upon P95 latency $>120\text{ ms}$ or DB connection saturation $>80\%$.

---

## 4. Interface Protocols & Communication Matrix

The following matrix formally specifies every network boundary, protocol, security standard, and timeout cascade across the architecture:

| Source Component | Target Component | Transport Protocol | Security Standard | Payload Schema / Data Bounds | Target Timeout ($T_{max}$) | Retry / Circuit Breaker Policy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Public Browser / Mobile** | Nginx Edge WAF | HTTPS (HTTP/2) | TLS 1.3 / HSTS | JSON / HTML ($<500\text{ KB}$) | 5,000 ms | Client Retry (Max 3, Backoff) |
| **POS Terminal (Online)** | Nginx Edge WAF | HTTPS (HTTP/2) | TLS 1.3 / Bearer JWT | JSON Check Payload ($<50\text{ KB}$) | 2,500 ms | Fallback to Local SQLite ($<15\text{ ms}$) |
| **POS Terminal (Sync Replay)** | Nginx Edge WAF | HTTPS (HTTP/2) | TLS 1.3 / Bearer JWT | Batch Receipts Array ($<2\text{ MB}$) | 10,000 ms | Exp. Backoff Jitter ($1\text{s} \to 60\text{s}$) |
| **Nginx Edge WAF** | HAProxy Ingress | HTTP / TCP | Private Subnet | Proxy Protocol v2 / Stream | 3,000 ms | Failover to Alternate AZ (10s) |
| **HAProxy Ingress** | Compute Nodes | HTTP/1.1 | Private Subnet | WSGI / ASGI Request Stream | 2,500 ms | Round-Robin Alternate Node |
| **Compute Node 1** | KDS Display Screen | WebSocket (WSS) | TLS 1.3 / JWT Auth | JSON Ticket Dispatch ($<10\text{ KB}$) | **250 ms (SLA)** | Auto-Reconnect with Local Queue |
| **Compute Nodes** | Redis Event Bus | RESP3 | Pre-Shared Key (Auth) | Key-Value / Streams ($<100\text{ KB}$) | 500 ms | Local Memory Buffer / Warning Log |
| **Celery Worker** | Redis Event Bus | RESP3 | Pre-Shared Key (Auth) | CloudEvents 1.0 JSON | 1,000 ms | `XACK` Retry with Dead-Letter Queue |
| **Compute Nodes** | PgBouncer | PostgreSQL Wire (TCP) | MD5 / SCRAM-SHA-256 | SQL Statements / Transactions | 1,500 ms | Pool Queue Timeout (1,000 ms) |
| **PgBouncer** | PostgreSQL Primary | PostgreSQL Wire (TCP) | UNIX Socket / TLS | Binary Protocol Flow | 10,000 ms | Transaction Cancel / Rollback |
| **Compute Nodes** | Ceph Object Vault | S3 REST (HTTPS) | SigV4 / IAM Token | PDF/A Binary / WAL ($<5\text{ MB}$) | 5,000 ms | Celery Async Retry (5 Attempts) |
| **Prometheus Server** | All Nodes | HTTP GET | Private Subnet / Token | Prometheus Text Exposition Format | 2,000 ms | Drop Sample on Scrape Timeout |

---

## 5. End-to-End Operational Data Flows

### 5.1 Synchronous Flow: Real-Time POS Dining Order & Room Folio Charge

This flow models a dining check payment posted directly to a resident hotel guest's room folio:

```
+==================================================================================================================+
|                        SYNCHRONOUS FLOW: POS DINING CHECK POSTED TO HOTEL ROOM FOLIO                             |
+==================================================================================================================+
|                                                                                                                  |
|  [ POS Terminal ] ──(1) POST /api/v1/pos/checks/settle-to-room ─────────────────────────────> [ Nginx Edge WAF ]  |
|                                                                                                      │           |
|                                                                                      (2) TLS Term    │           |
|                                                                                          & Rate Check▼           |
|  [ Compute Instance 1 ] <──(4) Dynamic HTTP Request ───────────────────────────────── [ HAProxy Load Balancer ]  |
|         │                                                                                                        |
|         ├─(5) Validate JWT & Check State                                                                         |
|         ├─(6) SET pms:lock:folio:{folio_id} NX PX 5000 ─────────────> [ Redis In-Memory Engine ]                 |
|         │     (Acquire Distributed Concurrency Lock)                                                             |
|         │                                                                                                        |
|         ├─(7) BEGIN SQL Transaction ────────────────────────────────> [ PgBouncer ] ──> [ PostgreSQL Primary ]    |
|         │     • Verify Room Folio Status (OPEN / ACTIVE)                                                         |
|         │     • INSERT INTO folio_charges (room_id, pos_check_id, amount, tax_breakdown)                         |
|         │     • UPDATE pos_checks SET status = 'SETTLED_ROOM'                                                    |
|         │     • INSERT INTO outbox_events (event_type = 'pos.meal_sold', payload = {...})                        |
|         │     COMMIT;                                                                                            |
|         │                                                                                                        |
|         ├─(8) DEL pms:lock:folio:{folio_id} ────────────────────────> [ Redis In-Memory Engine ]                 |
|         │                                                                                                        |
|         ├─(9) WebSocket Push: Fire Kitchen Course (<250ms) ─────────> [ Kitchen KDS Screen ]                     |
|         │                                                                                                        |
|         └─(10) HTTP 200 OK (Folio Balance Updated & Receipt JSON) ──> [ POS Terminal ]                           |
|                                                                              │                                   |
|                                                                              └─(11) Native ESC/POS Print Receipt |
+==================================================================================================================+
```

1. **Step 1:** Floor server selects "Room Charge" for Table 4 on POS Terminal. Terminal issues HTTPS `POST /api/v1/pos/checks/settle-to-room` with payload: `{ "check_id": "chk_8812", "room_number": "104", "guest_name": "Smith", "total": 84.50 }`.
2. **Step 2–3:** Nginx terminates TLS 1.3, verifies rate-limiting budget ($<120\text{ req/min}$), and forwards request to HAProxy.
3. **Step 4:** HAProxy routes the request over the private subnet to `Compute Instance 1` in AZ-A.
4. **Step 5–6:** Compute runtime validates JWT claims (`pos_write` permission). It requests a 5-second distributed lock from Redis (`SET pms:lock:folio:104 <uuid> NX PX 5000`) to guarantee no concurrent check-out or charge operations can collide.
5. **Step 7:** Compute opens an ACID transaction through PgBouncer into PostgreSQL:
   - Validates that Room 104 is currently checked in to guest "Smith".
   - Inserts the line-item charge into `folio_charges` with calculated effective tax breakdown (Food @ 8%, Beverage @ 20%).
   - Marks `pos_checks` row as `SETTLED_ROOM`.
   - **Atomically inserts** a CloudEvents 1.0 event record into table `outbox_events` in the same database commit.
   - Executes `COMMIT;`.
6. **Step 8:** Distributed lock on Redis is released.
7. **Step 9:** Order course tickets are pushed over active WebSocket channel to the Kitchen KDS screen within $<250\text{ ms}$.
8. **Step 10–11:** HTTP 200 OK response returns to POS Terminal; Rust bridge sends bytecode pulse to thermal receipt printer.

---

### 5.2 Asynchronous Flow: Transactional Outbox -> Celery -> BOM & Append-Only GL

```
+==================================================================================================================+
|                     ASYNCHRONOUS FLOW: BILL-OF-MATERIALS EXPLOSION & APPEND-ONLY GL JOURNAL                      |
+==================================================================================================================+
|                                                                                                                  |
|  [ PostgreSQL `outbox_events` ] <── (Polled / Stream Pushed) ── [ Outbox Producer Service ]                      |
|                                                                            │                                     |
|                                                     (1) XADD events:outbox │                                     |
|                                                                            v                                     |
|                                                            [ Redis Stream Engine ]                               |
|                                                                            │                                     |
|                                             (2) Stream Read via Group XREAD▼                                     |
|                                                            [ Celery Async Worker ]                               |
|                                                                            │                                     |
|         +──────────────────────────────────────────────────────────────────┴───────────────────+                 |
|         │                                                                                      │                 |
|         v (3) Sub-Task 1: Recipe BOM Explosion                                                 v (4) Sub-Task 2: |
|  [ Recipe Engine ]                                                                      [ General Ledger Engine ]|
|  • Parse items: 2x "Prime Ribeye Steak"                                                 • Enforce Double-Entry   |
|  • Load BOM: 2x 350g Beef Ribeye, 2x 50g Garlic Butter                                  • Debit: Room Folio Rec. |
|  • Decrement `kitchen_inventory_stock` rows                                             • Credit: Food Rev (F&B) |
|  • If stock < reorder_threshold ──> Emit Alert                                          • Credit: Sales Tax Liab |
|         │                                                                                      │                 |
|         +─────────────────────────────────┬────────────────────────────────────────────────────+                 |
|                                           │ (5) Single Atomic DB Commit                                          |
|                                           v                                                                      |
|                                  [ PgBouncer / PostgreSQL ]                                                      |
|                                  • INSERT INTO gl_journal_entries                                                |
|                                  • INSERT INTO inventory_transactions                                            |
|                                  • UPDATE outbox_events SET processed_at = NOW()                                 |
+==================================================================================================================+
```

1. **Step 1:** The Outbox Producer reads new records from PostgreSQL `outbox_events` and streams them into Redis stream `events:outbox`.
2. **Step 2:** Celery worker daemon pulls the `pos.meal_sold` event.
3. **Step 3 (BOM Explosion):**
   - The inventory worker decodes items sold (e.g., 2x "Prime Ribeye Steak").
   - Resolves recipe sub-components: $2 \times 350\text{g} = 700\text{g}$ Beef Ribeye, $2 \times 50\text{g} = 100\text{g}$ Garlic Compound Butter.
   - Decrements stock balances in `inventory_stock` and records unit cost basis.
4. **Step 4 (General Ledger Balancing):**
   - General Ledger engine constructs balanced double-entry accounting lines:
     $$\text{Debit (Asset: Accounts Receivable Folio 104)} = \$84.50$$
     $$\text{Credit (Revenue: F&B Dining Sales)} = \$72.00$$
     $$\text{Credit (Liability: Effective Sales Tax Payable)} = \$12.50$$
     $$\sum \text{Debits} - \sum \text{Credits} = \$84.50 - \$84.50 = \$0.00\text{ (Balanced)}$$
5. **Step 5:** Writes are committed to PostgreSQL as immutable append-only journal entries.

---

### 5.3 Offline-First Resiliency Flow: 72-Hour WAN Disconnect & Replay

```
+==================================================================================================================+
|                           LOCAL-FIRST OFFLINE CONTINUITY & BATCH RECONCILIATION FLOW                             |
+==================================================================================================================+
|                                                                                                                  |
|  [ WAN SEVERED / ISP OUTAGE ]                                                                                    |
|         │                                                                                                        |
|         ├─(1) Network Probe Fails ──> POS Terminal Switches to Offline Autonomous Mode                           |
|         │                                                                                                        |
|         ├─(2) Server enters Order ──> Validated against Embedded SQLite Menu & Price Catalog                    |
|         │                                                                                                        |
|         ├─(3) Settlement Complete ──> Written to Local SQLite `offline_receipt_events` (Status: PENDING)         |
|         │                                                                                                        |
|         ├─(4) Native Rust Bridge  ──> Fires Local ESC/POS Thermal Printer (Cash Drawer Kicks)                   |
|         │                             (Service continues uninterrupted for up to 72 continuous hours)            |
|         │                                                                                                        |
|  [ WAN RESTORED / LINK REESTABLISHED ]                                                                           |
|         │                                                                                                        |
|         ├─(5) Heartbeat Probe Succeeds ──> Sync Replay Engine Awakens                                            |
|         │                                                                                                        |
|         ├─(6) Packets Chunked into Batches (25 Receipts / Payload with SHA-256 Hashes)                           |
|         │                                                                                                        |
|         ├─(7) POST /api/v1/pos/sync/batch (Bearer JWT + Idempotency Keys `idemp_chk_9901`) ──> [ Nginx / Cloud ] |
|         │                                                                                                        |
|         ├─(8) Cloud Deduplication Layer: Check Redis `pos:sync:dedup`                                            |
|         │     • If hash exists ──> Skip duplicate                                                                |
|         │     • If hash new ──> Ingest, write to PostgreSQL, and insert into Outbox Stream                        |
|         │                                                                                                        |
|         └─(9) Cloud returns HTTP 200 (Ingested IDs) ──> Local SQLite marks records `SYNCED`                      |
+==================================================================================================================+
```

---

### 5.4 Real-Time Kitchen Display Flow: Sub-250ms Order Dispatch

```
+==================================================================================================================+
|                                REAL-TIME KITCHEN DISPLAY SYSTEM (KDS) DISPATCH                                   |
+==================================================================================================================+
|                                                                                                                  |
|  [ POS Terminal / Mobile QR ] ──(1) Create Order ──> [ Compute Plane (Instance 1) ]                              |
|                                                               │                                                  |
|                                                               ├─(2) Publish `kds:station:hot_line`               |
|                                                               │     to Redis Pub/Sub                             |
|                                                               v                                                  |
|                                                    [ Redis Pub/Sub Layer ]                                       |
|                                                               │                                                  |
|                                                               └─(3) Push Event to Active WebSocket Session       |
|                                                                     │                                            |
|                                                                     v (Sub-250ms Total Transit)                  |
|                                                    [ Kitchen KDS Display Screen ]                                |
|                                                    • Render Digital Ticket Tile                                  |
|                                                    • Audio Beep Alert                                            |
|                                                    • Start Course Preparation Timer                              |
+==================================================================================================================+
```

---

## 6. Security, Multi-Tenancy & Trust Boundaries

```
+==================================================================================================================+
|                                      SECURITY & ZERO-TRUST BOUNDARIES                                            |
+==================================================================================================================+
|                                                                                                                  |
|  [ UNTRUSTED PUBLIC ZONE ]        [ PERIMETER SECURITY ZONE ]          [ SECURE CLOUD VPC PRIVATE SUBNET ]       |
|  • Public Internet Guests         • Nginx Edge WAF                     • Docker Modular Monolith Containers      |
|  • On-Premise POS LAN Hardware    • TLS 1.3 / HSTS Enforcer            • Redis In-Memory Cluster                 |
|  • OTA Webhook Callers            • Leaky-Bucket Rate Limiters         • PgBouncer Connection Multiplexer        |
|                                   • CORS Whitelist Filter              • PostgreSQL Dedicated Database           |
|                                                                        • Ceph Encrypted WORM Storage             |
|                                                                                                                  |
|  ───────────────────────────────> ───────────────────────────────────> ────────────────────────────────────────  |
|         WAN Boundary                     Perimeter Filter                    Strict Zero-Trust Subnet            |
|         (Public IPs)                     (Mutual Authentication)             (No Direct External Routing)        |
+==================================================================================================================+
```

### 6.1 Perimeter Defense & WAF Rules
1. **IP Allowlisting & Geo-Fencing:** Management endpoints (`/admin/*`, `/system/*`) are strictly restricted to verified property static IP ranges and administrative VPN CIDRs.
2. **Payload Inspection:** Nginx WAF validates maximum HTTP body size ($<5\text{ MB}$ for document upload, $<100\text{ KB}$ for standard API calls), rejecting SQL injection patterns, cross-site scripting (XSS) vectors, and malformed JSON before hitting application workers.

### 6.2 Authentication & Token Revocation Lifecycle
1. **Stateless JWT Specification:**
   - **Algorithm:** RS256 (Asymmetric RSA-SHA256 signature verification).
   - **Claims:** `{ "sub": "usr_9912", "tenant_id": "tenant_boutique_01", "role": "MANAGER", "modules": ["pms", "pos", "kds", "gl"], "exp": 1755860400 }`.
   - **Lifespan:** Short-lived access tokens (15-minute expiration) paired with cryptographically secured HTTP-only refresh tokens (7-day sliding window).
2. **Immediate Token Revocation Mechanism:**
   - When a staff member is terminated or a POS terminal is decommissioned, an invalidation event writes the user/device ID to Redis key `auth:revoked:<id>` with TTL matching token expiration.
   - Compute workers check Redis revocation cache on sensitive operations (refunds, audit close, manager overrides) with $<1\text{ ms}$ overhead.

### 6.3 Data Multi-Tenancy Isolation
1. **Siloed Multi-Instance Architecture:** Each hospitality enterprise or property operates on a dedicated PostgreSQL schema and isolated compute sandbox.
2. **Strict AI & Developer Guardrails:**
   - Zero Cross-Tenant SQL Queries: Application middleware dynamically enforces `SET search_path TO tenant_<id>` on every acquired database connection.
   - Zero Cross-Module Direct Database Joins: Modules (PMS, POS, Inventory) never execute SQL `JOIN` statements across domain boundaries; all cross-domain interaction occurs via CloudEvents 1.0 JSON payloads.

---

## 7. High Availability, Fault Recovery & Disaster Recovery

```
+==================================================================================================================+
|                                    HIGH AVAILABILITY & DISASTER RECOVERY MATRIX                                  |
+==================================================================================================================+
|                                                                                                                  |
|  [ RECOVERY METRIC ]                 [ TARGET SLA ]             [ ENFORCEMENT MECHANISM ]                        |
|  • Recovery Point Objective (RPO)    RPO < 1 Second             Continuous PostgreSQL WAL Archive Shipping       |
|  • Recovery Time Objective (RTO)     RTO < 60 Seconds           Automated Container & Database Standby Failover  |
|  • High Availability (Uptime)        99.9% Uptime               Multi-AZ Stateless Compute & Health Probing      |
|  • Compliance Data Retention         7 Years (2,555 Days)       Ceph Object Lock WORM Protection                 |
+==================================================================================================================+
```

### 7.1 Multi-AZ Failover Topologies
1. **Stateless Compute Auto-Healing:**
   - HAProxy continuously polls compute instances across Availability Zone A and Availability Zone B every 10 seconds.
   - If an application container fails (OOM, unhandled exception), HAProxy instantly drops the failed instance and routes 100% of ingress traffic to the healthy peer in the alternate AZ within $<10\text{ seconds}$.
   - Container orchestration engine spawns a replacement container within 30 seconds.
2. **Database Standby Failover:**
   - PostgreSQL synchronous standby replica deployed across secondary AZ.
   - In the event of primary hardware failure, automated health daemon promotes standby to primary with zero data loss ($\text{RPO} = 0$) and service restoration within $<60\text{ seconds}$ ($\text{RTO} < 60\text{s}$).

### 7.2 Backup, PITR & Disaster Recovery Procedures
1. **Point-In-Time Recovery (PITR):**
   - Base database snapshots captured daily at 03:00 local property time during Night Audit.
   - Continuous Write-Ahead Log (WAL) archiving pushes WAL files to the Immutable Object Vault every 60 seconds.
   - Enables restoration to any precise microsecond timestamp over the preceding 35 days.
2. **Disaster Recovery Testing:** Automated weekly recovery drill spins up an ephemeral PostgreSQL instance, applies the latest base snapshot, replays WAL segments, and verifies database checksum integrity.

---

## 8. Telemetry, Observability & SLO Enforcement

```
+==================================================================================================================+
|                                      OBSERVABILITY & MONITORING ARCHITECTURE                                     |
+==================================================================================================================+
|                                                                                                                  |
|  [ TELEMETRY SOURCES ]                [ PROMETHEUS SCRAPER ]                   [ GRAFANA VISUALIZATION ]         |
|  • App Compute Tasks (/metrics) ──>   • Scrape Interval: 15s             ──>   • Executive SLA/SLO Dashboards    |
|  • PgBouncer Connection Pool    ──>   • Alertmanager Rules Evaluation    ──>   • Real-Time Revenue Telemetry     |
|  • PostgreSQL Exporter          ──>   • Time-Series Retention: 90 Days   ──>   • Automated Pager Alerts          |
|  • Redis Info Stats             ──>                                                                              |
+==================================================================================================================+
```

### 8.1 Key Performance Indicator (KPI) & SLO Matrix

| Metric Category | Target SLO Benchmark | Warning Threshold (Paging Alert) | Critical Breach Threshold | Automated Remediation Action |
| :--- | :--- | :--- | :--- | :--- |
| **API Latency ($p_{50}$)** | $\le 45\text{ ms}$ | $>75\text{ ms}$ for 3 consecutive min | $>150\text{ ms}$ | Compute task auto-scale trigger |
| **API Latency ($p_{95}$)** | $\le 120\text{ ms}$ | $>180\text{ ms}$ for 2 consecutive min | $>300\text{ ms}$ | Drain slow worker, spawn replacement |
| **API Latency ($p_{99}$)** | $\le 300\text{ ms}$ | $>500\text{ ms}$ | $>1,000\text{ ms}$ | Route traffic to alternate AZ |
| **KDS Order Dispatch** | $\le 250\text{ ms}$ | $>400\text{ ms}$ | $>1,000\text{ ms}$ | Reset WebSocket connection pool |
| **Database Socket Pool** | $\le 10\text{ active sockets}$ | $>20\text{ queued clients}$ | $>28\text{ allocated sockets}$ | Terminate idle connections ($>30\text{s}$) |
| **Database Cache Hit Ratio** | $\ge 99.0\%$ | $<98.0\%$ | $<95.0\%$ | Flag unindexed queries in slow log |
| **Redis RAM Utilization** | $\le 50\%\text{ (256 MB)}$ | $>70\%\text{ (358 MB)}$ | $>85\%\text{ (435 MB)}$ | Evict volatile expired cache keys |
| **Offline Sync Batch Duration** | $\le 5.0\text{ s per 100 chks}$ | $>10.0\text{ s}$ | $>20.0\text{ s}$ | Throttle concurrent terminal syncs |

### 8.2 Grafana Operational Dashboards
1. **Executive Operational View:** Real-time property check-in velocity, active dining covers, bar order rate, gross revenue per hour, and payment settlement success rate ($>99.9\%$).
2. **Infrastructure SRE View:** Multi-AZ container CPU/RAM utilization curves, PgBouncer client wait queues, PostgreSQL disk IOPS and WAL generation velocity, Redis stream consumer lag, and end-to-end network latency histograms.

---

## 9. Architectural Compliance & Sign-Off

This High-Level Architecture (HLA) Specification represents the authoritative technical foundation for the DevZen Hospitality OS. All subsequent infrastructure provisioning (Terraform / OpenTofu), backend micro-app coding (Django / FastAPI), desktop client builds (Tauri / Rust), and database migrations MUST strictly conform to the resource allocations, interface contracts, security boundaries, and local-first resiliency models set forth in this document.
