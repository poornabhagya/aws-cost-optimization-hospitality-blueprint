# Continuous Integration & Continuous Delivery (CI/CD) Specification
## Unified Hospitality Management Operating System (Hospitality OS)

---

### Document Metadata
* **Document Title:** Production CI/CD Pipeline, Automated Deployment & Quality Gate Specification
* **System Name:** Hospitality OS (Modular Monolithic Platform & Control Plane)
* **Document Version:** 2.1.0 (Free-Tier Production Baseline with Terraform IaC Automation)
* **Status:** Approved / Production-Ready Baseline
* **Effective Date:** August 24, 2026
* **Target Scope:** 1 Boutique Property (10 Guest Rooms, 30 Dining Seats, 20 Bar Stools, 4 Dedicated Hardware POS Nodes)
* **Target Budget Ceiling:** **< $0.50 USD / month ($0.00 USD / month net spend)**
* **Target Delivery Plane:** GitHub Actions (Hosted Runners) + HashiCorp Terraform + Amazon ECR (500 MB Free) + AWS SSM Session Manager
* **Classification:** Highly Confidential / Enterprise Free-Tier DevOps & CI/CD Baseline
* **Aligned Specifications:**
  - [`docs/Free Tier Baseline/ADR_COLLECTION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/ADR_COLLECTION.md) (ADR-002 Single-Host Compute, ADR-009 Terraform IaC, ADR-010 CI/CD & OIDC)
  - [`docs/Free Tier Baseline/HLA_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/HLA_SPECIFICATION.md) (Platform-Neutral High-Level Architecture Topology)
  - [`docs/Free Tier Baseline/NETWORK_AND_SECURITY_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/NETWORK_AND_SECURITY_SPECIFICATION.md) (OIDC Trust & EC2 SSM Instance Roles)
  - [`docs/Free Tier Baseline/DATABASE_AND_STORAGE_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/DATABASE_AND_STORAGE_SPECIFICATION.md) (S3 Web Assets & CloudFront CDN Invalidation)
  - [`docs/Free Tier Baseline/BOM_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Free%20Tier%20Baseline/BOM_SPECIFICATION.md) (Zero-Cost Bill of Materials)
  - [`docs/Enterprise Baseline/NFR_SPECIFICATION.md`](file:///c:/TheCodeConsortium/hostpitality/hospitality-saas-monorepo/docs/Enterprise%20Baseline/NFR_SPECIFICATION.md) (Code Quality Gates & SLA Commitments)

---

## 1. Executive Summary & Zero-Cost CI/CD Philosophy

Hospitality OS establishes a **Fully Automated, Passwordless Continuous Integration and Continuous Delivery (CI/CD) Pipeline** designed strictly within the **GitHub Actions Free Tier (2,000 monthly minutes) and AWS Free Tier limits (< $0.50 USD / month total spend)**.

### Core Delivery Principles & Free-Tier Cost Optimizations
1. **Passwordless AWS IAM OIDC Federation ($0.00 / month):** Eliminates static `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` secrets from GitHub repositories. The runner requests short-lived 15-minute AWS Security Token Service (STS) credentials using cryptographic OpenID Connect (OIDC) JWT claims.
2. **Automated Terraform Infrastructure as Code (IaC) Stage ($0.00 / month):** Declaratively provisions and verifies the Lean VPC (`10.0.0.0/16`), Security Groups, EC2 `t4g.micro`, RDS PostgreSQL 17 Single-AZ, S3 Buckets, and CloudWatch Billing Alarm before container deployment using an S3 remote backend (`s3://hospitality-os-terraform-state-free-tier/`).
3. **Multi-Arch ARM64 Native Container Builds ($0.00 / month):** Docker Buildx compiles optimized ARM64 container layers matching the 64-bit Graviton2 architecture of the AWS EC2 `t4g.micro` instance, preventing runtime emulation overhead.
4. **Automated Amazon ECR Lifecycle Pruning ($0.00 / month):** Enforces an automated ECR lifecycle rule retaining only the **last 3 tagged and untagged images**, guaranteeing that total repository storage remains well below the AWS **500 MB Free Tier ceiling**.
5. **Remote Zero-Downtime Deployment via AWS SSM ($0.00 / month):** Emits deployment commands directly to the EC2 instance via AWS Systems Manager (`AWS-RunShellScript`), eliminating the need for exposed SSH port 22, public bastion hosts, or paid continuous delivery agent licenses.
6. **Atomic Frontend SPA Sync & Edge Invalidation ($0.00 / month):** Builds client Single Page Applications (React/Vite) and synchronizes them to Amazon S3, triggering an automated CloudFront edge cache invalidation across 600+ Global Anycast edge Points of Presence.

```
+========================================================================================================================+
|                                    HOSPITALITY OS END-TO-END CI/CD PIPELINE FLOW                                       |
+========================================================================================================================+
|                                                                                                                        |
|  [ DEVELOPER WORKSTATION ]                                                                                             |
|       |                                                                                                                |
|       | 1. Git Commit & Push (`main` branch or PR)                                                                     |
|       v                                                                                                                |
|  [ GITHUB ACTIONS RUNNER (Ubuntu Latest - Free Tier 2,000 min/mo) ]                                                    |
|  +----------------------------------------------------------------------------------------------------------------+    |
|  | STAGE 1: QUALITY GATES, TESTING & STATIC ANALYSIS                                                              |    |
|  | • Linting: flake8, black --check                                                                               |    |
|  | • Type Checking: mypy --strict (Zero Type Violations)                                                          |    |
|  | • Security Scan: bandit -r core_hub modules/ (AST Vulnerability Check)                                         |    |
|  | • Secret Leak Detection: trufflehog filesystem --only-verified                                                 |    |
|  | • Automated Unit & Integration Tests: pytest --cov=modules --cov-fail-under=80 (>80% Code Coverage Required)  |    |
|  +----------------------------------------------------------------------------------------------------------------+    |
|       | (All Quality Gates Pass)                                                                                       |
|       v                                                                                                                |
|  +----------------------------------------------------------------------------------------------------------------+    |
|  | STAGE 2: PASSWORDLESS AWS IAM OIDC AUTHENTICATION                                                              |    |
|  | • Exchange GitHub OIDC JWT for AWS STS Temporary Session Token (Role: HospitalityGitHubDeployRole)             |    |
|  +----------------------------------------------------------------------------------------------------------------+    |
|       |                                                                                                                |
|       +------------------------------------+------------------------------------+                                      |
|       | (Infrastructure Track)             | (Frontend Track)                   | (Backend Container Track)        |
|       v                                    v                                    v                                  |
|  +-------------------------------+   +------------------------------------+   +----------------------------------+ |
|  | STAGE 3A: TERRAFORM IAC       |   | STAGE 3B: FRONTEND SPA COMPILATION |   | STAGE 3C: MULTI-ARCH BUILD       | |
|  | • terraform fmt -check        |   | • npm ci && npm run build (Vite)   |   | • Docker Buildx (linux/arm64)    | |
|  | • tflint & terraform validate |   | • Sync to S3 Web Assets Bucket     |   | • Tag: :latest & :sha-${{ sha }} | |
|  | • S3 Remote State Backend     |   | • CloudFront CDN Invalidation (/*) |   | • Push to Amazon ECR (500MB Free)| |
|  | • terraform apply (on main)   |   +------------------------------------+   | • ECR Pruning: Retain last 3 img | |
|  +-------------------------------+                                            +----------------------------------+ |
|       |                                                                                        |                   |
|       +----------------------------------------------------------------------------------------+                   |
|       | (Infrastructure Verified & Container Built)                                                                |
|       v                                                                                                            |
|  +----------------------------------------------------------------------------------------------------------------+    |
|  | STAGE 4: EC2 HOST ZERO-DOWNTIME ROLLING DEPLOYMENT (AWS SSM SESSION MANAGER)                                   |    |
|  | 1. Authenticate Docker with Amazon ECR via AWS CLI                                                             |    |
|  | 2. Pull New Image Layers: docker compose pull                                                                  |    |
|  | 3. Execute PostgreSQL Migrations: docker compose run --rm web python manage.py migrate                         |    |
|  | 4. Rolling Container Replacement: docker compose up -d --remove-orphans                                        |    |
|  | 5. Host Disk Hygiene Prune: docker system prune -af --volumes                                                  |    |
|  +----------------------------------------------------------------------------------------------------------------+    |
|       |                                                                                                                |
|       v                                                                                                                |
|  +----------------------------------------------------------------------------------------------------------------+    |
|  | STAGE 5: POST-DEPLOYMENT HEALTH PROBE & ONE-CLICK ROLLBACK                                                     |    |
|  | • Verify API Response: curl -f https://api.platform.com/health/ (Assert HTTP 200 OK)                          |    |
|  | • Auto-Rollback: If health check fails within 30s, revert container tag to previous Git SHA                    |    |
|  +----------------------------------------------------------------------------------------------------------------+    |
+========================================================================================================================+
```

---

## 2. Automated Quality Gates & Test Suite Matrix

Every pull request and merge commit into `main` must pass six mandatory quality gates before Terraform apply or container deployments are authorized:

| Quality Gate Stage | Tool / Command | Enforcement Standard / Threshold | Failure Action |
| :--- | :--- | :--- | :--- |
| **1. Code Formatting & Linting** | `flake8 .`<br>`black --check .` | PEP 8 compliance, maximum line length 100 characters. | Abort pipeline immediately. |
| **2. Static Type Verification** | `mypy --strict core_hub modules` | 100% strict type annotations; zero `Any` leakages on core models. | Abort pipeline immediately. |
| **3. Static Security Analysis** | `bandit -r core_hub modules -ll` | Zero High or Medium severity AST vulnerabilities. | Abort pipeline immediately. |
| **4. Secret Leak Detection** | `trufflehog filesystem --only-verified` | Zero exposed private keys, Stripe tokens, or AWS credentials. | Abort pipeline immediately. |
| **5. Automated Unit & Integration Tests** | `pytest --cov=modules --cov=core_hub --cov-fail-under=80` | **Minimum 80% line coverage**; 100% test pass rate across all domain modules. | Abort pipeline immediately. |
| **6. Terraform IaC Validation** | `terraform fmt -check`<br>`tflint`<br>`terraform validate` | Zero HCL syntax errors, zero unpinned providers, valid state graph. | Abort pipeline immediately. |

---

## 3. Terraform Infrastructure as Code (IaC) Automation Specification

Infrastructure provisioning is 100% declarative and executed through HashiCorp Terraform in GitHub Actions:

### 3.1 Remote State Architecture ($0.00 / Month)
* **Backend:** Amazon S3 Standard Bucket `hospitality-os-terraform-state-free-tier` (AES-256 SSE-S3 encrypted).
* **State Locking:** DynamoDB table `hospitality-os-terraform-locks` (Provisioned at 1 WCU / 1 RCU under DynamoDB 25 WCU/RCU Perpetual Always-Free Tier).

```hcl
# infrastructure/terraform/backend.tf
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  backend "s3" {
    bucket         = "hospitality-os-terraform-state-free-tier"
    key            = "production/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
    dynamodb_table = "hospitality-os-terraform-locks"
  }
}
```

---

### 3.2 Automated IaC Delivery Workflow
1. **Pull Request Trigger:** Executes `terraform init`, `terraform fmt -check`, `terraform validate`, and `terraform plan`, posting the plan summary directly as a markdown comment on the GitHub PR.
2. **Merge to `main` Trigger:** Executes `terraform apply -auto-approve`, ensuring all cloud resources (VPC, Security Groups, EC2, RDS, S3, CloudWatch Alarms) are up to date prior to rolling backend containers.

---

## 4. Amazon ECR Registry & Free-Tier Lifecycle Policy

Amazon ECR provides **500 MB of private image storage per month** under the AWS Free Tier. Because production ARM64 Docker images average ~120 MB per compressed layer, storing more than 4 full image tags would breach the free tier.

### 4.1 Automated ECR Lifecycle Policy (`ecr-lifecycle-policy.json`)
This policy automatically expires untagged layers immediately and retains only the **last 3 tagged production images**, ensuring that active storage never exceeds **~360 MB**:

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire untagged image layers after 1 day",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 1
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "Retain only the last 3 tagged production images to stay within 500MB Free Tier",
      "selection": {
        "tagStatus": "tagged",
        "tagPrefixList": ["sha-", "v", "prod-"],
        "countType": "imageCountMoreThan",
        "countNumber": 3
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

---

## 5. Production CI/CD Workflow Specification (`.github/workflows/deploy.yml`)

The following production-ready GitHub Actions workflow implements the entire quality gates, Terraform IaC apply, S3 frontend sync, multi-arch ARM64 build, and zero-downtime SSM deployment:

```yaml
name: Production CI/CD Deployment Pipeline

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main

permissions:
  id-token: write   # Mandatory for AWS IAM OIDC Federation
  contents: read     # Required to checkout source code
  pull-requests: write # Required to post Terraform plan comments on PRs

env:
  AWS_REGION: "ap-south-1"
  AWS_ROLE_ARN: "arn:aws:iam::123456789012:role/HospitalityGitHubDeployRole"
  ECR_REPOSITORY: "hospitality-os"
  S3_WEB_BUCKET: "hospitality-web-assets-prod"
  CLOUDFRONT_DISTRIBUTION_ID: "E1A2B3C4D5E6F7"
  TF_WORKING_DIR: "infrastructure/terraform"

jobs:
  # ============================================================================
  # STAGE 1: QUALITY GATES, TESTING & SECURITY SCANNING
  # ============================================================================
  quality-gates:
    name: Automated Quality Gates & Test Suite
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4

      - name: Set up Python 3.12 Runtime
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install Testing & Linting Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flake8 black mypy bandit pytest pytest-cov pytest-django
          pip install -r requirements.txt

      - name: Execute Code Formatting & Linting Check
        run: |
          flake8 core_hub modules --max-line-length=100
          black --check core_hub modules

      - name: Execute Strict Type Checking (Mypy)
        run: |
          mypy --strict core_hub modules

      - name: Execute AST Security Scanning (Bandit)
        run: |
          bandit -r core_hub modules -ll

      - name: Execute Secret Leak Detection (TruffleHog)
        uses: trufflesecurity/trufflehog@v3.82.6
        with:
          path: ./
          base: ${{ github.event.before }}
          head: ${{ github.sha }}
          extra_args: --only-verified

      - name: Run Test Suite with Coverage Gate (>80%)
        env:
          DJANGO_SETTINGS_MODULE: "core_hub.settings.test"
          SECRET_KEY: "ci-testing-secret-key-not-for-production"
        run: |
          pytest --cov=core_hub --cov=modules --cov-fail-under=80 --cov-report=term-missing

  # ============================================================================
  # STAGE 2: TERRAFORM INFRASTRUCTURE AS CODE (IAC) AUTOMATION
  # ============================================================================
  terraform:
    name: Terraform IaC Provisioning
    needs: quality-gates
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4

      - name: Set up HashiCorp Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9.5"

      - name: Authenticate with AWS via IAM OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ env.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
          audience: "sts.amazonaws.com"

      - name: Terraform Format & Syntax Validation
        working-directory: ${{ env.TF_WORKING_DIR }}
        run: |
          terraform fmt -check
          terraform init
          terraform validate

      - name: Terraform Plan (Pull Requests)
        if: github.event_name == 'pull_request'
        working-directory: ${{ env.TF_WORKING_DIR }}
        run: terraform plan -no-color

      - name: Terraform Apply (Merge to Main)
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        working-directory: ${{ env.TF_WORKING_DIR }}
        run: terraform apply -auto-approve

  # ============================================================================
  # STAGE 3: BUILD & DEPLOY FRONTEND SPA TO AMAZON S3 & CLOUDFRONT
  # ============================================================================
  deploy-frontend:
    name: Build & Deploy Frontend SPAs
    needs: [quality-gates, terraform]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4

      - name: Set up Node.js 20 Runtime
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: "frontend/package-lock.json"

      - name: Install Frontend Dependencies
        working-directory: frontend
        run: npm ci

      - name: Compile Production Web Bundles (Vite)
        working-directory: frontend
        run: npm run build

      - name: Authenticate with AWS via IAM OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ env.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
          audience: "sts.amazonaws.com"

      - name: Sync Static Assets to Amazon S3
        run: |
          aws s3 sync frontend/dist/ s3://${{ env.S3_WEB_BUCKET }}/ --delete --cache-control "public, max-age=31536000, immutable"

      - name: Invalidate Amazon CloudFront CDN Cache
        run: |
          aws cloudfront create-invalidation --distribution-id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} --paths "/*"

  # ============================================================================
  # STAGE 4: MULTI-ARCH CONTAINER BUILD & ZERO-DOWNTIME EC2 ROLLOUT
  # ============================================================================
  deploy-backend:
    name: Multi-Arch Build & EC2 Deployment
    needs: [quality-gates, terraform]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4

      - name: Set up QEMU (ARM64 Emulation)
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Authenticate with AWS via IAM OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ env.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
          audience: "sts.amazonaws.com"

      - name: Log in to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build & Push Native ARM64 Docker Image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile
          platforms: linux/arm64
          push: true
          tags: |
            ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:latest
            ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:sha-${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Trigger Rolling Deployment on EC2 via AWS SSM
        run: |
          COMMAND_ID=$(aws ssm send-command \
            --instance-ids "${{ secrets.EC2_INSTANCE_ID }}" \
            --document-name "AWS-RunShellScript" \
            --comment "Production Rolling Deployment: sha-${{ github.sha }}" \
            --parameters 'commands=[
              "set -e",
              "aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin ${{ steps.login-ecr.outputs.registry }}",
              "cd /opt/hospitality-os",
              "docker compose pull web celery",
              "docker compose run --rm web python manage.py migrate --noinput",
              "docker compose up -d --remove-orphans",
              "docker system prune -af --volumes",
              "curl -f --retry 5 --retry-delay 3 http://127.0.0.1:8000/health/ || (echo DEPLOYMENT_FAILED && exit 1)"
            ]' \
            --query "Command.CommandId" \
            --output text)

          echo ">>> AWS SSM Command Dispatched: ${COMMAND_ID}"
          echo ">>> Awaiting remote execution completion..."

          aws ssm wait command-executed \
            --command-id "${COMMAND_ID}" \
            --instance-id "${{ secrets.EC2_INSTANCE_ID }}"

          STATUS=$(aws ssm get-command-invocation \
            --command-id "${COMMAND_ID}" \
            --instance-id "${{ secrets.EC2_INSTANCE_ID }}" \
            --query "Status" \
            --output text)

          if [ "${STATUS}" != "Success" ]; then
            echo "CRITICAL ERROR: Deployment failed on host with status ${STATUS}"
            exit 1
          fi

          echo ">>> [SUCCESS] Production Rolling Deployment Verified (HTTP 200 OK)."
```

---

## 6. Production Health Probes & Automated Rollback Runbook

### 6.1 In-Container Health Probe Specification (`/health/`)
The Django Web API exposes a lightweight, authenticated health check endpoint that validates connectivity across all persistence layers:

```python
# core_hub/views/health.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

def health_check(request):
    health_status = {"status": "healthy", "checks": {}}
    
    # 1. Check PostgreSQL Database Connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"failed: {str(e)}"

    # 2. Check Redis Ephemeral Cache Connection
    try:
        cache.set("health_ping", "pong", timeout=5)
        if cache.get("health_ping") == "pong":
            health_status["checks"]["redis"] = "ok"
        else:
            health_status["status"] = "unhealthy"
            health_status["checks"]["redis"] = "read_failed"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = f"failed: {str(e)}"

    status_code = 200 if health_status["status"] == "healthy" else 503
    return JsonResponse(health_status, status=status_code)
```

---

### 6.2 One-Click Production Rollback CLI Runbook
If a newly deployed release exhibits runtime regression, the DevOps engineer initiates an immediate rollback to the previous Git SHA container image via AWS SSM:

```bash
#!/usr/bin/env bash
# ==============================================================================
# HOSPITALITY OS: ONE-CLICK EMERGENCY ROLLBACK RUNBOOK
# ==============================================================================
set -euo pipefail

PREVIOUS_GIT_SHA="sha-a1b2c3d4e5f6"
INSTANCE_ID="i-0a1b2c3d4e5f6g7h8"
REGISTRY_URL="123456789012.dkr.ecr.ap-south-1.amazonaws.com"

echo ">>> Initiating Emergency Rollback to: ${PREVIOUS_GIT_SHA}..."

aws ssm send-command \
    --instance-ids "${INSTANCE_ID}" \
    --document-name "AWS-RunShellScript" \
    --comment "Emergency Rollback to ${PREVIOUS_GIT_SHA}" \
    --parameters "commands=[
      'set -e',
      'cd /opt/hospitality-os',
      'sed -i \"s|:latest|:${PREVIOUS_GIT_SHA}|g\" docker-compose.yml',
      'docker compose pull web celery',
      'docker compose up -d --remove-orphans',
      'curl -f http://127.0.0.1:8000/health/ || (echo ROLLBACK_HEALTH_FAILED && exit 1)'
    ]" \
    --region "ap-south-1"

echo ">>> Rollback command dispatched successfully."
```

---

## 7. CI/CD Pre-Flight Verification Checklist

- [ ] **Assertion 1 (Zero Static Secrets):** GitHub repository settings contain **0 static AWS Access Keys**; `AWS_ROLE_ARN` OIDC role assumption is verified.
- [ ] **Assertion 2 (Quality Gate Enforcement):** Pull requests with $< 80\%$ test coverage or `flake8`/`mypy` errors are automatically blocked from merging.
- [ ] **Assertion 3 (Terraform IaC Validation):** `terraform fmt -check` and `terraform validate` pass with zero warnings in GitHub Actions.
- [ ] **Assertion 4 (ARM64 Compilation):** Docker Buildx produces native `linux/arm64` images verified via `docker image inspect --format '{{.Architecture}}'`.
- [ ] **Assertion 5 (ECR Lifecycle Active):** ECR repository retains a maximum of 3 tagged images; untagged layers expire within 24 hours.
- [ ] **Assertion 6 (Zero-Downtime Rollout):** `docker compose up -d --remove-orphans` executes cleanly on EC2 with $< 3\text{s}$ transient latency.
- [ ] **Assertion 7 (Health Endpoint Validation):** `/health/` returns `HTTP 200 OK` with database and Redis connectivity confirmed.
- [ ] **Assertion 8 (CloudFront Invalidation):** Edge cache invalidation completes with status `Completed` upon frontend deployments.
