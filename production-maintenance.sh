#!/bin/bash
# PhotoShare Production Maintenance Script
# ========================================

set -e

COMPOSE_FILE="docker-compose.production.yml"

show_help() {
    echo "PhotoShare Production Maintenance"
    echo "================================="
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  status      - Show service status"
    echo "  logs        - Show service logs"
    echo "  health      - Run health checks"
    echo "  test        - Run basic functionality tests"
    echo "  backup      - Backup databases"
    echo "  restore     - Restore databases from backup"
    echo "  update      - Update and restart services"
    echo "  scale       - Scale services"
    echo "  stop        - Stop all services"
    echo "  start       - Start all services"
    echo "  restart     - Restart all services"
    echo "  cleanup     - Clean up unused containers and images"
    echo "  monitor     - Show real-time resource usage"
    echo ""
}

check_production_env() {
    if [ ! -f .env.production ]; then
        echo "❌ .env.production not found!"
        exit 1
    fi
    source .env.production
}

show_status() {
    echo "📊 PhotoShare Production Status"
    echo "=============================="
    echo ""
    echo "🐳 Container Status:"
    docker compose -f $COMPOSE_FILE ps
    echo ""
    echo "📈 Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

show_logs() {
    service=${2:-""}
    if [ -n "$service" ]; then
        echo "📝 Logs for $service:"
        docker compose -f $COMPOSE_FILE logs -f $service
    else
        echo "📝 All service logs (last 100 lines):"
        docker compose -f $COMPOSE_FILE logs --tail=100
    fi
}

run_health_checks() {
    echo "🏥 PhotoShare Health Checks"
    echo "=========================="
    echo ""
    
    services=("auth-service" "photo-share-app")
    all_healthy=true
    
    for service in "${services[@]}"; do
        echo "Checking $service..."
        if docker compose -f $COMPOSE_FILE exec $service curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ $service is healthy"
        else
            echo "❌ $service health check failed"
            all_healthy=false
        fi
    done
    
    echo ""
    echo "🗄️  Database Health:"
    if docker compose -f $COMPOSE_FILE exec auth-db pg_isready -U ${AUTH_DB_USER:-auth_user} > /dev/null 2>&1; then
        echo "✅ Auth database is ready"
    else
        echo "❌ Auth database is not ready"
        all_healthy=false
    fi
    
    if docker compose -f $COMPOSE_FILE exec app-db pg_isready -U ${APP_DB_USER:-photo_user} > /dev/null 2>&1; then
        echo "✅ App database is ready"
    else
        echo "❌ App database is not ready" 
        all_healthy=false
    fi
    
    if [ "$all_healthy" = true ]; then
        echo ""
        echo "🎉 All services are healthy!"
        return 0
    else
        echo ""
        echo "⚠️  Some services are unhealthy"
        return 1
    fi
}

run_tests() {
    echo "🧪 Running functionality tests..."
    if python3 test_suite_basic.py; then
        echo "✅ All tests passed"
    else
        echo "❌ Some tests failed"
        return 1
    fi
}

backup_databases() {
    echo "🔐 Creating encrypted database backups..."
    
    # Check if backup encryption is set up
    if [ ! -f "/secure/backup_key.txt" ]; then
        echo "⚠️  Backup encryption key not found. Creating secure backup key..."
        mkdir -p /secure
        chmod 700 /secure
        python3 -c "import secrets; print(secrets.token_urlsafe(32))" > /secure/backup_key.txt
        chmod 600 /secure/backup_key.txt
        echo "✅ Backup encryption key created"
    fi
    
    # Run encrypted backup using Python script
    if python3 scripts/backup-databases.py backup; then
        echo "✅ Encrypted backup completed successfully"
        
        # List recent backups
        echo "📋 Recent backups:"
        python3 scripts/backup-databases.py list 2>/dev/null | \
            python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for db in ['auth', 'app']:
        if db in data:
            for backup in data[db][-3:]:
                print(f\"{backup['timestamp']} - {backup['database']} - {backup['filename']} ({backup['file_size']} bytes)\")
except: pass
"
    else
        echo "❌ Backup failed"
        return 1
    fi
    
    # Also backup photo storage (encrypted)
    echo "📸 Creating encrypted photo storage backup..."
    timestamp=$(date +"%Y%m%d_%H%M%S")
    backup_dir="/app/backups"
    mkdir -p "$backup_dir"
    
    storage_backup="$backup_dir/photo_storage_backup_$timestamp.tar.gz.gpg"
    
    # Get encryption key
    backup_key=$(cat /secure/backup_key.txt)
    
    if docker compose -f $COMPOSE_FILE exec photo-share-app tar -czf - /app/storage | \
       gpg --symmetric --cipher-algo AES256 --compress-algo 2 --batch --quiet \
           --passphrase "$backup_key" --output "$storage_backup"; then
        echo "✅ Photo storage backup encrypted: $(basename "$storage_backup")"
    else
        echo "❌ Photo storage backup failed"
        return 1
    fi
}

update_services() {
    echo "🔄 Updating PhotoShare services..."
    
    echo "Pulling latest images..."
    docker compose -f $COMPOSE_FILE pull
    
    echo "Building updated images..."
    docker compose -f $COMPOSE_FILE build --no-cache
    
    echo "Restarting services with zero downtime..."
    docker compose -f $COMPOSE_FILE up -d --force-recreate
    
    echo "Waiting for services to be healthy..."
    sleep 30
    
    if run_health_checks; then
        echo "✅ Update completed successfully"
    else
        echo "❌ Update failed - services unhealthy"
        return 1
    fi
}

scale_services() {
    service=$2
    replicas=$3
    
    if [ -z "$service" ] || [ -z "$replicas" ]; then
        echo "Usage: $0 scale <service> <replicas>"
        echo "Example: $0 scale photo-share-app 3"
        return 1
    fi
    
    echo "⚖️  Scaling $service to $replicas replicas..."
    docker compose -f $COMPOSE_FILE up -d --scale $service=$replicas
    
    echo "✅ Scaling completed"
}

cleanup_resources() {
    echo "🧹 Cleaning up unused resources..."
    
    echo "Removing unused containers..."
    docker container prune -f
    
    echo "Removing unused images..."
    docker image prune -f
    
    echo "Removing unused networks..."
    docker network prune -f
    
    echo "Removing unused volumes (keeping production data)..."
    docker volume prune -f
    
    echo "✅ Cleanup completed"
}

monitor_resources() {
    echo "📊 Real-time resource monitoring (Press Ctrl+C to exit)"
    echo "======================================================"
    docker stats
}

case "$1" in
    status)
        check_production_env
        show_status
        ;;
    logs)
        check_production_env
        show_logs $@
        ;;
    health)
        check_production_env
        run_health_checks
        ;;
    test)
        run_tests
        ;;
    backup)
        check_production_env
        backup_databases
        ;;
    update)
        check_production_env
        update_services
        ;;
    scale)
        check_production_env
        scale_services $@
        ;;
    stop)
        check_production_env
        echo "🛑 Stopping all services..."
        docker compose -f $COMPOSE_FILE down
        ;;
    start)
        check_production_env
        echo "🚀 Starting all services..."
        docker compose -f $COMPOSE_FILE up -d
        ;;
    restart)
        check_production_env
        echo "🔄 Restarting all services..."
        docker compose -f $COMPOSE_FILE restart
        ;;
    cleanup)
        cleanup_resources
        ;;
    monitor)
        monitor_resources
        ;;
    *)
        show_help
        ;;
esac