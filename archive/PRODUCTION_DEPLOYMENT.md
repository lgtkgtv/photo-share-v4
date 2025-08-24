# PhotoShare Production Deployment Guide
# =====================================

This guide covers deploying PhotoShare in a production environment with security, scalability, and reliability best practices.

## 📋 Prerequisites

- **Server Requirements:**
  - Linux server (Ubuntu 20.04+ recommended)
  - 4+ GB RAM
  - 20+ GB disk space
  - Docker 20.10+
  - Docker Compose 2.0+

- **Network Requirements:**
  - Ports 80, 443 open for web traffic
  - Domain name configured (for SSL)
  - Firewall properly configured

## 🚀 Quick Start

### 1. Clone and Configure

```bash
git clone <your-repo>
cd photo-share-consul

# Copy and configure environment
cp .env.production.template .env.production
```

### 2. Configure Environment Variables

Edit `.env.production` with your production values:

```bash
# CRITICAL: Change these values!
JWT_SECRET_KEY=your-256-bit-secure-key-here
AUTH_DB_PASSWORD=secure-auth-password
APP_DB_PASSWORD=secure-app-password
REDIS_PASSWORD=secure-redis-password

# Domain configuration
DOMAIN=yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com
```

**⚠️ Security Warning:** Never commit `.env.production` to version control!

### 3. SSL Certificate Setup

For production with SSL:

```bash
# Option 1: Let's Encrypt (recommended)
certbot certonly --standalone -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem config/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem config/ssl/

# Option 2: Custom certificates
cp your-certificate.pem config/ssl/fullchain.pem
cp your-private-key.pem config/ssl/privkey.pem
```

### 4. Deploy

```bash
./deploy-production.sh
```

The script will:
- ✅ Validate configuration
- ✅ Build production images
- ✅ Start all services
- ✅ Run health checks
- ✅ Run functionality tests

## 🏗️ Architecture

```
Internet → NGINX (SSL/Load Balancer) → Services
                     ↓
    ┌─────────────────────────────────────────┐
    │                                         │
    │  Auth Service (Port 8001)              │
    │  ├── FastAPI + JWT                     │
    │  ├── RBAC System                       │
    │  └── Email Verification                │
    │                                         │
    │  App Service (Port 8000)               │
    │  ├── FastAPI + Photo Upload            │
    │  ├── File Storage                      │
    │  └── Permission Checking               │
    │                                         │
    └─────────────────────────────────────────┘
                     ↓
    ┌─────────────────────────────────────────┐
    │             Databases                   │
    │  ├── Auth PostgreSQL (Port 5433)       │
    │  └── App PostgreSQL (Port 5432)        │
    │                                         │
    │             Storage                     │
    │  ├── Photo Files (/app/storage)        │
    │  └── Redis Cache (Optional)            │
    └─────────────────────────────────────────┘
```

## 🔧 Production Services

### Core Services
- **auth-service**: Authentication, RBAC, email verification
- **photo-share-app**: Photo upload/management, API endpoints
- **auth-db**: PostgreSQL for user data, roles, permissions
- **app-db**: PostgreSQL for photos, metadata
- **nginx**: Reverse proxy, SSL termination, load balancing

### Optional Services
- **redis**: Session storage, caching
- **monitoring**: Metrics collection (Prometheus-ready)

## 📊 Management Commands

### Service Management

```bash
# Check status
./production-maintenance.sh status

# View logs
./production-maintenance.sh logs
./production-maintenance.sh logs auth-service

# Health checks
./production-maintenance.sh health

# Run tests
./production-maintenance.sh test
```

### Operations

```bash
# Backup databases
./production-maintenance.sh backup

# Update services
./production-maintenance.sh update

# Scale services
./production-maintenance.sh scale photo-share-app 3

# Monitor resources
./production-maintenance.sh monitor

# Cleanup unused resources
./production-maintenance.sh cleanup
```

### Service Control

```bash
# Stop all services
./production-maintenance.sh stop

# Start all services
./production-maintenance.sh start

# Restart all services
./production-maintenance.sh restart
```

## 🛡️ Security Features

### Authentication & Authorization
- ✅ JWT-based authentication
- ✅ Role-based access control (RBAC)
- ✅ Email verification required
- ✅ Rate limiting on all endpoints
- ✅ Secure password hashing (bcrypt)

### Network Security
- ✅ HTTPS/SSL encryption
- ✅ Security headers (HSTS, CSP, etc.)
- ✅ CORS configuration
- ✅ Internal network isolation
- ✅ Non-root container users

### Data Protection
- ✅ Database connection encryption
- ✅ Secure environment variable handling
- ✅ File upload validation
- ✅ SQL injection protection

## 📈 Performance & Scaling

### Horizontal Scaling

Scale individual services:
```bash
# Scale app service to handle more traffic
./production-maintenance.sh scale photo-share-app 4

# Scale auth service for high authentication load
./production-maintenance.sh scale auth-service 2
```

### Database Optimization
- Connection pooling enabled
- Query optimization with indexes
- Separate databases for auth/app services

### File Storage
- Local storage with Docker volumes
- Ready for cloud storage integration
- File size limits configurable

## 📊 Monitoring

### Health Endpoints
- Auth Service: `https://yourdomain.com/api/auth/health`
- App Service: `https://yourdomain.com/api/health`
- NGINX: `https://yourdomain.com/health`

### Metrics (Prometheus-compatible)
```bash
curl https://yourdomain.com/metrics
```

### Log Locations
```bash
# Service logs
docker compose -f docker-compose.production.yml logs

# NGINX logs
docker compose -f docker-compose.production.yml exec nginx tail -f /var/log/nginx/access.log
```

## 💾 Backup & Recovery

### Automated Backups

Set up automated daily backups:
```bash
# Add to crontab
0 2 * * * /path/to/photo-share-consul/production-maintenance.sh backup
```

### Manual Backup
```bash
./production-maintenance.sh backup
```

Creates timestamped backups in `backups/` directory:
- `auth_db_backup.sql` - User data, roles, permissions
- `app_db_backup.sql` - Photos metadata
- `photo_storage_backup.tar.gz` - Photo files

### Disaster Recovery

1. **Restore Databases:**
```bash
# Restore auth database
docker compose -f docker-compose.production.yml exec auth-db psql -U auth_user photo_share_auth < backups/TIMESTAMP/auth_db_backup.sql

# Restore app database  
docker compose -f docker-compose.production.yml exec app-db psql -U photo_user photo_share < backups/TIMESTAMP/app_db_backup.sql
```

2. **Restore Photo Files:**
```bash
# Restore photo storage
docker compose -f docker-compose.production.yml exec photo-share-app tar -xzf - -C /app/storage < backups/TIMESTAMP/photo_storage_backup.tar.gz
```

## 🔄 Updates & Maintenance

### Regular Updates

1. **Update Dependencies:**
```bash
./production-maintenance.sh update
```

2. **Security Updates:**
```bash
# Update base images monthly
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d --force-recreate
```

### SSL Certificate Renewal

For Let's Encrypt:
```bash
# Renew certificates (automated with certbot)
certbot renew --dry-run

# Copy renewed certificates
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem config/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem config/ssl/

# Restart NGINX
docker compose -f docker-compose.production.yml restart nginx
```

## 🚨 Troubleshooting

### Common Issues

1. **Service Won't Start:**
```bash
# Check logs
./production-maintenance.sh logs service-name

# Check configuration
./production-maintenance.sh health
```

2. **Database Connection Issues:**
```bash
# Check database health
docker compose -f docker-compose.production.yml exec auth-db pg_isready -U auth_user
docker compose -f docker-compose.production.yml exec app-db pg_isready -U photo_user
```

3. **SSL Certificate Issues:**
```bash
# Check certificate validity
openssl x509 -in config/ssl/fullchain.pem -text -noout
```

4. **High Memory Usage:**
```bash
# Monitor resources
./production-maintenance.sh monitor

# Scale down if needed
./production-maintenance.sh scale photo-share-app 2
```

### Emergency Procedures

**Service Recovery:**
```bash
# Restart all services
./production-maintenance.sh restart

# If that fails, stop and start
./production-maintenance.sh stop
./production-maintenance.sh start
```

**Database Recovery:**
```bash
# Restore from latest backup
./production-maintenance.sh restore
```

## 📞 Support

### Log Analysis
```bash
# Get last 100 lines of all logs
./production-maintenance.sh logs

# Focus on specific service
./production-maintenance.sh logs auth-service
```

### Performance Analysis
```bash
# Resource usage
./production-maintenance.sh monitor

# Service status
./production-maintenance.sh status
```

### Testing
```bash
# Verify functionality
./production-maintenance.sh test
```

---

## ✅ Production Checklist

Before going live:

- [ ] Environment variables configured and secure
- [ ] SSL certificates installed and valid
- [ ] Firewall rules configured
- [ ] Domain DNS pointing to server
- [ ] Backup strategy implemented
- [ ] Monitoring set up
- [ ] Load testing completed
- [ ] Security audit completed
- [ ] Documentation updated
- [ ] Team trained on maintenance procedures

---

**🎉 Your PhotoShare application is now ready for production use!**

For additional support or custom configurations, refer to the service-specific documentation or contact your development team.