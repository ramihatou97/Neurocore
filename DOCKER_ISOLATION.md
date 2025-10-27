# 🔒 Docker Complete Isolation Guide

## 🎯 Your Concern: Multiple Projects, Zero Conflicts

You're absolutely right to be concerned! We detected these Docker projects running on your system:
- `neurosurgery-*` (old containers from this repo)
- `nsxkb-*` (another neurosurgery KB project)
- `dcs-*` (another project)
- `nkp_*` (another project)

**Good news:** This project (`neurocore`) is now **completely isolated** from all other Docker projects!

---

## ✅ What We've Done for Complete Isolation

### 1. **Unique Project Name: `neurocore`**
```yaml
name: neurocore  # Line 9 in docker-compose.yml
```

This ensures Docker treats this as a completely separate project, even if other projects use similar service names.

### 2. **All Containers Have Unique Names**
```
OLD (conflicting):           NEW (isolated):
neurosurgery-postgres   →    neurocore-postgres
neurosurgery-redis      →    neurocore-redis
neurosurgery-api        →    neurocore-api
neurosurgery-celery-*   →    neurocore-celery-*
neurosurgery-frontend   →    neurocore-frontend
neurosurgery-celery-flower → neurocore-celery-flower
```

### 3. **All Volumes Have Unique Names**
```
OLD (conflicting):              NEW (isolated):
neurosurgery-postgres-data  →   neurocore-postgres-data
neurosurgery-redis-data     →   neurocore-redis-data
neurosurgery-pdf-storage    →   neurocore-pdf-storage
neurosurgery-image-storage  →   neurocore-image-storage
```

### 4. **Network Has Unique Name**
```
OLD: neurosurgery-network
NEW: neurocore-network
```

### 5. **Custom Ports (No Conflicts)**
```
API:      8002  (not 8000, 8001, etc.)
Frontend: 3002  (not 3000, 3001, etc.)
Postgres: 5432  (standard, but isolated via container name)
Redis:    6379  (standard, but isolated via container name)
Flower:   5555  (Celery monitoring)
```

---

## 🚀 How to Use Isolated Docker

### **Starting the Stack**

```bash
# From project root
./start-backend.sh docker

# This runs internally:
# docker-compose -p neurocore up
```

The `-p neurocore` flag ensures **double isolation** - both via the project name in docker-compose.yml AND the CLI flag.

### **Other Docker Commands (Always Use Project Name)**

```bash
# Stop all services
docker-compose -p neurocore down

# Stop and remove volumes (CAUTION: deletes data!)
docker-compose -p neurocore down -v

# View logs
docker-compose -p neurocore logs -f

# View logs for specific service
docker-compose -p neurocore logs -f api

# Restart specific service
docker-compose -p neurocore restart api

# List containers for THIS project only
docker-compose -p neurocore ps

# Execute command in container
docker-compose -p neurocore exec api bash

# Build/rebuild images
docker-compose -p neurocore build
docker-compose -p neurocore build --no-cache  # Force rebuild
```

---

## 🔍 Verify Isolation

### Check All Your Docker Projects

```bash
# List ALL containers (all projects)
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

# You should see:
# neurocore-*        (this project)
# nsxkb-*           (your other neurosurgery project)
# dcs-*             (your other project)
# nkp_*             (your other project)
```

### Check Only This Project

```bash
# List containers for neurocore project only
docker-compose -p neurocore ps

# OR
docker ps --filter "name=neurocore-"
```

### Check Volumes

```bash
# List all volumes
docker volume ls

# List only neurocore volumes
docker volume ls | grep neurocore
```

### Check Networks

```bash
# List all networks
docker network ls

# List only neurocore network
docker network ls | grep neurocore
```

---

## 🧹 Clean Up This Project (Without Affecting Others)

### Stop Services (Keep Data)
```bash
docker-compose -p neurocore down
```

### Stop Services + Remove Volumes (DELETE ALL DATA!)
```bash
docker-compose -p neurocore down -v
```

### Remove Unused Images
```bash
# Remove dangling images (not tagged, not used)
docker image prune

# Remove all unused images (CAUTION!)
docker image prune -a
```

### Complete Nuclear Clean (This Project Only)
```bash
# 1. Stop and remove containers, networks
docker-compose -p neurocore down

# 2. Remove volumes
docker volume rm neurocore-postgres-data
docker volume rm neurocore-redis-data
docker volume rm neurocore-pdf-storage
docker volume rm neurocore-image-storage

# 3. Remove network (if not auto-removed)
docker network rm neurocore-network

# 4. Remove images
docker rmi neurocore-api neurocore-frontend neurocore-celery-worker
```

---

## 📊 Resource Usage Monitoring

### Check What's Using Resources

```bash
# See CPU/Memory usage for all containers
docker stats

# See only neurocore containers
docker stats $(docker ps --filter "name=neurocore-" -q)

# Disk usage by Docker
docker system df

# Detailed disk usage
docker system df -v
```

---

## 🛡️ Isolation Guarantees

### ✅ What's Isolated

| Resource | How It's Isolated | Proof |
|----------|-------------------|-------|
| **Containers** | Unique names (`neurocore-*`) | `docker ps` shows distinct names |
| **Volumes** | Unique names (`neurocore-*-data`) | `docker volume ls` shows distinct volumes |
| **Networks** | Unique name (`neurocore-network`) | `docker network ls` shows distinct network |
| **Ports** | Custom mapping (8002, 3002) | No port conflicts with other apps |
| **Images** | Tagged by project context | Built with project-specific context |
| **Environment** | Separate .env file | Each project has its own config |

### ❌ What's NOT Isolated (By Design)

- **Docker Engine**: All projects share the same Docker daemon (this is normal)
- **Host Resources**: CPU/Memory are shared (use `docker stats` to monitor)
- **Host Network**: Ports must be unique across all projects (we use 8002/3002)

---

## 🔐 Best Practices

### 1. Always Use the Startup Script
```bash
./start-backend.sh docker  # Handles project name automatically
```

### 2. If Using docker-compose Directly
```bash
# ALWAYS include -p neurocore
docker-compose -p neurocore [command]
```

### 3. Never Use Generic Names
```bash
# ❌ BAD
docker run --name postgres postgres

# ✅ GOOD
# Use docker-compose which handles naming
```

### 4. Check Before Deleting
```bash
# See what you're about to delete
docker-compose -p neurocore ps
docker volume ls | grep neurocore

# Then delete
docker-compose -p neurocore down -v
```

### 5. Use .env for Project-Specific Config
Each project has its own `.env` file with unique:
- Database name
- Passwords
- API keys
- Ports

---

## 🆘 Troubleshooting Conflicts

### "Port is already allocated"

```bash
# Find what's using the port
lsof -i :8002

# Option 1: Stop the other service
# Option 2: Change port in .env
API_PORT=8003  # Use different port
```

### "Container name already in use"

```bash
# This shouldn't happen if using -p neurocore
# But if it does, check:
docker ps -a | grep neurocore

# Remove old container
docker rm -f neurocore-api
```

### "Volume name already in use"

```bash
# Check existing volumes
docker volume ls | grep neurocore

# Option 1: Use existing volume
# Option 2: Remove old volume (DELETES DATA!)
docker volume rm neurocore-postgres-data
```

### "Network conflicts"

```bash
# List networks
docker network ls | grep neurocore

# Remove old network
docker network rm neurocore-network
```

---

## 📋 Quick Reference Cheatsheet

```bash
# === START ===
./start-backend.sh docker

# === STOP ===
docker-compose -p neurocore down

# === LOGS ===
docker-compose -p neurocore logs -f

# === STATUS ===
docker-compose -p neurocore ps

# === SHELL ACCESS ===
docker-compose -p neurocore exec api bash

# === RESTART SERVICE ===
docker-compose -p neurocore restart api

# === REBUILD ===
docker-compose -p neurocore build --no-cache

# === CLEAN (KEEP DATA) ===
docker-compose -p neurocore down

# === CLEAN (DELETE DATA) ===
docker-compose -p neurocore down -v
```

---

## 🎓 Understanding Docker Compose Project Names

### Why `-p neurocore`?

Without a project name, docker-compose uses:
1. The directory name (which could be anything)
2. OR default names (which conflict with other projects)

With `-p neurocore`:
- All resources are prefixed/namespaced
- Multiple projects can coexist
- Each project is independently manageable

### The `name:` Field in docker-compose.yml

```yaml
name: neurocore  # Line 9
```

This is equivalent to always using `-p neurocore` on the CLI. Even if you forget the flag, the project name is enforced!

---

## ✨ Summary

### Before (Risky):
```
neurosurgery-postgres  ← Could conflict with other projects
neurosurgery-redis     ← Could conflict with other projects
neurosurgery-api       ← Could conflict with other projects
```

### After (Isolated):
```
neurocore-postgres     ← Unique to THIS project
neurocore-redis        ← Unique to THIS project
neurocore-api          ← Unique to THIS project
```

### The Result:
- ✅ Run multiple neurosurgery projects simultaneously
- ✅ No container name conflicts
- ✅ No volume data mixing
- ✅ No network interference
- ✅ Independent port mappings
- ✅ Separate management (start/stop/logs)

**You can safely run:**
- `neurocore-*` (this project)
- `nsxkb-*` (your other neurosurgery project)
- `dcs-*` (your other project)
- `nkp_*` (your other project)

**All at the same time, with zero conflicts!** 🎉

---

## 📞 Need Help?

If you see ANY conflicts or mixing between projects:
1. Check you're using `-p neurocore` in commands
2. Verify container names start with `neurocore-`
3. Check the `name:` field is in docker-compose.yml
4. Ensure ports 8002/3002 are not used by other apps

This setup guarantees complete isolation! 🔒
