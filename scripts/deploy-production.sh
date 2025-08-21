#!/bin/bash
# Production Deployment Script for Photo Share Service
set -e

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
MONITORING_FILE="docker-compose.monitoring.yml"
ENV_FILE=".env"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Photo Share Service - Production Deployment${NC}"
echo "=============================================="

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}📋 Checking prerequisites...${NC}"
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root - consider using a dedicated user"
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
    fi
    
    # Check if environment file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        print_error "Environment file $ENV_FILE not found. Run: python3 scripts/setup-environment.py --environment production"
    fi
    
    # Check critical environment variables
    source "$ENV_FILE"
    
    if [[ -z "$JWT_SECRET_KEY" ]] || [[ "$JWT_SECRET_KEY" == *"template"* ]]; then
        print_error "JWT_SECRET_KEY not properly configured. Run: python3 scripts/generate-jwt-secrets.py --update-env $ENV_FILE"
    fi
    
    if [[ -z "$POSTGRES_PASSWORD" ]] || [[ "$POSTGRES_PASSWORD" == *"secure_password"* ]]; then
        print_error "POSTGRES_PASSWORD not properly configured"
    fi
    
    print_status "Prerequisites check passed"
}

# Backup current data
backup_data() {
    echo -e "${BLUE}💾 Creating backup...${NC}"
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup database if running
    if docker ps | grep -q "photo-share-db"; then
        print_status "Backing up database..."
        docker exec photo-share-db pg_dump -U ${POSTGRES_USER:-postgres} ${POSTGRES_DB:-photo_share} > "$BACKUP_DIR/database.sql"
    fi
    
    # Backup photos if they exist
    if [[ -d "photos" ]]; then
        print_status "Backing up photos..."
        cp -r photos "$BACKUP_DIR/"
    fi
    
    # Backup environment file
    cp "$ENV_FILE" "$BACKUP_DIR/"
    
    print_status "Backup created in $BACKUP_DIR"
}

# Deploy services
deploy_services() {
    echo -e "${BLUE}🛠️  Deploying services...${NC}"
    
    # Pull latest images
    print_status "Pulling latest images..."
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Build application image
    print_status "Building application..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache photo-share-platform
    
    # Start infrastructure services first
    print_status "Starting database and Redis..."
    docker-compose -f "$COMPOSE_FILE" up -d platform-db redis-cache
    
    # Wait for database to be ready
    echo "Waiting for database to be ready..."
    for i in {1..30}; do
        if docker exec photo-share-db pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-photo_share} > /dev/null 2>&1; then
            print_status "Database is ready"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Run database migrations
    print_status "Running database migrations..."
    docker-compose -f "$COMPOSE_FILE" run --rm photo-share-platform python manage_db.py migrate
    
    # Start application
    print_status "Starting application..."
    docker-compose -f "$COMPOSE_FILE" up -d photo-share-platform
    
    # Start reverse proxy if configured
    if grep -q "nginx:" "$COMPOSE_FILE"; then
        print_status "Starting nginx reverse proxy..."
        docker-compose -f "$COMPOSE_FILE" up -d nginx
    fi
    
    print_status "Services deployed successfully"
}

# Deploy monitoring stack
deploy_monitoring() {
    echo -e "${BLUE}📊 Deploying monitoring stack...${NC}"
    
    if [[ -f "$MONITORING_FILE" ]]; then
        docker-compose -f "$MONITORING_FILE" up -d
        print_status "Monitoring stack deployed"
    else
        print_warning "Monitoring configuration not found - skipping"
    fi
}

# Health check
health_check() {
    echo -e "${BLUE}🏥 Running health checks...${NC}"
    
    # Wait for application to start
    echo "Waiting for application to start..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            print_status "Application is healthy"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Run security tests
    print_status "Running security validation..."
    python3 scripts/test-security-improvements.py || print_warning "Some security tests failed"
    
    # Check database pool status
    print_status "Checking database connection pool..."
    curl -s http://localhost:8000/api/platform/stats | jq '.database_pool' || print_warning "Could not check database pool"
    
    print_status "Health checks completed"
}

# Show deployment summary
show_summary() {
    echo -e "${BLUE}📋 Deployment Summary${NC}"
    echo "===================="
    
    echo "🔗 Service URLs:"
    echo "  • API Service: http://localhost:8000"
    echo "  • API Docs: http://localhost:8000/docs"
    echo "  • Health Check: http://localhost:8000/health"
    
    if docker ps | grep -q "photo-share-prometheus"; then
        echo "  • Prometheus: http://localhost:9090"
    fi
    
    if docker ps | grep -q "photo-share-grafana"; then
        echo "  • Grafana: http://localhost:3000"
    fi
    
    echo ""
    echo "📊 Running Containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep photo-share
    
    echo ""
    echo "💽 Data Volumes:"
    docker volume ls | grep photo-share
    
    echo ""
    echo "📁 Backup Location: $BACKUP_DIR"
    
    echo ""
    echo -e "${GREEN}🎉 Production deployment completed successfully!${NC}"
}

# Main deployment process
main() {
    check_prerequisites
    backup_data
    deploy_services
    
    # Ask about monitoring
    read -p "Deploy monitoring stack? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        deploy_monitoring
    fi
    
    health_check
    show_summary
    
    echo -e "${BLUE}🔧 Post-deployment tasks:${NC}"
    echo "1. Configure SSL certificates for HTTPS"
    echo "2. Set up automated backups"
    echo "3. Configure monitoring alerts"
    echo "4. Review logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "5. Set up log rotation"
}

# Handle script arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    backup)
        backup_data
        ;;
    health)
        health_check
        ;;
    logs)
        docker-compose -f "$COMPOSE_FILE" logs -f
        ;;
    stop)
        docker-compose -f "$COMPOSE_FILE" down
        ;;
    restart)
        docker-compose -f "$COMPOSE_FILE" restart
        ;;
    *)
        echo "Usage: $0 {deploy|backup|health|logs|stop|restart}"
        exit 1
        ;;
esac