# Backup and Recovery Documentation

Comprehensive backup and recovery procedures for the Neurocore application.

## Overview

The backup system provides multiple backup strategies:
- **Database Backup**: PostgreSQL database with vector embeddings
- **Files Backup**: Uploaded PDFs and images
- **Full Backup**: Database + Files + Configuration + Docker volumes
- **Automated Backups**: Scheduled via cron jobs

## Backup Scripts

### 1. Database Backup

**Script**: `backup-database.sh`

Creates compressed PostgreSQL backups with metadata.

```bash
# Manual backup
./backup-database.sh

# Named backup
./backup-database.sh my-backup-name

# Custom configuration
BACKUP_DIR=/custom/path BACKUP_RETAIN=20 ./backup-database.sh
```

**Features**:
- Compressed with gzip
- Includes all tables, indexes, and vector data
- Automatic retention management (default: 10 backups)
- Integrity verification
- Metadata file with backup details

**Default Location**: `/opt/neurocore/backups/database/`

### 2. Files Backup

**Script**: `backup-files.sh`

Creates compressed archives of uploaded files (PDFs, images).

```bash
# Manual backup
./backup-files.sh

# Named backup
./backup-files.sh my-files-backup

# Custom configuration
BACKUP_DIR=/custom/path BACKUP_RETAIN=7 ./backup-files.sh
```

**Features**:
- Compressed tar.gz archive
- Includes PDFs and images
- Automatic retention management (default: 7 backups)
- Compression ratio reporting
- Metadata file with file counts

**Default Location**: `/opt/neurocore/backups/files/`

### 3. Full Backup

**Script**: `backup-full.sh`

Creates comprehensive backup of entire system.

```bash
# Manual full backup
./backup-full.sh

# Named full backup
./backup-full.sh production-backup-before-upgrade
```

**Includes**:
- Complete database dump
- All uploaded files (PDFs, images)
- Configuration files (.env, docker-compose.yml)
- Docker volume backups (Prometheus, Grafana data)
- Backup manifest with checksums

**Features**:
- Comprehensive system snapshot
- SHA256 checksums for verification
- System information capture
- Automatic retention management (default: 5 backups)
- Detailed manifest file

**Default Location**: `/opt/neurocore/backups/full/`

## Restore Scripts

### 1. Database Restore

**Script**: `restore-database.sh`

Restores PostgreSQL database from backup.

```bash
# Restore from backup file
./restore-database.sh /opt/neurocore/backups/database/backup-20250127-143000.sql.gz

# Force restore without confirmation
FORCE_RESTORE=true ./restore-database.sh /path/to/backup.sql.gz
```

**Process**:
1. Verifies backup integrity
2. Creates pre-restore backup
3. Stops application containers
4. Terminates active connections
5. Drops and recreates database
6. Restores from backup
7. Enables extensions (vector, pg_trgm)
8. Runs migrations
9. Verifies restore
10. Restarts application

**⚠️ WARNING**: This will **OVERWRITE** the current database!

### 2. Files Restore

**Script**: `restore-files.sh`

Restores uploaded files from backup.

```bash
# Restore from backup file
./restore-files.sh /opt/neurocore/backups/files/files-backup-20250127-143000.tar.gz

# Force restore without confirmation
FORCE_RESTORE=true ./restore-files.sh /path/to/backup.tar.gz
```

**Process**:
1. Verifies backup integrity
2. Creates pre-restore backup
3. Stops application containers
4. Extracts files to target directories
5. Sets correct permissions
6. Verifies file counts
7. Restarts application

**⚠️ WARNING**: This will **OVERWRITE** existing files!

## Automated Backups

### Setup Cron Jobs

Add to crontab for automated backups:

```bash
# Edit crontab
crontab -e

# Add backup schedules
# Daily database backup at 2:00 AM
0 2 * * * /opt/neurocore/scripts/backup/backup-database.sh >> /var/log/neurocore/backup-database.log 2>&1

# Weekly files backup on Sunday at 3:00 AM
0 3 * * 0 /opt/neurocore/scripts/backup/backup-files.sh >> /var/log/neurocore/backup-files.log 2>&1

# Monthly full backup on 1st of month at 4:00 AM
0 4 1 * * /opt/neurocore/scripts/backup/backup-full.sh >> /var/log/neurocore/backup-full.log 2>&1
```

### Setup SystemD Timers (Alternative)

Create timer units for more advanced scheduling:

```bash
# Create backup timer
sudo systemctl edit --force --full neurocore-backup.timer

# Add timer configuration
[Unit]
Description=Neurocore Daily Backup Timer

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target

# Enable and start timer
sudo systemctl enable neurocore-backup.timer
sudo systemctl start neurocore-backup.timer
```

## Backup Best Practices

### 1. Backup Frequency

Recommended schedule:
- **Database**: Daily (automated)
- **Files**: Weekly (automated)
- **Full**: Monthly (automated) + Before major updates (manual)

### 2. Retention Policy

Default retention:
- Database backups: 10 days
- Files backups: 7 weeks
- Full backups: 5 months

Adjust based on:
- Available disk space
- Compliance requirements
- Data change frequency

### 3. Backup Verification

Always verify backups:

```bash
# Test database backup integrity
gzip -t /path/to/backup.sql.gz

# Test files backup integrity
tar -tzf /path/to/backup.tar.gz > /dev/null

# Check backup metadata
cat /path/to/backup.sql.gz.meta
```

### 4. Off-site Backups

Copy backups to remote location:

```bash
# Sync to remote server
rsync -avz --delete \
  /opt/neurocore/backups/ \
  backup-server:/backups/neurocore/

# Sync to S3
aws s3 sync \
  /opt/neurocore/backups/ \
  s3://neurocore-backups/ \
  --delete

# Sync to Google Cloud Storage
gsutil -m rsync -r -d \
  /opt/neurocore/backups/ \
  gs://neurocore-backups/
```

### 5. Backup Monitoring

Monitor backup success:

```bash
# Check last backup time
ls -lht /opt/neurocore/backups/database/ | head -2

# Check backup logs
tail -f /var/log/neurocore/backup-database.log

# Alert on old backups
find /opt/neurocore/backups/database/ -name "backup-*.sql.gz" -mtime +2 -exec echo "Old backup: {}" \;
```

## Disaster Recovery Procedures

### Scenario 1: Database Corruption

```bash
# 1. Stop application
docker compose stop api celery-worker

# 2. Restore from latest backup
./restore-database.sh /opt/neurocore/backups/database/backup-latest.sql.gz

# 3. Verify database
docker exec neurocore_postgres psql -U neurosurgery_admin -d neurosurgery_kb -c "SELECT COUNT(*) FROM users;"

# 4. Start application
docker compose start api celery-worker

# 5. Verify application
curl http://localhost:8002/health
```

### Scenario 2: Lost Files

```bash
# 1. Stop application
docker compose stop api

# 2. Restore from latest backup
./restore-files.sh /opt/neurocore/backups/files/files-backup-latest.tar.gz

# 3. Verify files
ls -lR /opt/neurocore/data/pdfs/
ls -lR /opt/neurocore/data/images/

# 4. Start application
docker compose start api

# 5. Verify file access
curl http://localhost:8002/api/v1/pdfs
```

### Scenario 3: Complete System Failure

```bash
# 1. Restore infrastructure
# - Provision new server
# - Install Docker and Docker Compose
# - Clone repository
# - Restore .env file from backup

# 2. Start database
docker compose up -d postgres redis

# 3. Restore database
./restore-database.sh /path/to/backup/database.sql.gz

# 4. Restore files
./restore-files.sh /path/to/backup/files.tar.gz

# 5. Start all services
docker compose up -d

# 6. Verify system
./scripts/health-check.sh
```

## Backup Security

### Encryption

Encrypt sensitive backups:

```bash
# Encrypt backup
gpg --symmetric --cipher-algo AES256 backup.sql.gz

# Decrypt backup
gpg --decrypt backup.sql.gz.gpg > backup.sql.gz
```

### Access Control

Restrict backup access:

```bash
# Set backup directory permissions
chmod 700 /opt/neurocore/backups
chown root:root /opt/neurocore/backups

# Restrict script permissions
chmod 750 /opt/neurocore/scripts/backup/*.sh
```

### Backup Integrity

Verify backup checksums:

```bash
# Generate checksum
sha256sum backup.sql.gz > backup.sql.gz.sha256

# Verify checksum
sha256sum -c backup.sql.gz.sha256
```

## Testing Backups

### Regular Backup Testing

Test backups monthly:

```bash
# 1. Create test environment
docker compose -f docker-compose.test.yml up -d

# 2. Restore backup to test environment
DB_CONTAINER=test_postgres ./restore-database.sh /path/to/backup.sql.gz

# 3. Verify data integrity
docker exec test_postgres psql -U test_user -d test_db -c "SELECT COUNT(*) FROM users;"

# 4. Clean up
docker compose -f docker-compose.test.yml down -v
```

## Troubleshooting

### Backup Failed

```bash
# Check disk space
df -h /opt/neurocore/backups

# Check permissions
ls -la /opt/neurocore/backups

# Check container status
docker ps -a | grep neurocore

# Check logs
docker compose logs postgres
```

### Restore Failed

```bash
# Verify backup integrity
gzip -t backup.sql.gz
tar -tzf backup.tar.gz

# Check database logs
docker compose logs postgres

# Check application logs
docker compose logs api

# Rollback using pre-restore backup
./restore-database.sh /tmp/pre-restore-*.sql.gz
```

### Slow Backups

```bash
# Use parallel compression
pigz backup.sql > backup.sql.gz

# Exclude unnecessary data
pg_dump --exclude-table-data=logs ...

# Increase backup retention
BACKUP_RETAIN=30 ./backup-database.sh
```

## Monitoring

### Backup Metrics

Track backup metrics in Prometheus:

```promql
# Backup age (hours)
(time() - file_mtime{path="/opt/neurocore/backups/database/backup-*.sql.gz"}) / 3600

# Backup size (bytes)
file_size_bytes{path="/opt/neurocore/backups/database/backup-*.sql.gz"}

# Backup success rate
rate(backup_success_total[24h])
```

### Grafana Dashboard

Create dashboard with:
- Last backup time
- Backup size over time
- Backup success/failure rate
- Disk space usage
- Backup age alerts

## Support

For backup issues:
1. Check backup logs: `/var/log/neurocore/backup-*.log`
2. Verify disk space: `df -h`
3. Test backup integrity: `gzip -t backup.sql.gz`
4. Review documentation
5. Contact DevOps team

---

**Last Updated:** January 2025
**Maintained by:** DevOps Team
**Status:** Production Ready ✅
