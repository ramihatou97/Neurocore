# Production Operations Guide

Complete guide for deploying, operating, and maintaining the Neurocore application in production.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Initial Setup](#initial-setup)
5. [Deployment](#deployment)
6. [Monitoring](#monitoring)
7. [Backup & Recovery](#backup--recovery)
8. [Scaling](#scaling)
9. [Security](#security)
10. [Troubleshooting](#troubleshooting)
11. [Maintenance](#maintenance)
12. [Emergency Procedures](#emergency-procedures)

## Overview

**Neurocore** is a production-ready neurosurgery knowledge base with AI-powered features, comprehensive monitoring, and automated deployment capabilities.

### Key Features

- **Production-Grade Infrastructure**: Multi-stage Docker builds, resource limits, health checks
- **CI/CD Pipeline**: Automated testing, building, and deployment via GitHub Actions
- **Comprehensive Monitoring**: Prometheus, Grafana, Loki for metrics and logs
- **Automated Backups**: Database, files, and full system backups
- **Security Hardening**: Rate limiting, security headers, non-root containers
- **High Availability**: Health checks, automatic restarts, graceful shutdowns

### Technology Stack

- **Backend**: FastAPI (Python 3.11)
- **Frontend**: React + Vite
- **Database**: PostgreSQL 15 + pgvector
- **Cache**: Redis 7
- **Task Queue**: Celery + Redis
- **Monitoring**: Prometheus + Grafana + Loki
- **Deployment**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Load Balancer                        │
│                     (Nginx/HAProxy/AWS ELB)                 │
└────────────────────┬─────────────────────┬──────────────────┘
                     │                     │
         ┌───────────▼──────────┐  ┌──────▼───────────┐
         │   Frontend (Nginx)   │  │  API (FastAPI)   │
         │   Port: 3002         │  │  Port: 8002      │
         └──────────────────────┘  └────┬─────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────┐
         │                              │                  │
    ┌────▼─────┐              ┌────────▼────────┐  ┌─────▼──────┐
    │ Postgres │              │   Redis Cache    │  │   Celery   │
    │  +vector │              │   Port: 6381     │  │  Workers   │
    │Port: 5434│              └──────────────────┘  └────────────┘
    └──────────┘
         │
    ┌────▼─────────────────────────────────┐
    │        Monitoring Stack              │
    │  Prometheus │ Grafana │ Loki         │
    │  Port: 9091 │  3003   │ 3101         │
    └──────────────────────────────────────┘
```

### Port Allocation

**Neurocore Ports (Isolated)**:
- API: 8002
- Frontend: 3002
- PostgreSQL: 5434
- Redis: 6381
- Flower: 5555
- Prometheus: 9091
- Grafana: 3003
- Loki: 3101
- cAdvisor: 8081
- Node Exporter: 9101
- AlertManager: 9093

**Other Systems**:
- System PostgreSQL: 5432 (untouched)
- DCS Project: 5433, 6380, 3001, 5173 (preserved)

## Prerequisites

### Server Requirements

**Minimum** (Development/Staging):
- CPU: 4 cores
- RAM: 8 GB
- Disk: 100 GB SSD
- OS: Ubuntu 22.04 LTS or similar

**Recommended** (Production):
- CPU: 8+ cores
- RAM: 16+ GB
- Disk: 250+ GB SSD (RAID 10)
- OS: Ubuntu 22.04 LTS
- Network: 1 Gbps

### Software Requirements

```bash
# Docker
docker --version  # 24.0+

# Docker Compose
docker compose version  # 2.20+

# Git
git --version  # 2.30+

# Curl
curl --version  # 7.68+

# jq (for JSON parsing)
jq --version  # 1.6+
```

### External Services

- **OpenAI API Key**: For AI features
- **SMTP Server**: For email notifications (optional)
- **Slack Webhook**: For alerts (optional)
- **Domain/SSL**: For production deployment

## Initial Setup

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install utilities
sudo apt install -y jq bc curl git
```

### 2. Clone Repository

```bash
# Create application directory
sudo mkdir -p /opt/neurocore
sudo chown $USER:$USER /opt/neurocore

# Clone repository
cd /opt/neurocore
git clone https://github.com/your-org/neurosurgery-kb.git .
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env

# Required variables:
# - DB_PASSWORD
# - SECRET_KEY
# - OPENAI_API_KEY
# - SMTP_PASSWORD (if using email)
# - GRAFANA_ADMIN_PASSWORD
```

### 4. Create Data Directories

```bash
# Create data directories
mkdir -p data/pdfs
mkdir -p data/images
mkdir -p logs
mkdir -p backups/{database,files,full}

# Set permissions
chmod 755 data logs backups
```

### 5. Initialize Database

```bash
# Start database only
docker compose up -d postgres redis

# Wait for database to be ready
sleep 10

# Run migrations
docker compose run --rm api alembic upgrade head
```

### 6. Start Application

```bash
# Start all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## Deployment

### Automated Deployment (Recommended)

Using CI/CD pipeline:

```bash
# For staging (automatic on push to develop)
git checkout develop
git push origin develop
# Deployment starts automatically

# For production (requires version tag)
git checkout main
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
# Deployment starts, requires approval
```

### Manual Deployment

Using deployment script:

```bash
# Deploy to staging
./scripts/deploy/deploy.sh staging

# Deploy to production
./scripts/deploy/deploy.sh production v1.0.0
```

### Deployment Steps

The deployment process includes:

1. Pre-deployment backup
2. Pull latest code
3. Build Docker images
4. Run database migrations
5. Deploy new version
6. Wait for services
7. Health checks
8. Post-deployment tasks

### Deployment Verification

```bash
# Run health check
./scripts/deploy/health-check.sh

# Check logs
docker compose logs -f api

# Monitor metrics
open http://your-server:3003  # Grafana
```

## Monitoring

### Access Monitoring Dashboards

- **Grafana**: http://your-server:3003
  - Username: admin
  - Password: From `.env` (GRAFANA_ADMIN_PASSWORD)

- **Prometheus**: http://your-server:9091
- **AlertManager**: http://your-server:9093

### Key Metrics to Monitor

**Application Metrics**:
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (5xx responses)
- Active users

**Infrastructure Metrics**:
- CPU usage
- Memory usage
- Disk I/O
- Network traffic

**Database Metrics**:
- Active connections
- Query performance
- Replication lag (if applicable)
- Cache hit rate

**Business Metrics**:
- PDFs uploaded
- Chapters generated
- Search queries
- User registrations

### Setting Up Alerts

Edit `monitoring/prometheus/alerts.yml`:

```yaml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"
```

### Log Analysis

Using Loki in Grafana:

```logql
# View API errors
{container="neurocore_api"} |= "ERROR"

# Search by request ID
{container="neurocore_api"} |= "request_id=abc-123"

# Count error rate
sum(rate({container="neurocore_api"} |= "ERROR" [5m]))
```

## Backup & Recovery

### Automated Backups

Set up cron jobs:

```bash
# Edit crontab
crontab -e

# Daily database backup at 2 AM
0 2 * * * /opt/neurocore/scripts/backup/backup-database.sh >> /var/log/neurocore/backup-database.log 2>&1

# Weekly files backup on Sunday at 3 AM
0 3 * * 0 /opt/neurocore/scripts/backup/backup-files.sh >> /var/log/neurocore/backup-files.log 2>&1

# Monthly full backup on 1st of month at 4 AM
0 4 1 * * /opt/neurocore/scripts/backup/backup-full.sh >> /var/log/neurocore/backup-full.log 2>&1
```

### Manual Backups

```bash
# Database backup
./scripts/backup/backup-database.sh

# Files backup
./scripts/backup/backup-files.sh

# Full system backup
./scripts/backup/backup-full.sh
```

### Disaster Recovery

```bash
# Restore database
./scripts/backup/restore-database.sh /path/to/backup.sql.gz

# Restore files
./scripts/backup/restore-files.sh /path/to/backup.tar.gz

# Full system restore
./scripts/backup/restore-full.sh backup-name
```

## Scaling

### Vertical Scaling

Increase resources for existing containers:

```yaml
# In docker-compose.prod.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4.0'      # Increase from 2.0
          memory: 4G       # Increase from 2G
```

### Horizontal Scaling

Add more API workers:

```bash
# Scale API containers
docker compose up -d --scale api=3

# Scale Celery workers
docker compose up -d --scale celery-worker=5
```

### Database Scaling

For read-heavy workloads:

1. **Read Replicas**: Set up PostgreSQL replication
2. **Connection Pooling**: Use PgBouncer
3. **Query Optimization**: Add indexes, optimize queries

### Load Balancing

Use Nginx or HAProxy:

```nginx
upstream api_backend {
    least_conn;
    server 192.168.1.10:8002;
    server 192.168.1.11:8002;
    server 192.168.1.12:8002;
}

server {
    listen 80;
    location / {
        proxy_pass http://api_backend;
    }
}
```

## Security

### SSL/TLS Configuration

Use Let's Encrypt:

```bash
# Install certbot
sudo apt install certbot

# Obtain certificate
sudo certbot certonly --standalone -d api.neurosurgery-kb.com

# Configure Nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/api.neurosurgery-kb.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.neurosurgery-kb.com/privkey.pem;
}
```

### Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

### Security Best Practices

1. **Keep secrets secure**: Use environment variables, never commit secrets
2. **Regular updates**: Update dependencies and OS packages
3. **Access control**: Use SSH keys, disable password authentication
4. **Audit logs**: Review logs regularly for suspicious activity
5. **Backup encryption**: Encrypt sensitive backups
6. **Rate limiting**: Prevent abuse with rate limits
7. **HTTPS only**: Redirect all HTTP to HTTPS
8. **Security headers**: CSP, HSTS, X-Frame-Options (already configured)

## Troubleshooting

### Common Issues

#### API Not Responding

```bash
# Check container status
docker compose ps

# Check logs
docker compose logs api

# Restart API
docker compose restart api
```

#### Database Connection Errors

```bash
# Check database status
docker compose logs postgres

# Check connections
docker exec neurocore_postgres psql -U neurosurgery_admin -d neurosurgery_kb -c "SELECT count(*) FROM pg_stat_activity;"

# Restart database
docker compose restart postgres
```

#### High Memory Usage

```bash
# Check container stats
docker stats

# Identify memory hogs
docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep Up

# Adjust resource limits in docker-compose.prod.yml
```

#### Disk Space Full

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -af --volumes

# Clean old backups
find /opt/neurocore/backups -type f -mtime +30 -delete

# Clean logs
find /var/log -name "*.log" -mtime +7 -delete
```

### Getting Support

1. Check logs: `docker compose logs`
2. Review monitoring dashboards
3. Consult documentation
4. Contact DevOps team

## Maintenance

### Regular Maintenance Tasks

**Daily**:
- Monitor application metrics
- Check error logs
- Verify backups completed

**Weekly**:
- Review resource usage
- Check security updates
- Test backup restoration

**Monthly**:
- Update dependencies
- Review and rotate logs
- Performance optimization
- Capacity planning

### Update Procedure

```bash
# 1. Backup system
./scripts/backup/backup-full.sh

# 2. Pull updates
git fetch --all --tags
git checkout tags/v1.1.0

# 3. Deploy
./scripts/deploy/deploy.sh production v1.1.0

# 4. Verify
./scripts/deploy/health-check.sh
```

## Emergency Procedures

### Complete System Failure

```bash
# 1. Assess situation
docker compose ps
./scripts/deploy/health-check.sh

# 2. Try restart
docker compose restart

# 3. If restart fails, rollback
./scripts/deploy/rollback.sh production

# 4. If rollback fails, restore from backup
./scripts/backup/restore-database.sh /path/to/backup.sql.gz
./scripts/backup/restore-files.sh /path/to/backup.tar.gz
```

### Data Breach Response

1. **Isolate**: Disconnect affected systems
2. **Assess**: Determine scope and impact
3. **Contain**: Stop the breach
4. **Eradicate**: Remove threat
5. **Recover**: Restore from clean backups
6. **Review**: Analyze incident and prevent recurrence

### Contact Information

- **DevOps On-Call**: [Phone/Pager]
- **Security Team**: security@neurosurgery-kb.com
- **Management**: ops-manager@neurosurgery-kb.com

---

**Document Version**: 1.0
**Last Updated**: January 2025
**Maintained by**: DevOps Team
**Status**: Production Ready ✅

For additional documentation:
- [CI/CD Pipeline](.github/workflows/README.md)
- [Monitoring Stack](monitoring/README.md)
- [Backup & Recovery](scripts/backup/README.md)
- [API Documentation](http://your-server:8002/api/docs)
