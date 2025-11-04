# Production Deployment Guide - Neurocore
## HTTPS, Security, and Production Configuration

---

## Table of Contents
1. [Step 1: HTTPS Configuration](#step-1-https-configuration)
2. [Step 2: JWT Secret Generation](#step-2-jwt-secret-generation)
3. [Step 3: API Keys Configuration](#step-3-api-keys-configuration)
4. [Step 4: Production URLs](#step-4-production-urls)
5. [Step 5: Rate Limiting Verification](#step-5-rate-limiting-verification)
6. [Complete Deployment Checklist](#complete-deployment-checklist)

---

## Step 1: HTTPS Configuration

### Prerequisites
- Domain name configured with DNS pointing to your server
- Ubuntu/Debian server with Docker installed
- Nginx installed on host machine
- Ports 80, 443 open in firewall

### 1.1: Install Certbot (Let's Encrypt)

```bash
# Install Certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Create webroot directory for certificate validation
sudo mkdir -p /var/www/certbot
```

### 1.2: Obtain SSL Certificates

```bash
# Replace with your actual domains
export API_DOMAIN="api.your-domain.com"
export APP_DOMAIN="app.your-domain.com"
export EMAIL="your-email@example.com"

# Obtain certificates for API
sudo certbot certonly --webroot \
  -w /var/www/certbot \
  -d $API_DOMAIN \
  --email $EMAIL \
  --agree-tos \
  --no-eff-email

# Obtain certificates for Frontend
sudo certbot certonly --webroot \
  -w /var/www/certbot \
  -d $APP_DOMAIN \
  --email $EMAIL \
  --agree-tos \
  --no-eff-email
```

### 1.3: Install Nginx Configuration

```bash
# Copy the nginx configuration
sudo cp deployment/nginx.conf /etc/nginx/sites-available/neurocore

# Update domains in the config
sudo sed -i "s/api.your-domain.com/$API_DOMAIN/g" /etc/nginx/sites-available/neurocore
sudo sed -i "s/app.your-domain.com/$APP_DOMAIN/g" /etc/nginx/sites-available/neurocore

# Enable the site
sudo ln -s /etc/nginx/sites-available/neurocore /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 1.4: Set Up Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot creates a systemd timer automatically
# Verify it's active
sudo systemctl status certbot.timer
```

### 1.5: Configure Docker for HTTPS

Update your `.env` file:
```bash
# Change HTTP to HTTPS
export API_URL=https://${API_DOMAIN}
export FRONTEND_URL=https://${APP_DOMAIN}
```

### 1.6: Update CORS Settings

Edit `backend/main.py` to allow your production frontend:
```python
origins = [
    "https://app.your-domain.com",  # Production frontend
    "http://localhost:3002",         # Local development (optional)
]
```

**✅ Step 1 Complete**: HTTPS is now configured with automatic certificate renewal.

---

## Step 2: JWT Secret Generation

### 2.1: Generate Cryptographically Secure Secret

```bash
# Generate a secure 256-bit (32-byte) JWT secret
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))"
```

**Example output:**
```
JWT_SECRET=5K8vX2pQ9mN7rS4tY6wZ1aB3cD0eF8gH2iJ4kL6mN9oP1qR3sT5uV7wX9yZ0
```

### 2.2: Update .env File

```bash
# Copy the generated secret to .env
# Replace the placeholder with your actual secret
export JWT_SECRET=5K8vX2pQ9mN7rS4tY6wZ1aB3cD0eF8gH2iJ4kL6mN9oP1qR3sT5uV7wX9yZ0

# Also set JWT expiry (24 hours recommended for production)
export JWT_EXPIRY_HOURS=24
export JWT_ALGORITHM=HS256
```

### 2.3: Verify JWT Configuration

```bash
# Check if JWT secret is properly set
docker exec neurocore-api python3 -c "
from backend.config import settings
assert len(settings.JWT_SECRET) >= 32, 'JWT secret too short!'
print('✅ JWT secret is properly configured')
print(f'   Length: {len(settings.JWT_SECRET)} characters')
print(f'   Expiry: {settings.JWT_EXPIRY_HOURS} hours')
"
```

**✅ Step 2 Complete**: JWT secret is cryptographically secure.

---

## Step 3: API Keys Configuration

### 3.1: Verify All Provider Keys

```bash
# Check which keys are configured
cat .env | grep -E "(OPENAI|ANTHROPIC|GOOGLE|PERPLEXITY)_API_KEY" | sed 's/=.*/=***/'
```

### 3.2: Set Production API Keys

Edit `.env` and add your production API keys:

```bash
# ==================== AI Providers ====================

# OpenAI (REQUIRED - for embeddings)
export OPENAI_API_KEY=sk-proj-...your-key...

# Anthropic Claude (REQUIRED - for synthesis)
export ANTHROPIC_API_KEY=sk-ant-...your-key...

# Google Gemini (REQUIRED - for research)
export GOOGLE_API_KEY=...your-key...

# Perplexity AI (OPTIONAL - for real-time research)
export PERPLEXITY_API_KEY=pplx-...your-key...
```

### 3.3: Validate API Keys

```bash
# Test OpenAI
docker exec neurocore-api python3 -c "
import openai
from backend.config import settings
client = openai.Client(api_key=settings.OPENAI_API_KEY)
try:
    client.models.list()
    print('✅ OpenAI API key valid')
except Exception as e:
    print(f'❌ OpenAI API key invalid: {e}')
"

# Test Anthropic
docker exec neurocore-api python3 -c "
import anthropic
from backend.config import settings
client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
try:
    client.messages.create(
        model='claude-3-haiku-20240307',
        max_tokens=10,
        messages=[{'role': 'user', 'content': 'Hi'}]
    )
    print('✅ Anthropic API key valid')
except Exception as e:
    print(f'❌ Anthropic API key invalid: {e}')
"

# Test Google Gemini
docker exec neurocore-api python3 -c "
import google.generativeai as genai
from backend.config import settings
genai.configure(api_key=settings.GOOGLE_API_KEY)
try:
    list(genai.list_models())
    print('✅ Google API key valid')
except Exception as e:
    print(f'❌ Google API key invalid: {e}')
"
```

**✅ Step 3 Complete**: All API keys are configured and validated.

---

## Step 4: Production URLs

### 4.1: Update Environment Variables

Edit `.env` file:

```bash
# ==================== Production URLs ====================

# API URL (with HTTPS)
export API_URL=https://api.your-domain.com

# Frontend URL (with HTTPS)
export FRONTEND_URL=https://app.your-domain.com

# CORS Origins (comma-separated)
export CORS_ORIGINS=https://app.your-domain.com

# API Port (internal, proxied by nginx)
export API_PORT=8002

# Frontend Port (internal, proxied by nginx)
export FRONTEND_PORT=3002
```

### 4.2: Update Frontend Environment

Edit `frontend/.env.production`:

```bash
# Create production environment file
cat > frontend/.env.production <<EOF
VITE_API_BASE_URL=https://api.your-domain.com
VITE_WS_BASE_URL=wss://api.your-domain.com
EOF
```

### 4.3: Update Frontend API Configuration

Check `frontend/src/utils/constants.js`:

```javascript
// Should read from environment variables
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002';
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8002';
```

### 4.4: Rebuild Frontend for Production

```bash
# Build production frontend
docker-compose build frontend

# Restart services
docker-compose up -d
```

**✅ Step 4 Complete**: Production URLs configured with HTTPS.

---

## Step 5: Rate Limiting Verification

### 5.1: Check Rate Limit Configuration

```bash
# Verify rate limiting in .env
cat .env | grep -E "RATE_LIMIT"
```

Expected output:
```bash
export RATE_LIMIT_ENABLED=true
export RATE_LIMIT_REQUESTS_PER_MINUTE=100
export RATE_LIMIT_BURST=20
```

### 5.2: Verify Rate Limit Service

```bash
# Check if rate limiting is active
docker exec neurocore-api python3 -c "
from backend.services.rate_limit_service import RateLimitService
from backend.database.connection import get_db

db_session = next(get_db())
rate_limiter = RateLimitService(db_session)
print('✅ Rate limiting service initialized')
print(f'   Redis connected: {rate_limiter.redis_client.ping()}')
"
```

### 5.3: Test Rate Limiting

```bash
# Test API rate limit (should succeed first, then hit limit)
for i in {1..10}; do
  response=$(curl -s -o /dev/null -w "%{http_code}" https://api.your-domain.com/health)
  echo "Request $i: HTTP $response"
  sleep 0.1
done
```

### 5.4: Monitor Rate Limit Metrics

```bash
# Check Redis for rate limit keys
docker exec neurocore-redis redis-cli KEYS "rate_limit:*" | head -10
```

**✅ Step 5 Complete**: Rate limiting is active and monitoring requests.

---

## Complete Deployment Checklist

### Pre-Deployment

- [ ] Domain DNS configured (A records for api and app subdomains)
- [ ] Server firewall configured (ports 80, 443, 22 open)
- [ ] Docker and Docker Compose installed
- [ ] Nginx installed on host
- [ ] Database backups configured

### Security Configuration

- [ ] **Step 1**: HTTPS certificates obtained and configured
- [ ] **Step 2**: Strong JWT secret generated (32+ characters)
- [ ] **Step 3**: All required API keys configured and validated
- [ ] **Step 4**: Production URLs set (HTTPS, not HTTP)
- [ ] **Step 5**: Rate limiting enabled and tested

### Application Configuration

- [ ] `.env` file updated with production values
- [ ] `DISABLE_AUTH=false` (authentication enabled)
- [ ] Database credentials are secure (not default passwords)
- [ ] Redis password set (optional but recommended)
- [ ] CORS origins restricted to production frontend
- [ ] Log level set to INFO or WARNING
- [ ] Sentry DSN configured (if using error tracking)

### Docker Configuration

- [ ] `docker-compose.yml` uses production-ready settings
- [ ] Volumes configured for persistent data
- [ ] Health checks enabled for all services
- [ ] Resource limits set (optional)
- [ ] Restart policy: `unless-stopped` or `always`

### Deployment Execution

```bash
# 1. Clone repository
git clone https://github.com/your-org/neurocore.git
cd neurocore

# 2. Configure environment
cp .env.example .env
# Edit .env with production values

# 3. Build and start services
docker-compose up -d --build

# 4. Wait for services to be healthy
docker-compose ps

# 5. Run database migrations
docker exec neurocore-api python3 -m alembic upgrade head

# 6. Verify deployment
curl https://api.your-domain.com/health
```

### Post-Deployment Verification

```bash
# 1. Check all services are running
docker-compose ps

# 2. Verify HTTPS
curl -I https://api.your-domain.com/health | grep "HTTP/2 200"

# 3. Test authentication
curl https://api.your-domain.com/api/v1/pdfs
# Should return: {"detail":"Missing authorization credentials"}

# 4. Check logs for errors
docker-compose logs --tail=50

# 5. Test frontend
curl -I https://app.your-domain.com | grep "HTTP/2 200"

# 6. Verify SSL grade
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=api.your-domain.com
```

### Monitoring Setup

```bash
# 1. Set up log rotation
cat > /etc/logrotate.d/neurocore <<EOF
/var/log/nginx/neurocore_*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 \`cat /var/run/nginx.pid\`
    endscript
}
EOF

# 2. Monitor Docker containers
docker stats --no-stream

# 3. Check database size
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT pg_size_pretty(pg_database_size('neurosurgery_kb')) as database_size;
"

# 4. Monitor Redis memory
docker exec neurocore-redis redis-cli INFO memory | grep used_memory_human
```

---

## Troubleshooting

### HTTPS Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew manually
sudo certbot renew --force-renewal

# Check nginx SSL configuration
sudo nginx -t
```

### Authentication Not Working

```bash
# Verify DISABLE_AUTH is false
docker exec neurocore-api env | grep DISABLE_AUTH

# Check JWT secret length
docker exec neurocore-api python3 -c "
from backend.config import settings
print(f'JWT secret length: {len(settings.JWT_SECRET)}')
"

# Test token generation
docker exec neurocore-api python3 -c "
from backend.utils.auth import create_access_token
token = create_access_token({'user_id': 'test'})
print(f'Token generated: {token[:20]}...')
"
```

### Rate Limiting Issues

```bash
# Check Redis connection
docker exec neurocore-redis redis-cli PING

# Check rate limit keys
docker exec neurocore-redis redis-cli KEYS "rate_limit:*"

# Clear rate limits (if needed)
docker exec neurocore-redis redis-cli FLUSHDB
```

### Performance Issues

```bash
# Check container resource usage
docker stats

# Check database connections
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT count(*) FROM pg_stat_activity;
"

# Check slow queries
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"
```

---

## Security Best Practices

1. **Regular Updates**
   ```bash
   # Update Docker images monthly
   docker-compose pull
   docker-compose up -d
   ```

2. **Database Backups**
   ```bash
   # Daily automated backups
   docker exec neurocore-postgres pg_dump -U nsurg_admin neurosurgery_kb | gzip > backup_$(date +%Y%m%d).sql.gz
   ```

3. **Secret Rotation**
   - Rotate JWT secret every 90 days
   - Rotate API keys if compromised
   - Update SSL certificates automatically (Let's Encrypt)

4. **Monitoring**
   - Set up Sentry for error tracking
   - Monitor disk space (Docker volumes)
   - Set up uptime monitoring (UptimeRobot, Pingdom)

5. **Firewall Rules**
   ```bash
   # Allow only necessary ports
   sudo ufw allow 22/tcp   # SSH
   sudo ufw allow 80/tcp   # HTTP (for Let's Encrypt)
   sudo ufw allow 443/tcp  # HTTPS
   sudo ufw enable
   ```

---

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review this guide thoroughly
- Check GitHub issues: https://github.com/your-org/neurocore/issues

**Deployment Status**: Ready for production with all security measures in place.
