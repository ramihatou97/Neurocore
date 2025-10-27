# 🚀 Backend Startup Guide

## The Problem You Encountered

If you saw this error:
```
ModuleNotFoundError: No module named 'backend'
```

This happened because you were running uvicorn from **inside** the `backend/` directory. The imports in `main.py` use absolute paths like `from backend.config import settings`, which require running from the **project root** directory.

---

## ✅ Solutions (Choose One)

### **Option 1: Use the Startup Script** ⭐ **RECOMMENDED**

We've created a helper script that handles everything for you:

```bash
# Make sure you're in the project root directory
cd "/Users/ramihatoum/Desktop/The neurosurgical core of knowledge"

# Run the script
./start-backend.sh
```

**Other startup modes:**
```bash
./start-backend.sh docker      # Full stack with Docker (all services)
./start-backend.sh docker-api  # Only API, Postgres, Redis
./start-backend.sh prod        # Production mode
./start-backend.sh help        # Show all options
```

---

### **Option 2: Manual Command**

If you prefer to run manually, use this command from the **project root**:

```bash
# Make sure you're in the project root (NOT inside backend/)
cd "/Users/ramihatoum/Desktop/The neurosurgical core of knowledge"

# Run uvicorn with the correct module path
python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8002
```

**❌ WRONG (what you did before):**
```bash
cd backend
python3 -m uvicorn main:app --reload  # This fails!
```

**✅ CORRECT:**
```bash
# Stay in project root
python3 -m uvicorn backend.main:app --reload
```

---

### **Option 3: Docker Compose** 🐳 **BEST FOR FULL STACK**

This is the recommended production approach that starts everything (Postgres, Redis, API, Celery, Frontend):

```bash
# Start all services
docker-compose up

# Or start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down
```

**Start only specific services:**
```bash
# Just the API and its dependencies
docker-compose up postgres redis api

# With Celery workers
docker-compose up postgres redis api celery-worker
```

---

## 🔧 Configuration Fixed

The following issues in your `.env` file have been corrected:

1. **Database Port**: Changed from `5434` → `5432` (standard PostgreSQL port)
2. **Redis Port**: Changed from `6381` → `6379` (standard Redis port)

These changes ensure compatibility with the default Docker setup.

---

## 📋 Prerequisites

### For Local Development (Option 1 & 2):

1. **Python 3.9+** installed ✓ (You have 3.9.6)
2. **Dependencies installed:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **PostgreSQL running** on localhost:5432
   - Database: `neurosurgery_kb`
   - User: `nsurg_admin`
   - Password: `SecureNeurosurgeryPassword2025!`

4. **Redis running** on localhost:6379

### For Docker (Option 3):
1. **Docker Desktop** installed
2. **Docker Compose** available
3. That's it! Everything else is handled automatically.

---

## 🧪 Verify It's Working

Once started, check these endpoints:

1. **Health Check:**
   ```bash
   curl http://localhost:8002/health
   ```

2. **Root Endpoint:**
   ```bash
   curl http://localhost:8002/
   ```

3. **API Documentation:**
   Open in browser: http://localhost:8002/api/docs

---

## 🐛 Troubleshooting

### "Cannot connect to database"
- Make sure PostgreSQL is running
- Verify credentials in `.env` match your database
- Check port is 5432 (not 5434)

### "Cannot connect to Redis"
- Make sure Redis is running
- Check port is 6379 (not 6381)

### "Module not found" errors
- Make sure you're running from project root (not inside `backend/`)
- Verify all dependencies are installed: `pip3 install -r requirements.txt`

### Port 8002 already in use
- Change `API_PORT` in `.env` to a different port
- Or kill the process using port 8002:
  ```bash
  lsof -ti:8002 | xargs kill -9
  ```

---

## 📚 Project Structure

```
The neurosurgical core of knowledge/
├── backend/                    # Backend package directory
│   ├── __init__.py
│   ├── main.py                # FastAPI app
│   ├── config/
│   ├── api/
│   ├── services/
│   └── database/
├── frontend/                   # React frontend
├── docker-compose.yml         # Docker orchestration
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables
├── start-backend.sh          # Startup helper script ⭐ NEW
└── STARTUP_GUIDE.md          # This guide ⭐ NEW
```

---

## 🎯 Quick Start Cheatsheet

```bash
# 1. Navigate to project root
cd "/Users/ramihatoum/Desktop/The neurosurgical core of knowledge"

# 2. Choose one:

# Easy mode - use the script
./start-backend.sh

# Docker mode - full stack
docker-compose up

# Manual mode - from project root
python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8002
```

---

## 🚦 Next Steps

1. **Test the API** at http://localhost:8002/api/docs
2. **Start the frontend** in another terminal:
   ```bash
   cd frontend
   npm run dev
   ```
3. **Access the app** at http://localhost:3002

---

## 💡 Pro Tips

- Use `./start-backend.sh docker` for the most reliable experience
- The script checks for common issues before starting
- Logs are colored for easy reading
- All configurations are in `.env` - one place to rule them all

Happy coding! 🧠⚕️
