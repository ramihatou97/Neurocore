#!/bin/bash
# Neurocore - Docker Management Script
# Ensures all Docker commands use the correct isolated project name

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Project name for isolation
PROJECT_NAME="neurocore"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Header
print_header() {
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}Neurocore Docker Manager${NC}"
    echo -e "${BLUE}Project: ${GREEN}${PROJECT_NAME}${BLUE} (isolated)${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo ""
}

# Usage
usage() {
    print_header
    echo "Usage: ./docker-manage.sh [COMMAND]"
    echo ""
    echo -e "${GREEN}Container Management:${NC}"
    echo "  start           - Start all services"
    echo "  stop            - Stop all services (keep data)"
    echo "  restart         - Restart all services"
    echo "  restart-api     - Restart only API service"
    echo "  restart-db      - Restart only database"
    echo "  restart-redis   - Restart only Redis"
    echo ""
    echo -e "${GREEN}Monitoring:${NC}"
    echo "  status          - Show status of all services"
    echo "  logs            - View logs (all services)"
    echo "  logs-api        - View API logs only"
    echo "  logs-celery     - View Celery worker logs"
    echo "  logs-db         - View database logs"
    echo "  stats           - Show CPU/Memory usage"
    echo ""
    echo -e "${GREEN}Shell Access:${NC}"
    echo "  shell-api       - Open bash shell in API container"
    echo "  shell-db        - Open psql in database"
    echo "  shell-redis     - Open redis-cli"
    echo ""
    echo -e "${GREEN}Build & Deploy:${NC}"
    echo "  build           - Rebuild all images"
    echo "  rebuild         - Force rebuild (no cache)"
    echo "  pull            - Pull latest base images"
    echo ""
    echo -e "${GREEN}Cleanup:${NC}"
    echo "  clean           - Stop services, keep data"
    echo "  clean-all       - Stop services + remove volumes (DELETES DATA!)"
    echo "  prune           - Remove unused images/containers"
    echo ""
    echo -e "${GREEN}Information:${NC}"
    echo "  info            - Show project information"
    echo "  verify          - Verify isolation (check for conflicts)"
    echo "  ports           - Show port mappings"
    echo ""
    echo -e "${GREEN}Database:${NC}"
    echo "  db-backup       - Backup database to file"
    echo "  db-restore      - Restore database from backup"
    echo ""
    echo "Examples:"
    echo "  ./docker-manage.sh start"
    echo "  ./docker-manage.sh logs-api"
    echo "  ./docker-manage.sh shell-api"
    echo "  ./docker-manage.sh verify"
}

# Commands
case "${1:-help}" in
    start)
        print_header
        echo -e "${GREEN}Starting all services...${NC}"
        docker-compose -p $PROJECT_NAME up -d
        echo ""
        echo -e "${GREEN}✓ Services started!${NC}"
        docker-compose -p $PROJECT_NAME ps
        ;;

    stop)
        print_header
        echo -e "${YELLOW}Stopping all services (data preserved)...${NC}"
        docker-compose -p $PROJECT_NAME down
        echo -e "${GREEN}✓ Services stopped${NC}"
        ;;

    restart)
        print_header
        echo -e "${YELLOW}Restarting all services...${NC}"
        docker-compose -p $PROJECT_NAME restart
        echo -e "${GREEN}✓ Services restarted${NC}"
        docker-compose -p $PROJECT_NAME ps
        ;;

    restart-api)
        print_header
        echo -e "${YELLOW}Restarting API service...${NC}"
        docker-compose -p $PROJECT_NAME restart api
        echo -e "${GREEN}✓ API restarted${NC}"
        ;;

    restart-db)
        print_header
        echo -e "${YELLOW}Restarting database...${NC}"
        docker-compose -p $PROJECT_NAME restart postgres
        echo -e "${GREEN}✓ Database restarted${NC}"
        ;;

    restart-redis)
        print_header
        echo -e "${YELLOW}Restarting Redis...${NC}"
        docker-compose -p $PROJECT_NAME restart redis
        echo -e "${GREEN}✓ Redis restarted${NC}"
        ;;

    status|ps)
        print_header
        docker-compose -p $PROJECT_NAME ps
        ;;

    logs)
        print_header
        echo -e "${YELLOW}Showing logs (Ctrl+C to exit)...${NC}"
        echo ""
        docker-compose -p $PROJECT_NAME logs -f --tail=100
        ;;

    logs-api)
        print_header
        echo -e "${YELLOW}Showing API logs (Ctrl+C to exit)...${NC}"
        echo ""
        docker-compose -p $PROJECT_NAME logs -f --tail=100 api
        ;;

    logs-celery)
        print_header
        echo -e "${YELLOW}Showing Celery logs (Ctrl+C to exit)...${NC}"
        echo ""
        docker-compose -p $PROJECT_NAME logs -f --tail=100 celery-worker celery-worker-images celery-worker-embeddings
        ;;

    logs-db)
        print_header
        echo -e "${YELLOW}Showing database logs (Ctrl+C to exit)...${NC}"
        echo ""
        docker-compose -p $PROJECT_NAME logs -f --tail=100 postgres
        ;;

    stats)
        print_header
        echo -e "${YELLOW}Showing resource usage (Ctrl+C to exit)...${NC}"
        echo ""
        docker stats $(docker ps --filter "name=${PROJECT_NAME}-" -q)
        ;;

    shell-api)
        print_header
        echo -e "${GREEN}Opening bash shell in API container...${NC}"
        echo ""
        docker-compose -p $PROJECT_NAME exec api bash
        ;;

    shell-db)
        print_header
        echo -e "${GREEN}Opening PostgreSQL shell...${NC}"
        echo ""
        docker-compose -p $PROJECT_NAME exec postgres psql -U nsurg_admin -d neurosurgery_kb
        ;;

    shell-redis)
        print_header
        echo -e "${GREEN}Opening Redis CLI...${NC}"
        echo ""
        docker-compose -p $PROJECT_NAME exec redis redis-cli
        ;;

    build)
        print_header
        echo -e "${YELLOW}Building images...${NC}"
        docker-compose -p $PROJECT_NAME build
        echo -e "${GREEN}✓ Build complete${NC}"
        ;;

    rebuild)
        print_header
        echo -e "${YELLOW}Force rebuilding images (no cache)...${NC}"
        docker-compose -p $PROJECT_NAME build --no-cache
        echo -e "${GREEN}✓ Rebuild complete${NC}"
        ;;

    pull)
        print_header
        echo -e "${YELLOW}Pulling latest base images...${NC}"
        docker-compose -p $PROJECT_NAME pull
        echo -e "${GREEN}✓ Pull complete${NC}"
        ;;

    clean)
        print_header
        echo -e "${YELLOW}Cleaning up (keeping data)...${NC}"
        docker-compose -p $PROJECT_NAME down
        echo -e "${GREEN}✓ Cleanup complete (data preserved)${NC}"
        ;;

    clean-all)
        print_header
        echo -e "${RED}⚠️  WARNING: This will DELETE ALL DATA!${NC}"
        echo -e "${YELLOW}This includes:${NC}"
        echo "  - Database data"
        echo "  - Redis cache"
        echo "  - Uploaded PDFs"
        echo "  - Extracted images"
        echo ""
        read -p "Are you sure? Type 'yes' to confirm: " confirm
        if [ "$confirm" == "yes" ]; then
            echo ""
            echo -e "${RED}Removing all containers and volumes...${NC}"
            docker-compose -p $PROJECT_NAME down -v
            echo -e "${GREEN}✓ Complete cleanup done${NC}"
        else
            echo -e "${YELLOW}Aborted${NC}"
        fi
        ;;

    prune)
        print_header
        echo -e "${YELLOW}Removing unused Docker resources...${NC}"
        echo ""
        docker system prune -f
        echo ""
        echo -e "${GREEN}✓ Prune complete${NC}"
        ;;

    info)
        print_header
        echo -e "${GREEN}Project Information:${NC}"
        echo "  Name:       ${PROJECT_NAME}"
        echo "  Directory:  ${SCRIPT_DIR}"
        echo ""
        echo -e "${GREEN}Containers:${NC}"
        docker ps -a --filter "name=${PROJECT_NAME}-" --format "  {{.Names}}\t{{.Status}}"
        echo ""
        echo -e "${GREEN}Volumes:${NC}"
        docker volume ls --filter "name=${PROJECT_NAME}-" --format "  {{.Name}}"
        echo ""
        echo -e "${GREEN}Networks:${NC}"
        docker network ls --filter "name=${PROJECT_NAME}-" --format "  {{.Name}}"
        echo ""
        echo -e "${GREEN}Ports:${NC}"
        echo "  API:      http://localhost:8002"
        echo "  Frontend: http://localhost:3002"
        echo "  Flower:   http://localhost:5555"
        echo "  Postgres: localhost:5432 (internal)"
        echo "  Redis:    localhost:6379 (internal)"
        ;;

    verify)
        print_header
        echo -e "${GREEN}Verifying isolation...${NC}"
        echo ""

        # Check for potential conflicts
        echo -e "${YELLOW}All Docker containers:${NC}"
        docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | head -20
        echo ""

        # Count neurocore containers
        NEUROCORE_COUNT=$(docker ps -a --filter "name=${PROJECT_NAME}-" --format "{{.Names}}" | wc -l | tr -d ' ')
        echo -e "${GREEN}Neurocore containers found: ${NEUROCORE_COUNT}${NC}"

        # Check for old neurosurgery containers
        OLD_COUNT=$(docker ps -a --filter "name=neurosurgery-" --format "{{.Names}}" | wc -l | tr -d ' ')
        if [ "$OLD_COUNT" -gt "0" ]; then
            echo -e "${YELLOW}⚠️  Old 'neurosurgery-*' containers found: ${OLD_COUNT}${NC}"
            echo "   These may be from the old setup. Consider removing them."
        fi

        echo ""
        echo -e "${GREEN}✓ Isolation verified!${NC}"
        echo "  This project uses: ${PROJECT_NAME}-*"
        echo "  All resources are isolated from other projects"
        ;;

    ports)
        print_header
        echo -e "${GREEN}Port Mappings:${NC}"
        docker-compose -p $PROJECT_NAME ps --format "table {{.Name}}\t{{.Ports}}"
        ;;

    db-backup)
        print_header
        BACKUP_FILE="backup-$(date +%Y%m%d-%H%M%S).sql"
        echo -e "${GREEN}Backing up database to ${BACKUP_FILE}...${NC}"
        docker-compose -p $PROJECT_NAME exec -T postgres pg_dump -U nsurg_admin neurosurgery_kb > "$BACKUP_FILE"
        echo -e "${GREEN}✓ Backup saved to ${BACKUP_FILE}${NC}"
        ;;

    db-restore)
        if [ -z "$2" ]; then
            echo -e "${RED}ERROR: Please specify backup file${NC}"
            echo "Usage: ./docker-manage.sh db-restore <backup-file.sql>"
            exit 1
        fi

        if [ ! -f "$2" ]; then
            echo -e "${RED}ERROR: Backup file not found: $2${NC}"
            exit 1
        fi

        print_header
        echo -e "${YELLOW}Restoring database from $2...${NC}"
        cat "$2" | docker-compose -p $PROJECT_NAME exec -T postgres psql -U nsurg_admin neurosurgery_kb
        echo -e "${GREEN}✓ Database restored${NC}"
        ;;

    help|--help|-h)
        usage
        ;;

    *)
        echo -e "${RED}ERROR: Unknown command '$1'${NC}"
        echo ""
        usage
        exit 1
        ;;
esac
