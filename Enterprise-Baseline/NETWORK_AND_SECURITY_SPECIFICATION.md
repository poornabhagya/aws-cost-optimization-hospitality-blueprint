# Network & Security Architecture Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Production-Grade Network Topology, Subnet Allocation & Defense-in-Depth Security Specification
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 1.0.0 (Production Engineering Baseline)
* **Status:** Approved / Production-Ready Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Cloud Provider:** Amazon Web Services (AWS) — Primary Region: `us-east-1` (Dual-AZ: `us-east-1a`, `us-east-1b`)
* **Classification:** Highly Confidential / Enterprise Security & Network Baseline
* **Aligned Specifications:**
  - [`docs/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/BRD_SPECIFICATION.md) (Local-First POS Autonomy, Append-Only GL)
  - [`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md) (Multi-AZ 99.9% Uptime, TLS 1.3, Rate Limits, 30 DB Sockets, $p_{95} \le 120\text{ ms}$)
  - [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md) (2x Compute Tasks, 35 Ingress Sockets, 512MB RAM Compute, 512MB Redis)
  - [`docs/HLA_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/HLA_SPECIFICATION.md) (7-Tier Platform Topology)
  - [`docs/ADR_COLLECTION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/ADR_COLLECTION.md) (ADR-001 through ADR-011 AWS Service Blueprints)

---

## 1. Executive Summary & Security Philosophy

Hospitality OS enforces a **Zero-Trust Network Architecture (ZTNA)** and **Defense-in-Depth** model across all 7 architectural tiers. The cloud network topology is designed to provide:
1. **Multi-AZ High Availability:** Active-Active stateless compute and Multi-AZ persistence spanning two isolated Availability Zones (`us-east-1a` and `us-east-1b`) satisfying the $\ge 99.9\%$ SLA ($\le 43.8$ minutes downtime/year).
2. **Strict Micro-Segmentation:** Three distinct security boundaries per AZ (Public Ingress Tier, Private Compute Tier, and Fully Isolated Persistence Tier).
3. **No Direct Database Internet Egress:** Relational storage (RDS PostgreSQL) and in-memory caches (ElastiCache Redis) reside in non-routable isolated subnets with zero default internet routing.
4. **Least-Privilege Traffic Paths:** East-West traffic between tiers is restricted to exact application ports (`TCP 5432` for PostgreSQL via PgBouncer, `TCP 6379` for Redis, `TCP 8000` for Gunicorn) using chained AWS Security Groups.
5. **Private Data Plane Exfiltration Defense:** Compute workers communicate with AWS native APIs (ECR, SSM, Secrets Manager, CloudWatch Logs) over AWS PrivateLink VPC Interface Endpoints and S3 Gateway Endpoints, completely bypassing public internet gateways for internal API operations.

---

## 2. Global VPC Topology & IP CIDR Sizing Plan

### 2.1 Addressing Scheme Overview
The platform allocates a dedicated `/20` IPv4 CIDR block (`10.0.0.0/20`), providing **4,096 total IPv4 addresses**. This provides ample headroom for dual-AZ container orchestration, elastic network interfaces (ENIs), private endpoints, and future tenant expansion while maintaining dense, non-overlapping routing.

```
+==================================================================================================================+
|                                    HOSPITALITY OS GLOBAL VPC CIDR BLOCK: 10.0.0.0/20                             |
|                                            (4,096 Total IPv4 Addresses)                                          |
+==================================================================================================================+
|                                                                                                                  |
|  [ AVAILABILITY ZONE A: us-east-1a ]                        [ AVAILABILITY ZONE B: us-east-1b ]                  |
|                                                                                                                  |
|  +----------------------------------------------------+     +----------------------------------------------------+
|  | Public Subnet A: 10.0.0.0/24 (256 IPs)             |     | Public Subnet B: 10.0.1.0/24 (256 IPs)             |
|  | • AWS ALB Ingress Node A                           |     | • AWS ALB Ingress Node B                           |
|  | • NAT Gateway A (Elastic IP: 54.x.x.x)             |     | • (Optional Standby NAT / Direct IGW)              |
|  +----------------------------------------------------+     +----------------------------------------------------+
|                           |                                                          |                           |
|                           v                                                          v                           |
|  +----------------------------------------------------+     +----------------------------------------------------+
|  | Private Compute Subnet A: 10.0.2.0/23 (512 IPs)    |     | Private Compute Subnet B: 10.0.4.0/23 (512 IPs)    |
|  | • ECS Fargate Task 1 (Django + Gunicorn)           |     | • ECS Fargate Task 2 (Django + Gunicorn)           |
|  | • Celery Outbox Worker A                           |     | • Celery Outbox Worker B                           |
|  | • AWS PrivateLink VPC Interface Endpoints (ENIs)   |     | • AWS PrivateLink VPC Interface Endpoints (ENIs)   |
|  +----------------------------------------------------+     +----------------------------------------------------+
|                           |                                                          |                           |
|                           v                                                          v                           |
|  +----------------------------------------------------+     +----------------------------------------------------+
|  | Isolated Database Subnet A: 10.0.6.0/24 (256 IPs)  |     | Isolated Database Subnet B: 10.0.7.0/24 (256 IPs)  |
|  | • RDS PostgreSQL 17 Primary (db.t4g.micro)         |     | • RDS PostgreSQL Multi-AZ Standby Replica          |
|  | • ElastiCache Redis 7.2 Primary (cache.t4g.micro)  |     | • ElastiCache Redis Secondary Subnet               |
|  +----------------------------------------------------+     +----------------------------------------------------+
|                                                                                                                  |
|  [ UNALLOCATED / FUTURE EXPANSION SPACE ]                                                                        |
|  • CIDR Range: 10.0.8.0/21 (2,048 IPs) — Reserved for Multi-Property Fleet VPC Peering & Disaster Recovery       |
+==================================================================================================================+
```

### 2.2 AWS Reserved IP Allocation Standard
Every subnet provisioned in AWS reserves the first 4 and last 1 IP addresses:
- `x.x.x.0`: Network Address.
- `x.x.x.1`: AWS Default VPC Router.
- `x.x.x.2`: AWS DNS Server (AmazonProvidedDNS / Route 53 Resolver).
- `x.x.x.3`: AWS Reserved for future operational expansion.
- `x.x.x.255`: Network Broadcast Address (AWS does not support broadcast, address is reserved).

*Usable Host IPs per `/24` subnet:* $256 - 5 = 251\text{ usable addresses}$.  
*Usable Host IPs per `/23` subnet:* $512 - 5 = 507\text{ usable addresses}$.

---

## 3. 6-Subnet Multi-AZ Allocation Specification

The VPC is systematically partitioned into 6 subnets across 2 Availability Zones (`us-east-1a` and `us-east-1b`):

| Subnet Identifier | Availability Zone | IPv4 CIDR Block | Total IPs | Usable IPs | Tier Classification | Primary Hosted Workloads & Interfaces |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `subnet-pub-a` | `us-east-1a` | `10.0.0.0/24` | 256 | 251 | **Tier 2: Public Ingress** | AWS Application Load Balancer (Node A), NAT Gateway A |
| `subnet-pub-b` | `us-east-1b` | `10.0.1.0/24` | 256 | 251 | **Tier 2: Public Ingress** | AWS Application Load Balancer (Node B) |
| `subnet-priv-app-a` | `us-east-1a` | `10.0.2.0/23` | 512 | 507 | **Tier 3: Private Compute** | ECS Fargate App Task 1, Celery Worker Task, VPC Interface ENIs |
| `subnet-priv-app-b` | `us-east-1b` | `10.0.4.0/23` | 512 | 507 | **Tier 3: Private Compute** | ECS Fargate App Task 2, Celery Standby Task, VPC Interface ENIs |
| `subnet-iso-db-a` | `us-east-1a` | `10.0.6.0/24` | 256 | 251 | **Tier 5: Isolated Persistence** | AWS RDS PostgreSQL 17 Primary, AWS ElastiCache Redis Node |
| `subnet-iso-db-b` | `us-east-1b` | `10.0.7.0/24` | 256 | 251 | **Tier 5: Isolated Persistence** | RDS PostgreSQL Standby Subnet, ElastiCache Subnet Group |
| *Reserved (Future)* | Multi-AZ | `10.0.8.0/21` | 2,048 | 2,043 | **Unallocated Space** | Reserved for Tenant Peering / Read Replica Clusters |

---

## 4. Gateway & Routing Table Architecture

### 4.1 Gateway Strategy & Cost Optimization
1. **Internet Gateway (`igw-hospitality-prod`):**
   - Attached to the VPC root.
   - Provides direct, bidirectional internet connectivity strictly for resources in the Public Subnets (`subnet-pub-a`, `subnet-pub-b`).
2. **NAT Gateway (`nat-hospitality-az-a`):**
   - Provisioned in `subnet-pub-a` with a dedicated Elastic IP (`eip-nat-a`).
   - Enables outbound-only egress for Private Compute Subnets (e.g., Stripe Payment API calls, external webhook dispatches).
   - **Cost Control Architecture:** All internal AWS service communications (ECR image pulls, SSM parameter fetches, S3 file uploads, CloudWatch log streams) are routed through **VPC Endpoints**, preventing NAT Gateway data processing charges ($\$0.045/\text{GB}$).
3. **Zero Routing for Persistence Subnets:**
   - Isolated Database subnets have **NO** route to an Internet Gateway or NAT Gateway. They can never initiate outbound internet connections or receive inbound external connections.

### 4.2 Route Table Master Configuration

```
+----------------------------------------------------------------------------------------------------+
|                                    ROUTE TABLE TOPOLOGY MATRIX                                     |
|                                                                                                    |
|  [ PUBLIC ROUTE TABLE ] (rtb-public)                                                               |
|  • 10.0.0.0/20 --------> local (VPC Inter-Subnet)                                                  |
|  • 0.0.0.0/0 -----------> igw-hospitality-prod (Internet Gateway)                                 |
|  • Associated Subnets: subnet-pub-a (10.0.0.0/24), subnet-pub-b (10.0.1.0/24)                    |
|                                                                                                    |
|  [ PRIVATE COMPUTE ROUTE TABLE ] (rtb-private-app)                                                 |
|  • 10.0.0.0/20 --------> local (VPC Inter-Subnet)                                                  |
|  • pl-63a5400a ---------> vpce-s3-gateway (AWS S3 Prefix List)                                     |
|  • 0.0.0.0/0 -----------> nat-hospitality-az-a (Outbound NAT Gateway)                             |
|  • Associated Subnets: subnet-priv-app-a (10.0.2.0/23), subnet-priv-app-b (10.0.4.0/23)            |
|                                                                                                    |
|  [ ISOLATED DATABASE ROUTE TABLE ] (rtb-isolated-db)                                               |
|  • 10.0.0.0/20 --------> local (VPC Inter-Subnet Only)                                             |
|  • 0.0.0.0/0 -----------> NO ROUTE (Blackhole / Strict Isolation)                                  |
|  • Associated Subnets: subnet-iso-db-a (10.0.6.0/24), subnet-iso-db-b (10.0.7.0/24)                |
+----------------------------------------------------------------------------------------------------+
```

#### Detailed Route Specifications Table

| Route Table Name | Destination CIDR / Prefix | Target Gateway / Interface | Purpose & Traffic Flow |
| :--- | :--- | :--- | :--- |
| **`rtb-public`** | `10.0.0.0/20` | `local` | Internal VPC routing between public resources. |
| | `0.0.0.0/0` | `igw-hospitality-prod` | Ingress from public clients & egress for NAT Gateway. |
| **`rtb-private-app`** | `10.0.0.0/20` | `local` | Routing to VPC endpoints and persistence subnets. |
| | `pl-63a5400a` (S3 Prefix List) | `vpce-s3-gateway` | Zero-cost private data transfer to S3 buckets. |
| | `0.0.0.0/0` | `nat-hospitality-az-a` | Outbound external API calls (Stripe, Twilio, SendGrid). |
| **`rtb-isolated-db`** | `10.0.0.0/20` | `local` | Strict local-only database connections from compute tasks. |
| | *No Default Route* | *None* | Complete external isolation; zero internet attack surface. |

---

## 5. Security Groups Master Matrix (Zero-Trust Model)

Security groups act as stateful virtual firewalls at the Elastic Network Interface (ENI) level. In accordance with ZTNA principles:
- **Default Rule:** Implicit deny on all inbound traffic.
- **East-West Chaining:** Rules reference other Security Group IDs (`sg-xxxxxx`), never raw IP addresses, preventing IP spoofing and eliminating maintenance during container rescheduling.
- **Strict Egress Lockdown:** Compute and persistence security groups restrict outbound traffic exclusively to authorized downstream targets and ports.

```
+==================================================================================================================+
|                                    SECURITY GROUP CHAINING TOPOLOGY                                              |
+==================================================================================================================+
|                                                                                                                  |
|  [ INCOMING INTERNET TRAFFIC ]                                                                                   |
|               |                                                                                                  |
|               | HTTPS (TCP 443) / HTTP (TCP 80)                                                                  |
|               v                                                                                                  |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | SECURITY GROUP: sg-alb-ingress (Application Load Balancer)                                               |    |
|  | • Inbound: TCP 443 (0.0.0.0/0), TCP 80 (0.0.0.0/0 - Auto-Redirect to 443)                                 |    |
|  | • Outbound: TCP 8000 -> Restricted strictly to sg-ecs-compute                                            |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|                                                     |                                                            |
|                                                     | HTTP Container Target Port (TCP 8000)                      |
|                                                     v                                                            |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | SECURITY GROUP: sg-ecs-compute (ECS Fargate Web & Celery Tasks)                                          |    |
|  | • Inbound: TCP 8000 <- Restricted strictly from sg-alb-ingress                                           |    |
|  | • Outbound:                                                                                              |    |
|  |     - TCP 5432 -> sg-rds-postgres (PostgreSQL via PgBouncer)                                             |    |
|  |     - TCP 6379 -> sg-redis-cache (ElastiCache Redis)                                                     |    |
|  |     - TCP 443  -> sg-vpc-endpoints (AWS PrivateLink APIs)                                                |    |
|  |     - TCP 443  -> 0.0.0.0/0 (Outbound NAT Gateway for Third-Party APIs)                                  |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|                                  |                                       |                                       |
|               +------------------+                                       +------------------+                    |
|               | TCP 5432                                                                    | TCP 6379           |
|               v                                                                             v                    |
|  +--------------------------------------------+               +--------------------------------------------+     |
|  | SECURITY GROUP: sg-rds-postgres            |               | SECURITY GROUP: sg-redis-cache             |     |
|  | • Inbound: TCP 5432 <- sg-ecs-compute only |               | • Inbound: TCP 6379 <- sg-ecs-compute only |     |
|  | • Outbound: NONE (Total Egress Lockdown)   |               | • Outbound: NONE (Total Egress Lockdown)   |     |
|  +--------------------------------------------+               +--------------------------------------------+     |
|                                                                                                                  |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | SECURITY GROUP: sg-vpc-endpoints (AWS PrivateLink Interface Endpoints)                                   |    |
|  | • Inbound: TCP 443 <- sg-ecs-compute only                                                                |    |
|  | • Outbound: NONE (Local Service Termination)                                                             |    |
|  +----------------------------------------------------------------------------------------------------------+    |
+==================================================================================================================+
```

### 5.1 Ingress / Egress Rules Reference Matrix

| Security Group ID & Name | Rule Direction | Protocol & Port | Source / Destination Identifier | Rule Description & Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **`sg-alb-ingress`**<br>*(ALB Edge Gateway)* | **Inbound** | `TCP 443` | `0.0.0.0/0` (IPv4) & `::/0` (IPv6) | Public HTTPS ingress for web guests and POS terminals. |
| | **Inbound** | `TCP 80` | `0.0.0.0/0` (IPv4) & `::/0` (IPv6) | HTTP port for immediate 301 redirect to HTTPS (TLS 1.3). |
| | **Egress** | `TCP 8000` | `sg-ecs-compute` | Forward clean HTTP requests to ECS Fargate containers. |
| **`sg-ecs-compute`**<br>*(Application Plane)* | **Inbound** | `TCP 8000` | `sg-alb-ingress` | Receive reverse-proxied traffic from ALB listener. |
| | **Egress** | `TCP 5432` | `sg-rds-postgres` | SQL queries dispatched to PgBouncer / PostgreSQL. |
| | **Egress** | `TCP 6379` | `sg-redis-cache` | Distributed locking, search cache & Celery task broker. |
| | **Egress** | `TCP 443` | `sg-vpc-endpoints` | Private AWS API requests (ECR, SSM, Secrets, Logs). |
| | **Egress** | `TCP 443` | `0.0.0.0/0` (via NAT GW) | Outbound HTTPS to external payment gateways (Stripe). |
| **`sg-rds-postgres`**<br>*(Database Plane)* | **Inbound** | `TCP 5432` | `sg-ecs-compute` | ACID transactional persistence queries from app tasks. |
| | **Egress** | *None* | `None` (Implicit Deny) | Total egress lockdown. Database cannot initiate outbound connections. |
| **`sg-redis-cache`**<br>*(In-Memory Plane)* | **Inbound** | `TCP 6379` | `sg-ecs-compute` | In-memory key-value cache operations and lock acquisition. |
| | **Egress** | *None* | `None` (Implicit Deny) | Total egress lockdown. Cache cannot initiate outbound connections. |
| **`sg-vpc-endpoints`**<br>*(PrivateLink ENIs)* | **Inbound** | `TCP 443` | `sg-ecs-compute` | Secure internal access to AWS management APIs. |
| | **Egress** | *None* | `None` (Implicit Deny) | Interface endpoints terminate local VPC connections. |

---

## 6. Network Access Control Lists (NACLs) & VPC Endpoints

### 6.1 Stateless Network ACL (NACL) Layer
While Security Groups provide stateful instance-level filtering, Network ACLs enforce a **stateless, subnet-boundary layer of defense** against spoofed packets, unauthorized subnet traversal, and protocol abuse.

#### A. Public Subnet NACL (`nacl-public`)

| Rule # | Direction | Protocol | Port Range | Source / Destination CIDR | Action | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **100** | Inbound | `TCP` | `80` | `0.0.0.0/0` | **ALLOW** | Allow inbound HTTP for TLS redirect. |
| **110** | Inbound | `TCP` | `443` | `0.0.0.0/0` | **ALLOW** | Allow inbound HTTPS from internet clients. |
| **120** | Inbound | `TCP` | `1024-65535` | `0.0.0.0/0` | **ALLOW** | Allow return traffic from NAT Gateway / internet. |
| **\*** | Inbound | `ALL` | `ALL` | `0.0.0.0/0` | **DENY** | Default implicit drop. |
| **100** | Outbound | `TCP` | `8000` | `10.0.2.0/23`, `10.0.4.0/23` | **ALLOW** | Forward ALB traffic to Private Compute subnets. |
| **110** | Outbound | `TCP` | `80`, `443` | `0.0.0.0/0` | **ALLOW** | NAT Gateway outbound internet routing. |
| **120** | Outbound | `TCP` | `1024-65535` | `0.0.0.0/0` | **ALLOW** | Ephemeral return traffic to public HTTP/S clients. |
| **\*** | Outbound | `ALL` | `ALL` | `0.0.0.0/0` | **DENY** | Default implicit drop. |

#### B. Private Compute Subnet NACL (`nacl-private-compute`)

| Rule # | Direction | Protocol | Port Range | Source / Destination CIDR | Action | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **100** | Inbound | `TCP` | `8000` | `10.0.0.0/24`, `10.0.1.0/24` | **ALLOW** | Inbound requests from ALB in Public subnets. |
| **110** | Inbound | `TCP` | `1024-65535` | `10.0.0.0/20` | **ALLOW** | Ephemeral return traffic from RDS, Redis & VPCEs. |
| **120** | Inbound | `TCP` | `1024-65535` | `0.0.0.0/0` | **ALLOW** | Ephemeral return traffic from NAT Gateway (Stripe). |
| **\*** | Inbound | `ALL` | `ALL` | `0.0.0.0/0` | **DENY** | Default implicit drop. |
| **100** | Outbound | `TCP` | `5432` | `10.0.6.0/24`, `10.0.7.0/24` | **ALLOW** | Outbound SQL traffic to Isolated Database subnets. |
| **110** | Outbound | `TCP` | `6379` | `10.0.6.0/24`, `10.0.7.0/24` | **ALLOW** | Outbound cache/lock traffic to Redis subnets. |
| **120** | Outbound | `TCP` | `443` | `10.0.0.0/20` | **ALLOW** | HTTPS traffic to PrivateLink VPC Interface Endpoints. |
| **130** | Outbound | `TCP` | `443` | `0.0.0.0/0` | **ALLOW** | HTTPS egress via NAT Gateway for Payment APIs. |
| **140** | Outbound | `TCP` | `1024-65535` | `10.0.0.0/24`, `10.0.1.0/24` | **ALLOW** | Ephemeral return traffic to ALB. |
| **\*** | Outbound | `ALL` | `ALL` | `0.0.0.0/0` | **DENY** | Default implicit drop. |

#### C. Isolated Database Subnet NACL (`nacl-isolated-db`)

| Rule # | Direction | Protocol | Port Range | Source / Destination CIDR | Action | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **100** | Inbound | `TCP` | `5432` | `10.0.2.0/23`, `10.0.4.0/23` | **ALLOW** | Allow PostgreSQL queries from Compute subnets only. |
| **110** | Inbound | `TCP` | `6379` | `10.0.2.0/23`, `10.0.4.0/23` | **ALLOW** | Allow Redis commands from Compute subnets only. |
| **\*** | Inbound | `ALL` | `ALL` | `0.0.0.0/0` | **DENY** | Drop all other traffic (including any internet CIDR). |
| **100** | Outbound | `TCP` | `1024-65535` | `10.0.2.0/23`, `10.0.4.0/23` | **ALLOW** | Return query response data to Compute subnets. |
| **\*** | Outbound | `ALL` | `ALL` | `0.0.0.0/0` | **DENY** | Drop all outbound traffic to internet or public tier. |

---

### 6.2 AWS VPC Endpoints (PrivateLink & Gateway Endpoints)

To uphold zero-trust security and eliminate data transfer costs, all communication between internal ECS containers and AWS management services is kept strictly inside the AWS private backbone using VPC Endpoints.

```
+----------------------------------------------------------------------------------------------------+
|                                  AWS VPC ENDPOINTS TOPOLOGY                                        |
|                                                                                                    |
|  [ ECS FARGATE COMPUTE SUBNET ]                                                                    |
|               |                                                                                    |
|               +---(S3 Gateway Endpoint: No Cost, Route Table Entry)----> [ Amazon S3 Storage ]     |
|               |                                                         • Folio WORM Vault         |
|               |                                                         • Database WAL Backups     |
|               |                                                                                    |
|               +---(AWS PrivateLink Interface Endpoints: ENIs with Private IPs in 10.0.2.0/23)       |
|                   |                                                                                |
|                   +-----> [ com.amazonaws.us-east-1.ecr.api ] ----> ECR Container Manifest Auth   |
|                   +-----> [ com.amazonaws.us-east-1.ecr.dkr ] ----> ECR Docker Image Layer Pulls  |
|                   +-----> [ com.amazonaws.us-east-1.ssm ] --------> SSM Parameter Store (Secrets)  |
|                   +-----> [ com.amazonaws.us-east-1.secretsmanager ] -> Dynamic Secret Rotation    |
|                   +-----> [ com.amazonaws.us-east-1.logs ] -------> CloudWatch Container Logs     |
|                   +-----> [ com.amazonaws.us-east-1.kms ] --------> Envelope Decryption Key Ops   |
+----------------------------------------------------------------------------------------------------+
```

#### VPC Endpoints Provisioning Matrix

| Endpoint Service Name | Type | Subnet Associations | Private DNS Enabled | Security Group Applied | Functional Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `com.amazonaws.us-east-1.s3` | **Gateway** | `subnet-priv-app-a`, `subnet-priv-app-b` | N/A (Route Table Entry) | N/A | High-throughput zero-cost S3 backup & WORM folio archival. |
| `com.amazonaws.us-east-1.ecr.api` | **Interface** | `subnet-priv-app-a`, `subnet-priv-app-b` | **Yes** | `sg-vpc-endpoints` | Container image authentication and repository metadata lookups. |
| `com.amazonaws.us-east-1.ecr.dkr` | **Interface** | `subnet-priv-app-a`, `subnet-priv-app-b` | **Yes** | `sg-vpc-endpoints` | Fast private Docker image layer retrieval during task starts. |
| `com.amazonaws.us-east-1.ssm` | **Interface** | `subnet-priv-app-a`, `subnet-priv-app-b` | **Yes** | `sg-vpc-endpoints` | Dynamic environment secret injection at ECS task launch. |
| `com.amazonaws.us-east-1.secretsmanager` | **Interface** | `subnet-priv-app-a`, `subnet-priv-app-b` | **Yes** | `sg-vpc-endpoints` | Automated database credential retrieval and rotation. |
| `com.amazonaws.us-east-1.logs` | **Interface** | `subnet-priv-app-a`, `subnet-priv-app-b` | **Yes** | `sg-vpc-endpoints` | High-frequency container stdout/stderr log transmission. |
| `com.amazonaws.us-east-1.kms` | **Interface** | `subnet-priv-app-a`, `subnet-priv-app-b` | **Yes** | `sg-vpc-endpoints` | Cryptographic decryption operations for environment secrets. |

---

## 7. VPC Flow Logs & Network Auditing Policy

### 7.1 Flow Logs Architecture & Capture Specification
All network interfaces within `vpc-hospitality-prod` are subject to continuous packet-level auditing via **AWS VPC Flow Logs**. Flow Logs capture 100% of IP traffic traversing network interfaces, providing forensic traceability for security audits and anomaly detection.

* **Log Destination:** Amazon CloudWatch Logs (`/aws/vpc/flow-logs/production`) with replica export to encrypted S3 compliance bucket (`s3://hospitality-os-security-audit-prod/vpc-flow-logs/`).
* **Traffic Filter:** `ALL` (Captures both `ACCEPT` and `REJECT` traffic).
* **Aggregation Interval:** `60 seconds` (Maximum granularity for near-real-time intrusion detection).
* **Log Retention Period:** **30 Days** in CloudWatch Logs; **7 Years** in S3 Glacier Vault for compliance retention.

```hcl
# Terraform VPC Flow Log Resource Definition
resource "aws_flow_log" "vpc_flow_log" {
  iam_role_arn             = aws_iam_role.flow_log_role.arn
  log_destination_type     = "cloud-watch-logs"
  log_destination          = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type             = "ALL"
  vpc_id                   = aws_vpc.main.id
  max_aggregation_interval = 60

  log_format = "$${version} $${account-id} $${interface-id} $${srcaddr} $${dstaddr} $${srcport} $${dstport} $${protocol} $${packets} $${bytes} $${start} $${end} $${action} $${log-status}"

  tags = {
    Name        = "hospitality-os-vpc-flow-log"
    Environment = "production"
  }
}
```

### 7.2 Security Monitoring & Athena Audit Query Library

Amazon Athena is configured to query partition-projected VPC Flow Logs stored in S3 for rapid incident response and threat hunting.

#### Query 1: Top 20 Rejected Inbound Traffic Sources (Port Scan Detection)
```sql
SELECT 
    srcaddr, 
    dstport, 
    protocol, 
    COUNT(*) AS reject_count,
    SUM(bytes) AS total_bytes
FROM hospitality_security_db.vpc_flow_logs
WHERE action = 'REJECT' 
  AND day = date_format(current_date, '%Y/%m/%d')
GROUP BY srcaddr, dstport, protocol
ORDER BY reject_count DESC
LIMIT 20;
```

#### Query 2: Anomalous Egress Sockets from Isolated Database Subnet (Breach Indicator)
```sql
SELECT 
    srcaddr, 
    dstaddr, 
    dstport, 
    action, 
    COUNT(*) AS connection_attempts
FROM hospitality_security_db.vpc_flow_logs
WHERE (srcaddr LIKE '10.0.6.%' OR srcaddr LIKE '10.0.7.%')
  AND dstaddr NOT LIKE '10.0.%'
GROUP BY srcaddr, dstaddr, dstport, action
ORDER BY connection_attempts DESC;
```
*(Expected Result: 0 rows. Any returned row triggers an immediate Sev-1 security incident).*

#### Query 3: Active Database Connection Volume to PostgreSQL (Port 5432)
```sql
SELECT 
    srcaddr, 
    COUNT(*) AS total_sessions,
    SUM(bytes) / (1024 * 1024) AS total_mb_transferred
FROM hospitality_security_db.vpc_flow_logs
WHERE dstport = 5432 
  AND action = 'ACCEPT'
  AND start >= (to_unixtime(now()) - 3600)
GROUP BY srcaddr
ORDER BY total_sessions DESC;
```

---

## 8. Network Security Verification & Pre-Flight Checklist

Before approving production traffic migration, the following automated network assertions must pass in the CI/CD pipeline:

- [ ] **Assertion 1 (Subnet Isolation):** `subnet-iso-db-a` and `subnet-iso-db-b` route tables have exactly 1 route (`10.0.0.0/20 -> local`) and zero internet gateways.
- [ ] **Assertion 2 (Security Group Chaining):** `sg-rds-postgres` ingress rule allows `TCP 5432` strictly from `sg-ecs-compute` (Zero IP CIDRs configured).
- [ ] **Assertion 3 (ALB Egress Lockdown):** `sg-alb-ingress` egress allows `TCP 8000` strictly to `sg-ecs-compute`.
- [ ] **Assertion 4 (PrivateLink Coverage):** All 6 interface VPC endpoints resolve to private IP addresses inside `10.0.2.0/23` and `10.0.4.0/23`.
- [ ] **Assertion 5 (VPC Flow Logs Active):** CloudWatch Log Group `/aws/vpc/flow-logs/production` is actively ingesting records at 60s aggregation intervals.
- [ ] **Assertion 6 (Public S3 Access Blocked):** All VPC-associated S3 buckets have `aws_s3_bucket_public_access_block` enabled with all 4 block settings set to `true`.
