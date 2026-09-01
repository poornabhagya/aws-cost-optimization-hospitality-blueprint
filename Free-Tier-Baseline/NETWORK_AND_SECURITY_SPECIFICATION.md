# Network & Security Architecture Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Production Network Topology, Subnet Sizing & Zero-Cost Security Specification
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 2.0.0 (Free-Tier Production Baseline)
* **Status:** Approved / Production-Ready Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Budget Ceiling:** **< $0.50 USD / month ($0.00 USD / month net spend)**
* **Target Cloud Provider & Region:** Amazon Web Services (AWS) — Primary Region: Asia Pacific (Mumbai) `ap-south-1`
* **Classification:** Highly Confidential / Enterprise Free-Tier Network & Security Baseline
* **Aligned Specifications:**
  - [`docs/Free Tier Baseline/ADR_COLLECTION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/ADR_COLLECTION.md) (Master Free-Tier ADR Decisions: ADR-001 through ADR-011)
  - [`docs/Free Tier Baseline/HLA_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/HLA_SPECIFICATION.md) (Platform-Neutral High-Level Architecture Topology)
  - [`docs/Enterprise Baseline/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/BRD_SPECIFICATION.md) (Domain Rules, 72h POS Autonomy, Append-Only GL)
  - [`docs/Enterprise Baseline/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/NFR_SPECIFICATION.md) ($p_{95} \le 120\text{ ms}$, TLS 1.3, Rate Limits, 30 DB Sockets)
  - [`docs/Enterprise Baseline/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/CAPACITY_SIZING.md) (0.50 vCPU / 1GB RAM Compute, 512MB Redis, 20GB gp3 PostgreSQL)

---

## 1. Executive Summary & Zero-Cost Security Philosophy

Hospitality OS enforces a **Defense-in-Depth, Zero-Trust Security Model** tailored specifically to operate within the **AWS 12-Month Free Tier and Perpetual Always-Free Tier limits (< $0.50 USD / month total spend)**.

### Core Security & Networking Tenets
1. **Zero-Cost Lean VPC Topology ($0.00 / month):** Eliminates expensive enterprise managed network services (saving over **$75.50/month** by provisioning **0 NAT Gateways** and **0 VPC PrivateLink Interface Endpoints**).
2. **Strict Micro-Segmentation via AWS Security Groups:** The compute host resides in a public subnet to allow direct free internet egress via an Internet Gateway (IGW), while the PostgreSQL database resides in a completely non-routable private DB subnet group with zero public internet ingress or egress.
3. **In-Container Edge Ingress & Rate Limiting:** Offloads Layer 7 reverse proxying, TLS 1.3 termination (Let's Encrypt / ACME auto-renewals), and leaky-bucket rate limiting to an In-Container NGINX proxy, eliminating the $28.74/month cost of AWS ALB and AWS WAF.
4. **Zero Static Credentials in CI/CD & Production:** All delivery pipelines authenticate dynamically via AWS IAM OpenID Connect (OIDC) temporary STS tokens; remote EC2 administration is conducted via AWS Systems Manager (SSM) Session Manager without exposed SSH keys.
5. **PCI-DSS SAQ-A & GDPR Compliance:** Direct browser-to-Stripe tokenization isolates the host from credit card PAN/CVV exposure; cryptographic salt-shredding guarantees GDPR Article 17 deletion compliance while preserving immutable accounting ledgers.

---

## 2. Zero-Cost Lean VPC Topology & Subnet Allocation Plan

### 2.1 Addressing Scheme Overview
The platform allocates a dedicated `/16` IPv4 CIDR block (`10.0.0.0/16`), providing **65,536 total IPv4 addresses**. This provides vast address space for container bridges, database subnet groups, and future fleet VPC peering while maintaining simple routing tables.

```
+==================================================================================================================+
|                                    HOSPITALITY OS ZERO-COST LEAN VPC: 10.0.0.0/16                                |
|                                            (65,536 Total IPv4 Addresses)                                         |
+==================================================================================================================+
|                                                                                                                  |
|  [ PUBLIC SUBNET (10.0.1.0/24 - 256 IPs / 251 Usable) — Availability Zone: ap-south-1a ]                        |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | Attached to: Internet Gateway (igw-hospitality-prod) | Route: 0.0.0.0/0 -> igw-hospitality-prod          |    |
|  |                                                                                                          |    |
|  |   [ Amazon EC2 Instance: t4g.micro (ARM64 Graviton2 / 1.0 GB RAM) — IP: 10.0.1.50 ]                      |    |
|  |   • Docker Compose Multi-Container Stack (Nginx Ingress + Django API + Celery Worker + Redis 7.2)        |    |
|  |   • Security Group: sg_hospitality_ec2 (Inbound: TCP 80, 443 | Outbound: ALL via IGW)                     |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|                                                     |                                                            |
|                                                     | Private SQL Traffic Only (TCP Port 5432)                   |
|                                                     v                                                            |
|  [ PRIVATE DATABASE SUB-TIER (RDS DB Subnet Group: dbsubnet-hospitality-prod) ]                                 |
|  +----------------------------------------------------+     +----------------------------------------------------+
|  | Private DB Subnet A (10.0.2.0/24 - ap-south-1a)    |     | Private DB Subnet B (10.0.3.0/24 - ap-south-1b)    |
|  | (256 IPs / 251 Usable)                             |     | (256 IPs / 251 Usable - RDS Subnet Group Prereq)   |
|  |                                                    |     |                                                    |
|  | • Amazon RDS PostgreSQL 17 Single-AZ (10.0.2.100)   |     | • (Standby Placement Space for Future Scaling)     |
|  | • Security Group: sg_hospitality_rds               |     | • Security Group: sg_hospitality_rds               |
|  | • PubliclyAccessible = false                       |     | • PubliclyAccessible = false                       |
|  | • Route Table: Local Only (10.0.0.0/16 -> local)   |     | • Route Table: Local Only (10.0.0.0/16 -> local)   |
|  | • ZERO IGW / ZERO NAT GATEWAY (100% Isolated)      |     | • ZERO IGW / ZERO NAT GATEWAY (100% Isolated)      |
|  +----------------------------------------------------+     +----------------------------------------------------+
|                                                                                                                  |
|  [ NETWORKING COST SUMMARY ]                                                                                     |
|  • Internet Gateway (IGW) : $0.00 / month (AWS Free Attachment)                                                  |
|  • NAT Gateways           : $0.00 / month (0 Provisioned — Saves $32.85/mo)                                      |
|  • VPC Interface Endpoints: $0.00 / month (0 Provisioned — Saves $42.65/mo)                                      |
|  • TOTAL MONTHLY NETWORK SPEND: $0.00 USD / month                                                                |
+==================================================================================================================+
```

---

### 2.2 Subnet Allocation Master Table

Every subnet provisioned in AWS reserves the first 4 and last 1 IP addresses (Network, VPC Router, AmazonProvidedDNS, Reserved, and Broadcast):

| Subnet Identifier | Availability Zone | IPv4 CIDR Block | Total IPs | Usable IPs | Tier Classification | Hosted Workloads & Security Association |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`subnet-public-a`** | `ap-south-1a` | `10.0.1.0/24` | 256 | 251 | **Tier 2/3: Public Compute** | Amazon EC2 `t4g.micro` container host (`sg_hospitality_ec2`), Internet Gateway attached. |
| **`subnet-private-db-a`** | `ap-south-1a` | `10.0.2.0/24` | 256 | 251 | **Tier 5: Isolated Database**| Amazon RDS PostgreSQL 17 primary instance (`sg_hospitality_rds`). Non-routable. |
| **`subnet-private-db-b`** | `ap-south-1b` | `10.0.3.0/24` | 256 | 251 | **Tier 5: Isolated Database**| Secondary AZ subnet fulfilling RDS Multi-AZ / DB Subnet Group requirements. Non-routable. |
| *Reserved (Future)* | Multi-AZ | `10.0.4.0/22` | 1,024 | 1,019 | **Unallocated Space** | Reserved for multi-property tenant fleet scaling or disaster recovery replicas. |

---

### 2.3 Route Table Master Configuration

```
+----------------------------------------------------------------------------------------------------+
|                                    LEAN VPC ROUTE TABLE CONFIGURATION                              |
|                                                                                                    |
|  [ PUBLIC ROUTE TABLE: rtb_hospitality_public ]                                                    |
|  • 10.0.0.0/16 --------> local (VPC Inter-Subnet Communication)                                    |
|  • 0.0.0.0/0 -----------> igw-hospitality-prod (Direct Ingress/Egress via Internet Gateway)       |
|  • Associated Subnets: subnet-public-a (10.0.1.0/24)                                                |
|                                                                                                    |
|  [ ISOLATED DATABASE ROUTE TABLE: rtb_hospitality_isolated_db ]                                    |
|  • 10.0.0.0/16 --------> local (VPC Inter-Subnet Communication Only)                                |
|  • 0.0.0.0/0 -----------> NO ROUTE (Blackhole / Strict Isolation / Zero External Egress)           |
|  • Associated Subnets: subnet-private-db-a (10.0.2.0/24), subnet-private-db-b (10.0.3.0/24)        |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. AWS Security Groups Master Defense Matrix (Zero-Trust)

AWS Security Groups operate as stateful virtual firewalls at the Elastic Network Interface (ENI) boundary. All rules adhere to least-privilege access and explicit security group chaining.

```
+==================================================================================================================+
|                                    SECURITY GROUP CHAINING & BOUNDARY TOPOLOGY                                   |
+==================================================================================================================+
|                                                                                                                  |
|  [ INCOMING INTERNET TRAFFIC ]                                                                                   |
|               |                                                                                                  |
|               | HTTPS (TCP Port 443) / HTTP (TCP Port 80)                                                        |
|               v                                                                                                  |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | SECURITY GROUP: sg_hospitality_ec2 (Amazon EC2 Container Host)                                           |    |
|  | • Inbound Rules:                                                                                         |    |
|  |     - TCP Port 80  <- 0.0.0.0/0 (HTTP: Automated Let's Encrypt ACME Challenge & 301 HTTPS Redirect)     |    |
|  |     - TCP Port 443 <- 0.0.0.0/0 (HTTPS: TLS 1.3 Client & POS Traffic)                                   |    |
|  |     - TCP Port 22  <- CLOSED BY DEFAULT (Zero SSH Exposure; Admin access via AWS SSM Session Manager)   |    |
|  | • Outbound Rules:                                                                                        |    |
|  |     - ALL Traffic  -> 0.0.0.0/0 (Free outbound internet via IGW for OS updates & Stripe Payment API)     |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|                                                     |                                                            |
|                                                     | SQL Queries (TCP Port 5432)                                |
|                                                     | Restricted strictly to sg_hospitality_ec2 Security Group ID|
|                                                     v                                                            |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | SECURITY GROUP: sg_hospitality_rds (Amazon RDS PostgreSQL 17 Database)                                   |    |
|  | • Inbound Rules:                                                                                         |    |
|  |     - TCP Port 5432 <- sg_hospitality_ec2 ID ONLY (Zero IP CIDR references; 100% Private Access)         |    |
|  | • Outbound Rules:                                                                                        |    |
|  |     - NONE (Implicit Deny: Database cannot initiate outbound connections)                                |    |
|  +----------------------------------------------------------------------------------------------------------+    |
+==================================================================================================================+
```

### 3.1 Ingress & Egress Security Group Master Table

| Security Group ID & Name | Direction | Protocol & Port | Source / Destination | Security Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **`sg_hospitality_ec2`**<br>*(EC2 Container Host)* | **Inbound** | `TCP 80` | `0.0.0.0/0` (IPv4) & `::/0` (IPv6) | Inbound ACME HTTP-01 Let's Encrypt challenge & 301 redirect to HTTPS. |
| | **Inbound** | `TCP 443` | `0.0.0.0/0` (IPv4) & `::/0` (IPv6) | Public HTTPS ingress for web guests, front desk PMS, and POS sync terminals. |
| | **Inbound** | `TCP 22` | **NONE (Disabled)** | **SSH Port 22 closed.** Remote management conducted via IAM-authenticated SSM. |
| | **Outbound** | `ALL Traffic` | `0.0.0.0/0` (via IGW) | Outbound HTTPS for OS security patches, Docker base pulls, and Stripe API calls. |
| **`sg_hospitality_rds`**<br>*(RDS PostgreSQL 17)* | **Inbound** | `TCP 5432` | `sg_hospitality_ec2` ID | ACID SQL transactional queries permitted exclusively from the EC2 host. |
| | **Outbound** | *None* | `None` (Implicit Deny) | Total egress lockdown. Database cannot initiate outbound network sockets. |

---

## 4. Edge Ingress Security, Rate Limiting & NGINX Hardening

The frontmost entrypoint is an in-container **NGINX 1.26 Alpine** reverse proxy enforcing TLS 1.3 cryptographic termination, security headers, and leaky-bucket rate limiting.

### 4.1 Production `nginx.conf` Hardening Specification
```nginx
# ==============================================================================
# HOSPITALITY OS: INGRESS REVERSE PROXY & RATE LIMITING SPECIFICATION
# ==============================================================================
user nginx;
worker_processes auto;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Performance & Socket Tuning
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # Leaky-Bucket Rate Limiting Zones (NFR Specification Alignment)
    limit_req_zone $binary_remote_addr zone=booking_limit:10m rate=30r/m; # 30 req/min for booking engine
    limit_req_zone $binary_remote_addr zone=pos_limit:10m     rate=120r/m; # 120 req/min for POS sync
    limit_req_zone $binary_remote_addr zone=pms_limit:10m     rate=60r/m;  # 60 req/min for front desk PMS
    limit_req_status 429;

    # Compression Tuning (BOM Optimization)
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # HTTP to HTTPS Automated 301 Redirect
    server {
        listen 80;
        listen [::]:80;
        server_name api.platform.com;

        # ACME Let's Encrypt Challenge Resolver
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    # Production HTTPS Server (TLS 1.3 Termination)
    server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;
        server_name api.platform.com;

        # SSL Certificates (Managed via Certbot Sidecar)
        ssl_certificate /etc/letsencrypt/live/api.platform.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/api.platform.com/privkey.pem;

        # Cryptographic Ciphers (NFR TLS 1.3 Policy)
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305';
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 1d;
        ssl_session_tickets off;

        # Enterprise Defense-in-Depth Security Headers
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://js.stripe.com; frame-src https://js.stripe.com; connect-src 'self' https://api.stripe.com;" always;

        # Direct Web Booking Engine API (Rate Limit: 30 req/min, Burst: 10)
        location /api/v1/booking/ {
            limit_req zone=booking_limit burst=10 nodelay;
            proxy_pass http://web:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }

        # Point-of-Sale Terminal Synchronization (Rate Limit: 120 req/min, Burst: 30)
        location /api/v1/pos/ {
            limit_req zone=pos_limit burst=30 nodelay;
            proxy_pass http://web:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }

        # Front Desk Property Management System (Rate Limit: 60 req/min, Burst: 15)
        location /api/v1/pms/ {
            limit_req zone=pms_limit burst=15 nodelay;
            proxy_pass http://web:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }

        # Default Proxy Routing to Gunicorn Web API
        location / {
            proxy_pass http://web:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }
    }
}
```

---

## 5. Secrets Management & Identity Governance

### 5.1 Passwordless GitHub Actions CI/CD (OIDC Federation)
Deployments authenticate dynamically via AWS Security Token Service (STS) using OpenID Connect (OIDC), eliminating static `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` credentials:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowGitHubActionsOidcFederation",
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

---

### 5.2 EC2 IAM Instance Profile (`HospitalityEc2InstanceRole`)
The EC2 host is assigned an IAM Instance Profile granting strictly scoped permissions:
1. `AmazonSSMManagedInstanceCore`: Enables AWS Systems Manager Session Manager for passwordless, audited terminal shell access without exposing SSH port 22.
2. `AmazonEC2ContainerRegistryReadOnly`: Allows the Docker daemon to authenticate and pull private container image layers from Amazon ECR (500 MB Free Tier).

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSsmSessionManagement",
      "Effect": "Allow",
      "Action": [
        "ssm:DescribeAssociation",
        "ssm:GetDeployablePatchSnapshotForInstance",
        "ssm:GetDocument",
        "ssm:GetManifest",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:ListAssociations",
        "ssm:ListInstanceAssociations",
        "ssm:PutInventory",
        "ssm:PutComplianceItems",
        "ssm:PutConfigurePackageResult",
        "ssm:UpdateAssociationStatus",
        "ssm:UpdateInstanceAssociationStatus",
        "ssm:UpdateInstanceInformation",
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowEcrImagePull",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
```

---

### 5.3 Host-Level Secret Injection Architecture
To eliminate the $1.00/mo KMS CMK and $0.40/secret/mo AWS Secrets Manager charges:
1. Production environment secrets are stored encrypted inside **GitHub Actions Repository Secrets**.
2. During the deployment step, secrets are injected into `/opt/hospitality-os/.env.production` on the EC2 host via AWS SSM Session Manager.
3. The `.env.production` file is secured with strict Linux file permissions (`chmod 600`, owned by `root:root`).
4. Docker Compose ingests `.env.production` at container runtime, passing environment variables into memory without writing credentials to container images or Git.

---

## 6. Data Protection, Payment Isolation & Regulatory Compliance

### 6.1 Payment Security (PCI-DSS SAQ-A Compliance)
Hospitality OS achieves **PCI-DSS SAQ-A Compliance** (the lowest compliance scope) by completely offloading cardholder data handling to Stripe:

```
+----------------------------------------------------------------------------------------------------+
|                                    PCI-DSS SAQ-A PAYMENT ISOLATION FLOW                            |
|                                                                                                    |
|  [ Guest Web Browser / POS Touchscreen ]                                                           |
|       |                                                                                            |
|       | 1. Directly loads Stripe Elements iframe (Hosted on Stripe CDN)                            |
|       v                                                                                            |
|  [ Stripe Secure Tokenization Vault ]                                                              |
|       |                                                                                            |
|       | 2. Validates Credit Card PAN & CVV; Returns Token: tok_1P987... / pm_987...                |
|       v                                                                                            |
|  [ Hospitality OS API (EC2 Host: Nginx -> Django) ]                                                |
|       |                                                                                            |
|       | 3. Submits payment token to Stripe API: stripe.PaymentIntent.create(payment_method="pm_...")|
|       v                                                                                            |
|  [ Amazon RDS PostgreSQL 17 Database ]                                                             |
|  • Stores ONLY: Stripe Charge ID (ch_123), Last 4 Digits ("4242"), Card Brand ("Visa").           |
|  • RAW CARD NUMBERS (PAN), CVVS, AND PIN DATA NEVER TOUCH EC2 MEMORY OR DATABASE TABLES.           |
+----------------------------------------------------------------------------------------------------+
```

---

### 6.2 GDPR Data Privacy & Append-Only Accounting Reconciliation
* **Conflict:** GDPR Article 17 mandates deleting personal data upon request, while tax laws mandate retaining financial records for 7 years.
* **Resolution via Cryptographic Salt-Shredding:**
  - Each guest profile has a unique cryptographic salt key (`kms_salt_gst_123`).
  - Upon an approved GDPR erasure request, the salt key is destroyed, and PII columns in `GuestProfile` are overwritten with `ANONYMIZED_GDPR`.
  - Double-entry General Ledger journal entries reference the opaque `guest_id`, preserving 100% financial balancing without retaining identifying personal information.

---

## 7. Security Pre-Flight Verification Checklist

Before approving production traffic migration, the SecOps engineer must execute and verify the following assertions:

- [ ] **Assertion 1 (Zero Paid Network Services):** AWS CLI confirms 0 NAT Gateways (`aws ec2 describe-nat-gateways`) and 0 VPC Endpoints (`aws ec2 describe-vpc-endpoints`) provisioned in `ap-south-1`.
- [ ] **Assertion 2 (SSH Port 22 Closed):** Port scan (`nmap -p 22 <ec2-public-ip>`) confirms port 22 is closed / filtered.
- [ ] **Assertion 3 (Database Isolation):** `sg_hospitality_rds` allows `TCP 5432` strictly from `sg_hospitality_ec2`; RDS parameter `PubliclyAccessible` is `false`.
- [ ] **Assertion 4 (TLS 1.3 Active):** SSL Labs / `testssl.sh` confirms NGINX serves valid Let's Encrypt certificate with TLS 1.3/1.2 only.
- [ ] **Assertion 5 (Rate Limiting Verification):** Synthetic burst requests ($> 30\text{ req/min}$) to `/api/v1/booking/` return `HTTP 429 Too Many Requests`.
- [ ] **Assertion 6 (OIDC Active):** GitHub repository settings contain 0 static AWS Access Keys; deployments authenticate via OIDC STS role assumption.
- [ ] **Assertion 7 (Billing Alarm Active):** CloudWatch Billing Alarm `hospitality-os-free-tier-budget-breach` is active with threshold set to `$0.50 USD`.
