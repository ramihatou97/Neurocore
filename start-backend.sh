#!/bin/bash
# Neurosurgery Knowledge Base - Backend Startup Script
# This script ensures the backend starts correctly with proper Python paths

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}===================================${NC}"
echo -e "${GREEN}Neurosurgery Knowledge Base Backend${NC}"
echo -e "${GREEN}===================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Please create a .env file based on .env.example"
    exit 1
fi

echo -e "${YELLOW}Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is not installed!${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ Found: $PYTHON_VERSION${NC}"
echo ""

echo -e "${YELLOW}Checking required packages...${NC}"
if ! python3 -c "import fastapi" &> /dev/null; then
    echo -e "${RED}ERROR: FastAPI not installed!${NC}"
    echo "Install dependencies with: pip3 install -r requirements.txt"
    exit 1
fi
echo -e "${GREEN}✓ FastAPI installed${NC}"

if ! python3 -c "import uvicorn" &> /dev/null; then
    echo -e "${RED}ERROR: Uvicorn not installed!${NC}"
    echo "Install dependencies with: pip3 install -r requirements.txt"
    exit 1
fi
echo -e "${GREEN}✓ Uvicorn installed${NC}"
echo ""

# Determine startup mode
MODE="${1:-dev}"

case "$MODE" in
    dev|development)
        echo -e "${GREEN}Starting backend in DEVELOPMENT mode...${NC}"
        echo -e "${YELLOW}Note: Database and Redis must be running!${NC}"
        echo ""
        echo "Command: python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8002"
        echo ""
        python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8002
        ;;

    docker)
        echo -e "${GREEN}Starting full stack with Docker Compose...${NC}"
        if ! command -v docker-compose &> /dev/null; then
            echo -e "${RED}ERROR: docker-compose not installed!${NC}"
            exit 1
        fi
        echo -e "${YELLOW}Project: neurocore (isolated from other Docker projects)${NC}"
        echo ""
        docker-compose -p neurocore up
        ;;

    docker-api)
        echo -e "${GREEN}Starting only API service with Docker Compose...${NC}"
        echo -e "${YELLOW}Project: neurocore (isolated from other Docker projects)${NC}"
        echo ""
        docker-compose -p neurocore up postgres redis api
        ;;

    prod|production)
        echo -e "${GREEN}Starting backend in PRODUCTION mode...${NC}"
        echo -e "${YELLOW}Note: Database and Redis must be running!${NC}"
        echo ""
        python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8002 --workers 4
        ;;

    help|--help|-h)
        echo "Usage: ./start-backend.sh [MODE]"
        echo ""
        echo "Modes:"
        echo "  dev         - Development mode with auto-reload (default)"
        echo "  docker      - Full stack with Docker Compose (recommended)"
        echo "  docker-api  - Only API, Postgres, and Redis with Docker"
        echo "  prod        - Production mode with multiple workers"
        echo "  help        - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./start-backend.sh              # Start in dev mode"
        echo "  ./start-backend.sh docker       # Start full stack"
        echo "  ./start-backend.sh prod         # Start in production"
        ;;

    *)
        echo -e "${RED}ERROR: Unknown mode '$MODE'${NC}"
        echo "Run './start-backend.sh help' for usage information"
        exit 1
        ;;
esac
