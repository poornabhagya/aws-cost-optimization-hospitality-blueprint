# Capacity Sizing & Technical Resource Allocation Specification

**Document Metadata:**
- **Document Version:** 1.0.0
- **System Scope:** 1 Boutique Property (10 Rooms, 30 Dining Seats, 20 Bar Seats, 4 POS Nodes)
- **Author:** Principal Infrastructure Architect / Lead Capacity Planning Engineer
- **Status:** Draft / In-Review
- **Effective Date:** August 20, 2026
- **Aligned Documents:** `docs/BRD_SPECIFICATION.md`, `docs/NFR_SPECIFICATION.md`

---

## 1. Executive Workload & Demand Synthesis

### 1.1 Operational Footprint & Concurrency Profile
The operational profile for a single boutique hospitality deployment models the physical and digital interactions of a hybrid lodging and food-and-beverage property. All resource requirements are mathematically derived from first principles based on physical asset boundaries, staff scheduling, and guest interaction channels.

```
+----------------------------------------------------------------------------------------------------+
|                                PROPERTY PHYSICAL & LOGICAL FOOTPRINT                              |
|                                                                                                    |
|  [ LODGING & ROOMS ]      [ FOOD & BEVERAGE ]         [ PHYSICAL STATIONS ]   [ CONCURRENT USERS ] |
|  * 10 Boutique Keys       * 30 Dining Room Seats      * 1 Front Desk PC       * 7 Staff Sessions   |
|  * Max 20-25 Guests       * 20 Bar Stools/Seats       * 1 Dining POS Node     * 20-30 Guest Web    |
|  * 8-10 Turns/Day         * 75-100 Checks/Day         * 1 Bar Speed POS Node    QR & Direct Search |
|                           * 240-320 KDS Items/Day     * 1 Kitchen KDS Node                         |
+----------------------------------------------------------------------------------------------------+
```

### 1.2 Aggregate Ingress Traffic Math
Traffic entering the property application gateway comprises three discrete operational channels:
1. **Public Web & QR Guests:** Direct room booking calendar lookups, digital menu views, and guest self-service folio queries.
2. **Local Point-of-Sale (POS) & KDS Terminals:** Fast order item creation, order state modification, kitchen routing, and payment authorizations.
3. **Property Management & Staff Operations:** Front desk check-ins/check-outs, housekeeping status updates, night audit ledger reconciliations, and back-office management.

#### Mathematical Derivation of Baseline and Peak Demand
Let $RPS_{aggregate}$ represent the total incoming request rate across all operational channels:

$$RPS_{aggregate} = RPS_{web} + RPS_{pos} + RPS_{staff} + RPS_{telemetry}$$

$$\text{Baseline Demand: } RPS_{baseline} = 0.03 + 0.08 + 0.02 + 0.15 = 0.28\text{ RPS}$$

$$\text{Peak Sustained Demand: } RPS_{peak} = 0.50 + 1.20 + 0.50 + 0.30 = 2.50\text{ RPS}$$

$$\text{Burst Demand Ceiling (Replay / Surges): } RPS_{burst} = 10.00\text{ RPS}$$

| Operational Ingress Channel | Normal Window Volume | Peak Rush Window | Sustained Baseline (RPS) | Peak Sustained (RPS) | Maximum Burst (RPS) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Direct Web & Mobile QR** | 1,200–1,800 hits/day | 18:00–22:00 | 0.02 – 0.05 RPS | 0.25 – 0.50 RPS | 1.00 – 2.00 RPS |
| **Dining & Bar POS Stations** | 75–100 checks/day | 12:00–14:00, 19:00–21:30 | 0.05 – 0.10 RPS | 0.80 – 1.20 RPS | 2.50 RPS |
| **Front Desk PMS & Back-Office** | 8–10 check-ins/day | 11:00–12:00, 15:00–17:00 | 0.01 – 0.03 RPS | 0.30 – 0.50 RPS | 1.00 RPS |
| **KDS Live Dispatch / Poll** | 240–320 items/day | 12:30–13:30, 19:30–20:30 | 0.04 – 0.08 RPS | 0.40 – 0.80 RPS | 1.50 RPS |
| **Offline Batch Replay Surge** | 0–3 events/month | Network restoration | 0.00 RPS | 0.00 RPS | 5.00 – 10.00 RPS |
| **Internal Health Probes** | Constant interval | Continuous 10s probes | 0.10 – 0.20 RPS | 0.20 – 0.40 RPS | 0.40 RPS |
| **Total Property Ingress** | **—** | **Rushes / Network Reconnect** | **0.22 – 0.46 RPS** | **2.00 – 2.50 RPS** | **10.00 RPS** |

### 1.3 Workload Tiering Model
The architecture distributes execution across distinct infrastructure planes:
- **Stateless Application Execution Plane:** Handles HTTP/REST requests, business logic validation, JWT authentication, and SQL transaction dispatch.
- **In-Memory Ephemeral State Plane:** Handles distributed locking (`pms:lock`), JWT revocation tracking, room search caching, and idempotency replay buffers.
- **Relational Persistence Plane:** ACID transactional storage, schema-per-tenant isolation, immutable ledger entries, and outbox event tables.
- **Connection Multiplexing Plane:** Mediates connection boundaries between stateless compute tasks and relational storage engines.
- **Durable Object Archival Plane:** Immutable storage for closed guest folio invoices, fiscal compliance receipts, and point-in-time recovery archives.

```
+----------------------------------------------------------------------------------------------------+
|                                    FIVE-TIER WORKLOAD TOPOLOGY                                     |
|                                                                                                    |
|  [ Ingress / Routing Layer ]  ----> Reverse Proxy / TLS 1.3 Termination                            |
|               |                                                                                    |
|               v                                                                                    |
|  [ Stateless Compute Plane ]  ----> Modular Monolith App Workers (Python 3.12 / Gunicorn)          |
|         |            |                                                                             |
|         |            +------------> [ Ephemeral State Plane ] (Key-Value Store / Redis)            |
|         v                                                                                          |
|  [ Multiplexing Plane ]       ----> Connection Pooler (PgBouncer in Transaction Mode)              |
|         |                                                                                          |
|         v                                                                                          |
|  [ Relational Persistence ]   ----> PostgreSQL 17 Primary Engine (WAL Archive Stream)              |
|                                                     |                                              |
|                                                     v                                              |
|  [ Durable Object Vault ]     <---------------------+ Encrypted Compliance & Snapshot Storage      |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Compute Tier Capacity Sizing (Application Execution Plane)

### 2.1 Worker Process & Thread Concurrency Modeling

#### Mathematical Capacity per Execution Worker
Let $T_{req}$ be the average end-to-end processing time per HTTP transaction executed on the compute worker (measured at median $p_{50} = 45\text{ ms} = 0.045\text{ s}$).

The theoretical continuous transaction processing capacity $C_{worker}$ of a single synchronous worker thread is:

$$C_{worker} = \frac{1}{T_{req}} = \frac{1}{0.045\text{ s}} \approx 22.22\text{ requests / second (RPS)}$$

Accounting for context switching, database socket I/O wait, and serialization overhead, an efficiency coefficient $\eta = 0.80$ is applied:

$$C_{effective} = C_{worker} \times \eta = 22.22 \times 0.80 = 17.78\text{ RPS per worker}$$

#### Concurrency Modeling at Peak and Burst
Using Little's Law ($L = \lambda \times W$), where $L$ is the average number of concurrent requests in the system, $\lambda$ is arrival rate (RPS), and $W$ is mean execution latency ($T_{req} = 0.045\text{ s}$):

1. **At Peak Sustained Load ($\lambda = 2.50\text{ RPS}$):**
   $$L_{peak} = 2.50\text{ req/s} \times 0.045\text{ s} = 0.1125\text{ concurrent requests}$$
   *Interpretation:* Peak operational traffic utilizes approximately **11.3% of 1 worker thread**.

2. **At Maximum Burst / Batch Replay ($\lambda = 10.00\text{ RPS}$):**
   $$L_{burst} = 10.00\text{ req/s} \times 0.045\text{ s} = 0.4500\text{ concurrent requests}$$
   *Interpretation:* Even during maximum offline POS replay bursts, active concurrency remains under **0.50 concurrent requests**.

#### Execution Pipeline Topology
- **Model:** Pre-fork worker process model with async I/O coroutines or lightweight OS threads (2 worker processes per container instance).
- **Aggregate Concurrency:** 2 instances $\times$ 2 workers = 4 worker processes active.
- **Combined Max Throughput:** $4 \times 17.78\text{ RPS} = 71.12\text{ RPS}$ maximum sustained capacity.

---

### 2.2 Memory (RAM) Budget Allocation
Each stateless application container instance is sized with a strict boundary of **512 MB RAM**.

#### Container Memory Map (512 MB Allocation)

```
+--------------------------------------------------------------------------------------------------+
|                              512 MB RUNTIME CONTAINER MEMORY MAP                                |
|                                                                                                  |
| [ Base OS / C-Libs ]  [ Py3.12 Runtime ]  [ App Framework & ORM ]  [ Sockets ]  [ Request Heap ] |
|      (48 MB)               (42 MB)                 (110 MB)          (35 MB)         (64 MB)     |
|      9.38%                 8.20%                   21.48%            6.84%          12.50%       |
|                                                                                                  |
| [ Dynamic Safety Buffer / Headroom / OOM Protection ]                                            |
|      (213 MB)                                                                                    |
|      41.60%                                                                                      |
+--------------------------------------------------------------------------------------------------+
```

#### Itemized Memory Budget Breakdown Table

| Memory Component | Allocated Memory (MB) | Percentage of Total | Functional Purpose & Scope |
| :--- | :--- | :--- | :--- |
| **Base OS & Shared C-Libraries** | 48.0 MB | 9.38% | Alpine/Debian slim userland, musl/glibc runtime, SSL/TLS crypto primitives. |
| **Python 3.12 Interpreter Core** | 42.0 MB | 8.20% | Python binary base memory, bytecode compiler, default modules, GC overhead. |
| **Application Framework & ORM Models** | 110.0 MB | 21.48% | Django runtime, loaded domain models (PMS, POS, Inventory, GL), routing tables. |
| **Client Connection & Socket Buffers** | 35.0 MB | 6.84% | PostgreSQL socket buffers, Key-Value cache sockets, ingress HTTP buffers. |
| **Active Request Execution Heap** | 64.0 MB | 12.50% | Serialized JSON payloads (up to 128 KB each), query result sets, PDF assembly buffers. |
| **Dynamic Headroom & OOM Buffer** | 213.0 MB | 41.60% | Transient spike buffer preventing Out-Of-Memory (OOM) killer invocations. |
| **Total Container Sizing Boundary** | **512.0 MB** | **100.00%** | **Rigid resource limit per compute task.** |

---

### 2.3 Compute Core (vCPU) Sizing & Redundancy

#### Baseline vCPU Requirement per Runtime Instance
- **Baseline Allocation:** **0.25 vCPU** (250 milli-cores) per container instance.
- **Processing Power:** 250 milli-cores on modern server CPUs (e.g., 2.8–3.5 GHz) yield $> 1.0\times 10^9$ CPU cycles/second.
- **Cycles per Request:** At $45\text{ ms}$ processing latency with ~25% CPU utilization ($11.25\text{ ms}$ active compute), a single request consumes $\approx 3.375\times 10^7$ CPU cycles.
- **Theoretical Single Instance Capacity:** $\frac{250\text{ mCPU}}{11.25\text{ ms/req}} = 22.2\text{ RPS}$.

#### High Availability & Multi-Fault Domain Redundancy Footprint
To satisfy the **99.9% Uptime Availability SLA** (maximum unplanned downtime $\le 43.8\text{ min/month}$), the compute plane must never run as a single point of failure (SPOF).

```
+----------------------------------------------------------------------------------------------------+
|                                HIGH-AVAILABILITY COMPUTE TOPOLOGY                                  |
|                                                                                                    |
|                                 [ Ingress Gateway / Load Balancer ]                                |
|                                            |              |                                        |
|                     +----------------------+              +----------------------+                 |
|                     |                                                            |                 |
|                     v                                                            v                 |
|      +------------------------------+                     +------------------------------+         |
|      |       FAILURE DOMAIN A       |                     |       FAILURE DOMAIN B       |         |
|      |  [ App Runtime Instance 1 ]  |                     |  [ App Runtime Instance 2 ]  |         |
|      |  * Compute: 0.25 vCPU        |                     |  * Compute: 0.25 vCPU        |         |
|      |  * Memory:  512 MB RAM       |                     |  * Memory:  512 MB RAM       |         |
|      +------------------------------+                     +------------------------------+         |
|                                                                                                    |
|      TOTAL ALLOCATED COMPUTE PLANE: 0.50 vCPU  |  1,024 MB RAM  |  2 Isolated Fault Domains        |
+----------------------------------------------------------------------------------------------------+
```

#### Saturation & Safety Headroom Analysis
- **Total Redundant Compute Capacity:** $2\text{ instances} \times 22.2\text{ RPS} = 44.4\text{ RPS sustained}$.
- **Property Peak Sustained Demand:** $2.50\text{ RPS}$.
- **Safety Factor Calculation:**

$$\text{Safety Factor} = \frac{\text{Provisioned Capacity}}{\text{Peak Demand}} = \frac{44.4\text{ RPS}}{2.50\text{ RPS}} = 17.76\times \approx 18\times \text{ (Sustained)}$$

$$\text{Single Instance Degraded Safety Factor} = \frac{22.2\text{ RPS}}{2.50\text{ RPS}} = 8.88\times \text{ (During Single Node Failure)}$$

Even in an event where an entire failure domain experiences total outage, the remaining single instance processes the property's absolute peak load with nearly $9\times$ headroom.

---

## 3. Database & Persistence Capacity Sizing

### 3.1 Compute & Memory Allocation (Relational Engine)
The persistence tier utilizes a dedicated relational database engine (PostgreSQL 17) provisioned with a **0.50 vCPU** and **2.0 GB RAM** resource boundary.

```
+----------------------------------------------------------------------------------------------------+
|                             RELATIONAL ENGINE MEMORY ALLOCATION (2.0 GB)                           |
|                                                                                                    |
|  [ Shared Working Buffers ]   [ OS Kernel & Page Cache ]   [ Conn Work Mem ]   [ Maint Work Mem ]  |
|       (512 MB / 25%)               (614 MB / 30%)             (160 MB / 8%)       (128 MB / 6.4%)  |
|                                                                                                    |
|  [ Server Engine Overhead, Query Parser & Dynamic Headroom ]                                       |
|       (634 MB / 31.0%)                                                                             |
+----------------------------------------------------------------------------------------------------+
```

#### Detailed Database Memory Budget Table

| Configuration Parameter | Sized Value | Memory Allocation | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| `shared_buffers` | 25% of RAM | 512.0 MB | Houses active working set tables, primary key B-Tree index pages, and hot folio/cart rows in memory. |
| **OS Kernel & Page Cache** | ~30% of RAM | 614.0 MB | Caches disk blocks, filesystem inode metadata, and dirty write-back pages. |
| `work_mem` | 16.0 MB per op | 160.0 MB *(10 conns)* | Allocated per sort, hash join, and aggregation operation (16 MB $\times$ 10 active connections). |
| `maintenance_work_mem` | Fixed budget | 128.0 MB | Dedicated to background VACUUM, index re-indexing, and DDL schema migrations. |
| `max_connections` (Backend) | 20 sockets | — | Direct server process cap to prevent memory thrashing. |
| **Engine Overhead & Headroom** | Remaining RAM | 634.0 MB | Dynamic query planner structures, replication send buffers, and transient connection spikes. |
| **Total Persistence Memory** | **100.0%** | **2,048.0 MB (2.0 GB)** | **Full relational instance memory allocation.** |

---

### 3.2 Connection Multiplexing & Pool Math

#### Client-to-Backend Socket Ratio
Uncontrolled relational database connections degrade query latency through CPU cache contention and memory fragmentation. The system mandates a dedicated connection pooler operating in **Transaction Pooling Mode**.

```
+----------------------------------------------------------------------------------------------------+
|                               CONNECTION MULTIPLEXING TOPOLOGY                                     |
|                                                                                                    |
|  [ Ingress Client Sockets ]                                                                        |
|  * 4 POS/KDS Terminals                                                                             |
|  * 7 Staff Sessions            ====(Up to 30 Active Client Sockets)====> [ PgBouncer Pooler ]      |
|  * 20-30 Guest Web Sessions                                                       |                |
|                                                                                   | (Multiplexed)  |
|                                                                                   v                |
|  [ Relational Persistence ]    <====(5 to 10 Backend Connections)================-+                |
|  * PostgreSQL 17 Engine                                                                            |
+----------------------------------------------------------------------------------------------------+
```

#### Transaction Throughput & Headroom Derivation
Let:
- $N_{backend} = 5$ (Number of active backend database server connections in the pool)
- $T_{tx} = 5.0\text{ ms} = 0.005\text{ s}$ (Average database transaction execution time for indexed CRUD operations)

The continuous transaction capacity $TPS_{pool}$ is:

$$TPS_{pool} = \frac{N_{backend}}{T_{tx}} = \frac{5\text{ connections}}{0.005\text{ s / tx}} = 1,000.0\text{ Transactions / Second (TPS)}$$

#### Headroom Comparison
- **Peak Property Transaction Rate:** $\approx 2.00\text{ TPS}$ (even assuming 1 HTTP request = 1 full DB transaction).
- **Headroom Ratio:**

$$\text{DB Throughput Headroom} = \frac{TPS_{pool}}{TPS_{peak}} = \frac{1,000\text{ TPS}}{2.00\text{ TPS}} = 500\times \text{ Headroom}$$

This guarantees zero queue wait time in the connection pooler under any normal or burst condition.

---

### 3.3 Storage Volume, IOPS & Growth Modeling

#### 3-Year Linear Storage Trajectory
Daily storage accumulation is driven by:
- POS sales receipts & line items (75–100 checks $\times$ 3.2 items $\approx 320$ line item rows $\approx 640\text{ KB/day}$).
- Outbox event log records ($\approx 1.2\text{ MB/day}$, pruned after 14 days).
- General Ledger immutable double-entry journal rows ($\approx 400\text{ KB/day}$).
- Room folio balance updates & audit logs ($\approx 300\text{ KB/day}$).
- Index B-tree growth ($\approx 50\%$ of raw data volume).
- **Net Daily Growth Rate:** $\approx 2.50\text{ MB / day} \approx 912.5\text{ MB / year}$.

```
+----------------------------------------------------------------------------------------------------+
|                                3-YEAR STORAGE ACCUMULATION TRAJECTORY                              |
|                                                                                                    |
|  HORIZON          DAILY CHECKS    DAILY GROWTH    ACTIVE DATA VOLUME    PROVISIONED VOLUME BUFFER  |
|  ---------------  --------------  --------------  --------------------  -------------------------  |
|  Day 1 (Schema)   --              --              ~ 85 MB               20.0 GB (99.58% Free)      |
|  Year 1           75 - 100 / day  ~ 2.5 MB / day  ~ 1.00 GB             20.0 GB (95.00% Free)      |
|  Year 2           75 - 100 / day  ~ 2.5 MB / day  ~ 1.91 GB             20.0 GB (90.45% Free)      |
|  Year 3           75 - 100 / day  ~ 2.5 MB / day  ~ 2.82 GB             20.0 GB (85.90% Free)      |
+----------------------------------------------------------------------------------------------------+
```

#### Provisioned Storage Boundary & Safety Buffer
- **Baseline Provisioned Volume:** **20.0 GB** solid-state disk volume.
- **Year 3 Cumulative Storage:** **2.82 GB**.
- **Storage Safety Margin:**

$$\text{Storage Safety Buffer} = \frac{20.0\text{ GB} - 2.82\text{ GB}}{2.82\text{ GB}} \times 100\% = 609.2\% \text{ safety buffer over 3 years}$$

#### IOPS & Disk Throughput Sizing
- **Peak Database Write IOPS:**
  - WAL write operations: $\approx 10\text{ writes/sec}$
  - Checkpoint flushes & page dirties: $\approx 20\text{ IOPS}$
  - Outbox event table updates: $\approx 10\text{ IOPS}$
  - **Peak Transactional Demand:** **6 to 50 IOPS**.
- **Standard Baseline Solid-State Disk Performance:**
  - **Baseline Provisioned IOPS:** **3,000 IOPS**.
  - **Baseline Throughput:** **125 MB/s**.
- **IOPS Headroom Ratio:**

$$\text{IOPS Headroom} = \frac{3,000\text{ IOPS}}{50\text{ IOPS (Peak)}} = 60\times \text{ IOPS Safety Factor}$$

$$\text{Throughput Headroom} = \frac{125\text{ MB/s}}{0.25\text{ MB/s (Peak Writes)}} = 500\times \text{ Throughput Safety Factor}$$

---

## 4. In-Memory Caching & Ephemeral State Sizing

### 4.1 Key Lifecycle & Cache Volume Math
The in-memory ephemeral caching layer provides low-latency key-value storage for distributed locks, authentication session invalidation, room availability search slices, and offline sync replay buffers.

```
+----------------------------------------------------------------------------------------------------+
|                                IN-MEMORY DATA DOMAIN DISTRIBUTION                                  |
|                                                                                                    |
|  [ Room Search Slices ]  [ Outbox Events ]  [ Sync Buffer ]  [ JWT Sessions ]  [ Locks ]           |
|      (2.00 MB)                (0.40 MB)         (0.15 MB)         (0.05 MB)     (0.01 MB)          |
|      76.6%                    15.3%             5.7%              1.9%          0.4%               |
|                                                                                                    |
|  TOTAL ACTIVE WORKING DATA: ~ 2.61 MB across ~ 1,500 keys                                          |
|  TOTAL ALLOCATED CAPACITY:  512.00 MB (99.49% Available Cache Headroom)                            |
+----------------------------------------------------------------------------------------------------+
```

#### Itemized Ephemeral Key Lifecycle Breakdown Table

| Key Namespace / Domain | Concurrent Active Keys | Average Value Size | Key TTL Policy | Active Memory Footprint | Functional Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `auth:jwt:revoked:*` | 50 – 100 keys | 512 bytes | 30 Minutes (Sliding) | ~0.05 MB | Instant token version revocation tracking. |
| `pms:avail:slice:*` | 300 – 500 keys | 4.0 KB | 5 Minutes (Fixed) | ~2.00 MB | 30-day room availability search cache slices. |
| `pms:lock:*` | 5 – 10 keys | 256 bytes | 10 Seconds (Strict) | ~0.01 MB | Distributed locking for check-in / room assignment. |
| `pos:sync:dedup:*` | 500 – 1,000 keys | 128 bytes | 24 Hours (Fixed) | ~0.15 MB | Offline POS receipt replay idempotency filter. |
| `outbox:buffer:*` | 50 – 200 items | 2.0 KB | Ephemeral (< 60s) | ~0.40 MB | Ephemeral worker queue dispatcher buffer. |
| **Total Active Key Set** | **~1,000 – 1,800 keys** | **—** | **—** | **< 30.0 MB** | **Encompasses all active keys and overhead.** |

---

### 4.2 In-Memory Engine Sizing & Eviction Configuration
- **Provisioned Memory Boundary:** **512.0 MB RAM**.
- **Max Active Working Memory:** **~30.0 MB** (including Redis jemalloc memory fragmentation overhead).
- **Steady-State Utilization Ratio:**

$$\text{Cache Utilization} = \frac{30.0\text{ MB}}{512.0\text{ MB}} = 5.86\% \approx 5.9\% \text{ utilization at peak load}$$

- **Eviction Policy:** `volatile-lru` (evicts least-recently-used keys with an explicit TTL if memory threshold is reached, protecting persistent locks and sync buffers).
- **Maxmemory Safety Margin:** $> 94.0\%$ unallocated memory headroom ensuring complete immunity from cache thrashing.

---

## 5. Network Throughput & Bandwidth Capacity Sizing

### 5.1 Monthly Data Transfer Model (Ingress / Egress)
Bandwidth sizing models all outbound data flows across public internet and local LAN interfaces over a standard 30-day operating month.

```
+----------------------------------------------------------------------------------------------------+
|                                  MONTHLY EGRESS BANDWIDTH MODEL                                    |
|                                                                                                    |
|  [ Internal Replication & Metrics ]  ==================================> 4.50 GB / mo (55.5%)     |
|  [ Static Web & QR Assets ]          =====================> 2.25 GB / mo (27.8%)                   |
|  [ API JSON Responses ]              =========> 0.90 GB / mo (11.1%)                               |
|  [ POS Heartbeats & Telemetry ]      ===> 0.23 GB / mo (2.8%)                                      |
|  [ Guest Invoice Folio PDFs ]        => 0.15 GB / mo (1.9%)                                        |
|                                                                                                    |
|  TOTAL ESTIMATED EGRESS: 8.03 GB / Month  |  PROVISIONED BASELINE CAP: 15.00 GB / Month            |
+----------------------------------------------------------------------------------------------------+
```

#### Itemized Monthly Data Volume Model

| Data Transfer Channel | Daily Transaction Volume | Average Payload Size | Monthly Data Volume (30 Days) | Interface Type |
| :--- | :--- | :--- | :--- | :--- |
| **API JSON Responses** | 10,000 API calls / day | 3.0 KB / payload | 0.90 GB / month | Public / LAN Egress |
| **Guest Folio & Invoice PDFs** | 10 checkouts / day | 500.0 KB / PDF | 0.15 GB / month | Public HTTPS Egress |
| **POS Telemetry & Heartbeats** | 15,000 pings / day | 0.5 KB / message | 0.23 GB / month | LAN / WebSocket Egress |
| **Static Web & QR Menu Assets** | 1,500 visits / day | 50.0 KB / page load | 2.25 GB / month | CDN / Gateway Egress |
| **Metric Streaming & Log Push** | Continuous (24/7) | ~1.75 KB / sec | 4.50 GB / month | Private Network Egress |
| **Total Aggregate Egress** | **—** | **—** | **8.03 GB / month** | **< 8.50 GB / month** |

- **Baseline Data Transfer Sizing Cap:** **15.0 GB / month** (providing an 86.8% headroom margin above peak operational volume).

---

### 5.2 Network Concurrency & Load Balancing Units
The ingress reverse proxy / load balancing layer terminates TLS 1.3 connections and routes traffic to compute containers.

#### Ingress Gateway Sizing Parameters
- **Maximum Concurrent TCP/TLS Sockets:** 35 concurrent connections (7 staff nodes + 4 POS/KDS hardware terminals + 24 active guest sessions).
- **New Connection Establishment Rate:** $\approx 0.50\text{ new connections / second}$ (dominated by keep-alive HTTP/2 and WebSocket connections).
- **Processed Hourly Bandwidth:**

$$\text{Hourly Bandwidth} = \frac{8.03\text{ GB}}{30 \times 24\text{ hours}} = 0.0111\text{ GB / hour} \approx 0.02\text{ GB / hour (Peak)}$$

- **Ingress Sizing Conclusion:** Peak socket and bandwidth demand consumes $< 0.1\%$ of the capacity of a standard entry-level load balancer or reverse proxy instance.

---

## 6. Resource Allocation Summary Matrix

The following master matrix consolidates the platform-agnostic resource units sized for the single boutique property deployment.

| Subsystem Layer | Minimum Resource Unit Allocation | Redundancy / HA Multiplier | Effective Provisioned Footprint | Peak System Demand | Safety / Headroom Factor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Stateless Compute Plane** | 0.25 vCPU<br>512 MB RAM | $2\times$ Dual Failure Domain | **0.50 vCPU<br>1,024 MB RAM** | 2.50 RPS<br>128 MB RAM | **17.8x Compute Headroom**<br>(44.4 RPS capacity) |
| **In-Memory Cache Plane** | 0.25 vCPU<br>512 MB RAM | $1\times$ Active Instance<br>*(Ephemeral)* | **0.25 vCPU<br>512 MB RAM** | ~30 MB Cache<br>1,500 Keys | **17.1x Memory Headroom**<br>(5.9% utilization) |
| **Relational Database** | 0.50 vCPU<br>2,048 MB RAM | $1\times$ Primary Instance<br>*(Synchronous Standby Optional)* | **0.50 vCPU<br>2,048 MB RAM** | 2.50 TPS<br>634 MB Working Set | **500x Transaction Headroom**<br>(1,000 TPS capacity) |
| **Primary Storage Volume** | 20.0 GB Solid-State Disk<br>3,000 Baseline IOPS | Storage Volume Mirroring | **20.0 GB Disk<br>3,000 IOPS** | 2.82 GB (Year 3)<br>50 IOPS Peak | **609% Storage Headroom**<br>**60x IOPS Headroom** |
| **Ingress Gateway / Proxy** | Entry-level TLS Proxy<br>100 Socket Capacity | Dual Failure Domain Routing | **1 Gateway Cluster** | 35 Concurrent Sockets<br>0.02 GB/hr | **> 100x Gateway Headroom** |
| **Monthly Network Egress** | 15.0 GB / month Egress Cap | High-Bandwidth Backbone | **15.0 GB / month** | 8.03 GB / month | **86.8% Bandwidth Headroom** |

---

## 7. Architectural Compliance & Next Steps

1. **Platform Neutrality:** This specification defines pure compute, memory, storage, IOPS, connection, and network units. Deployment-specific mappings to physical bare-metal, hypervisors, container runtimes (Docker/Podman/Kubernetes), or cloud-specific compute blocks shall be detailed in Architecture Decision Records (ADRs).
2. **Cost Analysis Separation:** Financial expenditure modeling, hardware procurement, and cloud cost calculations are strictly maintained in the Bill of Materials (BoM).
3. **Continuous Sizing Validation:** Resource utilization metrics shall be validated against these baseline figures via automated synthetic load tests prior to production property commissioning.
