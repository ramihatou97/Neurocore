# Database Migration Deployment Guide

**Issue Fixed:** Chapter delete functionality (version_metadata column mismatch)
**Date:** 2025-11-01
**Critical:** Read this before any database operations

---

## 🎯 What Was Fixed

**Problem:** Database column `chapter_versions.metadata` didn't match model expectation `version_metadata`
**Impact:** ALL chapter delete operations failed with 500 errors
**Solution:** Two-part fix for complete coverage

---

## 📋 Files Changed

### 1. Source Schema (Fixed for Future)
**File:** `backend/database/migrations/004_comprehensive_features.sql:34`
```sql
# BEFORE:
metadata JSONB DEFAULT '{}',

# AFTER:
version_metadata JSONB DEFAULT '{}',
```
**Why:** Ensures fresh deployments create the correct column from the start

### 2. Migration Script (Safety Net)
**File:** `backend/database/migrations/008_fix_chapter_versions_metadata_column.sql`
- Idempotent migration that renames `metadata` → `version_metadata`
- Checks if column already correct before renaming
- Safe to run multiple times

---

## 🔄 Deployment Scenarios

### Scenario A: Current Running System (YOU ARE HERE)

**Status:**
- ✅ Database manually fixed (ALTER TABLE applied)
- ✅ Docker volume `neurocore-postgres-data` persists the fix
- ✅ Delete functionality working

**Action Required:**
- ✅ **NONE** - System is already fixed and working
- ℹ️ Volume persists data, so fix remains across container restarts
- ⚠️ Only loses fix if you run `docker-compose down -v` (removes volumes)

**What Happens on Container Restart:**
```bash
docker-compose restart
# Result: Fix persists (volume-backed data unchanged)
```

### Scenario B: Fresh Deployment (New Environment)

**Status:**
- New database initialization
- No existing volumes
- Clean slate

**Action Required:**
- ✅ **NONE** - Automatic via docker-entrypoint-initdb.d
- Migrations 001-008 run in order automatically
- Column created correctly from start (004 fixed)
- 008 runs but finds column already correct

**What Happens:**
```bash
docker-compose up
# PostgreSQL initializes → Runs all .sql files in migrations/
# 001.sql → 002.sql → ... → 004.sql (creates version_metadata) → ... → 008.sql (redundant but safe)
# Result: Database ready with correct schema
```

### Scenario C: Database Rebuild (Volume Wipe)

**Status:**
- Intentional fresh start
- Removes all data including fix

**Action Required:**
```bash
# 1. Backup data if needed
docker exec neurocore-postgres pg_dump -U nsurg_admin neurosurgery_kb > backup.sql

# 2. Remove volumes
docker-compose down -v

# 3. Restart (fresh initialization)
docker-compose up

# Result: Fresh database with correct schema (same as Scenario B)
```

### Scenario D: Production Migration (Existing DB Without Fix)

**Status:**
- Existing deployment that never received the fix
- Database has wrong column name
- Cannot wipe and rebuild (has production data)

**Action Required - Manual Migration:**

```bash
# Option 1: Execute migration directly
docker exec -i neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb < \
  backend/database/migrations/008_fix_chapter_versions_metadata_column.sql

# Option 2: Interactive execution
docker exec -it neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb
# Then paste the migration SQL from 008_fix_chapter_versions_metadata_column.sql

# Option 3: Quick fix (same as what was done on current system)
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb \
  -c "ALTER TABLE chapter_versions RENAME COLUMN metadata TO version_metadata;"

# Verification:
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb \
  -c "\d chapter_versions" | grep version_metadata
# Should show: version_metadata | jsonb | | | '{}'::jsonb
```

---

## 🔍 Understanding Docker PostgreSQL Initialization

**Critical Concept:** `/docker-entrypoint-initdb.d`

```yaml
# docker-compose.yml line 23:
volumes:
  - postgres_data:/var/lib/postgresql/data
  - ./backend/database/migrations:/docker-entrypoint-initdb.d
```

**How It Works:**
1. PostgreSQL checks if `/var/lib/postgresql/data` is empty
2. **If empty:** Initializes new database cluster + runs scripts in `/docker-entrypoint-initdb.d`
3. **If has data:** Skips initialization entirely (volume already initialized)

**Implications:**
- Migration scripts in `migrations/` only run on FIRST initialization
- Once volume exists, scripts are NEVER re-run automatically
- Manual execution required for existing databases

**Why This Matters:**
- Current system: Volume exists → 008 never runs → Manual fix was necessary
- Fresh deployment: No volume → All migrations run → Correct from start
- Production migration: Volume exists → Must run 008 manually

---

## 🧪 Testing & Verification

### Test 1: Verify Column Name
```bash
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb \
  -c "\d chapter_versions" | grep -E "metadata|version_metadata"
```
**Expected Output:**
```
 version_metadata   | jsonb                    |           |          | '{}'::jsonb
```
**NOT:**
```
 metadata           | jsonb                    |           |          | '{}'::jsonb
```

### Test 2: Verify Delete Endpoint Works
```bash
# Get chapters
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8002/api/v1/chapters

# Try delete (should NOT return 500)
curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8002/api/v1/chapters/CHAPTER_ID
```
**Expected:** 200 (success), 403 (forbidden), or 401 (unauthorized)
**NOT:** 500 Internal Server Error

### Test 3: Check API Logs (No version_metadata Errors)
```bash
docker logs neurocore-api --since 10m | grep -i "version_metadata"
# Should return NO results
```

---

## 📦 Volume Management

### Check Volumes
```bash
docker volume ls | grep neurocore
```
**Expected:**
```
neurocore-postgres-data   # Contains database (includes fix)
neurocore-redis-data      # Cache data
neurocore-pdf-storage     # Uploaded PDFs
neurocore-image-storage   # Extracted images
```

### Volume Persistence
- **Normal restart:** `docker-compose restart` → Volumes unchanged ✅
- **Stop/Start:** `docker-compose down && docker-compose up` → Volumes persist ✅
- **Volume wipe:** `docker-compose down -v` → **ALL DATA DELETED** ⚠️

### Backup Before Volume Operations
```bash
# Backup database
docker exec neurocore-postgres pg_dump -U nsurg_admin \
  -Fc neurosurgery_kb > neurocore_backup_$(date +%Y%m%d_%H%M%S).dump

# Restore database
docker exec -i neurocore-postgres pg_restore -U nsurg_admin \
  -d neurosurgery_kb -c < neurocore_backup_TIMESTAMP.dump
```

---

## 🚀 Deployment Checklist

### For Current System (No Action Needed)
- [x] Manual fix applied
- [x] Delete functionality verified
- [x] Source schema updated (004)
- [x] Safety migration created (008)
- [x] Volume persists fix
- [x] System fully operational

### For Fresh Deployment
- [ ] Ensure migrations directory mounted (`docker-compose.yml:23`)
- [ ] Verify 004 has `version_metadata` (not `metadata`)
- [ ] Deploy with `docker-compose up`
- [ ] Verify schema: `\d chapter_versions`
- [ ] Test delete functionality

### For Production Migration
- [ ] Backup database first
- [ ] Run 008 migration manually
- [ ] Verify column renamed
- [ ] Test delete endpoint
- [ ] Monitor logs for errors
- [ ] Keep backup until verified stable

---

## 🔧 Troubleshooting

### Issue: Delete still returns 500 error
**Check:**
```bash
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb \
  -c "SELECT column_name FROM information_schema.columns WHERE table_name='chapter_versions' AND column_name IN ('metadata', 'version_metadata');"
```
**Should return:** `version_metadata` only
**If returns:** `metadata` → Run migration manually (Scenario D)

### Issue: Migration 008 fails
**Error:** "column metadata does not exist"
**Meaning:** Column already correctly named (no action needed)

**Error:** "column version_metadata already exists"
**Meaning:** Column already correctly named (no action needed)

### Issue: Fresh deployment has wrong column
**Check:** `004_comprehensive_features.sql` line 34
**Should be:** `version_metadata JSONB DEFAULT '{}'`
**If not:** Update file, rebuild images, wipe volumes, redeploy

### Issue: Lost fix after restart
**Cause:** Ran `docker-compose down -v` (wiped volumes)
**Solution:** Don't use `-v` flag unless intentional
**Recovery:** Fresh initialization will be correct (004 fixed)

---

## 📚 Technical Details

### SQLAlchemy Reserved Names
**Why rename?** SQLAlchemy uses `metadata` as a class attribute for table definitions
**Conflict:** Model attribute `metadata` would clash with column name `metadata`
**Solution:** Rename column to `version_metadata` to avoid namespace collision

### Model Definition
**File:** `backend/database/models/chapter_version.py:41`
```python
# Version metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
version_metadata = Column(JSONB, default={})
```

### Database Schema
```sql
CREATE TABLE chapter_versions (
    ...
    version_metadata JSONB DEFAULT '{}',  -- NOT 'metadata'
    ...
);
```

### Migration Order
```
001 → Initial schema
002 → Embeddings
003 → Vector optimization
004 → Chapter versions (creates version_metadata) ← FIXED HERE
005 → Gap analysis
006 → Chapter-level schema
007 → Stage 12 review
008 → Fix metadata→version_metadata (safety net) ← CATCHES EDGE CASES
```

---

## ⚠️ Critical Warnings

1. **NEVER** run `docker-compose down -v` in production without backups
2. **ALWAYS** test migrations on a copy first
3. **VERIFY** schema after any database changes
4. **MONITOR** logs for version_metadata errors after deployment
5. **BACKUP** before any migration operations

---

## 📞 Support

**Issue:** Delete chapter not working
**Check:** This guide, section "🧪 Testing & Verification"

**Issue:** Schema mismatch errors
**Check:** This guide, section "🔧 Troubleshooting"

**Issue:** Migration questions
**Reference:** `DELETE_CHAPTER_FIX_REPORT.md` for detailed analysis

---

## 📝 Summary

### Current State
✅ **Production system is FIXED and WORKING**
- Manual fix applied to running database
- Volume persists the fix
- Delete functionality operational
- No action required

### Future Deployments
✅ **All future deployments will be CORRECT from the start**
- Source schema fixed (004)
- Safety migration in place (008)
- Automatic initialization
- No manual intervention needed

### Edge Cases
✅ **All scenarios covered**
- Volume persistence: Fix remains ✅
- Fresh deployment: Correct from start ✅
- Database rebuild: Correct schema ✅
- Production migration: Manual process documented ✅

---

**Status:** ✅ **COMPLETE AND PRODUCTION-READY**

**Last Updated:** 2025-11-01
**Author:** AI Development Team
