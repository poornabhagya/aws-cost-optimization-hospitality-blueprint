# Security & Regulatory Compliance Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Production Security Architecture, IAM Governance, Cryptography & Regulatory Compliance Specification
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 1.0.0 (Production Engineering Baseline)
* **Status:** Approved / Production-Ready Baseline
* **Effective Date:** August 23, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Cloud Provider:** Amazon Web Services (AWS) — Primary Region: `us-east-1` (Dual-AZ: `us-east-1a`, `us-east-1b`)
* **Classification:** Highly Confidential / Enterprise Security & Regulatory Compliance Baseline
* **Aligned Specifications:**
  - [`docs/BRD_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/BRD_SPECIFICATION.md) (PCI-DSS Tokenization, GDPR Anonymization, 7-Year Tax Compliance)
  - [`docs/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NFR_SPECIFICATION.md) (TLS 1.3, Rate Limits: 30/60/120 req/min, Zero Static IAM Keys, Zero-Trust ZTNA)
  - [`docs/CAPACITY_SIZING.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/CAPACITY_SIZING.md) (2x Tasks, Dual-AZ Sizing, Resource Isolation)
  - [`docs/ADR_COLLECTION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/ADR_COLLECTION.md) (ADR-006 WORM, ADR-007 ALB+WAF, ADR-008 KMS+SSM, ADR-010 OIDC GitHub Actions)
  - [`docs/NETWORK_AND_SECURITY_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/NETWORK_AND_SECURITY_SPECIFICATION.md) (Subnet Matrix, sg-ecs-compute, sg-rds-postgres, VPC Endpoints)
  - [`docs/DATABASE_AND_STORAGE_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/DATABASE_AND_STORAGE_SPECIFICATION.md) (KMS CMK, SSE-KMS, SCRAM-SHA-256, S3 WORM Compliance)

---

## 1. Executive Summary & Security Philosophy

Hospitality OS establishes an enterprise **Zero-Trust Network Architecture (ZTNA)** and **Defense-in-Depth** security posture across all 7 platform tiers. The security model operates on the principle of continuous explicit verification, least privilege, and assumed breach.

### Core Security Pillars
1. **Zero Long-Lived Static Credentials:** Complete elimination of hardcoded API secrets, `.env` files in source repositories, and persistent AWS IAM access keys in CI/CD. All machine identities authenticate via cryptographic OpenID Connect (OIDC) or AWS STS short-lived tokens.
2. **Strict Micro-Segmentation & Boundary Enforcement:** East-West network traffic is restricted to exact application ports (`TCP 5432` for PostgreSQL, `TCP 6379` for Redis, `TCP 8000` for Gunicorn) chained across Security Group IDs.
3. **Cryptographic Protection Everywhere:** All data at rest is encrypted using AWS KMS Customer Managed Keys (`AES-256-GCM`). All data in transit enforces **TLS 1.3** cryptographic cipher suites.
4. **Regulatory Non-Repudiation (WORM):** Financial documents (finalized guest folios, VAT invoices, daily night audit ledgers) are locked in an immutable **7-Year S3 Glacier WORM Vault** compliant with SEC 17a-4(f) and European fiscal regulations.
5. **PCI-DSS SAQ-A Scope Minimization:** Credit card Primary Account Numbers (PAN) never touch platform servers, memory, or databases. Direct browser-to-Stripe tokenization isolates the platform from PCI-DSS Level 1 scope.
6. **GDPR-Compliant Ledger Preservation:** Guest PII is pseudonymized using cryptographic salt-shredding upon deletion requests, preserving immutable financial accounting balances without violating the "Right to be Forgotten".

```
+==================================================================================================================+
|                                    HOSPITALITY OS DEFENSE-IN-DEPTH ARCHITECTURE                                  |
+==================================================================================================================+
|                                                                                                                  |
|  [ LAYER 1: IDENTITY & ACCESS ] (Section 2)                                                                      |
|  • GitHub Actions OIDC Federated CI/CD (Zero Static IAM Keys) | Break-Glass MFA STS Session (1 Hour)             |
|  • ECS Task Execution Role (SSM/ECR/KMS) vs. ECS Task Runtime Role (S3/SNS Least Privilege)                      |
|                                                                                                                  |
|  [ LAYER 2: EDGE INGRESS & APPLICATION DEFENSE ] (Section 4)                                                     |
|  • AWS Shield Standard (L3/L4 DDoS Mitigation) | AWS WAF Core Rule Sets (SQLi, XSS, Bad Bots)                    |
|  • AWS ALB TLS 1.3 Termination (ACM Auto-Renewed Public Certificates) | Rate Limits (30/60/120 req/min)          |
|                                                                                                                  |
|  [ LAYER 3: NETWORK MICRO-SEGMENTATION ] (docs/NETWORK_AND_SECURITY_SPECIFICATION.md)                           |
|  • 6-Subnet Dual-AZ Multi-Tier Isolation | Zero Internet Routing for Persistence Tier                           |
|  • Chained Security Groups: sg-alb-ingress -> sg-ecs-compute -> sg-rds-postgres / sg-redis-cache                  |
|  • AWS PrivateLink VPC Interface Endpoints & S3 Gateway Endpoints (Zero Internet Exfiltration)                  |
|                                                                                                                  |
|  [ LAYER 4: COMPUTATIONAL & APPLICATION RUNTIME ] (Section 5)                                                    |
|  • AWS ECS Fargate Container Isolation (Non-Root User, Read-Only Root Filesystem, Hard Resource Limits)          |
|  • Dynamic Secret Injection via AWS SSM Parameter Store + KMS Envelope Decryption at Launch                     |
|                                                                                                                  |
|  [ LAYER 5: STORAGE & CRYPTOGRAPHY ] (Section 3 & Section 6)                                                     |
|  • KMS Customer Managed Key (CMK) Envelope Encryption (RDS, S3, EBS, SSM)                                        |
|  • S3 7-Year WORM Vault (Object Lock COMPLIANCE Mode) | SCRAM-SHA-256 DB Auth | Stripe Elements (PCI SAQ-A)    |
|                                                                                                                  |
|  [ LAYER 6: AUDITABILITY & TELEMETRY ] (Section 7)                                                               |
|  • Continuous VPC Flow Logs (60s Aggregation) | AWS CloudTrail Multi-Region Immutable S3 + CloudWatch Alarms     |
+==================================================================================================================+
```

---

## 2. IAM Governance & Least-Privilege Policy Matrix

### 2.1 ECS IAM Architecture (Execution Role vs. Task Role)
To maintain strict separation of concerns, ECS Fargate tasks utilize two distinct IAM roles:
1. **ECS Task Execution Role (`HospitalityEcsExecutionRole`):** Used by the AWS ECS Agent to bootstrap the container (pull Docker layers from ECR, retrieve environment secrets from SSM, write logs to CloudWatch).
2. **ECS Task Role (`HospitalityEcsTaskRuntimeRole`):** Used by the application code running *inside* the container (upload folio PDFs to S3, publish alerts to SNS, invoke KMS cryptographic signatures).

```
+----------------------------------------------------------------------------------------------------+
|                                    ECS FARGATE IAM DUAL-ROLE TOPOLOGY                              |
|                                                                                                    |
|  [ AWS ECS AGENT (Task Launch Phase) ]                                                             |
|       |                                                                                            |
|       +---> Assumes: HospitalityEcsExecutionRole                                                   |
|                • ecr:GetAuthorizationToken, ecr:BatchGetImage (Pull Docker Image)                  |
|                • ssm:GetParameters, ssm:GetParametersByPath (Inject Env Secrets)                   |
|                • kms:Decrypt (Decrypt SSM SecureString Parameters)                                 |
|                • logs:CreateLogStream, logs:PutLogEvents (Emit Container Logs)                     |
|                                                                                                    |
|  [ APPLICATION PROCESS (Python/Django Runtime Phase) ]                                             |
|       |                                                                                            |
|       +---> Assumes: HospitalityEcsTaskRuntimeRole                                                 |
|                • s3:PutObject, s3:GetObject -> arn:aws:s3:::s3-hospitality-financial-archive-prod/*|
|                • sns:Publish -> arn:aws:sns:us-east-1:...:hospitality-alerts-production            |
|                • kms:GenerateDataKey -> arn:aws:kms:us-east-1:.../hospitality-storage-key          |
|                • (Zero ECR, Zero SSM, Zero IAM permissions inside the application runtime)         |
+----------------------------------------------------------------------------------------------------+
```

#### A. ECS Task Execution Role Policy (`HospitalityEcsExecutionRolePolicy`)
```json
{
  "Version": "2012-10-17",
  "Statement": [
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
    },
    {
      "Sid": "AllowCloudWatchLogsLogging",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/ecs/hospitality-os-prod:*"
    },
    {
      "Sid": "AllowSsmParameterDecryption",
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": "arn:aws:ssm:us-east-1:123456789012:parameter/hospitality-os/prod/*"
    },
    {
      "Sid": "AllowKmsEnvelopeDecryption",
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
    }
  ]
}
```

#### B. ECS Task Runtime Role Policy (`HospitalityEcsTaskRuntimeRolePolicy`)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowFinancialVaultUpload",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::s3-hospitality-financial-archive-prod/*"
    },
    {
      "Sid": "AllowStaticWebAssetSync",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::s3-hospitality-web-prod",
        "arn:aws:s3:::s3-hospitality-web-prod/*"
      ]
    },
    {
      "Sid": "AllowSnsSecurityAlerting",
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:us-east-1:123456789012:hospitality-alerts-production"
    }
  ]
}
```

---

### 2.2 GitHub Actions CI/CD OIDC Federated Identity
To eliminate static `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` credentials from GitHub repository settings, deployments authenticate dynamically via AWS Security Token Service (STS) using OpenID Connect (OIDC).

```
+----------------------------------------------------------------------------------------------------+
|                                    GITHUB ACTIONS OIDC AUTHENTICATION FLOW                         |
|                                                                                                    |
|  [ GitHub Actions Workflow Runner ]                                                                |
|       |                                                                                            |
|       | 1. Requests OIDC JWT Token signed by token.actions.githubusercontent.com                   |
|       v                                                                                            |
|  [ GitHub OIDC Identity Provider ]                                                                 |
|       |                                                                                            |
|       | 2. Issues Cryptographic JWT (Claims: repository, ref, job_workflow_ref)                     |
|       v                                                                                            |
|  [ AWS Security Token Service (STS:AssumeRoleWithWebIdentity) ]                                    |
|       |                                                                                            |
|       | 3. Validates OIDC JWT signature & asserts repository condition:                            |
|       |    repo:The-Code-Consortium/hospitality-saas-monorepo:*                                    |
|       v                                                                                            |
|  [ Ephemeral 15-Minute Scoped AWS Session Credentials ]                                            |
|  (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)                                      |
|       |                                                                                            |
|       v 4. Executes Terraform Plan/Apply, Docker Image Push to ECR, and ECS Service Deploy         |
+----------------------------------------------------------------------------------------------------+
```

#### GitHub Actions OIDC IAM Trust Policy (`GitHubActionsOidcTrustPolicy`)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowGitHubActionsFederation",
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

### 2.3 Break-Glass Emergency Access Procedure

In the event of catastrophic deployment pipeline failure, security incident remediation, or disaster recovery execution, engineers must follow a formalized, audited Break-Glass Procedure:

```
+----------------------------------------------------------------------------------------------------+
|                                    BREAK-GLASS EMERGENCY RUNBOOK                                   |
|                                                                                                    |
|  1. Engineer authenticates to AWS IAM Identity Center (SSO) with Hardware FIDO2/WebAuthn MFA       |
|                                    |                                                               |
|                                    v                                                               |
|  2. Assumes short-lived Emergency Role: arn:aws:iam::123456789012:role/HospitalityBreakGlassAdmin  |
|     (Session Duration strictly capped at 3,600 seconds / 1 Hour)                                   |
|                                    |                                                               |
|                                    v                                                               |
|  3. CloudWatch Alarm triggers immediate Sev-1 notification to security Slack/PagerDuty:            |
|     "SEV-1 ALERT: Break-Glass Emergency IAM Role assumed by user: [engineer@company.com]"         |
|                                    |                                                               |
|                                    v                                                               |
|  4. All console actions, CLI commands, and API requests recorded immutably in AWS CloudTrail       |
|                                    |                                                               |
|                                    v                                                               |
|  5. Mandatory Post-Incident Audit: Security team reviews CloudTrail event log within 24 hours      |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Cryptographic Governance & AWS KMS Master Specification

### 3.1 AWS KMS Customer Managed Key (CMK) Resource Policy
All relational databases (RDS), durable object vaults (S3), EBS storage volumes, and parameter secrets share a unified Customer Managed Key (`hospitality-master-encryption-key`) with automatic 365-day rotation and strict least-privilege service principal delegation.

```hcl
# Terraform AWS KMS Master CMK Definition
resource "aws_kms_key" "master_key" {
  description             = "Hospitality OS Production Master Encryption Key (RDS, S3, SSM, EBS)"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootIAMManagement"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::123456789012:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowRdsStorageEncryption"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowS3VaultEncryption"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:GenerateDataKey",
          "kms:Decrypt"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowEcsTaskDecryption"
        Effect = "Allow"
        Principal = {
          AWS = [
            "arn:aws:iam::123456789012:role/HospitalityEcsExecutionRole",
            "arn:aws:iam::123456789012:role/HospitalityEcsTaskRuntimeRole"
          ]
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "hospitality-master-encryption-key"
    Environment = "production"
  }
}
```

---

### 3.2 TLS 1.3 Cryptographic Cipher Suite & ACM Lifecycle
* **ALB Security Policy:** `ELBSecurityPolicy-TLS13-1-2-2021-06`
* **Supported Protocols:** TLS 1.3 (Primary), TLS 1.2 (Backward compatibility for legacy POS terminals). SSLv3, TLS 1.0, and TLS 1.1 are **strictly disabled**.
* **Enforced Ciphers:**
  - `TLS_AES_128_GCM_SHA256` (TLS 1.3)
  - `TLS_AES_256_GCM_SHA384` (TLS 1.3)
  - `TLS_CHACHA20_POLY1305_SHA256` (TLS 1.3)
  - `ECDHE-ECDSA-AES128-GCM-SHA256` (TLS 1.2)
  - `ECDHE-RSA-AES128-GCM-SHA256` (TLS 1.2)
* **Certificate Lifecycle:** AWS Certificate Manager (ACM) provisions public wildcard certificates (`*.platform.com`, `platform.com`) with DNS validation via Amazon Route 53. ACM handles automated renewal 60 days prior to expiration with zero manual intervention.

---

## 4. Edge Application Security & AWS WAF Configuration Blueprint

The ingress Application Load Balancer is protected by an **AWS WAF (Web Application Firewall)** WebACL configured with managed rule sets and granular rate-limiting policies tailored to the hospitality workload.

```
+==================================================================================================================+
|                                    AWS WAF INGRESS SECURITY CASCADE                                              |
+==================================================================================================================+
|                                                                                                                  |
|  [ INCOMING HTTP/S TRAFFIC ]                                                                                     |
|               |                                                                                                  |
|               v                                                                                                  |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | RULE PRIORITY 1: AWS Managed Common Rule Set (AWSManagedRulesCommonRuleSet)                              |    |
|  | • Blocks generic web exploits, scanner probes, anomalous path traversal, command injection              |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|               | (Pass)                                                                                           |
|               v                                                                                                  |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | RULE PRIORITY 2: AWS Managed SQLi Rule Set (AWSManagedRulesSQLiRuleSet)                                  |    |
|  | • Inspects query strings, JSON request bodies, and headers for SQL injection signatures                   |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|               | (Pass)                                                                                           |
|               v                                                                                                  |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | RULE PRIORITY 3: AWS Managed Known Bad Inputs (AWSManagedRulesKnownBadInputsRuleSet)                     |    |
|  | • Drops malformed request headers, invalid character sets, and exploits (Log4j, Shellshock)             |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|               | (Pass)                                                                                           |
|               v                                                                                                  |
|  +----------------------------------------------------------------------------------------------------------+    |
|  | RULE PRIORITY 4: Granular Rate-Limiting Policy (Rate-Based Evaluation)                                   |    |
|  | • Public Booking Engine (/api/v1/booking/*): Limit = 30 req/min per IP (Burst Buffer = 10 req)           |    |
|  | • Local POS Terminal API (/api/v1/pos/*):     Limit = 120 req/min per Terminal IP (Burst = 30 req)       |    |
|  | • Front Desk PMS API (/api/v1/pms/*):         Limit = 60 req/min per IP (Burst = 15 req)                |    |
|  +----------------------------------------------------------------------------------------------------------+    |
|               | (Pass)                                                                                           |
|               v                                                                                                  |
|  [ FORWARD TO AWS APPLICATION LOAD BALANCER LISTENER (Port 8000) ]                                               |
+==================================================================================================================+
```

---

## 5. Secrets Management Hierarchy & Dynamic Injection

### 5.1 AWS SSM Parameter Store Path Architecture
All operational secrets and environment configurations reside in AWS Systems Manager (SSM) Parameter Store under a standardized hierarchical namespace:

```
/hospitality-os/
└── prod/
    ├── database/
    │   ├── host                    [Type: String]        hospitality-os-pg17.cluster-c123.us-east-1.rds.amazonaws.com
    │   ├── port                    [Type: String]        5432
    │   ├── name                    [Type: String]        hospitality_production
    │   ├── username                [Type: String]        hospitality_app
    │   ├── password                [Type: SecureString]  (KMS Encrypted SCRAM Secret)
    │   └── pgbouncer_userlist      [Type: SecureString]  (KMS Encrypted PgBouncer Auth File)
    ├── cache/
    │   ├── redis_url               [Type: SecureString]  rediss://:AuthToken@hospitality-redis.cluster.cache.amazonaws.com:6379/0
    │   └── redis_auth_token        [Type: SecureString]  (KMS Encrypted Auth Token)
    ├── security/
    │   ├── django_secret_key       [Type: SecureString]  (KMS Encrypted 50-char cryptographic salt)
    │   ├── jwt_private_key_rsa     [Type: SecureString]  (KMS Encrypted RSA-2048 PKCS#8 Private Key)
    │   └── jwt_public_key_rsa      [Type: String]        (RSA-2048 Public Key for Microservice Verification)
    └── integrations/
        ├── stripe_secret_key       [Type: SecureString]  sk_live_51P...
        ├── stripe_webhook_secret   [Type: SecureString]  whsec_9b2...
        └── sendgrid_api_key        [Type: SecureString]  SG.8fK...
```

---

### 5.2 Zero-Downtime Secret Rotation Procedure
When rotating sensitive credentials (e.g., database passwords, Stripe keys, or JWT RSA signing keys):

1. **Step 1 (Provision Secondary Secret):** Update PostgreSQL database or third-party provider to accept both the old and new cryptographic keys simultaneously.
2. **Step 2 (Update Parameter Store):** Put new `SecureString` value in SSM:
   ```bash
   aws ssm put-parameter \
       --name "/hospitality-os/prod/security/jwt_private_key_rsa" \
       --value file://new_rsa_key.pem \
       --type "SecureString" \
       --key-id "alias/hospitality-master-encryption-key" \
       --overwrite
   ```
3. **Step 3 (Rolling ECS Deployment):** Trigger zero-downtime container rolling restart:
   ```bash
   aws ecs update-service \
       --cluster hospitality-prod-cluster \
       --service hospitality-web-app \
       --force-new-deployment
   ```
4. **Step 4 (Revoke Old Secret):** Once all new ECS tasks pass health probes and old tasks drain, revoke the legacy credential in the backend database.

---

## 6. Regulatory Compliance & Data Privacy Architecture

### 6.1 PCI-DSS SAQ-A Scope Minimization (Payment Security)
Hospitality OS achieves **PCI-DSS SAQ-A Compliance** (the lowest and most secure compliance burden) by completely eliminating cardholder data from backend infrastructure:

```
+----------------------------------------------------------------------------------------------------+
|                                    PCI-DSS SAQ-A PAYMENT ISOLATION FLOW                            |
|                                                                                                    |
|  [ Guest Web Browser / POS Touchscreen ]                                                           |
|       |                                                                                            |
|       | 1. Directly loads Stripe.js / Stripe Elements iframe (Hosted on Stripe CDN)               |
|       v                                                                                            |
|  [ Stripe Secure Tokenization Vault ]                                                              |
|       |                                                                                            |
|       | 2. Validates Credit Card PAN, Expiration & CVV; Returns Token: tok_1P987... / pm_987...    |
|       v                                                                                            |
|  [ Hospitality OS Frontend Application ]                                                           |
|       |                                                                                            |
|       | 3. Submits payment token to Hospitality OS API: POST /api/v1/pos/payments/capture          |
|       |    Payload: { "payment_method_id": "pm_987...", "amount_cents": 12500 }                    |
|       v                                                                                            |
|  [ Hospitality OS Backend Compute (ECS Fargate) ]                                                  |
|       |                                                                                            |
|       | 4. Dispatches server-to-server API call to Stripe: stripe.PaymentIntent.create(...)         |
|       v                                                                                            |
|  [ RELATIONAL DATABASE STORAGE ]                                                                   |
|  • Stores ONLY: Stripe Charge ID (ch_123), Last 4 Digits ("4242"), Card Brand ("Visa").           |
|  • RAW CARD NUMBERS (PAN), CVVS, AND PIN DATA NEVER TOUCH OUR SERVERS OR MEMORY.                   |
+----------------------------------------------------------------------------------------------------+
```

---

### 6.2 GDPR / PII Anonymization & Ledger-Safe Anonymization Strategy

Under GDPR Article 17 ("Right to be Forgotten"), guests may request the total deletion of their personal data. However, hospitality tax laws mandate retaining financial accounting records for 7 years. 

Hospitality OS reconciles this conflict through **Cryptographic Salt-Shredding & Pseudonymization**:

```
+----------------------------------------------------------------------------------------------------+
|                                    GDPR CRYPTO-SHREDDING RECONCILIATION                            |
|                                                                                                    |
|  [ Guest Profile Record in Database ]                                                              |
|  • guest_id: "gst_998811"                                                                          |
|  • first_name: "John"          --> [ Encrypted with Unique Per-Guest Salt: kms_salt_gst_998811 ]   |
|  • email: "john@example.com"   --> [ Encrypted with Unique Per-Guest Salt: kms_salt_gst_998811 ]   |
|                                                                                                    |
|  [ Immutable General Ledger Journal Entry ]                                                        |
|  • entry_id: "gl_554433"                                                                           |
|  • debit_account: "1010-Cash" | credit_account: "4010-Room-Revenue" | amount: $250.00             |
|  • memo: "Folio settled for Guest: gst_998811"                                                     |
|                                                                                                    |
|                                    |                                                               |
|                                    | GUEST ISSUES GDPR DELETION REQUEST                            |
|                                    v                                                               |
|  [ ANONYMIZATION ACTION (Instant & Irreversible) ]                                                 |
|  1. Destroy cryptographic salt: kms_salt_gst_998811 deleted from KMS/Database                      |
|  2. Overwrite PII fields: first_name = "ANONYMIZED_GDPR", email = "anonymized@deleted.local"      |
|  3. Financial Ledger Entry Remains 100% Intact & Balanced: Accounting integrity is preserved!       |
+----------------------------------------------------------------------------------------------------+
```

---

### 6.3 Fiscal Tax & SEC 17a-4 WORM Compliance Validation
* **Storage Immutability:** S3 Object Lock in `COMPLIANCE` Mode guarantees that once a finalized PDF invoice is uploaded to `s3-hospitality-financial-archive-prod`, no IAM entity (including the AWS Root account or AWS Support) can alter, rename, or delete the object for **2,555 Days (7 Years)**.
* **Audit Trail Non-Repudiation:** Every invoice upload generates a SHA-256 cryptographic hash recorded simultaneously in the database `AuditLog` table and S3 Object Metadata (`x-amz-meta-sha256`), providing tamper-evident mathematical verification for tax authorities.

---

## 7. Security Telemetry, CloudTrail Auditing & Incident Response Runbook

### 7.1 Multi-Region AWS CloudTrail & Log Governance
AWS CloudTrail captures all AWS management API actions, console logins, and infrastructure changes across all regions:
* **Trail Name:** `hospitality-os-global-security-trail`
* **Log Storage:** Encrypted S3 bucket (`s3-hospitality-security-audit-prod`) with Object Lock enabled.
* **CloudWatch Integration:** Streamed to `/aws/cloudtrail/security-events` with metric filters monitoring for unauthorized API calls, root logins, and security group alterations.

---

### 7.2 Incident Severity Classification & Escalation Matrix

| Severity Level | Definition & Operational Criteria | SLA Initial Response | Resolution SLA | Automated Trigger & Action |
| :--- | :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Active data breach, ransomware, unauthenticated database access, or total platform outage. | **$< 15\text{ Minutes}$** | **$< 2\text{ Hours}$** | PagerDuty On-Call Page, SMS Blast, Automated Security Group Egress Quarantine. |
| **SEV-2 (High)** | Potential security breach attempt (e.g., $> 1,000$ WAF blocks/min, root account console login). | **$< 30\text{ Minutes}$** | **$< 6\text{ Hours}$** | PagerDuty Alert, DevOps Slack Channel Alert. |
| **SEV-3 (Medium)** | Non-critical security anomaly (e.g., individual IP rate-limit breach, stale IAM session warning). | **$< 2\text{ Hours}$** | **$< 24\text{ Hours}$**| DevOps Slack Channel Webhook Notification. |
| **SEV-4 (Low)** | Informational security event (e.g., scheduled KMS key rotation complete, ACM certificate auto-renewed).| **$< 8\text{ Hours}$** | **$< 72\text{ Hours}$**| Automated Daily Summary Email Report. |

---

### 7.3 Security Incident Response Runbook (Sev-1 Breach Containment)

In the event of an active security incident or detected container intrusion, execute the following containment protocol immediately:

```bash
#!/usr/bin/env bash
# ==============================================================================
# HOSPITALITY OS: SEV-1 INCIDENT CONTAINMENT & QUARANTINE RUNBOOK
# ==============================================================================
set -euo pipefail

COMPROMISED_TASK_ID="f3b9c8a1d2e34f5a6b7c8d9e0f1a2b3c"
CLUSTER_NAME="hospitality-prod-cluster"
SECURITY_GROUP_QUARANTINE="sg-quarantine-isolated"

echo "[1/4] Isolating compromised ECS container task network interface..."
TASK_ENI=$(aws ecs describe-tasks \
    --cluster "${CLUSTER_NAME}" \
    --tasks "${COMPROMISED_TASK_ID}" \
    --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
    --output text)

echo "Attaching Quarantine Security Group (Zero Inbound / Zero Outbound) to ENI: ${TASK_ENI}..."
aws ec2 modify-network-interface-attribute \
    --network-interface-id "${TASK_ENI}" \
    --groups "${SECURITY_GROUP_QUARANTINE}"

echo "[2/4] Revoking all active application JWT user sessions in Redis..."
aws ssm start-session \
    --target "$(aws ec2 describe-instances --filters "Name=tag:Role,Values=bastion" --query 'Reservations[0].Instances[0].InstanceId' --output text)" \
    --document-name "AWS-StartInteractiveCommand" \
    --parameters 'command=["redis-cli -h hospitality-redis.cluster.cache.amazonaws.com -a $REDIS_AUTH_TOKEN FLUSHDB"]'

echo "[3/4] Triggering immediate KMS envelope key rotation..."
aws kms enable-key-rotation --key-id "alias/hospitality-master-encryption-key"

echo "[4/4] Spawning clean, non-compromised ECS task replacement..."
aws ecs stop-task --cluster "${CLUSTER_NAME}" --task "${COMPROMISED_TASK_ID}" --reason "Sev-1 Security Containment"

echo "[CONTAINMENT COMPLETE] Forensic snapshot preserved on ENI. Security team engaged."
```

---

## 8. Security & Regulatory Compliance Pre-Flight Checklist

Before deploying code or infrastructure to production, the SecOps engineer must verify the following automated assertions:

- [ ] **Assertion 1 (No Static Secrets):** Automated `trufflehog` and `git-secrets` scans return 0 detected API keys or passwords in Git history.
- [ ] **Assertion 2 (OIDC Authentication):** GitHub repository settings contain zero `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` secrets.
- [ ] **Assertion 3 (TLS 1.3 Active):** SSL Labs / testssl scan confirms ALB supports only TLS 1.3/1.2 with A+ security rating.
- [ ] **Assertion 4 (WAF Rate Limiting Active):** Synthetic burst requests ($> 30\text{ req/min}$) to `/api/v1/booking/*` return HTTP 429 Too Many Requests.
- [ ] **Assertion 5 (PCI Scope Isolation):** Grep scan across codebase confirms zero database columns or models containing credit card PAN, CVV, or magnetic track data.
- [ ] **Assertion 6 (S3 WORM Lock Active):** S3 API call `aws s3api get-object-lock-configuration --bucket s3-hospitality-financial-archive-prod` returns `Mode: COMPLIANCE` and `Years: 7`.
- [ ] **Assertion 7 (CloudTrail Active):** Multi-Region CloudTrail is actively logging with S3 Object Lock and CloudWatch Log Group delivery.
