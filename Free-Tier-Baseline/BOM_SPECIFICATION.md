# Infrastructure Bill of Materials (BOM) & FinOps Sizing Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Production Cloud Infrastructure Bill of Materials (BOM) & FinOps Cost Specification
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 2.0.0 (Free-Tier Production Baseline)
* **Status:** Approved / Production-Ready Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Budget Ceiling:** **< $0.50 USD / month ($0.00 USD / month net spend)**
* **Target Cloud Provider & Region:** Amazon Web Services (AWS) — Primary Region: Asia Pacific (Mumbai) `ap-south-1`
* **Classification:** Highly Confidential / Enterprise Free-Tier FinOps Baseline
* **Aligned Specifications:**
  - [`docs/Free Tier Baseline/ADR_COLLECTION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/ADR_COLLECTION.md) (Master Free-Tier ADR Decisions: ADR-001 through ADR-011)
  - [`docs/Free Tier Baseline/HLA_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/HLA_SPECIFICATION.md) (Platform-Neutral High-Level Architecture Topology)
  - [`docs/Free Tier Baseline/LLD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/LLD_SPECIFICATION.md) (Cloud Low-Level Design & Subsystem Wiring)
  - [`docs/Free Tier Baseline/NETWORK_AND_SECURITY_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/NETWORK_AND_SECURITY_SPECIFICATION.md) (Zero-Cost Lean VPC & Subnet Security Rules)
  - [`docs/Free Tier Baseline/DATABASE_AND_STORAGE_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/DATABASE_AND_STORAGE_SPECIFICATION.md) (Single-AZ RDS, Redis Container, SQLite WAL, S3)
  - [`docs/Free Tier Baseline/SECURITY_AND_COMPLIANCE_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/SECURITY_AND_COMPLIANCE_SPECIFICATION.md) (OIDC, SSM, SAQ-A, GDPR Salt-Shredding)
  - [`docs/Free Tier Baseline/CICD_AND_DEPLOYMENT_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/CICD_AND_DEPLOYMENT_SPECIFICATION.md) (GitHub Actions & ECR Automation)
  - [`docs/Enterprise Baseline/BOM_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/BOM_SPECIFICATION.md) (Enterprise Baseline Reference: $174.15/month)

---

## 1. Executive Cost Summary & Zero-Cost Baseline Reconciliation

Hospitality OS establishes a **Zero-Cost Production Infrastructure Baseline ($0.00 USD / month)** engineered strictly within the **AWS 12-Month Free Tier and Perpetual Always-Free Tier limits (< $0.50 USD / month total spend)**.

### Financial Reconciliation: Enterprise Baseline vs. Free-Tier Target

```
+==================================================================================================================+
|                                    FINANCIAL RECONCILIATION & COST REDUCTION CASCADE                             |
+==================================================================================================================+
|                                                                                                                  |
|  [ ENTERPRISE BASELINE ARCHITECTURE ]                                      [ ZERO-COST FREE-TIER ARCHITECTURE ]  |
|  • AWS ECS Fargate Compute Tasks (Dual-AZ)  : $10.61 / mo                  • Amazon EC2 t4g.micro (750h Free)    : $0.00 |
|  • AWS Application Load Balancer (ALB)      : $17.68 / mo                  • In-Container NGINX Reverse Proxy    : $0.00 |
|  • AWS WAF Layer-7 WebACL                   : $11.06 / mo                  • In-Container Rate Limiting          : $0.00 |
|  • AWS RDS PostgreSQL Multi-AZ (db.t4g.micro): $37.80 / mo                 • RDS PostgreSQL Single-AZ (750h Free): $0.00 |
|  • AWS ElastiCache Redis (cache.t4g.micro)  : $14.60 / mo                  • In-Container Redis 7.2 (128MB AOF)  : $0.00 |
|  • VPC NAT Gateway (Single-AZ)              : $32.85 / mo                  • 0 NAT Gateways (Direct Free IGW)    : $0.00 |
|  • VPC PrivateLink Endpoints (6 Endpoints)  : $42.65 / mo                  • 0 PrivateLink Endpoints             : $0.00 |
|  • AWS KMS Customer Managed Keys (CMK)      : $1.00 / mo                   • AWS Default SSE-S3 & RDS KMS        : $0.00 |
|  • AWS Secrets Manager Secrets (3 Secrets)  : $1.20 / mo                   • Host-Level .env Injection (chmod600): $0.00 |
|  • CloudWatch Metric Logs & Alarms          : $4.25 / mo                   • CloudWatch Free Tier (10 Metrics)   : $0.00 |
|  • Amazon Route 53 DNS Hosted Zone          : $0.50 / mo                   • Apex DNS Zone (Optional)            : $0.00-$0.50
|  --------------------------------------------------------                  ---------------------------------------------
|  TOTAL ENTERPRISE SPEND: $174.15 USD / month ($2,089.80/yr)                TOTAL FREE-TIER SPEND: < $0.50 USD / month    |
|                                                                            NET MONTHLY REDUCTION: 100.0% SAVINGS         |
+==================================================================================================================+
```

---

## 2. Itemized Free-Tier Bill of Materials (BOM) Matrix

All infrastructure components are provisioned strictly within AWS 12-Month Free Tier and Perpetual Always-Free Tier quotas:

| Category | Service Name | AWS Resource Identifier | Architecture & Sizing Spec | Pricing Model / Free Tier Allocation | Monthly Net Cost (USD) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Compute** | Amazon EC2 | `i-hospitality-compute-prod` | 1x `t4g.micro` (ARM64 Graviton2, 2 vCPUs, 1.0 GB RAM, 30 GB gp3 root) | **750 Hours / Month Free Tier** (12 Months) | **$0.00** |
| **Edge & Ingress**| Open-Source NGINX | `hospitality_nginx` | In-Container Alpine Reverse Proxy (Ports 80/443, ACME Let's Encrypt TLS 1.3) | **Open Source** (0 ALB / 0 WAF Fees) | **$0.00** |
| **Database** | Amazon RDS PostgreSQL | `hospitality-db-prod` | Single-AZ `db.t4g.micro` (1.0 GB RAM, 20 GB gp3 SSD, 3,000 IOPS, 125 MB/s) | **750 Hours / Month + 20 GB Free Tier** | **$0.00** |
| **Cache & Queue** | Open-Source Redis | `hospitality_redis` | In-Container Redis 7.2 Alpine (`maxmemory 128mb`, AOF disk sync) | **Open Source** (0 ElastiCache Fees) | **$0.00** |
| **Static Storage**| Amazon S3 Standard | `hospitality-web-assets-prod` | React SPA static bundles, Vite builds, tenant logos (SSE-S3 AES-256) | **5 GB / Month S3 Standard Free Tier** | **$0.00** |
| **Compliance Vault**| Amazon S3 Standard | `hospitality-financial-archive-prod`| 7-Year (2,555-Day) WORM Compliance Hold (SEC 17a-4 / European VAT) | **5 GB / Month S3 Standard Free Tier** | **$0.00** |
| **Backup Storage**| Amazon S3 Standard | `hospitality-wal-backups-prod` | Continuous WAL archive logs for Point-in-Time Recovery ($\text{RPO} \le 1.0\text{s}$) | **5 GB / Month S3 Standard Free Tier** | **$0.00** |
| **CDN & Edge** | Amazon CloudFront | `E1A2B3C4D5E6F7` | 600+ Global Anycast Edge PoPs, SigV4 Origin Access Control (OAC) | **1 TB / Month Data Transfer Out Free Perpetual** | **$0.00** |
| **Networking** | AWS Lean VPC | `vpc-hospitality-prod` | 1 Public Subnet (`10.0.1.0/24`), 2 DB Subnets (`10.0.2.0/24`, `10.0.3.0/24`) | **Free Internet Gateway** (0 NAT GW / 0 PrivateLink) | **$0.00** |
| **CI/CD Delivery**| GitHub Actions | `deploy.yml` | Hosted Linux Runner (Ubuntu Latest), multi-arch Docker Buildx ARM64 | **2,000 Minutes / Month Free Tier** | **$0.00** |
| **Registry** | Amazon ECR | `hospitality-os` | Private container image repository (3-image automated lifecycle pruning) | **500 MB / Month Free Tier** | **$0.00** |
| **Identity & Access**| AWS IAM & STS | `HospitalityGitHubDeployRole` | Passwordless OIDC federation trust policy for GitHub Actions | **Always Free** (Zero Static IAM Keys) | **$0.00** |
| **Host Management**| AWS Systems Manager | `AWS-RunShellScript` | SSM Session Manager for terminal access and container rolling updates | **Always Free** (SSH Port 22 Closed) | **$0.00** |
| **DNS Management**| Amazon Route 53 | `hostedzone-platform-prod` | 1 Public Hosted Zone for apex domain and SSL certificate validation | **$0.50 / Hosted Zone / Month** (Optional) | **$0.00 – $0.50** |
| **Telemetry** | Amazon CloudWatch | `hospitality-os-budget-alarm` | 10 Custom Metrics, 3 Alarms, 1 Billing Alarm ($0.50 threshold) | **Always Free Tier** (10 Metrics / 3 Alarms) | **$0.00** |
| **TOTALS** | **Consolidated Spend**| **100% Free-Tier Stack** | **Single Boutique Client Property Cloud Footprint** | **AWS Free Tier & Perpetual Always-Free** | **< $0.50 USD / mo** |

---

## 3. Multi-Tenant Unit Economics & Client ROI Analysis

### 3.1 Unit Cost per Completed Guest Transaction
For a boutique property processing **1,000 monthly guest room nights and restaurant dining orders**:

$$\text{Unit Cost per Transaction} = \frac{\text{Total Monthly Cloud Spend}}{\text{Total Monthly Completed Transactions}} = \frac{\$0.00\text{ USD}}{1,000} = \mathbf{\$0.0000\text{ USD / transaction}}$$

Even if the optional Amazon Route 53 apex hosted zone ($0.50/mo) is billed:

$$\text{Unit Cost with DNS} = \frac{\$0.50\text{ USD}}{1,000} = \mathbf{\$0.0005\text{ USD / transaction}} \quad (0.0006\%\text{ of an } \$85\text{ check})$$

---

### 3.2 Client Contract Profitability & Cloud COGS Analysis
For an entry-level single-property SaaS deployment contracted at **Rs. 30,000 (~$100.00 USD total contract value)**:

| Commercial Metric | Enterprise Baseline Infrastructure | Zero-Cost Free-Tier Target | Variance / Impact |
| :--- | :--- | :--- | :--- |
| **Contract Gross Revenue** | $100.00 USD | $100.00 USD | — |
| **Monthly Cloud Hosting COGS**| $174.15 USD / month | **$0.00 USD / month** | **-$174.15 / mo (Eliminated)** |
| **Hosting COGS % of Revenue** | **174.15% (Net Loss)** | **0.00% (Zero COGS)** | **+174.15% Margin Expansion** |
| **Net Gross Profit Margin** | **Negative Margin** | **100.00% Profit Margin** | **Maximum Capital Efficiency** |

---

## 4. FinOps Governance & CloudWatch Billing Guardrails

### 4.1 Automated CloudWatch Billing Alarm ($0.50 Threshold)
An automated metric alarm continuously evaluates AWS estimated charges every 6 hours. If any unexpected paid AWS service is provisioned, an automated high-priority alert is dispatched via AWS SNS:

```hcl
# ==============================================================================
# HOSPITALITY OS: CLOUDWATCH BILLING ALARM TERRAFORM HCL DEFINITION
# ==============================================================================

resource "aws_sns_topic" "billing_alerts" {
  name = "hospitality-os-free-tier-billing-alerts"
}

resource "aws_sns_topic_subscription" "devops_email" {
  topic_arn = aws_sns_topic.billing_alerts.arn
  protocol  = "email"
  endpoint  = "devops@thecodeconsortium.com"
}

resource "aws_cloudwatch_metric_alarm" "free_tier_budget_guardrail" {
  alarm_name          = "hospitality-os-free-tier-budget-breach"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600 # 6 Hours
  statistic           = "Maximum"
  threshold           = 0.50  # $0.50 USD Threshold
  alarm_description   = "CRITICAL FINOPS ALERT: Monthly AWS spend has exceeded $0.50 USD! Immediately inspect provisioned resources in ap-south-1."
  alarm_actions       = [aws_sns_topic.billing_alerts.arn]

  dimensions = {
    Currency = "USD"
  }
}
```

---

### 4.2 Host Disk Space Hygiene Automation
To prevent exceeding the 30 GB gp3 free EBS volume limit, every automated deployment executes container layer and build cache pruning:

```bash
# Automated Post-Deployment Disk Space Cleanup Command
docker system prune -af --volumes
```

---

### 4.3 12-Month Free-Tier Expiration Transition Roadmap

When the AWS 12-Month Free Tier for EC2 (`t4g.micro`) and RDS (`db.t4g.micro`) expires after year 1, the operations team executes one of two pre-planned cost-control strategies:

```
+==================================================================================================================+
|                                  12-MONTH FREE-TIER EXPIRATION TRANSITION STRATEGY                               |
+==================================================================================================================+
|                                                                                                                  |
|  STRATEGY A: 3-Year AWS Savings Plans / Reserved Instances (Retain AWS Infrastructure)                          |
|  • 1x EC2 t4g.micro 3-Year All-Upfront Reserved Instance           : ~$2.10 / month                              |
|  • 1x RDS PostgreSQL db.t4g.micro 3-Year All-Upfront Reserved Instance : ~$4.20 / month                          |
|  • Total Post-Year-1 AWS Hosting Spend                             : ~$6.30 USD / month ($75.60 / year)          |
|                                                                                                                  |
|  STRATEGY B: Migrate Container Host to Low-Cost Dedicated Cloud / OCI Always Free                                |
|  • Oracle Cloud Infrastructure (OCI Always Free) 4x OCPU / 24GB RAM : $0.00 / month (Perpetual Free)              |
|  • Hetzner / DigitalOcean Cloud VPS (1 vCPU / 1GB RAM)              : ~€3.80 – €5.00 / month                     |
|  • Total Migration Time: < 30 Minutes (100% Docker Compose & S3 API Compatible)                                  |
+==================================================================================================================+
```

---

## 5. FinOps Pre-Flight Verification Checklist

- [ ] **Assertion 1 (Zero Paid Managed Services):** Confirmed 0 NAT Gateways (`$32.85/mo` avoided), 0 VPC Endpoints (`$42.65/mo` avoided), 0 ALB (`$17.68/mo` avoided), and 0 WAF WebACLs (`$11.06/mo` avoided).
- [ ] **Assertion 2 (Compute Free-Tier Compliance):** EC2 instance is configured as `t4g.micro` ARM64 Graviton2 (750 hours/month Free Tier eligible).
- [ ] **Assertion 3 (Database Free-Tier Compliance):** RDS PostgreSQL 17 is configured as Single-AZ `db.t4g.micro` with 20 GB gp3 storage (750 hours/month Free Tier eligible).
- [ ] **Assertion 4 (ECR Quota Compliance):** ECR lifecycle policy actively limits stored images to the last 3 tagged layers (< 360 MB total disk).
- [ ] **Assertion 5 (Billing Alarm Active):** AWS CloudWatch Billing Alarm `hospitality-os-free-tier-budget-breach` is active with `$0.50 USD` threshold.
- [ ] **Assertion 6 (Net Monthly Spend):** AWS Cost Explorer forecasted spend for current billing cycle is **$0.00 USD (< $0.50 USD ceiling)**.
