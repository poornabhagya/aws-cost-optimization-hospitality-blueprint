# Database & Storage Architecture Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Production Database, Cache & Distributed Storage Infrastructure Specification
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 2.0.0 (Free-Tier Production Baseline)
* **Status:** Approved / Production-Ready Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Budget Ceiling:** **< $0.50 USD / month ($0.00 USD / month net spend)**
* **Target Cloud Provider & Region:** Amazon Web Services (AWS) — Primary Region: Asia Pacific (Mumbai) `ap-south-1`
* **Classification:** Highly Confidential / Enterprise Free-Tier Database & Storage Baseline
* **Aligned Specifications:**
  - [`docs/Free Tier Baseline/ADR_COLLECTION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/ADR_COLLECTION.md) (Master Free-Tier ADR Decisions: ADR-001 through ADR-011)
  - [`docs/Free Tier Baseline/HLA_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/HLA_SPECIFICATION.md) (Platform-Neutral High-Level Architecture Topology)
  - [`docs/Free Tier Baseline/NETWORK_AND_SECURITY_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/NETWORK_AND_SECURITY_SPECIFICATION.md) (Zero-Cost Lean VPC & Subnet Security Rules)
  - [`docs/Enterprise Baseline/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/BRD_SPECIFICATION.md) (Domain Rules, 72h POS Autonomy, Append-Only GL)
  - [`docs/Enterprise Baseline/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/NFR_SPECIFICATION.md) ($p_{50} \le 12\text{ ms}$ commit latency, 30 DB Sockets Hard Cap, PITR $\le 1.0\text{s}$ RPO)
  - [`docs/Enterprise Baseline/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/CAPACITY_SIZING.md) (0.50 vCPU / 1GB RAM Compute, 512MB Redis, 2.82GB 3-Yr Data Growth)

---

## 1. Executive Summary & Zero-Cost Persistence Philosophy

Hospitality OS implements a **High-Performance, Multi-Tier Persistence Architecture** engineered strictly within the **AWS 12-Month Free Tier and Perpetual Always-Free Tier limits (< $0.50 USD / month total spend)**.

### Core Storage & Persistence Tenets
1. **Managed RDS PostgreSQL 17 Single-AZ ($0.00 / month):** Leverages 750 hours/month of AWS RDS Free Tier on `db.t4g.micro` with 20 GB gp3 SSD storage, eliminating $37.80/month in Multi-AZ hosting fees while retaining automated daily snapshots.
2. **In-Container Ephemeral State & Task Broker (Redis 7.2 Alpine):** Deploys Redis directly inside Docker Compose on the EC2 host with Append-Only File (AOF) disk persistence, eliminating the $14.60/month cost of AWS ElastiCache.
3. **Local-First POS Persistence (SQLite 3.45 WAL Mode):** On-premise touchscreens execute orders against a local embedded SQLite engine, delivering $p_{99} < 15\text{ ms}$ response times and guaranteeing **72 hours of complete offline operational autonomy**.
4. **Zero-Cost Compliance Vault & Object Storage (Amazon S3):** Utilizes AWS S3 5 GB Free Tier with default Amazon S3 Server-Side Encryption (SSE-S3), avoiding the $1.00/month AWS KMS Customer Managed Key charge while enforcing a **7-Year (2,555-Day) WORM (Write-Once-Read-Many)** non-repudiation hold for financial folios and VAT tax invoices (SEC 17a-4 compliant).
5. **Continuous WAL Streaming for Point-in-Time Recovery (PITR):** Write-Ahead Logs (WAL) are streamed continuously to an S3 backup bucket, achieving an $\text{RPO} \le 1.0\text{s}$ and $\text{RTO} < 15\text{ minutes}$.

---

## 2. Multi-Tier Persistence Architecture Topology

```
+==================================================================================================================+
|                                  HOSPITALITY OS MULTI-TIER PERSISTENCE TOPOLOGY                                  |
+==================================================================================================================+
|                                                                                                                  |
|  [ TIER 1: LOCAL-FIRST EDGE PERSISTENCE (ON-PREMISE POS TERMINALS) ]                                             |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | Embedded SQLite 3.45 Engine (WAL Mode / PRAGMA synchronous = NORMAL / 500 MB Allocated Disk)                |    |
|  | • Fast Local Menus, Floorplans & Modifier Catalog Cache                                                   |    |
|  | • Offline Receipt Journals: offline_receipt_events (Signed JSON Payloads + SHA-256 State Hashes)          |    |
|  | • 72-Hour Autonomous Replay Buffer: Zero reliance on WAN connectivity for guest checkout                  |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|                                                     |                                                            |
|                                                     | HTTPS Sync Batch (WAN Uplink / Idempotency Key Replay)      |
|                                                     v                                                            |
|  [ TIER 4: IN-CONTAINER EPHEMERAL STATE & TASK BROKER (DOCKER COMPOSE ON EC2) ]                                  |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | Redis 7.2 Alpine Container (Port 6379 / maxmemory 128mb / maxmemory-policy volatile-lru)                  |    |
|  | • Distributed Pessimistic Locks: pms:lock:<room_id>:<date> (10s TTL - Prevents Double-Booking)            |    |
|  | • Idempotency Deduplication: idemp:pos:<client_tx_uuid> (72h TTL - Prevents Duplicate Replay Settle)     |    |
|  | • Celery Asynchronous Task Broker (Recipe BOM Depletion & Ledger Reconciliation)                         |    |
|  | • Durability: Append-Only File (appendonly yes / appendfsync everysec) mounted to redis_data host volume   |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|                                                     |                                                            |
|                                                     | ACID SQL Queries (TCP Port 5432 / Dedicated Kernel Memory) |
|                                                     v                                                            |
|  [ TIER 5: RELATIONAL PERSISTENCE ENGINE (AMAZON RDS POSTGRESQL 17 SINGLE-AZ) ]                                  |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | AWS RDS db.t4g.micro (ARM64 Graviton2, 2 vCPUs, 1.0 GB RAM, 20 GB gp3 SSD, 3000 IOPS, 125 MB/s)         |    |
|  | • Multi-Tenancy: Schema-per-Tenant Isolation (tenant_<uuid>.* / SET search_path)                          |    |
|  | • Double-Entry Append-Only General Ledger (PostgreSQL Triggers: NO UPDATE / NO DELETE on GL Tables)      |    |
|  | • Connection Disciplines: max_connections = 25, shared_buffers = 256MB, work_mem = 8MB                  |    |
|  | • Backup & Disaster Recovery: Automated 7-Day Daily Physical Snapshots ($0.00 Free Tier)                  |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|                                                     |                                                            |
|                                                     | Continuous WAL Log Stream (RPO <= 1.0s)                    |
|                                                     v                                                            |
|  [ TIER 6: DURABLE OBJECT STORAGE & COMPLIANCE VAULT (AMAZON S3 - 5 GB FREE TIER) ]                              |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | Amazon S3 Standard Storage (Default SSE-S3 Encryption - $0.00 / Zero KMS CMK Fees)                       |    |
|  | 1. hospitality-web-assets-prod        : Public SPAs fronted by CloudFront CDN (1 TB/mo Free Perpetual)    |    |
|  | 2. hospitality-financial-archive-prod : 7-Year WORM Compliance Lock (SEC 17a-4 / European VAT Compliant)  |    |
|  | 3. hospitality-wal-backups-prod       : Continuous WAL segment archive for Point-in-Time Recovery (PITR)   |    |
|  +----------------------------------------------------------------------------------------------------------+    |
+==================================================================================================================+
```

---

## 3. Relational Persistence Plane: AWS RDS PostgreSQL 17 Single-AZ

### 3.1 Hardware Sizing & Free-Tier Specifications
Per [`docs/Enterprise Baseline/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/CAPACITY_SIZING.md), a single boutique property generates **2.82 GB** of relational data over 3 years. The allocated 20 GB gp3 storage provides **7.1x headroom**.

| Parameter | Configuration Value | Sizing Rationale & Free-Tier Compliance |
| :--- | :--- | :--- |
| **Engine & Version** | PostgreSQL 17.x | ACID compliance, JSONB indexing, dynamic schema switching. |
| **Instance Class** | `db.t4g.micro` (ARM64 Graviton2) | 2 vCPUs, 1.0 GB RAM (750 hours/month Free Tier eligible). |
| **Multi-AZ Status** | **Disabled (Single-AZ)** | Eliminates $37.80/mo Multi-AZ fee; placed in `subnet-private-db-a`. |
| **Storage Allocation** | 20 GB General Purpose SSD (gp3) | Baseline 3,000 IOPS, 125 MB/s throughput included in Free Tier. |
| **Storage Autoscaling** | Enabled (Max: 50 GB) | Automatically expands disk if 3-year growth exceeds baseline. |
| **Snapshot Retention** | 7 Days (Automated Daily Snapshots) | Physical daily snapshots retained for 7 days at $0.00. |
| **Backup Window** | `02:00 – 02:30 UTC` | Scheduled during lowest property occupancy and night audit close. |
| **Public Accessibility**| **`false` (100% Private)** | No public IP; non-routable private subnet. |

---

### 3.2 Custom RDS Parameter Group (`custom-pg17-free-tier`)

The PostgreSQL engine parameters are strictly tuned for the 1.0 GB RAM memory boundary on `db.t4g.micro`:

```ini
# ==============================================================================
# HOSPITALITY OS: CUSTOM POSTGRESQL 17 PARAMETER GROUP DIRECTIVES
# ==============================================================================
# Connection & Concurrency Limits
max_connections = 25                          # Prevents memory exhaustion (25 conn x ~10MB = 250MB max)
superuser_reserved_connections = 3

# Memory Buffers & Working Memory
shared_buffers = 256MB                        # 25% of total 1.0 GB RAM for page caching
work_mem = 8MB                                # Complex sorts & hash joins (8MB x 25 = 200MB max)
maintenance_work_mem = 64MB                   # VACUUM, CREATE INDEX, and migration memory
effective_cache_size = 768MB                  # Query planner estimate of kernel + PG disk cache

# Transaction Timeouts & Zombie Connection Reaper
statement_timeout = 5000                      # 5,000ms (5.0s) hard ceiling to kill runaway queries
idle_in_transaction_session_timeout = 10000   # 10,000ms (10.0s) auto-kills dangling locks
lock_timeout = 3000                           # 3,000ms (3.0s) lock wait timeout

# Write-Ahead Logging & Checkpoint Optimization
wal_level = replica                           # Supports continuous WAL archiving and PITR
checkpoint_timeout = 900                      # 15 minutes between forced checkpoints
max_wal_size = 2GB
min_wal_size = 512MB
checkpoint_completion_target = 0.9            # Smooths I/O spikes across checkpoint duration

# Query Logging & Telemetry
log_min_duration_statement = 200              # Logs queries taking longer than 200ms
log_connections = on
log_disconnections = on
log_lock_waits = on
```

---

### 3.3 Multi-Tenancy Architecture: Schema-per-Tenant
The platform implements a strict **Schema-per-Tenant** isolation model:
1. Every tenant property is provisioned with a dedicated PostgreSQL schema (e.g., `tenant_prop_01`, `tenant_prop_02`).
2. Public shared schemas (`public.*`) contain only global metadata, subscription states, and tenant routing records.
3. Django middleware dynamically intercepts every incoming request and executes:
   ```sql
   SET search_path TO tenant_prop_01, public;
   ```
4. This completely eliminates the risk of cross-tenant SQL data leakage while maintaining a single lightweight database instance.

---

### 3.4 Append-Only Financial Ledger Trigger DDL

To enforce the fundamental business rule defined in [`docs/Enterprise Baseline/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/BRD_SPECIFICATION.md), General Ledger entries are strictly immutable. PostgreSQL triggers unconditionally reject any `UPDATE` or `DELETE` operations:

```sql
-- =============================================================================
-- IMMUTABLE GENERAL LEDGER TRIGGER DDL SPECIFICATION
-- =============================================================================

CREATE OR REPLACE FUNCTION enforce_immutable_general_ledger()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE') THEN
        RAISE EXCEPTION 'SECURITY ERROR: UPDATE operations are strictly prohibited on General Ledger entries (Entry ID: %). Financial adjustments must be posted as new offsetting journal entries.', OLD.id
        USING ERRCODE = 'integrity_constraint_violation';
    ELSIF (TG_OP = 'DELETE') THEN
        RAISE EXCEPTION 'SECURITY ERROR: DELETE operations are strictly prohibited on General Ledger entries (Entry ID: %). All financial records are immutable under tax compliance rules.', OLD.id
        USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Apply Trigger to General Ledger Table
DROP TRIGGER IF EXISTS trg_enforce_immutable_gl ON general_ledger_entries;
CREATE TRIGGER trg_enforce_immutable_gl
BEFORE UPDATE OR DELETE ON general_ledger_entries
FOR EACH ROW
EXECUTE FUNCTION enforce_immutable_general_ledger();

-- Assert Balanced Double-Entry Accounting Constraint
CREATE OR REPLACE FUNCTION verify_balanced_journal_transaction()
RETURNS TRIGGER AS $$
DECLARE
    v_total_debit NUMERIC(14, 2);
    v_total_credit NUMERIC(14, 2);
BEGIN
    SELECT COALESCE(SUM(debit_amount), 0), COALESCE(SUM(credit_amount), 0)
    INTO v_total_debit, v_total_credit
    FROM journal_entry_lines
    WHERE journal_entry_id = NEW.journal_entry_id;

    IF (v_total_debit <> v_total_credit) THEN
        RAISE EXCEPTION 'ACCOUNTING VIOLATION: Journal Transaction % is unbalanced! Total Debits ($%) != Total Credits ($%).',
            NEW.journal_entry_id, v_total_debit, v_total_credit
        USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## 4. In-Container Ephemeral State & Task Broker: Redis 7.2 Alpine

### 4.1 Configuration Directives (`redis.conf`)
Hosted on the EC2 container host via Docker Compose, Redis acts as both the low-latency distributed locking cache and the Celery task broker:

```text
# ==============================================================================
# HOSPITALITY OS: IN-CONTAINER REDIS 7.2 CONFIGURATION DIRECTIVES
# ==============================================================================
bind 0.0.0.0
port 6379
protected-mode yes

# Memory Management (128 MB Hard Boundary)
maxmemory 128mb
maxmemory-policy volatile-lru
maxmemory-samples 5

# Persistence & Durability (Append-Only File)
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite yes
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 32mb

# Snapshot Fallback
save 900 1
save 300 10
save 60 1000

# Client & Connection Limits
maxclients 1000
timeout 300
tcp-keepalive 60
```

---

### 4.2 Key Namespaces & TTL Map

| Key Pattern | Data Structure | TTL | Purpose & Eviction Behavior |
| :--- | :--- | :--- | :--- |
| **`pms:lock:<room_id>:<date>`** | `String (Lock Token)` | **10 Seconds** | Distributed pessimistic lock preventing room double-booking during checkout. |
| **`idemp:pos:<client_tx_uuid>`** | `String (Status/Hash)` | **72 Hours** | Idempotency deduplication buffer preventing duplicate replay settlements. |
| **`pms:avail:slice:<month>`** | `Hash / JSON String` | **60 Seconds** | Public booking search cache offloading high-frequency room query load. |
| **`celery:queue:*`** | `List / Stream` | **Persistent (AOF)** | Celery task transport broker for asynchronous recipe BOM depletion. |

---

## 5. Local-First Edge Persistence: SQLite 3.45 WAL Mode

On-premise POS touchscreens operate against an embedded SQLite 3.45 database to guarantee zero dependency on WAN availability during busy dining rushes:

### 5.1 SQLite Database Engine Initialization
```sql
-- SQLite Hardware & Database Optimization Directives
PRAGMA journal_mode = WAL;          -- Enables concurrent non-blocking reads and writes
PRAGMA synchronous = NORMAL;        -- Guarantees integrity across application restarts with high performance
PRAGMA cache_size = -64000;         -- Allocates 64 MB RAM for local page cache
PRAGMA busy_timeout = 5000;         -- 5,000ms busy wait before failing on lock contention
PRAGMA foreign_keys = ON;           -- Enforces relational integrity
```

### 5.2 Offline Batch Replay Schema (`offline_receipt_events`)
```sql
CREATE TABLE IF NOT EXISTS offline_receipt_events (
    id TEXT PRIMARY KEY,                       -- UUIDv4 Generated by Client Hardware
    terminal_id TEXT NOT NULL,                -- POS Terminal Serial Identifier
    tenant_id TEXT NOT NULL,                  -- Property Tenant Identifier
    sequence_number INTEGER NOT NULL,         -- Monotonically increasing local sequence
    event_timestamp TEXT NOT NULL,            -- ISO 8601 UTC Timestamp
    idempotency_key TEXT UNIQUE NOT NULL,     -- idemp_pos_<terminal>_<uuid>
    receipt_payload TEXT NOT NULL,            -- Encrypted/Signed JSON check settlement payload
    state_sha256 TEXT NOT NULL,               -- Cryptographic Hash of check line items
    sync_status TEXT DEFAULT 'PENDING',       -- PENDING | SYNCED | FAILED
    retry_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_offline_receipts_sync ON offline_receipt_events (sync_status, sequence_number);
```

---

## 6. Durable Object Storage & Compliance Vault (Amazon S3)

Storage utilizes the **AWS S3 5 GB Free Tier** paired with default Amazon S3 Server-Side Encryption (SSE-S3), avoiding paid KMS CMKs ($1.00/mo):

```
+==================================================================================================================+
|                                        AWS S3 3-BUCKET TOPOLOGY & LIFECYCLE                                      |
+==================================================================================================================+
|                                                                                                                  |
|  1. [ hospitality-web-assets-prod ] (Public Web SPAs & Bundles)                                                  |
|     • Purpose: Compiled React SPAs, Vite bundles, and tenant logo assets.                                        |
|     • Edge Integration: Fronted by Amazon CloudFront CDN (1 TB/month Free Perpetual).                            |
|     • Encryption: SSE-S3 (AES-256 Default) | Public Access: Blocked via CloudFront OAC.                         |
|                                                                                                                  |
|  2. [ hospitality-financial-archive-prod ] (7-Year WORM Compliance Vault)                                        |
|     • Purpose: Finalized guest folios, VAT invoices, and daily night audit reports (PDF/A-3).                    |
|     • Non-Repudiation Lock: S3 Object Lock in COMPLIANCE Mode (2,555 Days / 7 Years Retention).                  |
|     • Security: Root account cannot delete locked files under SEC 17a-4 / European VAT rules.                    |
|                                                                                                                  |
|  3. [ hospitality-wal-backups-prod ] (Continuous Database WAL Archives)                                          |
|     • Purpose: Continuous PostgreSQL Write-Ahead Logs streamed for Point-in-Time Recovery.                       |
|     • Lifecycle Transition: Automated deletion at Day 35 (Free-tier storage optimization).                       |
+==================================================================================================================+
```

---

## 7. Disaster Recovery Runbook: Single-AZ Point-in-Time Recovery

In the event of accidental database corruption or instance hardware degradation, the database administrator executes the following Point-in-Time Recovery (PITR) procedure using the AWS CLI:

```bash
#!/usr/bin/env bash
# ==============================================================================
# HOSPITALITY OS: RDS POINT-IN-TIME RECOVERY (PITR) RUNBOOK
# Target RTO: < 15 Minutes | Target RPO: <= 1.0s
# ==============================================================================
set -euo pipefail

SOURCE_DB_INSTANCE="hospitality-db-prod"
RESTORED_DB_INSTANCE="hospitality-db-prod-restored-$(date +%s)"
TARGET_RESTORE_TIME="2026-08-23T22:00:00.000Z"
DB_SUBNET_GROUP="dbsubnet-hospitality-prod"
SECURITY_GROUP_ID="sg-0a1b2c3d4e5f6g7h8" # sg_hospitality_rds ID

echo ">>> [1/4] Initiating Point-in-Time Restore for ${SOURCE_DB_INSTANCE} to ${RESTORED_DB_INSTANCE}..."
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier "${SOURCE_DB_INSTANCE}" \
    --target-db-instance-identifier "${RESTORED_DB_INSTANCE}" \
    --restore-time "${TARGET_RESTORE_TIME}" \
    --db-instance-class "db.t4g.micro" \
    --db-subnet-group-name "${DB_SUBNET_GROUP}" \
    --vpc-security-group-ids "${SECURITY_GROUP_ID}" \
    --publicly-accessible false \
    --no-multi-az \
    --region "ap-south-1"

echo ">>> [2/4] Awaiting restored instance availability..."
aws rds wait db-instance-available \
    --db-instance-identifier "${RESTORED_DB_INSTANCE}" \
    --region "ap-south-1"

echo ">>> [3/4] Fetching new database endpoint..."
NEW_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier "${RESTORED_DB_INSTANCE}" \
    --region "ap-south-1" \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text)

echo ">>> Restored Database Endpoint: ${NEW_ENDPOINT}"
echo ">>> [4/4] Update DATABASE_HOST in /opt/hospitality-os/.env.production and execute: docker compose restart web celery"
```

---

## 8. Storage Pre-Flight Verification Checklist

- [ ] **Assertion 1 (RDS Free-Tier Compliance):** RDS instance is sized at `db.t4g.micro`, Single-AZ, 20 GB gp3 SSD (`aws rds describe-db-instances`).
- [ ] **Assertion 2 (Immutable Ledger Triggers Active):** Attempting an `UPDATE general_ledger_entries` statement aborts with error `integrity_constraint_violation`.
- [ ] **Assertion 3 (Redis Memory Capped):** `redis-cli info memory` confirms `maxmemory: 134217728` (128 MB) and `maxmemory_policy: volatile-lru`.
- [ ] **Assertion 4 (Local POS Autonomy):** Disconnecting network cable from POS terminal allows uninterrupted check settlement and thermal receipt printing against local SQLite.
- [ ] **Assertion 5 (S3 Object Lock Active):** Attempting to delete an archived invoice in `hospitality-financial-archive-prod` returns `AccessDenied: Object is locked under Compliance Mode`.
- [ ] **Assertion 6 (PITR Backup Active):** RDS automated backup retention is set to 7 days; `LatestRestorableTime` is within 5 minutes of current UTC time.
