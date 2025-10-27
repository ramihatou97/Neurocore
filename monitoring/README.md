# Monitoring Stack Documentation

Comprehensive monitoring, logging, and alerting for the Neurocore application using Prometheus, Grafana, Loki, and AlertManager.

## Overview

The monitoring stack provides:
- **Metrics Collection**: Prometheus for application and infrastructure metrics
- **Visualization**: Grafana for dashboards and data exploration
- **Log Aggregation**: Loki for centralized log management
- **Alerting**: AlertManager for intelligent alert routing
- **System Metrics**: Node Exporter for host metrics
- **Container Metrics**: cAdvisor for Docker container monitoring

## Architecture

```
┌─────────────────┐
│   Application   │
│  (FastAPI API)  │──────┐
└─────────────────┘      │
                         │  Metrics
┌─────────────────┐      │
│    Database     │      │
│  (PostgreSQL)   │──────┤
└─────────────────┘      │
                         │
┌─────────────────┐      │    ┌──────────────┐
│     Cache       │      ├───→│  Prometheus  │
│    (Redis)      │──────┘    │  (Metrics)   │
└─────────────────┘           └──────┬───────┘
                                     │
┌─────────────────┐                  │
│   Containers    │                  │
│   (cAdvisor)    │──────────────────┤
└─────────────────┘                  │
                                     │
┌─────────────────┐                  ▼
│   Host System   │           ┌──────────────┐
│ (Node Exporter) │──────────→│   Grafana    │
└─────────────────┘           │  (Visualize) │
                              └──────────────┘
┌─────────────────┐                  ▲
│   Docker Logs   │                  │
│   (Promtail)    │───────┐          │
└─────────────────┘        │          │
                           ▼          │
                    ┌──────────────┐  │
                    │     Loki     │──┘
                    │    (Logs)    │
                    └──────────────┘
```

## Components

### Prometheus (Port 9091)
- **Purpose**: Metrics collection and storage
- **Scrape Interval**: 15 seconds
- **Retention**: 30 days
- **Targets**:
  - Neurocore API
  - PostgreSQL
  - Redis
  - Celery workers
  - Node Exporter (system metrics)
  - cAdvisor (container metrics)
  - Monitoring stack itself

### Grafana (Port 3003)
- **Purpose**: Visualization and dashboarding
- **Default Credentials**: admin / SecureGrafanaPassword2025!
- **Datasources**:
  - Prometheus (default)
  - Loki
  - PostgreSQL
  - AlertManager
- **Pre-configured Dashboards**:
  - Application Performance
  - Infrastructure Health
  - Database Monitoring
  - Log Exploration

### Loki (Port 3101)
- **Purpose**: Log aggregation and querying
- **Retention**: 31 days
- **Log Sources**:
  - Docker containers
  - Application logs
  - System logs
  - Nginx access logs

### Promtail
- **Purpose**: Log shipping to Loki
- **Collects From**:
  - Docker container logs
  - System logs (/var/log)
  - Application-specific logs

### AlertManager (Port 9093)
- **Purpose**: Alert routing and notification
- **Notification Channels**:
  - Slack
  - Email
  - PagerDuty (optional)
  - Webhooks (optional)

### Node Exporter (Port 9101)
- **Purpose**: Host system metrics
- **Metrics**:
  - CPU usage
  - Memory usage
  - Disk I/O
  - Network statistics
  - Filesystem usage

### cAdvisor (Port 8081)
- **Purpose**: Container metrics
- **Metrics**:
  - Container CPU usage
  - Container memory usage
  - Container network I/O
  - Container filesystem usage

## Installation

### 1. Prerequisites

```bash
# Ensure main application is running
docker compose -f docker-compose.yml up -d

# Create monitoring directories
mkdir -p monitoring/{prometheus,grafana,loki,promtail,alertmanager}
mkdir -p monitoring/grafana/{provisioning/{datasources,dashboards},dashboards/{application,infrastructure,database,monitoring}}
```

### 2. Configure Environment Variables

Add to `.env`:

```bash
# Grafana
GRAFANA_ADMIN_PASSWORD=SecureGrafanaPassword2025!

# AlertManager (optional)
SMTP_PASSWORD=your-smtp-password
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
PAGERDUTY_SERVICE_KEY=your-pagerduty-key

# Database (for Grafana datasource)
POSTGRES_PASSWORD=your-postgres-password
```

### 3. Start Monitoring Stack

```bash
# Start monitoring stack
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Verify all services are running
docker compose -f docker-compose.monitoring.yml ps

# Check logs
docker compose -f docker-compose.monitoring.yml logs -f
```

### 4. Access Services

- **Grafana**: http://localhost:3003
- **Prometheus**: http://localhost:9091
- **AlertManager**: http://localhost:9093
- **cAdvisor**: http://localhost:8081

## Usage

### Grafana Dashboard

1. **Login**: http://localhost:3003
   - Username: `admin`
   - Password: Set in `.env` (default: `SecureGrafanaPassword2025!`)

2. **Explore Dashboards**:
   - Navigate to **Dashboards** → **Browse**
   - Select folder: Neurocore, Infrastructure, Database, or Monitoring

3. **Create Custom Dashboard**:
   - Click **+** → **Dashboard** → **Add new panel**
   - Select datasource (Prometheus or Loki)
   - Build queries and visualizations

### Prometheus Queries

Access Prometheus at http://localhost:9091

**Example Queries**:

```promql
# API request rate
rate(http_requests_total[5m])

# API response time (95th percentile)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Database connections
pg_stat_database_numbackends{datname="neurosurgery_kb"}

# Redis memory usage
redis_memory_used_bytes

# CPU usage by container
rate(container_cpu_usage_seconds_total[5m]) * 100

# Memory usage by container
container_memory_usage_bytes / container_spec_memory_limit_bytes * 100

# Disk space available
(node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100
```

### Loki Log Queries

Use Grafana's **Explore** feature with Loki datasource

**Example Queries**:

```logql
# All API logs
{container="neurocore_api"}

# Error logs only
{container="neurocore_api"} |= "ERROR"

# Logs for specific request ID
{container="neurocore_api"} |= "request_id=123-456-789"

# Database query logs
{container="neurocore_postgres"} |= "SELECT"

# Nginx access logs with 500 status
{container="neurocore_frontend"} |= "500"

# Count error rate
sum(rate({container="neurocore_api"} |= "ERROR" [5m]))

# Pattern extraction
{container="neurocore_api"} | pattern `<timestamp> <level> <message>`
```

### Alerting

#### View Active Alerts

1. **In Grafana**: Navigate to **Alerting** → **Alert rules**
2. **In Prometheus**: http://localhost:9091/alerts
3. **In AlertManager**: http://localhost:9093

#### Configure Alert Routes

Edit `monitoring/alertmanager/alertmanager.yml`:

```yaml
route:
  receiver: 'your-receiver'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
```

#### Test Alerts

```bash
# Trigger a test alert
curl -X POST http://localhost:9093/api/v1/alerts -d '[{
  "labels": {
    "alertname": "TestAlert",
    "severity": "warning",
    "service": "test"
  },
  "annotations": {
    "summary": "Test alert",
    "description": "This is a test alert"
  }
}]'
```

## Maintenance

### Update Configuration

After modifying configuration files:

```bash
# Reload Prometheus configuration
curl -X POST http://localhost:9091/-/reload

# Reload AlertManager configuration
curl -X POST http://localhost:9093/-/reload

# Restart specific service
docker compose -f docker-compose.monitoring.yml restart prometheus
```

### Backup Metrics

```bash
# Create backup directory
mkdir -p backups/monitoring

# Backup Prometheus data
docker compose -f docker-compose.monitoring.yml exec prometheus \
  tar czf /tmp/prometheus-backup.tar.gz /prometheus
docker cp neurocore_prometheus:/tmp/prometheus-backup.tar.gz \
  backups/monitoring/prometheus-$(date +%Y%m%d).tar.gz

# Backup Grafana dashboards
docker compose -f docker-compose.monitoring.yml exec grafana \
  tar czf /tmp/grafana-backup.tar.gz /var/lib/grafana
docker cp neurocore_grafana:/tmp/grafana-backup.tar.gz \
  backups/monitoring/grafana-$(date +%Y%m%d).tar.gz
```

### Clean Up Old Data

```bash
# Prometheus retains data for 30 days automatically
# To manually clean up old data:
docker compose -f docker-compose.monitoring.yml stop prometheus
docker volume rm neurocore_prometheus_data
docker compose -f docker-compose.monitoring.yml up -d prometheus

# Loki retains logs for 31 days automatically
# To manually clean up old logs:
docker compose -f docker-compose.monitoring.yml stop loki
docker volume rm neurocore_loki_data
docker compose -f docker-compose.monitoring.yml up -d loki
```

### Monitor Monitoring Stack

```bash
# Check disk usage
docker system df -v

# Check container stats
docker stats

# View logs
docker compose -f docker-compose.monitoring.yml logs -f prometheus
docker compose -f docker-compose.monitoring.yml logs -f grafana
docker compose -f docker-compose.monitoring.yml logs -f loki
```

## Troubleshooting

### Prometheus Not Scraping Targets

1. **Check target status**: http://localhost:9091/targets
2. **Verify network connectivity**:
   ```bash
   docker compose -f docker-compose.monitoring.yml exec prometheus \
     wget -O- http://api:8000/api/v1/performance/metrics
   ```
3. **Check service is exposing metrics**: http://localhost:8002/api/v1/performance/metrics

### Grafana Can't Connect to Datasources

1. **Check datasource configuration**: Grafana → Configuration → Data Sources
2. **Test connection**: Click "Save & Test" on datasource
3. **Verify network**: Ensure `neurocore_network` exists and services are connected

### Loki Not Receiving Logs

1. **Check Promtail status**:
   ```bash
   docker compose -f docker-compose.monitoring.yml logs promtail
   ```
2. **Verify log paths exist**:
   ```bash
   docker compose -f docker-compose.monitoring.yml exec promtail \
     ls -la /var/lib/docker/containers
   ```
3. **Test Loki endpoint**:
   ```bash
   curl http://localhost:3101/ready
   ```

### High Resource Usage

1. **Adjust scrape intervals** in `prometheus.yml`
2. **Reduce retention periods**:
   - Prometheus: `--storage.tsdb.retention.time=15d`
   - Loki: `retention_period: 360h` (15 days)
3. **Limit log ingestion** in `loki-config.yaml`:
   ```yaml
   limits_config:
     ingestion_rate_mb: 5
     ingestion_burst_size_mb: 10
   ```

## Best Practices

### Metrics

1. **Use labels sparingly**: High cardinality labels can impact performance
2. **Aggregate at query time**: Use PromQL functions like `sum()`, `avg()`
3. **Set appropriate retention**: Balance storage vs historical data needs
4. **Monitor monitoring**: Watch Prometheus and Grafana resource usage

### Logs

1. **Structure logs**: Use JSON format for easier parsing
2. **Add context**: Include request IDs, user IDs, trace IDs
3. **Set appropriate log levels**: DEBUG in dev, INFO in staging, WARNING in prod
4. **Rotate logs**: Configure log rotation to prevent disk filling

### Alerts

1. **Avoid alert fatigue**: Only alert on actionable issues
2. **Use severity levels**: Critical, warning, info
3. **Group related alerts**: Use `group_by` in AlertManager
4. **Document runbooks**: Add links to resolution procedures

### Security

1. **Change default passwords**: Update Grafana admin password
2. **Enable authentication**: Configure OAuth, LDAP, or SAML
3. **Restrict network access**: Use firewalls, VPNs
4. **Audit access**: Review Grafana audit logs regularly
5. **Encrypt traffic**: Use TLS for production deployments

## Integration with CI/CD

The monitoring stack integrates with the CI/CD pipeline:

- **Health checks** are verified during deployment
- **Metrics** are checked post-deployment
- **Alerts** are created for deployment issues
- **Dashboards** track deployment metrics

See `.github/workflows/` for CI/CD integration details.

## Support

For issues or questions:
- Check logs: `docker compose -f docker-compose.monitoring.yml logs`
- Review metrics: http://localhost:9091
- Explore dashboards: http://localhost:3003
- Contact DevOps team

---

**Last Updated:** January 2025
**Maintained by:** DevOps Team
**Status:** Production Ready ✅
