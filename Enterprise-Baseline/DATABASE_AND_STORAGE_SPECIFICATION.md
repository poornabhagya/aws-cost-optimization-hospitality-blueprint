# Database & Storage Architecture Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Production Database, Cache & Distributed Storage Infrastructure Specification
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 1.0.0 (Production Engineering Baseline)
* **Status:** Approved / Production-Ready Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Cloud Provider:** Amazon Web Services (AWS) — Primary Region: `us-east-1` (Dual-AZ: `us-east-1a`, `us-east-1b`)
* **Classification:** Highly Confidential / Enterprise Database & Persistence Baseline
* **Aligned Specifications:**
  - [`docs/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/BRD_SPECIFICATION.md) (Append-Only GL, Schema-per-Tenant, 7-Year Tax Compliance WORM)
  - [`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md) (Multi-AZ 99.9% Uptime, $p_{50} \le 12\text{ ms}$ commit latency, 30 DB Sockets Hard Cap, PITR $\le 1.0\text{s}$ RPO)
  - [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md) (0.50 vCPU / 2GB RAM / 20GB gp3 SSD PostgreSQL, 512MB Redis Memory Map, 2.82GB 3-Yr Data Growth)
  - [`docs/ADR_COLLECTION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/ADR_COLLECTION.md) (ADR-003 S3+CloudFront OAC, ADR-004 RDS+PgBouncer, ADR-005 ElastiCache Redis, ADR-006 S3 WORM Vault, ADR-008 KMS Encryption)
  - [`docs/NETWORK_AND_SECURITY_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NETWORK_AND_SECURITY_SPECIFICATION.md) (Isolated DB Subnets `subnet-iso-db-a` & `subnet-iso-db-b`, `sg-rds-postgres`, `sg-redis-cache`)

---

## 1. Executive Summary & Persistence Philosophy

Hospitality OS enforces a **Multi-Tier Persistence Architecture** designed around strict ACID transactional guarantees, zero cross-domain state corruption, sub-second disaster recovery, and regulatory non-repudiation.

The persistence fabric comprises three distinct operational storage planes:
1. **Relational ACID Persistence Plane (PostgreSQL 17 + PgBouncer):** Schema-per-tenant transactional persistence housing hotel reservations, table dining orders, recipe BOM depletions, effective-dated tax engines, and double-entry append-only general ledgers. Governed by a strict **30-client socket hard cap** multiplexed via PgBouncer.
2. **In-Memory Ephemeral State Plane (ElastiCache Redis 7.2):** Ultra-low latency ($< 1\text{ ms}$) key-value store managing distributed reservation locks, idempotency replay de-duplication, search availability caching, and Celery outbox task queues with Append-Only File (AOF) persistence.
3. **Durable Object & Compliance Vault Plane (AWS S3 & CloudFront):** Multi-bucket storage tiered by access characteristics: CloudFront edge-cached public web assets, continuous PostgreSQL WAL streaming archives, and SEC 17a-4 / European VAT compliant **7-Year WORM (Write-Once-Read-Many)** immutable invoice vaults.

```
+==================================================================================================================+
|                                    HOSPITALITY OS MULTI-TIER PERSISTENCE TOPOLOGY                                |
+==================================================================================================================+
|                                                                                                                  |
|  [ STATELESS COMPUTE PLANE ] (ECS Fargate Tasks across Dual-AZ: us-east-1a / us-east-1b)                         |
|    • 2x Application Web Workers (Django / Gunicorn)                                                              |
|    • 2x Asynchronous Celery Workers (Outbox Event Stream Consumers)                                              |
|                                                                                                                  |
|        |                                           |                                       |                     |
|        | TCP 6379 (TLS)                            | TCP 5432 (PgBouncer Unix/TCP)         | HTTPS (SigV4)       |
|        v                                           v                                       v                     |
|  +----------------------------+          +-----------------------------+       +-------------------------+       |
|  | AWS ELASTICACHE REDIS 7.2  |          | PGBOUNCER CONNECTION POOL   |       | AWS S3 & CLOUDFRONT     |       |
|  | (cache.t4g.micro / 512 MB) |          | Transaction Pooling Mode    |       |                         |       |
|  | • Distributed Locks (10s)  |          | (30 Sockets -> 5-10 DB Conn)|       | [s3-web-prod]           |       |
|  | • Idempotency Cache (72h)  |          +-----------------------------+       | • CloudFront SPA Origin |       |
|  | • Celery Task Broker       |                         |                      |                         |       |
|  | • AOF Disk Sync (everysec) |                         | TCP 5432 (SCRAM)     | [s3-financial-archive]  |       |
|  +----------------------------+                         v                      | • 7-Year WORM Lock      |       |
|                                          +-----------------------------+       | • Glacier Deep Archive  |       |
|                                          | AWS RDS POSTGRESQL 17       |       |                         |       |
|                                          | (db.t4g.micro / 20GB gp3)   |       | [s3-wal-backups]        |       |
|                                          | • Multi-AZ Active/Standby   | ----> | • Continuous WAL PITR   |       |
|                                          | • Append-Only Ledger        |       |   (RPO <= 1.0 Second)   |       |
|                                          | • KMS Envelope Encrypted    |       +-------------------------+       |
|                                          +-----------------------------+                                         |
+==================================================================================================================+
```

---

## 2. Relational Database Engine Specification (AWS RDS PostgreSQL 17 Multi-AZ)

### 2.1 Instance Sizing & Hardware Allocation
The relational database engine is tailored specifically for the single-property operational workload derived in [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md#section-4).

| Specification Attribute | Selected Engineering Baseline | Architectural Rationale & NFR Alignment |
| :--- | :--- | :--- |
| **Engine & Major Version** | **PostgreSQL 17.x (ARM64)** | Latest PostgreSQL engine with advanced query optimization, B-tree deduplication, and JSONB enhancements. |
| **Instance Hardware Class** | **`db.t4g.micro`** (12-Mo Free Tier) / **`db.t4g.small`** | 2 vCPUs (Graviton2 ARM64), 1.0 GB RAM (`t4g.micro`) or 2.0 GB RAM (`t4g.small`). Optimal baseline burst performance. |
| **High Availability Topology**| **Multi-AZ Synchronous Mirroring** | Physical active-standby replication spanning `subnet-iso-db-a` (`us-east-1a`) and `subnet-iso-db-b` (`us-east-1b`) ensuring $< 60\text{s}$ automated failover. |
| **Storage Type & Allocation**| **20 GB General Purpose SSD (gp3)** | Baseline **3,000 IOPS** and **125 MB/s throughput** independent of storage volume size. Meets $p_{50} \le 12\text{ ms}$ commit latency. |
| **Storage Auto-Scaling** | **Enabled (Maximum: 100 GB)** | Automatically provisions additional block storage upon reaching $< 20\%$ free disk space, preventing write-lockouts. |
| **3-Year Data Growth Projection**| **2.82 GB Cumulative Volume** | 3-year raw relational footprint (accounting for 100 checks/day, 10 rooms, GL ledger, audit logs) consumes only **14.1% of baseline 20GB disk**. |
| **Network & Placement** | **Isolated Persistence Subnet Group** | Attached strictly to `subnet-iso-db-a` and `subnet-iso-db-b` with `PubliclyAccessible = false` and security group `sg-rds-postgres`. |

---

### 2.2 PostgreSQL 17 Parameter Group Configuration

A dedicated custom Parameter Group (`hospitality-os-pg17-custom-params`) is attached to enforce query discipline, prevent resource starvation, and optimize write-ahead logging:

| PostgreSQL Parameter | Configured Value | Default PostgreSQL Value | Engineering Justification & Impact |
| :--- | :--- | :--- | :--- |
| `max_connections` | **`25`** | `100` | Hard cap preventing memory exhaustion on `db.t4g.micro`. Multiplexed via PgBouncer. |
| `shared_buffers` | **`512MB`** (or `25%` of RAM) | `128MB` | Reserves optimal database memory cache for frequently accessed tenant schemas and index trees. |
| `work_mem` | **`16MB`** | `4MB` | Dedicated workspace per complex sort/hash join operation without spilling temporary tables to disk. |
| `maintenance_work_mem` | **`128MB`** | `64MB` | Accelerates autovacuum, index creation, and schema migration processing speed. |
| `effective_cache_size` | **`1536MB`** (or `75%` of RAM) | `4096MB` | Informs query planner of available OS buffer cache to encourage efficient index scans. |
| `wal_level` | **`replica`** | `replica` | Enables continuous WAL streaming to S3 for Point-in-Time Recovery (PITR). |
| `checkpoint_completion_target`| **`0.9`** | `0.5` | Smooths out disk I/O spikes by spreading dirty page writes across the entire checkpoint interval. |
| `statement_timeout` | **`5000ms`** (5.0 Seconds) | `0` (Disabled) | Kills runaway SQL queries before exceeding ALB/Gunicorn timeout thresholds. |
| `idle_in_transaction_session_timeout`| **`10000ms`** (10.0 Seconds)| `0` (Disabled) | Automatically terminates orphaned open transactions holding locks, preventing table deadlock. |
| `password_encryption` | **`scram-sha-256`** | `scram-sha-256` | Enforces cryptographic authentication preventing plaintext or MD5 credential interception. |
| `rds.force_ssl` | **`1`** (Enabled) | `0` | Rejects unencrypted plaintext client connections; enforces TLS 1.3 / 1.2 in-transit. |

---

## 3. Connection Multiplexing Plane (PgBouncer Sidecar Architecture)

### 3.1 Mathematical Derivation of Connection Pooling
PostgreSQL follows a process-per-connection architecture where each active client connection allocates approximately **5 MB to 10 MB of dedicated server RAM** and incurs CPU context-switching overhead.

Given the concurrency profile from [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md#section-1):
- Total client connections across 2 web workers, 2 Celery workers, POS desktop terminals, and management consoles: **30 client sockets**.
- Direct connection from all clients would consume: $30 \times 10\text{ MB} = 300\text{ MB RAM}$ ($\approx 30\%$ of total RAM on `db.t4g.micro`).

$$\text{Multiplexing Efficiency: } \eta_{pool} = \frac{\text{Client Sockets}}{\text{Backend DB Connections}} = \frac{30}{5} = 6.0\text{x Reduction}$$

PgBouncer operates in **Transaction Pooling Mode**, holding physical database connections only during active SQL transaction execution and returning them immediately to the pool upon `COMMIT` or `ROLLBACK`.

```
+----------------------------------------------------------------------------------------------------+
|                                    PGBOUNCER MULTIPLEXING CASCADE                                  |
|                                                                                                    |
|  [ 30 Client Frontend Sockets ]                                                                    |
|    • 2x Gunicorn Web Workers (8 async greenlets each = 16 connections)                             |
|    • 2x Celery Outbox Event Workers (4 worker processes = 8 connections)                           |
|    • 6x Back-office & Management Sessions (6 connections)                                          |
|                                                                                                    |
|                                    |                                                               |
|                                    v                                                               |
|  +----------------------------------------------------------------------------------------------+  |
|  | PGBOUNCER INSTANCE (Transaction Pooling Mode)                                                |  |
|  | - Listens on: TCP 5432 / Unix Domain Socket                                                  |  |
|  | - Client Socket Pool: Max 100 Client Connections                                             |  |
|  | - Server Pool Size: Default 10 Server Connections (Peak Reserve: 2)                          |  |
|  +----------------------------------------------------------------------------------------------+  |
|                                    |                                                               |
|                                    | Physical Multiplexed Sockets (5 - 10 Backend Connections)     |
|                                    v                                                               |
|  +----------------------------------------------------------------------------------------------+  |
|  | AWS RDS POSTGRESQL 17 (max_connections = 25)                                                 |  |
|  | Memory Consumption: <= 50 MB dedicated to backend connection buffers                         |  |
|  +----------------------------------------------------------------------------------------------+  |
+----------------------------------------------------------------------------------------------------+
```

---

### 3.2 Production-Ready `pgbouncer.ini` Blueprint

```ini
[databases]
hospitality_production = host=hospitality-os-pg17.cluster-c123.us-east-1.rds.amazonaws.com port=5432 dbname=hospitality_production auth_user=pgbouncer_auth

[pgbouncer]
;; Administrative & Network Settings
logfile = /var/log/pgbouncer/pgbouncer.log
pidfile = /var/run/pgbouncer/pgbouncer.pid
listen_addr = 0.0.0.0
listen_port = 5432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
auth_query = SELECT usename, passwd FROM public.pgbouncer_get_auth($1)

;; Connection Pool Sizing & Limits
pool_mode = transaction
max_client_conn = 100
default_pool_size = 10
min_pool_size = 2
reserve_pool_size = 2
reserve_pool_timeout = 5.0
max_db_connections = 20

;; Timeout Controls
server_idle_timeout = 60.0
server_connect_timeout = 15.0
server_login_retry = 1.0
client_idle_timeout = 0.0
client_login_timeout = 60.0
query_timeout = 5.0
idle_transaction_timeout = 10.0

;; Low-Level Socket Tuning
pkt_buf = 4096
listen_backlog = 128
so_reuseport = 1
tcp_keepalive = 1
tcp_keepcnt = 3
tcp_keepidle = 30
tcp_keepintvl = 10
```

### 3.3 SCRAM-SHA-256 Secret Management (`userlist.txt`)
All credentials ingested by PgBouncer are formatted using SCRAM-SHA-256 password verifiers:
```text
"hospitality_app" "SCRAM-SHA-256$4096:5bV...==$B48...="
"pgbouncer_auth" "SCRAM-SHA-256$4096:8cK...==$Z91...="
```
*Note: Injected at container runtime from AWS SSM Parameter Store (`/hospitality-os/prod/database/pgbouncer_userlist`).*

---

## 4. In-Memory Ephemeral State Plane (AWS ElastiCache for Redis 7.2)

### 4.1 Instance Allocation & Operational Role
The ephemeral state plane handles high-frequency distributed locks, idempotency caches, and Celery task broker queues.

| Attribute | Selected Specification | Functional Purpose |
| :--- | :--- | :--- |
| **Engine & Version** | **Redis 7.2 (ElastiCache Managed)** | High-throughput in-memory data structures with sub-millisecond execution. |
| **Node Class** | **`cache.t4g.micro`** (512 MB RAM, 2 vCPUs) | Sized to accommodate the 512MB RAM ephemeral budget defined in [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md). |
| **Persistence Mechanism**| **Append-Only File (AOF) Enabled** | `appendonly = yes`, `appendfsync = everysec`. Ensures disk durability for task queues. |
| **Eviction Policy** | **`volatile-lru`** | Automatically evicts least-recently-used keys with an explicit TTL if memory exceeds 80%. |
| **Network & Encryption** | **Private Subnet + In-Transit TLS** | Bound to `sg-redis-cache` (Port 6379) with Auth Token requirement and in-transit TLS. |

---

### 4.2 Key Lifecycle & Namespace Specification

To prevent key collision and ensure bounded memory consumption, all Redis keys must adhere to strict hierarchical namespaces, serialization formats, and mandatory TTLs:

| Key Namespace Pattern | Data Structure | Serialization | Configured TTL | Eviction Policy | Business Purpose & Invalidation Trigger |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pms:lock:<room_id>:<date>` | `STRING` | Plaintext Timestamp | **10 Seconds** | No Eviction | Distributed pessimistic lock preventing simultaneous double-booking of a room during reservation settlement. |
| `idemp:pos:<client_tx_uuid>` | `STRING` | SHA-256 Payload Hash | **72 Hours** (259,200s) | `volatile-lru` | Deduplication buffer for offline POS batch replays. Returns cached response if client re-transmits identical transaction. |
| `pms:avail:slice:<month_yyyymm>`| `STRING` (JSON)| Compressed JSON | **60 Seconds** | `volatile-lru` | High-frequency room calendar availability cache for public web booking engine. Invalidated on reservation create/cancel. |
| `auth:jwt:revoked:<jti_uuid>` | `STRING` | Boolean `1` | **Remaining JWT TTL** | No Eviction | Fast-lookup blacklist for revoked JWT authentication tokens. |
| `celery:queue:<queue_name>` | `LIST` / `STREAM` | Binary MessagePack | **None (Persistent)**| No Eviction | Asynchronous task queue for outbox event publishing, recipe BOM explosion, and night audit ledger balancing. |
| `rate:ip:<client_ip>:<window>` | `INTEGER` | Atomic Increment | **60 Seconds** | `volatile-lru` | Sliding window rate limiter for public booking engine (30 req/min) and POS sync (120 req/min). |

---

## 5. Distributed Object Storage, Edge Delivery & Compliance Vault (AWS S3 & CloudFront)

The storage architecture is organized into three segregated AWS S3 buckets adhering to the principle of least privilege and strict data lifecycle management:

```
+==================================================================================================================+
|                                    AWS S3 THREE-BUCKET STORAGE TOPOLOGY                                          |
+==================================================================================================================+
|                                                                                                                  |
|  [ BUCKET 1: s3-hospitality-web-prod ] (Edge Delivery Plane)                                                     |
|  • Public Web SPA, Booking Engine Bundles, Digital QR Menus, Tenant Logos                                         |
|  • Ingress: Amazon CloudFront CDN (Global Anycast Edge PoPs) via Origin Access Control (OAC)                     |
|  • Security: Block Public Access = True (100% Private Origin; Direct S3 HTTP Access Denied)                       |
|  • Lifecycle: Continuous versioning with 30-day noncurrent object cleanup                                         |
|                                                                                                                  |
|  [ BUCKET 2: s3-hospitality-financial-archive-prod ] (Durable Compliance Vault)                                 |
|  • Finalized Guest Folio Invoices (PDF/A-3), VAT Audit Reports, Daily Night Audit Ledgers                        |
|  • Compliance Engine: S3 Object Lock in COMPLIANCE Mode (7-Year / 2,555 Days Retention)                         |
|  • Immutability: WORM (Write-Once-Read-Many) enforced cryptographically; CANNOT be deleted even by AWS Root      |
|  • Lifecycle Transition: Day 1-90 (Standard S3) -> Day 91-365 (Glacier Flexible) -> Day 366+ (Glacier Deep Archive)|
|                                                                                                                  |
|  [ BUCKET 3: s3-hospitality-wal-backups-prod ] (Disaster Recovery Plane)                                         |
|  • Continuous PostgreSQL 17 WAL Streaming Archives & Daily Database Physical Snapshots                           |
|  • Point-in-Time Recovery: Enables database replay to any exact second within the last 30 days (RPO <= 1.0s)      |
|  • Lifecycle: Expire and purge WAL files older than 35 days                                                      |
+==================================================================================================================+
```

---

### 5.1 Bucket 1: `s3-hospitality-web-prod` (Frontend Web Delivery & CDN)
* **Purpose:** Serves compiled React SPAs, Vite client bundles, and guest-facing QR assets.
* **Origin Access Control (OAC) Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontServicePrincipalReadOnly",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::s3-hospitality-web-prod/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE"
        }
      }
    }
  ]
}
```

---

### 5.2 Bucket 2: `s3-hospitality-financial-archive-prod` (7-Year WORM Vault)
* **Regulatory Compliance:** SEC Rule 17a-4(f), FINRA Rule 4511, and European Fiscal VAT Directives.
* **Immutability Mode:** **`COMPLIANCE` Mode** (Retention: **2,555 Days / 7 Years**).
* **Storage Lifecycle Transition Rules:**
  - **Day 0 – 90:** S3 Standard (`$0.023/GB/mo`) — Rapid retrieval for current-quarter accountant audits.
  - **Day 91 – 365:** S3 Glacier Flexible Archive (`$0.0036/GB/mo`) — 3-5 hour retrieval window for annual tax filings.
  - **Day 366 – 2,555:** S3 Glacier Deep Archive (`$0.00099/GB/mo`) — Ultra-low-cost cold storage for 7-year regulatory holding.

```hcl
# Terraform S3 Object Lock & Lifecycle Configuration
resource "aws_s3_bucket" "financial_archive" {
  bucket        = "s3-hospitality-financial-archive-prod"
  force_destroy = false

  object_lock_enabled = true
}

resource "aws_s3_bucket_object_lock_configuration" "worm_retention" {
  bucket = aws_s3_bucket.financial_archive.id

  rule {
    default_retention {
      mode  = "COMPLIANCE"
      years = 7
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "archive_lifecycle" {
  bucket = aws_s3_bucket.financial_archive.id

  rule {
    id     = "financial-archive-tiering"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }
}
```

---

### 5.3 Bucket 3: `s3-hospitality-wal-backups-prod` (WAL & PITR Vault)
* **Purpose:** Ingests streaming Write-Ahead Logs emitted by PostgreSQL `archive_command` via `pgBackRest` / `wal-g`.
* **Lifecycle Rule:** Non-current versions and archived WAL segments purged automatically after **35 days**, matching the RDS backup retention window.

---

## 6. Cryptography & Envelope Encryption Specification

Hospitality OS enforces cryptographic encryption at rest and in transit across all storage tiers:

```
+----------------------------------------------------------------------------------------------------+
|                                    AWS KMS ENVELOPE ENCRYPTION MODEL                               |
|                                                                                                    |
|  [ AWS KMS Customer Managed Key (CMK) ] (arn:aws:kms:us-east-1:.../hospitality-storage-key)        |
|  • FIPS 140-2 Level 2 Hardware Security Module (HSM) Cryptographic Origin                          |
|  • Automatic Annual Key Rotation Enabled                                                           |
|                                                                                                    |
|        |                                           |                               |               |
|        v                                           v                               v               v
|  [ RDS PostgreSQL ]                        [ S3 Buckets (SSE-KMS) ]        [ EBS gp3 Volumes ] [ SSM Secrets ]
|  • AES-256 Tablespace                      • AES-256 S3 Object Vault       • AES-256 Storage   • SecureString
|  • In-Transit TLS 1.3                      • SigV4 Signed Payloads         • Root/Data Blocks  • JWT/Stripe Keys
+----------------------------------------------------------------------------------------------------+
```

### 6.1 Cryptographic Master Keys Matrix

| Encrypted Target Subsystem | Encryption Standard | Cryptographic Key Provider | Key Rotation Schedule | Key Access Policy |
| :--- | :--- | :--- | :--- | :--- |
| **RDS PostgreSQL 17 Storage** | `AES-256-GCM` | AWS KMS Customer Managed Key (CMK) | Automated (365 Days) | Restricted strictly to `rds.amazonaws.com` Service Principal. |
| **S3 Financial Archive Objects**| `SSE-KMS` (AWS KMS) | AWS KMS Customer Managed Key (CMK) | Automated (365 Days) | `s3:PutObject` permitted for App Role; `s3:Delete*` blocked by WORM. |
| **S3 WAL Backup Storage** | `SSE-KMS` (AWS KMS) | AWS KMS Customer Managed Key (CMK) | Automated (365 Days) | Read/Write access restricted to Database Backup IAM Role. |
| **ElastiCache Redis In-Transit**| `TLS 1.3 / 1.2` | Amazon Trust Services Public PKI | Automated (ACM 365 Days) | Enforced via Redis `AUTH` token and TLS wrapper. |
| **SSM Parameter Store Values**| `AES-256 Envelope`| AWS KMS Default SSM Key (`aws/ssm`) | Automated Managed | Decryption permitted strictly for ECS Task Execution Role. |

---

## 7. Backup Lifecycle & Disaster Recovery Runbook

### 7.1 Recovery Objectives & SLAs
In accordance with [`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md#section-3):
- **Recovery Point Objective (RPO):** $\le 1.0\text{ Second}$ (Continuous PostgreSQL WAL streaming ensures zero financial transaction loss).
- **Recovery Time Objective (RTO):** $\le 60.0\text{ Seconds}$ (Automated Multi-AZ RDS failover) / $\le 15.0\text{ Minutes}$ (Full point-in-time snapshot restoration).

### 7.2 Backup Execution Schedule

| Backup Layer | Mechanism | Schedule / Frequency | Retention Window | Storage Target | RPO Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Continuous WAL Stream** | `pgBackRest` / RDS WAL Archiver | Continuous (Every 16MB WAL segment or 60s timeout) | 35 Days | `s3-hospitality-wal-backups-prod` | $\le 1.0\text{ s}$ |
| **Daily Full RDS Snapshot**| AWS RDS Automated Backup | Daily at `02:00 UTC` (Low-traffic night window) | 30 Days | Encrypted RDS Snapshot Storage | $\le 24\text{ h}$ |
| **Weekly Deep Snapshot** | AWS Backup Service Vault | Weekly (Sunday `03:00 UTC`) | 365 Days (1 Year) | AWS Backup Vault (KMS Encrypted)| $\le 7\text{ d}$ |
| **Redis Memory Snapshot** | ElastiCache Redis Daily Snapshot | Daily at `03:30 UTC` | 7 Days | Amazon S3 Managed Storage | $\le 24\text{ h}$ |

---

### 7.3 Point-In-Time Recovery (PITR) Operational Runbook

In the event of catastrophic data corruption (e.g., erroneous batch financial script or accidental database truncation), execute the following restoration procedure:

```bash
#!/usr/bin/env bash
# ==============================================================================
# HOSPITALITY OS: DISASTER RECOVERY & POINT-IN-TIME RESTORATION RUNBOOK
# ==============================================================================
set -euo pipefail

TARGET_TIMESTAMP="2026-08-23T14:45:00.000Z"
SOURCE_DB_INSTANCE="hospitality-os-pg17-primary"
RESTORED_DB_INSTANCE="hospitality-os-pg17-restored"
SUBNET_GROUP="hospitality-db-subnet-group"
SECURITY_GROUP="sg-0a1b2c3d4e5f6g7h8" # sg-rds-postgres

echo "[1/4] Initiating RDS Point-in-Time Recovery to timestamp: ${TARGET_TIMESTAMP}..."
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier "${SOURCE_DB_INSTANCE}" \
    --target-db-instance-identifier "${RESTORED_DB_INSTANCE}" \
    --restore-time "${TARGET_TIMESTAMP}" \
    --db-subnet-group-name "${SUBNET_GROUP}" \
    --vpc-security-group-ids "${SECURITY_GROUP}" \
    --db-instance-class "db.t4g.small" \
    --no-multi-az \
    --no-publicly-accessible

echo "[2/4] Waiting for restored database instance to become available..."
aws rds wait db-instance-available --db-instance-identifier "${RESTORED_DB_INSTANCE}"

echo "[3/4] Performing automated consistency assertion on restored append-only general ledger..."
python3 /infrastructure/scripts/verify_gl_integrity.py \
    --host "$(aws rds describe-db-instances --db-instance-identifier ${RESTORED_DB_INSTANCE} --query 'DBInstances[0].Endpoint.Address' --output text)" \
    --db "hospitality_production"

echo "[4/4] Updating PgBouncer target endpoint in AWS SSM Parameter Store..."
aws ssm put-parameter \
    --name "/hospitality-os/prod/database_host" \
    --value "$(aws rds describe-db-instances --db-instance-identifier ${RESTORED_DB_INSTANCE} --query 'DBInstances[0].Endpoint.Address' --output text)" \
    --type "SecureString" \
    --overwrite

echo "[SUCCESS] Point-in-Time Recovery complete. Restarting ECS compute tasks to ingest updated endpoint."
aws ecs update-service --cluster hospitality-prod-cluster --service hospitality-web-app --force-new-deployment
```

---

## 8. Database Architecture Pre-Flight Verification Checklist

Before approving any schema migration or production deployment, the database administrator and DevOps team must verify the following automated assertions:

- [ ] **Assertion 1 (Connection Cap):** PgBouncer `max_client_conn = 100` and `default_pool_size = 10` are enforced; total backend connections to PostgreSQL do not exceed 20.
- [ ] **Assertion 2 (Parameter Verification):** `statement_timeout = 5000ms` and `idle_in_transaction_session_timeout = 10000ms` are active in PostgreSQL runtime (`SHOW statement_timeout;`).
- [ ] **Assertion 3 (Immutability Lock):** S3 bucket `s3-hospitality-financial-archive-prod` has Object Lock enabled in `COMPLIANCE` mode with 7-year default retention.
- [ ] **Assertion 4 (KMS Envelope Encryption):** RDS storage, gp3 volumes, and S3 archives return `ServerSideEncryption: aws:kms` with the designated CMK.
- [ ] **Assertion 5 (Redis AOF Enabled):** Redis parameter group reflects `appendonly = yes` and `appendfsync = everysec`.
- [ ] **Assertion 6 (PITR Backup Health):** Automated RDS snapshot status is `available` and latest WAL archive is $< 60\text{ seconds}$ old in S3.
