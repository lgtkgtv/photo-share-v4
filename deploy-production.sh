#!/bin/bash
# PhotoShare Production Deployment Script
# =======================================

set -e  # Exit on error

echo "🚀 PhotoShare Production Deployment"
echo "==================================="

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo "❌ .env.production not found!"
    echo "Please copy .env.production.template to .env.production and configure it."
    exit 1
fi

# Validate required environment variables
echo "🔍 Validating environment configuration..."

source .env.production

required_vars=(
    "JWT_SECRET_KEY"
    "AUTH_DB_PASSWORD"
    "APP_DB_PASSWORD"
    "ALLOWED_ORIGINS"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set in .env.production"
        exit 1
    fi
done

# Check if JWT secret is the default (insecure) value
if [ "$JWT_SECRET_KEY" = "your-very-secure-256-bit-jwt-secret-key-here-change-in-production" ]; then
    echo "❌ JWT_SECRET_KEY is still set to the default value!"
    echo "Please generate a secure JWT secret key."
    echo "You can use: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
    exit 1
fi

# Pre-deployment checks
echo "🔍 Running pre-deployment checks..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if required ports are available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "❌ Port $port is already in use. Please free the port or change the configuration."
        exit 1
    fi
}

check_port ${AUTH_PORT:-8001}
check_port ${APP_PORT:-8000}
check_port ${NGINX_HTTP_PORT:-80}
check_port ${NGINX_HTTPS_PORT:-443}

echo "✅ Pre-deployment checks passed"

# Build production images
echo "🔨 Building production Docker images..."
docker compose -f docker-compose.production.yml build --no-cache

# Create necessary directories
echo "📁 Creating production directories..."
mkdir -p data/redis
mkdir -p config/ssl
mkdir -p logs

# Set proper permissions
chmod 755 data/redis
chmod 755 logs

# SSL Certificate setup reminder
if [ ! -f config/ssl/fullchain.pem ] || [ ! -f config/ssl/privkey.pem ]; then
    echo "⚠️  SSL certificates not found in config/ssl/"
    echo "For production deployment, you need:"
    echo "  - config/ssl/fullchain.pem"
    echo "  - config/ssl/privkey.pem"
    echo ""
    echo "You can:"
    echo "1. Use Let's Encrypt: certbot certonly --standalone -d yourdomain.com"
    echo "2. Use existing certificates from your certificate provider"
    echo "3. Continue without SSL for testing (not recommended for production)"
    echo ""
    read -p "Continue without SSL certificates? (y/N): " continue_without_ssl
    if [ "$continue_without_ssl" != "y" ] && [ "$continue_without_ssl" != "Y" ]; then
        echo "Please set up SSL certificates and run again."
        exit 1
    fi
fi

# Start services
echo "🚀 Starting production services..."
docker compose -f docker-compose.production.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Health checks
echo "🏥 Running health checks..."

services=("auth-service" "photo-share-app")
for service in "${services[@]}"; do
    echo "Checking $service..."
    if ! docker compose -f docker-compose.production.yml exec $service curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "❌ $service health check failed"
        echo "Checking logs..."
        docker compose -f docker-compose.production.yml logs $service --tail=20
        exit 1
    fi
    echo "✅ $service is healthy"
done

# Database initialization check
echo "🗄️  Checking database initialization..."
if ! docker compose -f docker-compose.production.yml exec auth-db pg_isready -U ${AUTH_DB_USER:-auth_user} > /dev/null 2>&1; then
    echo "❌ Auth database not ready"
    exit 1
fi

if ! docker compose -f docker-compose.production.yml exec app-db pg_isready -U ${APP_DB_USER:-photo_user} > /dev/null 2>&1; then
    echo "❌ App database not ready"
    exit 1
fi

echo "✅ Databases are ready"

# Run basic functionality test
echo "🧪 Running basic functionality test..."
if python3 test_suite_basic.py > /dev/null 2>&1; then
    echo "✅ Basic functionality test passed"
else
    echo "⚠️  Basic functionality test failed - check the services"
    echo "You can run 'python3 test_suite_basic.py' manually to see detailed results"
fi

# Final status
echo ""
echo "🎉 Production deployment completed successfully!"
echo "================================================"
echo ""
echo "📊 Service Status:"
docker compose -f docker-compose.production.yml ps
echo ""
echo "🌐 Service URLs:"
echo "  • Auth Service: http://localhost:${AUTH_PORT:-8001}/health"
echo "  • Photo Service: http://localhost:${APP_PORT:-8000}/health"
echo "  • API Documentation: http://localhost:${APP_PORT:-8000}/docs"

if [ -f config/ssl/fullchain.pem ]; then
    echo "  • Production URL: https://${DOMAIN:-localhost}"
else
    echo "  • Production URL: http://localhost (SSL not configured)"
fi

echo ""
echo "📝 Next steps:"
echo "1. Configure your domain DNS to point to this server"
echo "2. Set up SSL certificates if not already done"
echo "3. Configure monitoring and alerting"
echo "4. Set up regular backups"
echo "5. Review logs: docker compose -f docker-compose.production.yml logs"
echo ""
echo "🛡️  Security reminders:"
echo "• Never commit .env.production to version control"
echo "• Regularly update dependencies and base images"
echo "• Monitor logs for suspicious activity"
echo "• Set up proper firewall rules"
echo ""
echo "✅ PhotoShare is ready for production use!"