# Photo Share Service

**Version**: 2.3.0-monitoring  
**Last Updated**: August 20, 2025 - 11:35 AM PST  
**Status**: Production Ready ✅

A production-ready photo sharing application built with FastAPI and PostgreSQL, featuring comprehensive security, performance optimization, monitoring capabilities, and **email verification system**.

## 🚀 Quick Start

```bash
# Clone and start the service
git clone <repository-url>
cd photo-share-3
docker compose up --build

# Access the API
curl http://localhost:8080/health
```

**API Documentation**: http://localhost:8080/docs  
**Service Port**: The photo share service runs on port 8080 (mapped from internal port 8000)

## ✨ Features

### 🔐 **Security & Authentication**
- **Email verification system** with 24-hour expiration links
- JWT-based authentication with 30-minute token expiration
- Secure password hashing with bcrypt
- Rate limiting and request validation
- Input sanitization and file upload security
- CORS protection with configurable origins

### 📸 **Photo Management**
- Secure photo upload with validation (JPEG, PNG, WebP, GIF)
- Photo metadata storage (title, description, privacy settings)
- File download and URL generation
- Public/private photo sharing
- Automatic file naming and storage organization

### ⚡ **Performance & Monitoring**
- Memory-based caching with query optimization
- Prometheus metrics integration
- Real-time performance monitoring
- Health checks and service statistics
- Database connection pooling

### 🛡️ **Production-Ready Security**
- Security headers (X-Frame-Options, CSP, HSTS)
- File content validation and malware scanning
- SQL injection protection with parameterized queries
- Error handling without information disclosure
- Security event logging and audit trails

## 🏗️ Architecture

**Single Service Design** - Streamlined FastAPI application with PostgreSQL

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client        │───▶│  FastAPI Service │───▶│   PostgreSQL    │
│   (Web/Mobile)  │    │  (Port 8080)     │    │   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  File Storage    │
                       │  (Local/Cloud)   │
                       └──────────────────┘
```

## 🛠️ Technology Stack

- **Backend**: FastAPI 0.104+ (Python 3.11+)
- **Database**: PostgreSQL 15 with AsyncPG
- **ORM**: SQLAlchemy 2.0+ (async)
- **Authentication**: JWT with PassLib (bcrypt)
- **Monitoring**: Prometheus metrics
- **Container**: Docker with multi-stage builds
- **Security**: Custom middleware and validation

## 📚 Documentation Navigation

This project maintains comprehensive documentation as **living documents** that are updated with each significant milestone. Here's your guide to navigating the documentation:

### 🎯 **README.md** (This Document)
**Purpose**: Central hub and quick start guide  
**When to Use**: First time setup, feature overview, API reference  
**Contents**: Installation, features, API endpoints, configuration, basic testing

### 🔧 **CLAUDE.md** 
**Purpose**: Development guidance for AI assistants and developers  
**When to Use**: When working on code, understanding project structure  
**Contents**: Current architecture, development commands, project structure, key features  
**Target**: Developers and AI assistants working on the codebase

### 🏗️ **ARCHITECTURE.md**
**Purpose**: Comprehensive technical architecture documentation  
**When to Use**: Understanding system design, integration planning, troubleshooting  
**Contents**: Detailed architecture diagrams, database schema, authentication flows, performance strategies  
**Target**: Architects, senior developers, system administrators

### 🧪 **TEST_PLAN.md**
**Purpose**: Complete testing procedures and validation  
**When to Use**: Quality assurance, deployment validation, troubleshooting  
**Contents**: Manual tests, automated test suite, security tests, performance benchmarks  
**Target**: QA engineers, DevOps, deployment teams

### 📊 **PROJECT_STATUS_REPORT.md**
**Purpose**: Current project status and progress tracking  
**When to Use**: Project reviews, status updates, planning next steps  
**Contents**: Completed tasks, current functionality, known issues, recommendations  
**Target**: Project managers, stakeholders, development team leads

### 📋 **Navigation Guidelines**
- **Start with README.md** for quick setup and overview
- **Consult CLAUDE.md** for daily development work
- **Reference ARCHITECTURE.md** for deep technical understanding
- **Use TEST_PLAN.md** for validation and quality assurance
- **Check PROJECT_STATUS_REPORT.md** for current status and next steps

Each document is versioned and timestamped to ensure you're working with current information.

## 📊 API Endpoints

### Authentication
```bash
# Register new user
POST /api/users/register
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}

# Login and get JWT token
POST /api/users/login
FormData: username=user@example.com&password=SecurePassword123!

# Get current user info (requires Authorization header)
GET /api/users/me
```

### Photo Management
```bash
# Upload photo (requires authentication)
POST /api/photos/upload
Content-Type: multipart/form-data
- file: [image file]
- title: "My Photo" (optional)
- description: "Photo description" (optional)
- is_public: false (optional)

# List user's photos
GET /api/photos/

# List public photos
GET /api/photos/public

# Get photo details
GET /api/photos/{photo_id}

# Download photo file
GET /api/photos/{photo_id}/download

# Get photo URLs
GET /api/photos/{photo_id}/url
```

### Monitoring & Platform
```bash
# Health check
GET /health

# Service statistics
GET /api/platform/stats

# Security status
GET /api/platform/security

# Performance metrics
GET /api/platform/performance

# Prometheus metrics
GET /metrics
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=photo_share
DB_HOST=platform-db
DB_PORT=5432

# Security Configuration
JWT_SECRET_KEY=your-secure-jwt-secret-here
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Application Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Generate JWT Secret
```bash
# Generate secure JWT secret
python3 scripts/generate-jwt-secrets.py --update-env .env

# Validate configuration
python3 scripts/validate-config.py --env .env
```

## 🧪 Testing

### Quick Validation Tests (5-10 minutes)
```bash
# Test authentication flow
bash scripts/api-tests/test-auth-flow.sh

# Test photo upload (after authentication)
bash scripts/api-tests/test-photo-upload.sh

# View comprehensive test plan
cat TEST_PLAN.md
```

### Automated Test Suite
```bash
# Run all tests
cd services/photoshare
python3 run_tests.py all --verbose

# Run specific test categories
python3 run_tests.py unit          # Unit tests only
python3 run_tests.py integration   # Integration tests only
python3 run_tests.py security      # Security tests only
python3 run_tests.py performance   # Performance tests only

# Install test dependencies if needed
python3 run_tests.py all --install-deps
```

### Test Categories
- **Unit Tests**: Database models, security components, core functionality
- **Integration Tests**: API endpoints, authentication flow, photo management
- **Security Tests**: OWASP compliance, penetration testing, GDPR compliance
- **Performance Tests**: Caching, query optimization, response times

## 🛠️ Development Tools

The project includes several development and analysis tools in the `tools/` directory:

### SBOM Agent (Software Bill of Materials)
Generate comprehensive software bills of materials for security and compliance:

```bash
# Start the SBOM tools
docker compose -f tools/docker-compose.tools.yml up --build

# Generate SBOM for the project
cd tools/sbom-agent
python src/cli.py --project ../.. --output reports/

# View generated reports
ls -la tools/sbom-agent/reports/

# View integration guide
cat tools/sbom-agent/docs/integration-guide.md
```

### Shared Utilities
Development utilities for environment management:

```bash
# Detect project environment and dependencies
python tools/shared/environment_detector.py

# Validate file naming conventions
python tools/shared/filename_manager.py

# Manage project versions
python tools/shared/version_manager.py
```

### Vulnerability Testing
The SBOM agent includes test datasets for various languages and frameworks to help identify vulnerabilities.

### Example Usage Flow
```bash
# 1. Register a user
curl -X POST http://localhost:8080/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "DemoPassword123!"}'

# 2. Login and get token
TOKEN=$(curl -s -X POST http://localhost:8080/api/users/login \
  -F "username=demo@example.com" \
  -F "password=DemoPassword123!" | jq -r .access_token)

# 3. Upload a photo
curl -X POST http://localhost:8080/api/photos/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@path/to/photo.jpg" \
  -F "title=My Test Photo" \
  -F "is_public=true"

# 4. List your photos
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/photos/
```

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Photos Table
```sql
CREATE TABLE photos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size INTEGER NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    title VARCHAR(255),
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Sessions Table
```sql
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);
```

## 🚀 Deployment

### Development
```bash
# Start development environment
docker compose up --build

# View logs
docker compose logs -f backend

# Stop services
docker compose down
```

### Database Management
```bash
# Access PostgreSQL console
docker compose exec platform-db psql -U postgres -d photo_share

# Reset database (removes all data)
docker compose down -v && docker compose up --build
```

### Production Considerations
- Use secure JWT secrets (generate with provided script)
- Configure proper CORS origins for your frontend
- Set up SSL/TLS termination (nginx, load balancer)
- Configure persistent volume for database
- Set up monitoring and alerting (Prometheus/Grafana)
- Regular database backups
- Log aggregation and analysis

## 📁 Project Structure

```
photo-share-3/
├── .env                           # Configuration
├── docker-compose.yml             # Service deployment
├── CLAUDE.md                      # Development guidance
├── services/photoshare/           # Main application
│   ├── main_database.py          # FastAPI service (entry point)
│   ├── database.py               # PostgreSQL models & repositories
│   ├── security.py               # Security framework
│   ├── monitoring.py             # Prometheus metrics
│   ├── performance_simple.py     # Caching & optimization
│   ├── error_handling.py         # Error management
│   ├── file_storage.py           # File operations
│   ├── service_discovery.py      # Service registry
│   ├── requirements_fixed.txt    # Python dependencies
│   ├── requirements_test.txt     # Test dependencies
│   ├── run_tests.py              # Test runner
│   ├── Dockerfile.database       # Container definition
│   └── tests/                    # Test suite
│       ├── unit/                 # Unit tests
│       ├── integration/          # Integration tests
│       └── security/             # Security tests
├── tools/                        # Development and analysis tools
│   ├── docker-compose.tools.yml  # Tools container configuration  
│   ├── requirements.txt          # Tools dependencies
│   ├── sbom-agent/               # Software Bill of Materials generator
│   │   ├── src/                  # SBOM generation engine
│   │   ├── tests/                # Vulnerability test datasets
│   │   ├── reports/              # Generated SBOM analysis reports
│   │   └── docs/                 # Integration guides
│   └── shared/                   # Shared utilities
│       ├── environment_detector.py # Environment detection
│       ├── filename_manager.py   # File naming standards
│       └── version_manager.py    # Version management
├── scripts/                      # Utilities
│   ├── api-tests/                 # API testing scripts
│   │   ├── test-auth-flow.sh     # Authentication flow tests
│   │   ├── test-email-verification.sh # Email verification tests
│   │   └── test-photo-upload.sh  # Photo upload tests
│   ├── generate-jwt-secrets.py   # JWT secret generator
│   └── validate-config.py        # Configuration validation
```

## 🔍 Monitoring & Metrics

### Service Health
- **Health Endpoint**: `GET /health` - Basic service status
- **Detailed Health**: `GET /health/detailed` - Comprehensive health check (requires auth)

### Performance Metrics
- Request latency and throughput
- Database query performance
- Cache hit rates and efficiency
- Memory usage and optimization

### Security Metrics
- Authentication success/failure rates
- Rate limiting events
- Security violation attempts
- File upload validation results

## ✅ Clean Architecture

The project now maintains a clean, production-ready structure with no legacy files:

- **Current Service**: All development uses `services/photoshare/` - the active single-service application
- **Documentation**: Comprehensive and up-to-date markdown files with version tracking
- **Testing**: Complete test suite with API testing scripts in `scripts/api-tests/`
- **Tools**: Development and analysis tools in `tools/` directory

## 🤝 Contributing

1. **Development Setup**: Follow the Quick Start guide
2. **Code Standards**: FastAPI best practices, async/await patterns
3. **Security**: All changes must maintain security standards
4. **Testing**: Test API endpoints before submitting changes
5. **Documentation**: Update this README for any API changes

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **API Documentation**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health
- **Service Stats**: http://localhost:8080/api/platform/stats

For development questions, refer to `CLAUDE.md` for detailed technical guidance.