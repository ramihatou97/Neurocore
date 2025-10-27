# CI/CD Pipelines Documentation

Comprehensive GitHub Actions workflows for continuous integration, deployment, and security auditing.

## Overview

The CI/CD pipeline consists of four main workflows:

1. **Continuous Integration (CI)** - Automated testing and code quality checks
2. **Staging Deployment (CD)** - Automated deployment to staging environment
3. **Production Deployment (CD)** - Controlled deployment to production with approval gates
4. **Security Scanning** - Weekly security audits and vulnerability scanning

## Workflows

### 1. Continuous Integration (`ci.yml`)

**Triggers:**
- Push to `main`, `develop`, or `feature/**` branches
- Pull requests to `main` or `develop`

**Jobs:**
- **Backend Linting** - Black, isort, Flake8, MyPy
- **Backend Testing** - Pytest with PostgreSQL and Redis services
- **Frontend Linting** - ESLint and code quality checks
- **Frontend Testing** - Jest test suite with coverage
- **Frontend Build** - Production build verification
- **Docker Build** - Multi-stage Docker image builds
- **Security Scanning** - Safety, Bandit, npm audit

**Status Requirements:**
All jobs must pass before merging to main branches.

### 2. Staging Deployment (`cd-staging.yml`)

**Triggers:**
- Push to `develop` branch
- Manual workflow dispatch

**Jobs:**
1. **Build & Push Images** - Build and push to GitHub Container Registry
2. **Deploy** - Deploy to staging server via SSH
3. **Smoke Tests** - Verify deployment health
4. **Notification** - Send deployment status notification

**Environment:**
- Name: `staging`
- URL: Set via `STAGING_URL` secret

**Required Secrets:**
- `STAGING_API_URL` - Staging API base URL
- `STAGING_URL` - Staging frontend URL
- `STAGING_HOST` - Staging server hostname
- `STAGING_USER` - SSH user for staging server
- `STAGING_SSH_KEY` - SSH private key for staging access
- `GITHUB_TOKEN` - Automatically provided by GitHub

### 3. Production Deployment (`cd-production.yml`)

**Triggers:**
- Push tags matching `v*.*.*` (e.g., v1.0.0)
- Manual workflow dispatch (requires approval)

**Jobs:**
1. **Validation** - Verify version tag format and CI status
2. **Build & Push Images** - Build production images with semantic versioning
3. **Backup** - Create pre-deployment database backup
4. **Deploy** - Deploy to production with health checks
5. **Smoke Tests** - Comprehensive production health verification
6. **Post-Deployment** - Create GitHub release
7. **Rollback** - Automatic rollback on failure (manual trigger)
8. **Notification** - Send deployment status notification

**Environment:**
- Name: `production`
- URL: Set via `PRODUCTION_URL` secret
- Approval: Manual approval required for production deployment

**Required Secrets:**
- `PRODUCTION_API_URL` - Production API base URL
- `PRODUCTION_URL` - Production frontend URL
- `PRODUCTION_HOST` - Production server hostname
- `PRODUCTION_USER` - SSH user for production server
- `PRODUCTION_SSH_KEY` - SSH private key for production access
- `DB_USER` - Database user for backups
- `GITHUB_TOKEN` - Automatically provided by GitHub

**Backup Strategy:**
- Automatic backup before each deployment
- Keeps last 10 backups
- Stored in `/opt/neurocore/backups/` on production server

**Rollback Procedure:**
If deployment fails:
1. Automatically triggered on smoke test failure
2. Restores latest database backup
3. Reverts to previous container versions
4. Sends failure notification

### 4. Security Scanning (`security-scan.yml`)

**Triggers:**
- Weekly schedule (Mondays at 9:00 AM UTC)
- Push to `main` or `develop` when dependencies change
- Manual workflow dispatch

**Jobs:**
1. **Python Security** - Safety and pip-audit for dependency vulnerabilities
2. **Bandit Scan** - Python code security analysis
3. **NPM Security** - npm audit for frontend vulnerabilities
4. **Docker Security** - Trivy scanning for container vulnerabilities
5. **CodeQL Analysis** - Advanced code security analysis
6. **Secret Scanning** - Gitleaks for exposed secrets
7. **License Check** - License compliance verification
8. **Summary** - Aggregated security report

**Reports:**
All scan results are uploaded as artifacts and available for 90 days.

## Setup Instructions

### 1. Configure GitHub Secrets

Navigate to **Settings > Secrets and variables > Actions** and add:

#### Staging Secrets
```
STAGING_API_URL=https://api-staging.neurosurgery-kb.com
STAGING_URL=https://staging.neurosurgery-kb.com
STAGING_HOST=staging-server.example.com
STAGING_USER=deploy
STAGING_SSH_KEY=<private-ssh-key>
```

#### Production Secrets
```
PRODUCTION_API_URL=https://api.neurosurgery-kb.com
PRODUCTION_URL=https://neurosurgery-kb.com
PRODUCTION_HOST=production-server.example.com
PRODUCTION_USER=deploy
PRODUCTION_SSH_KEY=<private-ssh-key>
DB_USER=neurosurgery_admin
```

#### Optional Notification Secrets
```
SLACK_WEBHOOK=<slack-webhook-url>
EMAIL_USERNAME=<smtp-username>
EMAIL_PASSWORD=<smtp-password>
```

### 2. Configure GitHub Environments

Navigate to **Settings > Environments** and create:

#### Staging Environment
- **Name:** `staging`
- **URL:** `https://staging.neurosurgery-kb.com`
- **Protection rules:** None (auto-deploy)
- **Environment secrets:** Use staging secrets

#### Production Environment
- **Name:** `production`
- **URL:** `https://neurosurgery-kb.com`
- **Protection rules:**
  - ✅ Required reviewers (1-2 team members)
  - ✅ Wait timer (0 minutes)
- **Environment secrets:** Use production secrets

#### Production Backup Environment
- **Name:** `production-backup`
- **Protection rules:**
  - ✅ Required reviewers (1 team member)
- **Purpose:** Approve pre-deployment backups

#### Production Rollback Environment
- **Name:** `production-rollback`
- **Protection rules:**
  - ✅ Required reviewers (1-2 team members)
- **Purpose:** Approve production rollbacks

### 3. Configure Server Access

#### Generate SSH Keys
```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy

# Copy public key to servers
ssh-copy-id -i ~/.ssh/github_deploy.pub deploy@staging-server.example.com
ssh-copy-id -i ~/.ssh/github_deploy.pub deploy@production-server.example.com

# Add private key to GitHub secrets
cat ~/.ssh/github_deploy  # Copy this to STAGING_SSH_KEY and PRODUCTION_SSH_KEY
```

#### Server Directory Structure
```bash
# On staging and production servers
sudo mkdir -p /opt/neurocore
sudo chown deploy:deploy /opt/neurocore
cd /opt/neurocore

# Create backup directory (production only)
mkdir -p backups

# Set up log directory
mkdir -p logs
```

## Usage

### Continuous Integration

Runs automatically on all pushes and pull requests. No manual action required.

### Deploy to Staging

**Automatic:**
```bash
git checkout develop
git commit -m "feat: new feature"
git push origin develop
# Automatically triggers staging deployment
```

**Manual:**
1. Go to **Actions > Deploy to Staging**
2. Click **Run workflow**
3. Select branch
4. Click **Run workflow**

### Deploy to Production

**Recommended: Version Tag**
```bash
# Create and push version tag
git checkout main
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
# Automatically triggers production deployment
```

**Manual:**
1. Go to **Actions > Deploy to Production**
2. Click **Run workflow**
3. Enter version (e.g., v1.0.0)
4. Click **Run workflow**
5. Approve the deployment in the **Environments** section

### Run Security Scan

**Manual:**
1. Go to **Actions > Security Audit**
2. Click **Run workflow**
3. Click **Run workflow**

## Monitoring

### Check Deployment Status

1. Go to **Actions** tab
2. Click on the workflow run
3. View job logs and status

### View Security Reports

1. Go to **Actions > Security Audit**
2. Click on the latest run
3. Download artifacts for detailed reports

### Production Health Checks

After deployment, verify:
```bash
# Health check
curl https://api.neurosurgery-kb.com/health

# Readiness check
curl https://api.neurosurgery-kb.com/ready

# Detailed health
curl https://api.neurosurgery-kb.com/health/detailed
```

## Troubleshooting

### Deployment Failed

1. Check workflow logs for errors
2. Verify secrets are correctly set
3. Test SSH connection manually:
   ```bash
   ssh -i ~/.ssh/github_deploy deploy@staging-server.example.com
   ```
4. Check server logs:
   ```bash
   cd /opt/neurocore
   docker compose logs -f
   ```

### Rollback Production

**Automatic Rollback:**
If smoke tests fail, automatic rollback is triggered.

**Manual Rollback:**
```bash
# SSH to production server
ssh deploy@production-server.example.com

# Navigate to project directory
cd /opt/neurocore

# View available backups
ls -lh backups/

# Restore specific backup
gunzip -c backups/backup-20250127-143000.sql.gz | \
  docker compose exec -T postgres psql -U neurosurgery_admin neurosurgery_kb

# Restart containers
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart
```

### CI Tests Failing

1. Run tests locally:
   ```bash
   # Backend
   pytest backend/tests/ -v

   # Frontend
   cd frontend && npm test
   ```

2. Check for dependency issues:
   ```bash
   pip install -r requirements.txt
   cd frontend && npm ci
   ```

3. Verify database migrations:
   ```bash
   cd backend
   alembic upgrade head
   ```

## Best Practices

### Version Tagging
- Use semantic versioning: `v1.0.0`, `v1.1.0`, `v2.0.0`
- Create annotated tags: `git tag -a v1.0.0 -m "Release v1.0.0"`
- Always tag from `main` branch

### Branch Strategy
- `main` - Production-ready code
- `develop` - Staging environment
- `feature/*` - Feature development
- `hotfix/*` - Production hotfixes

### Deployment Workflow
1. Develop on `feature/*` branches
2. Merge to `develop` via PR
3. Auto-deploy to staging
4. Test in staging environment
5. Merge to `main` via PR
6. Create version tag
7. Deploy to production with approval
8. Monitor production metrics

### Security
- Run security scans weekly
- Review all HIGH and CRITICAL vulnerabilities
- Keep dependencies up to date
- Rotate SSH keys quarterly
- Use strong passwords in production

## Maintenance

### Update Dependencies

```bash
# Python
pip list --outdated
pip install --upgrade <package>
pip freeze > requirements.txt

# Frontend
cd frontend
npm outdated
npm update
```

### Clean Up Old Images

```bash
# On servers
docker image prune -af --filter "until=168h"  # Remove images older than 1 week
```

### Monitor Disk Space

```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df
```

## Support

For issues or questions:
- Create an issue in this repository
- Check workflow logs in the Actions tab
- Review server logs: `docker compose logs`
- Contact DevOps team

---

**Last Updated:** January 2025
**Maintained by:** DevOps Team
**Status:** Production Ready ✅
