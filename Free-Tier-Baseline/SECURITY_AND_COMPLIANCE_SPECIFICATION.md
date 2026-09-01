# Security & Regulatory Compliance Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Production Security Architecture, IAM Governance, Cryptography & Regulatory Compliance Specification
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 2.0.0 (Free-Tier Production Baseline)
* **Status:** Approved / Production-Ready Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Budget Ceiling:** **< $0.50 USD / month ($0.00 USD / month net spend)**
* **Target Cloud Provider & Region:** Amazon Web Services (AWS) — Primary Region: Asia Pacific (Mumbai) `ap-south-1`
* **Classification:** Highly Confidential / Enterprise Free-Tier Security & Compliance Baseline
* **Aligned Specifications:**
  - [`docs/Free Tier Baseline/ADR_COLLECTION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/ADR_COLLECTION.md) (Master Free-Tier ADR Decisions: ADR-001 through ADR-011)
  - [`docs/Free Tier Baseline/HLA_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/HLA_SPECIFICATION.md) (Platform-Neutral High-Level Architecture Topology)
  - [`docs/Free Tier Baseline/NETWORK_AND_SECURITY_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/NETWORK_AND_SECURITY_SPECIFICATION.md) (Zero-Cost Lean VPC & Subnet Security Rules)
  - [`docs/Free Tier Baseline/DATABASE_AND_STORAGE_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/DATABASE_AND_STORAGE_SPECIFICATION.md) (Free-Tier PostgreSQL, Redis, and S3 Storage Architecture)
  - [`docs/Enterprise Baseline/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/BRD_SPECIFICATION.md) (PCI-DSS Tokenization, GDPR Anonymization, 7-Year Tax Compliance)
  - [`docs/Enterprise Baseline/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/NFR_SPECIFICATION.md) (TLS 1.3, Rate Limits: 30/60/120 req/min, Zero Static IAM Keys, Zero-Trust ZTNA)

---

## 1. Executive Summary & Zero-Cost Security Philosophy

Hospitality OS enforces a **Defense-in-Depth, Zero-Trust Security Architecture** engineered strictly within the **AWS 12-Month Free Tier and Perpetual Always-Free Tier limits (< $0.50 USD / month total spend)**.

### Core Security Tenets & Free-Tier Cost Mitigations
1. **Zero-Cost Edge Ingress Defense (In-Container NGINX):** Eliminates the **$28.74/month** cost of AWS ALB and AWS WAF by deploying an In-Container NGINX reverse proxy with automated Let's Encrypt (Certbot) TLS 1.3 termination, leaky-bucket rate limiting (30/60/120 req/min), and strict HTTP security headers (HSTS, CSP, X-Frame-Options).
2. **Passwordless IAM Governance (OIDC & SSM):** Eliminates static, long-lived AWS IAM access keys across the entire development lifecycle. CI/CD pipelines authenticate via AWS IAM OpenID Connect (OIDC) federated temporary tokens; EC2 host administration is conducted via AWS Systems Manager (SSM) Session Manager without exposed SSH port 22.
3. **Zero-Cost Secret Management:** Ingests production environment variables securely at container runtime via host-level `.env.production` files (`chmod 600`) deployed through GitHub Actions Secrets, eliminating AWS Secrets Manager ($0.40/secret/mo) and KMS Customer Managed Keys ($1.00/mo).
4. **PCI-DSS SAQ-A Payment Isolation:** Complete cardholder data isolation via Stripe Elements. Zero raw Primary Account Numbers (PAN), CVVs, or PINs ever touch EC2 compute memory or PostgreSQL database tables.
5. **GDPR Salt-Shredding & Accounting Reconciliation:** Cryptographic salt-shredding deletes guest identifying personal data upon request while preserving immutable append-only General Ledger records.
6. **7-Year WORM Compliance Archival (Amazon S3):** Leverages S3 Object Lock in `COMPLIANCE` mode with default Amazon S3 Server-Side Encryption (SSE-S3), enforcing a 2,555-day immutable retention period under SEC 17a-4 and European VAT fiscal regulations.

```
+==================================================================================================================+
|                                  HOSPITALITY OS DEFENSE-IN-DEPTH SECURITY ARCHITECTURE                           |
+==================================================================================================================+
|                                                                                                                  |
|  [ LAYER 1: CLIENT EDGE & INGRESS SECURITY ]                                                                    |
|    • Public Guests / POS Terminals -> HTTPS TLS 1.3 Termination (ACME / Let's Encrypt Auto-Renewal)              |
|    • In-Container NGINX Leaky-Bucket Rate Limiting (Booking: 30 r/m | POS: 120 r/m | PMS: 60 r/m)                 |
|    • HTTP Security Headers: HSTS (63072000s), CSP (Stripe Only), X-Frame-Options DENY, X-Content-Type nosniff   |
|                                                                                                                  |
|  [ LAYER 2: NETWORK MICRO-SEGMENTATION & ACCESS CONTROL ]                                                       |
|    • Public Subnet: sg_hospitality_ec2 (Inbound: TCP 80, 443 | Outbound: ALL via Free Internet Gateway)          |
|    • Private Subnet: sg_hospitality_rds (Inbound: TCP 5432 strictly from sg_hospitality_ec2 ID | Outbound: NONE)     |
|    • Zero Public Exposure for Database | SSH Port 22 Closed (Admin via IAM-Authenticated SSM Session Manager)   |
|                                                                                                                  |
|  [ LAYER 3: IDENTITY, SECRETS & CI/CD GOVERNANCE ]                                                              |
|    • GitHub Actions CI/CD: Dynamic AWS IAM OIDC STS Token Authentication (Zero Static AWS IAM Keys)              |
|    • EC2 Instance Profile: HospitalityEc2InstanceRole (SSM Session Manager + ECR Image Pull Permissions)         |
|    • Host-Level Secret Injection: chmod 600 .env.production (Zero Secrets Manager / Zero Paid KMS CMK Spend)    |
|                                                                                                                  |
|  [ LAYER 4: DATA ENCRYPTION & COMPLIANCE VAULT ]                                                                |
|    • Encryption in Transit: TLS 1.3 / 1.2 with ECDHE-ECDSA/RSA-AES128-GCM-SHA256 Ciphers                        |
|    • Encryption at Rest: Default AWS Managed Encryption (SSE-S3 on S3 Buckets & AWS Managed Key on RDS gp3)    |
|    • 7-Year WORM Vault: S3 Object Lock in COMPLIANCE Mode (2,555 Days Retention - SEC 17a-4 / European VAT)     |
|    • Payment Isolation: PCI-DSS SAQ-A Tokenization via Stripe Elements (Zero Cardholder Data on EC2/RDS)        |
|    • Privacy: GDPR Article 17 Cryptographic Salt-Shredding with Append-Only GL Preservation                     |
|                                                                                                                  |
|  [ LAYER 5: INCIDENT GOVERNANCE & TELEMETRY GUARDRAILS ]                                                        |
|    • AWS CloudWatch Free Tier Billing Alarm ($0.50 Threshold) -> Automated Email/SNS Alert                      |
|    • Automated Container Quarantine Runbook via AWS SSM Session Manager                                         |
+==================================================================================================================+
```

---

## 2. IAM Governance & Passwordless Identity Architecture

### 2.1 GitHub Actions CI/CD OIDC Trust Policy
To prevent credential theft and eliminate static access keys, GitHub Actions authenticates dynamically via AWS Security Token Service (STS) using OpenID Connect:

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

#### GitHub Actions Deployment Role Permissions (`HospitalityGitHubDeployRole`)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEcrImageManagement",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "arn:aws:ecr:ap-south-1:123456789012:repository/hospitality-os"
    },
    {
      "Sid": "AllowSsmDeploymentTrigger",
      "Effect": "Allow",
      "Action": [
        "ssm:SendCommand",
        "ssm:GetCommandInvocation"
      ],
      "Resource": [
        "arn:aws:ecr:ap-south-1:123456789012:instance/*",
        "arn:aws:ssm:ap-south-1:*:document/AWS-RunShellScript"
      ]
    },
    {
      "Sid": "AllowS3SpaSync",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::hospitality-web-assets-prod",
        "arn:aws:s3:::hospitality-web-assets-prod/*"
      ]
    },
    {
      "Sid": "AllowCloudFrontInvalidation",
      "Effect": "Allow",
      "Action": "cloudfront:CreateInvalidation",
      "Resource": "*"
    }
  ]
}
```

---

### 2.2 EC2 IAM Instance Profile (`HospitalityEc2InstanceRole`)
The EC2 container host operates without static access keys, utilizing an IAM Instance Profile:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSsmManagedInstanceCore",
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
      "Sid": "AllowEcrImagePullOnly",
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

## 3. Zero-Cost Cryptographic Architecture

### 3.1 Cryptography at Rest ($0.00 / Month)
1. **Amazon S3 Buckets:** Default Amazon S3 Server-Side Encryption (SSE-S3 with AES-256) is enforced on all 3 buckets (`hospitality-web-assets-prod`, `hospitality-financial-archive-prod`, `hospitality-wal-backups-prod`). This eliminates the $1.00/month AWS KMS Customer Managed Key fee while satisfying enterprise encryption mandates.
2. **AWS RDS PostgreSQL 17:** Encrypted at rest using the AWS Default Managed RDS KMS Key (`aws/rds`), providing hardware-accelerated AES-256 block encryption for the 20 GB gp3 root storage volume at zero additional cost.
3. **Local POS SQLite Databases:** Database files are protected via operating system disk-level encryption (BitLocker / LUKS) on the physical terminal hardware.

---

### 3.2 Cryptography in Transit (TLS 1.3 Protocol)
All network communications terminate under strict TLS 1.3 / TLS 1.2 with forward secrecy:
* **Approved Protocols:** `TLSv1.3`, `TLSv1.2`
* **Disallowed Protocols:** `SSLv3`, `TLSv1.0`, `TLSv1.1` (Strictly Blocked)
* **Approved Cipher Suites:**
  - `ECDHE-ECDSA-AES128-GCM-SHA256`
  - `ECDHE-RSA-AES128-GCM-SHA256`
  - `ECDHE-ECDSA-AES256-GCM-SHA384`
  - `ECDHE-RSA-AES256-GCM-SHA384`
  - `ECDHE-ECDSA-CHACHA20-POLY1305`
  - `ECDHE-RSA-CHACHA20-POLY1305`

---

## 4. Payment Security & PCI-DSS SAQ-A Compliance

Hospitality OS is architected to qualify for **PCI-DSS SAQ-A (Self-Assessment Questionnaire A)**, the lowest compliance tier:

```
+========================================================================================================================+
|                                    PCI-DSS SAQ-A PAYMENT TOKENIZATION FLOW                                             |
+========================================================================================================================+
|                                                                                                                        |
|  [ GUEST WEB / POS CLIENT ]          [ STRIPE ELEMENTS VAULT ]          [ NGINX / DJANGO API ]        [ POSTGRESQL 17 ]|
|             |                                   |                                |                            |        |
|  1. Guest fills card details in                 |                                |                            |        |
|     Stripe Elements iframe (Hosted by Stripe)   |                                |                            |        |
|             |---------------------------------->|                                |                            |        |
|             |                                   | 2. Validates PAN, Expiry, CVV  |                            |        |
|             |                                   |    Generates Single-Use Token: |                            |        |
|             |                                   |    `pm_1P9876543210abcdef`     |                            |        |
|             |<----------------------------------|                                |                            |        |
|             |                                                                    |                            |        |
|  3. Client submits Token to Hospitality API:                                     |                            |        |
|     POST /api/v1/booking/payments/settle (payment_method_id: "pm_1P987...") ---->|                            |        |
|             |                                   |                                | 4. Executes Charge:        |        |
|             |                                   |<-------------------------------|    stripe.PaymentIntent.   |        |
|             |                                   |                                |    create(pm="pm_1P987")   |        |
|             |                                   |------------------------------->|                            |        |
|             |                                   | 5. Returns Charge Metadata:    |                            |        |
|             |                                   |    { id: "ch_99", brand: "Visa", last4: "4242", status: "succeeded" }|
|             |                                   |                                |                            |        |
|             |                                   |                                | 6. Stores Metadata: ------>|        |
|             |                                   |                                |    (Cardholder Name,       |        |
|             |                                   |                                |     Last4, Brand, ChgID)   |        |
|             |                                   |                                |    ZERO PAN / ZERO CVV     |        |
|             |<-------------------------------------------------------------------| Return 200 OK (Confirmed)   |        |
+========================================================================================================================+
```

### PCI-DSS Security Assertions
1. **Zero Cardholder Data Storage:** Credit card Primary Account Numbers (PAN), CVVs, and magnetic stripe data are never transmitted to, processed by, or stored within the EC2 instance or PostgreSQL database.
2. **CSP Script Restriction:** NGINX Content Security Policy strictly permits JavaScript execution only from `https://js.stripe.com`, preventing malicious client-side skimming scripts (Magecart attacks).

---

## 5. GDPR Data Privacy & Append-Only Financial Reconciliation

### 5.1 The Regulatory Conflict
* **GDPR Article 17 (Right to Erasure):** Mandates that guest personally identifiable information (PII) must be erased upon user request.
* **Tax & Fiscal Accounting Laws (SEC 17a-4 / European VAT):** Mandate that financial journal entries and transaction folios must be preserved immutably for 7 years.

---

### 5.2 Resolution via Cryptographic Salt-Shredding
Hospitality OS resolves this conflict through deterministic **Cryptographic Salt-Shredding**:

```
+========================================================================================================================+
|                                    GDPR CRYPTOGRAPHIC SALT-SHREDDING SEQUENCE                                          |
+========================================================================================================================+
|                                                                                                                        |
|  1. Active Guest Profile:                                                                                              |
|     • guest_id: "gst_uuid_8877"                                                                                        |
|     • salt_key: "k_sec_99a8b7c6..." (Stored in encrypted salt vault)                                                   |
|     • anonymized_id: SHA256("gst_uuid_8877" + "k_sec_99a8b7c6...") = "anon_77f6a2b1..."                             |
|     • PII Fields: { first_name: "John", last_name: "Doe", email: "john@example.com", phone: "+123456789" }            |
|                                                                                                                        |
|  2. Append-Only General Ledger Entry:                                                                                  |
|     • Journal Entry 1042: Debit Guest Ledger ($250.00), Credit Room Revenue ($250.00)                                  |
|     • Linked Account Reference: "anon_77f6a2b1..." (Opaque Hash ID)                                                    |
|                                                                                                                        |
|  3. GDPR Erasure Request Executed (POST /api/v1/guests/gst_uuid_8877/gdpr_erase):                                      |
|     a. Overwrite PII in GuestProfile:                                                                                  |
|        first_name = "ANONYMIZED_GDPR", last_name = "ANONYMIZED_GDPR", email = "erased@gdpr.internal"                  |
|     b. DESTROY & SHRED salt_key "k_sec_99a8b7c6...".                                                                   |
|                                                                                                                        |
|  4. Outcome:                                                                                                           |
|     • Guest PII is mathematically irrecoverable (100% GDPR Article 17 Compliant).                                      |
|     • General Ledger Entry 1042 remains fully balanced and intact (100% Tax Compliant).                               |
+========================================================================================================================+
```

---

## 6. Incident Response & Free-Tier Governance Runbook

### 6.1 AWS Free-Tier CloudWatch Billing Alarm ($0.50 Threshold)
To prevent unexpected cloud expenditures, an automated CloudWatch metric alarm monitors estimated AWS billing charges every 6 hours:

```hcl
# Terraform HCL Blueprint for Free-Tier Billing Guardrail
resource "aws_cloudwatch_metric_alarm" "billing_alarm_free_tier" {
  alarm_name          = "hospitality-os-free-tier-budget-breach"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600 # 6 Hours
  statistic           = "Maximum"
  threshold           = 0.50
  alarm_description   = "CRITICAL ALERT: Monthly AWS cloud spend has exceeded $0.50 USD! Inspect active resources immediately."
  alarm_actions       = [aws_sns_topic.billing_alerts.arn]

  dimensions = {
    Currency = "USD"
  }
}
```

---

### 6.2 Sev-1 Host Compromise Quarantine Runbook
In the event of suspected container tampering or unauthorized access, the DevOps engineer executes host isolation via AWS Systems Manager:

```bash
#!/usr/bin/env bash
# ==============================================================================
# HOSPITALITY OS: SEV-1 HOST COMPROMISE CONTAINMENT RUNBOOK
# ==============================================================================
set -euo pipefail

INSTANCE_ID="i-0a1b2c3d4e5f6g7h8"
ISOLATION_SECURITY_GROUP="sg-quarantine-isolated"

echo ">>> [1/4] Revoking public traffic ingress by attaching Quarantine Security Group..."
aws ec2 modify-instance-attribute \
    --instance-id "${INSTANCE_ID}" \
    --groups "${ISOLATION_SECURITY_GROUP}" \
    --region "ap-south-1"

echo ">>> [2/4] Terminating all active Docker containers on host via AWS SSM..."
aws ssm send-command \
    --instance-ids "${INSTANCE_ID}" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=[
      "docker compose -f /opt/hospitality-os/docker-compose.yml down",
      "docker kill $(docker ps -q) || true",
      "chmod 000 /opt/hospitality-os/.env.production"
    ]' \
    --region "ap-south-1"

echo ">>> [3/4] Creating forensic snapshot of EC2 Root EBS Volume..."
ROOT_VOLUME_ID=$(aws ec2 describe-instances \
    --instance-ids "${INSTANCE_ID}" \
    --query 'Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId' \
    --output text \
    --region "ap-south-1")

aws ec2 create-snapshot \
    --volume-id "${ROOT_VOLUME_ID}" \
    --description "Forensic Snapshot of Compromised Host ${INSTANCE_ID} - $(date +%s)" \
    --region "ap-south-1"

echo ">>> [4/4] Host quarantined successfully. Forensic snapshot captured."
```

---

## 7. Security Pre-Flight Verification Checklist

- [ ] **Assertion 1 (Zero Paid Security Services):** AWS CLI confirms 0 AWS WAF WebACLs (`aws wafv2 list-web-acls --scope REGIONAL`), 0 AWS Secrets Manager secrets, and 0 KMS CMKs provisioned.
- [ ] **Assertion 2 (OIDC Deployment Active):** GitHub repository secret settings contain 0 static AWS Access Keys (`AWS_ACCESS_KEY_ID`); deployment workflow utilizes `aws-actions/configure-aws-credentials` with `role-to-assume`.
- [ ] **Assertion 3 (In-Container Rate Limiting Active):** Sending 35 rapid requests to `/api/v1/booking/` returns `HTTP 429 Too Many Requests` on requests 31–35.
- [ ] **Assertion 4 (PCI-DSS SAQ-A Compliance):** Payment API logs confirm zero credit card PAN or CVV parameters logged in Gunicorn/Django request bodies.
- [ ] **Assertion 5 (GDPR Salt-Shredding Verified):** Executing `/api/v1/guests/<id>/gdpr_erase` overwrites PII columns while preserving General Ledger journal balancing.
- [ ] **Assertion 6 (S3 Compliance Mode Active):** `aws s3api get-object-legal-hold` on `hospitality-financial-archive-prod` confirms Object Lock retention of 2,555 days.
- [ ] **Assertion 7 (Billing Alarm Active):** CloudWatch alarm `hospitality-os-free-tier-budget-breach` is in `OK` state with `$0.50` threshold.
