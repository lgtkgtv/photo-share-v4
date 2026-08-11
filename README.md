# PhotoShare - Photo Sharing Platform (Active Development)

**Version**: 2.4.0-separated-auth  
**Status**: Active development, not production-hardened — see [Current State](#-current-state) below  
**Last Updated**: August 10, 2026

---

## 🎯 Quick Start

PhotoShare is a photo/video sharing platform built with a separated auth-service + app-service microservices architecture. The auth/security scaffolding (SSO, 2FA, RBAC, audit logging, WAF) is extensive, and the core photo/video/album/share product features work and are covered by tests, but this has not been through an independent security review and several real bugs in the core upload/streaming path were only found and fixed in-repo testing (see below) — "zero known vulnerabilities" is not a claim this codebase can currently support.

### ⚡ One-Command Setup

```bash
git clone <your-repo-url> photoshare
cd photoshare
./scripts/quickstart.sh
```

That's it — no manual env file setup, no separate steps. `quickstart.sh` generates `.env.auth-service` and `.env.application` with fresh random secrets (a shared `JWT_SECRET_KEY` between the two services, matching database credentials — see `scripts/generate-env-files.sh` if you want to know exactly what it does), builds and starts the full `docker-compose.separated.yml` stack, and polls both services' `/health` endpoints until they're actually up (a few minutes on first run while images build). It prints a ready-to-run `curl` command to register a test user when it's done.

This has been verified by tearing the stack down completely (`docker compose down -v`, removing the built images, deleting the generated env files) and re-running `./scripts/quickstart.sh` from that clean state.

To tear down: `docker compose -f docker-compose.separated.yml down` (add `-v` to also drop the database volumes).

**🚨 CRITICAL**: For local Python work outside Docker (running tests, etc.), use `uv` — see `./scripts/dev-setup.sh`. Never use `pip` directly in this repo.

---

## 🏗️ Architecture Overview

### Separated Microservices Design
```
┌─────────────────────────────────────────────────────────┐
│                PhotoShare Platform                      │
├─────────────────────┬───────────────────────────────────┤
│   Auth Service      │   Application Service            │
│   Port 8001         │   Port 8000                      │
├─────────────────────┼───────────────────────────────────┤
│ • User Management   │ • Photo Management               │
│ • JWT Tokens        │ • File Storage                   │
│ • SSO (Google, etc) │ • Image Processing               │
│ • 2FA (TOTP, SMS)   │ • Sharing & Permissions          │
│ • RBAC Permissions  │ • Performance Optimization       │
│ • Security Audits   │ • Security Monitoring            │
├─────────────────────┼───────────────────────────────────┤
│   Auth Database     │   App Database                   │
│   Port 5433         │   Port 5432                      │
└─────────────────────┴───────────────────────────────────┘
```

### Key Features
- 🔐 **Auth Scaffolding**: SSO, 2FA, RBAC, JWT authentication (extensive, not independently audited)
- 📷 **Photo & Video Management**: Upload, organize, share, tag, comment, view analytics
- 🛡️ **Defense-in-Depth Scaffolding**: WAF, audit logging, threat-detection middleware present
- 📱 **API-First**: RESTful APIs for web, mobile, and integration
- 🔧 **Dockerized**: Runs via `docker compose`, health checks included

---

## 📌 Current State

Honest status as of this writing, not the aspirational one further down this document:

- **Real, tested product features**: photo/video upload, albums, comments, tags, view/download analytics, and time-limited signed share-download links (66 end-to-end checks across `services/photoshare/tests/test_albums_e2e.py`, `test_shares_comments_tags_analytics_e2e.py`, and `test_share_download_e2e.py`). Before those features were added, roughly 48 of the app service's 58 routes were security/observability plumbing (WAF status, audit trail, threat detection, secret rotation, etc.) and only ~10 were actual photo features — that ratio has since improved with the product API, but the plumbing still dominates the route count.
- **Core upload/streaming path had real bugs, now fixed and tested**: `/api/media/upload` (photo and video), streaming, and thumbnail generation previously failed on first real invocation — an undefined `VIDEO_PROCESSOR_AVAILABLE` name, a wrong `FileStorageService.store_file()` call signature, a nonexistent `current_user.user_uuid` attribute, an undefined `ThreatType.UPLOAD_SECURITY` enum member, a WAF file-extension allowlist that rejected every video format, an undefined `UPLOAD_DIR`, and permission checks comparing a `current_user.user_id`/`media_record.user_id` attribute that doesn't exist on either class. These were only caught because a previously-uncollectible integration test file (`tests/integration/test_media_endpoints.py`) was repaired and actually run. The `current_user.user_id` pattern appears in roughly 40 other places across `main.py` (mostly admin/security endpoints) that are outside current test coverage — a compatibility alias was added so those calls no longer raise, but their behavior beyond "doesn't crash" is unverified.
- **Automated (pytest/CI) tests run against SQLite, not Postgres.** The full product journey (register → login → upload a photo → create an album → add photo to album → create a share link → resolve it → download via the signed URL → comment → tag → check analytics) has been manually verified end-to-end against the real `docker-compose.separated.yml` Postgres stack — see `./scripts/demo-user-journey.sh` — but this is a manual script run, not part of the automated CI gate (the `docker-compose-smoke-test` CI job only covers register/login/cross-service JWT).
- **That verification found and fixed a real gap**: the RBAC seed data (`services/auth-service/setup_rbac.py`, auto-run on auth-service startup) had zero `albums:*` permissions for any role, including admin — every real registered user was locked out of creating an album (403), a check that only exists in the live-Postgres RBAC path and is invisible to the SQLite e2e tests (which fabricate a user object with hardcoded permissions rather than reading real seeded roles). Fixed by adding `albums:write`/`albums:read` to the seed data; shares/comments/tags/analytics use ownership checks rather than RBAC permission strings, so they weren't affected by this particular gap.
- **"Zero known vulnerabilities" is not a supportable claim.** No independent security audit has been performed. The claim in older docs reflected the absence of a formal pentest finding, not a verified absence of bugs — and this session found multiple functional bugs in security-adjacent code (audit logging, permission checks) on first real execution.
- **Security/admin subsystem (SSO, 2FA, RBAC, threat detection, secret rotation, etc.) is extensive but largely unit-tested only**, not exercised end-to-end against live services in this test suite.

---

## 📚 Documentation Suite

This repo has a large amount of documentation (USER_GUIDE.md, THREAT_MODEL.md, WEBAPP_ADMIN_SECURITY_GUIDE.md, SECURITY_STATUS.md, etc.). Treat claims in those documents about "production-ready," "zero known vulnerabilities," or compliance readiness with the same skepticism as the claims that used to be in this file — they have not been re-audited against the current codebase.

---

### 🚀 **START HERE** → [README.md](./README.md) (This Document)
**Quick start, architecture overview, and navigation to all other documentation**

Get running in 5 minutes, understand the architecture, and find exactly what you need.

---

### 📖 **COMPLETE GUIDE** → [USER_GUIDE.md](./USER_GUIDE.md) 
**460+ pages | The definitive PhotoShare resource**

**Everything you need to know about PhotoShare in one comprehensive guide:**
- 🏗️ **Architecture Deep Dive**: Complete separated microservices design
- 🛠️ **Development Setup**: From zero to running (5-minute setup included)
- 🧪 **Testing Framework**: Unit, integration, security, performance testing  
- 🚀 **Production Deployment**: Zero-downtime deployment with monitoring
- 📚 **Complete API Reference**: Every endpoint documented with examples
- 🎓 **Advanced Usage**: Custom integrations, security config, troubleshooting
- 🔧 **Development Workflow**: Code development, debugging, best practices

**📍 Use this for**: Development, deployment, API integration, troubleshooting

---

### 🛡️ **SECURITY ARCHITECTURE** → [THREAT_MODEL.md](./THREAT_MODEL.md)
**A design-time STRIDE threat model — not an audit result; see [Current State](#-current-state)**

**Threat analysis and intended mitigations:**
- 🎯 **STRIDE Analysis**: Systematic identification of all threats
- 🔒 **Asset Protection**: Critical, high, and medium value asset security
- 📊 **Risk Assessment**: Threat heat maps showing mitigation effectiveness  
- 🚨 **Attack Scenarios**: Real-world attack patterns and comprehensive defenses
- 📈 **Security Controls Matrix**: 40+ implemented controls with status
- 🔄 **Security Maintenance**: Daily, weekly, monthly, quarterly procedures

**📍 Use this for**: Security architecture, threat assessment, compliance, audits

---

### 🔐 **SECURITY OPERATIONS** → [WEBAPP_ADMIN_SECURITY_GUIDE.md](./WEBAPP_ADMIN_SECURITY_GUIDE.md)
**300+ pages | Daily security operations and incident response**

**Everything needed for secure operations:**
- 🚀 **5-Minute Security Dashboard**: Quick daily security health checks
- 🛡️ **Daily Security Operations**: Morning routines and continuous monitoring
- 🚨 **4-Level Incident Response**: From info to emergency with automated procedures
- 👥 **RBAC Administration**: Complete user management and permission control
- 💾 **Security-Focused Backup**: Encrypted backup and disaster recovery procedures
- 📞 **Emergency Procedures**: Security lockdown and recovery scripts
- 🔧 **Security API Reference**: All security endpoints with examples
- 🆘 **Troubleshooting Guide**: Common security issues and resolutions

**📍 Use this for**: Daily operations, incident response, security administration

---

### 🛡️ **SECURITY STATUS** → [SECURITY_STATUS.md](./SECURITY_STATUS.md)
**Security implementation inventory — not an audit result. See [Current State](#-current-state) above.**

- 🔧 **Extensive security scaffolding present**: WAF, audit logging, RBAC, 2FA, secret rotation, threat-detection middleware
- ⚠️ **Not independently audited**: no external pentest or security review has been performed
- ⚠️ **Coverage is mostly unit-level**: security modules are unit-tested; end-to-end behavior against live services is largely unverified
- ⚠️ **Compliance claims (GDPR, SOC 2) are unverified**: nothing in this repo constitutes a compliance certification

**📍 Use this for**: an inventory of what security mechanisms exist, not a guarantee of their correctness

---

### 🔮 **FUTURE ROADMAP** → [FUTURE_ENHANCEMENT_ROADMAP.md](./FUTURE_ENHANCEMENT_ROADMAP.md)
**Strategic enhancement plan with cloud-native infrastructure, AI features, and platform expansion**

**4-phase strategic growth plan:**
- **Phase 1**: Cloud-Native Infrastructure (Kubernetes, service mesh)
- **Phase 2**: Advanced API Management (Enterprise gateway, developer portal)
- **Phase 3**: AI-Powered Features (Content recognition, smart organization)
- **Phase 4**: Platform Expansion (Video support, mobile/desktop apps)

**📍 Use this for**: Strategic planning, feature prioritization, resource planning

---

### 🛠️ **DEVELOPER GUIDANCE** → [CLAUDE.md](./CLAUDE.md)
**100+ pages | AI assistant and developer guidance for the codebase**

**Comprehensive development guidance:**
- 📁 **Project Structure**: Detailed directory and file organization
- ⚙️ **Configuration**: Complete environment setup and service configuration
- 🔧 **Development Workflow**: Code development, testing, and debugging
- 🚀 **Deployment Process**: Development to production deployment
- 📋 **Development Standards**: Code quality, security practices, documentation

**📍 Use this for**: New developer onboarding, development standards, AI assistant guidance

---

## 📂 **Clean Documentation Structure**

PhotoShare maintains a clean, organized documentation structure with **6 core documents** and archived historical materials:

### ✨ **Active Core Documents**:
- **[README.md](./README.md)** - This document: Quick start and navigation
- **[USER_GUIDE.md](./USER_GUIDE.md)** - Development and deployment guide
- **[THREAT_MODEL.md](./THREAT_MODEL.md)** - Security architecture and threat analysis (design-time analysis, not an audit result)
- **[WEBAPP_ADMIN_SECURITY_GUIDE.md](./WEBAPP_ADMIN_SECURITY_GUIDE.md)** - Security operations and incident response
- **[SECURITY_STATUS.md](./SECURITY_STATUS.md)** - Security implementation inventory (not independently audited — see [Current State](#-current-state))
- **[FUTURE_ENHANCEMENT_ROADMAP.md](./FUTURE_ENHANCEMENT_ROADMAP.md)** - Strategic 4-phase enhancement plan

### 🔗 **Redirect Documents** (Consolidated Content):
- **[PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)** → Redirects to [USER_GUIDE.md Production Section](./USER_GUIDE.md#-production-deployment)
- **[FRESH_REBUILD_ISSUES_REPORT.md](./FRESH_REBUILD_ISSUES_REPORT.md)** → Archive reference (all issues resolved)

### 📁 **Archived Documentation** (`./archive/`):
**Historical development documents preserved for reference:**
- Development Planning: `WORK_REMAINING.md`, `DIRECTORY_ANALYSIS.md`, `DIRECTORY_REORGANIZATION_SUMMARY.md`
- Security History: `SECURITY_GAPS_ANALYSIS.md` (renamed to avoid confusion - all gaps resolved)
- Implementation Plans: `VIDEO_SUPPORT_IMPLEMENTATION_PLAN.md` (consolidated into roadmap)
- Historical Reports: `FRESH_REBUILD_ISSUES_REPORT.md` (all issues resolved)
- Historical Threat Models: Previous service-specific models (consolidated into main THREAT_MODEL.md)

---

## 🧭 **Documentation Navigation Guide**

### **I'm New to PhotoShare** 
👉 **Start with**: [README.md Quick Start](#-5-minute-setup) → **IMPORTANT**: Run `./scripts/dev-setup.sh` first → [USER_GUIDE.md Development Setup](./USER_GUIDE.md#️-development-setup)

### **I'm Deploying to Production**
👉 **Follow**: [USER_GUIDE.md Production Deployment](./USER_GUIDE.md#-production-deployment) → [WEBAPP_ADMIN_SECURITY_GUIDE.md Operations](./WEBAPP_ADMIN_SECURITY_GUIDE.md#️-daily-security-operations)

### **I'm Building an Integration**
👉 **Reference**: [README.md API Quick Reference](#-api-quick-reference) → [USER_GUIDE.md Complete API Reference](./USER_GUIDE.md#-api-reference)

### **I'm Responsible for Security**
👉 **Study**: [THREAT_MODEL.md](./THREAT_MODEL.md) → [WEBAPP_ADMIN_SECURITY_GUIDE.md](./WEBAPP_ADMIN_SECURITY_GUIDE.md)

### **I'm Planning Future Development**  
👉 **Review**: [FUTURE_ENHANCEMENT_ROADMAP.md](./FUTURE_ENHANCEMENT_ROADMAP.md) → [USER_GUIDE.md Advanced Usage](./USER_GUIDE.md#-advanced-usage)

### **I'm Troubleshooting Issues**
👉 **Check**: [README.md Troubleshooting](#-troubleshooting) → [USER_GUIDE.md Complete Troubleshooting](./USER_GUIDE.md#-troubleshooting) → [WEBAPP_ADMIN_SECURITY_GUIDE.md Security Issues](./WEBAPP_ADMIN_SECURITY_GUIDE.md#-troubleshooting-guide)

### **I'm an AI Assistant Working on This Code**
👉 **Follow**: [CLAUDE.md](./CLAUDE.md) for complete development guidance and project context

---

## 📊 **Documentation Notes**

- 📚 **Large volume**: extensive documentation across README/USER_GUIDE/THREAT_MODEL/security guides
- ⚠️ **Not all current**: much of it predates the Phase 1 product API and the bug fixes described in [Current State](#-current-state); treat specific claims skeptically and verify against code
- 🧭 **Accessible**: clear navigation and multiple entry points

---

## 🚀 Deployment Options

### Development Environment
```bash
# REQUIRED: Set up Python environment first
./scripts/dev-setup.sh
source .venv/bin/activate

# Start services (Auth + App + Databases)
docker compose -f docker-compose.separated.yml up -d

# View logs
docker compose -f docker-compose.separated.yml logs -f
```

### Production Environment with Monitoring
```bash
# Full production stack with Prometheus & Grafana
docker compose -f docker-compose.separated.yml --profile monitoring up -d

# Access dashboards
echo "Grafana: http://localhost:3000 (admin/admin123)"
echo "Prometheus: http://localhost:9090"
```

### Production Environment with Reverse Proxy
```bash
# Production with NGINX reverse proxy
docker compose -f docker-compose.separated.yml --profile proxy --profile monitoring up -d
```

---

## 🔐 Security Features

### Authentication & Authorization
- ✅ **Multi-Factor Authentication**: TOTP, SMS, backup codes
- ✅ **Single Sign-On**: Google, GitHub, custom providers
- ✅ **Role-Based Access Control**: Granular permissions system
- ✅ **JWT Security**: Short-lived tokens with refresh rotation
- ✅ **Session Management**: Secure session handling and timeouts

### Data Protection
- ✅ **Encryption at Rest**: Database and file storage encryption
- ✅ **Encryption in Transit**: TLS 1.3 for all communications
- ✅ **Input Validation**: Comprehensive sanitization and validation
- ✅ **File Security**: Virus scanning and content analysis
- ✅ **Database Isolation**: Complete separation of auth and app data

### Monitoring & Response
- ✅ **Real-time Monitoring**: Security event detection and alerting
- ✅ **Audit Logging**: Tamper-proof audit trails
- ✅ **Threat Detection**: ML-based anomaly detection
- ✅ **Incident Response**: Automated containment and alerting
- ✅ **Compliance**: GDPR, SOC 2, regulatory compliance

---

## 📊 API Quick Reference

### Authentication Service (Port 8001)
```bash
# User registration
POST /api/auth/register

# User login
POST /api/auth/login

# Enable 2FA
POST /api/auth/2fa/enable

# SSO providers
GET /api/auth/sso/providers

# Health check
GET /health
```

### Application Service (Port 8000)  
```bash
# Photo upload
POST /api/photos/upload

# List photos
GET /api/photos/

# Download photo
GET /api/photos/{id}/download

# Platform stats
GET /api/platform/stats

# Security status
GET /api/platform/security
```

**📚 Full API documentation with examples available in [USER_GUIDE.md](./USER_GUIDE.md#-api-reference)**

---

## 🧪 Testing & Validation

### Test Suite
- **Unit tests** (`tests/unit/`, 208 tests): run against SQLite in-process, no live services needed
- **Phase 1 product API e2e tests** (`services/photoshare/tests/`): albums, shares/comments/tags/analytics, and signed share-download — 66 checks, SQLite-backed, run as plain scripts (`python <file>.py`), not via pytest
- **Two self-contained integration/security files**: `tests/integration/test_media_endpoints.py` (19 tests, upload/streaming/thumbnail/metadata against a mocked FastAPI dependency graph) and `tests/security/test_waf_protection.py` (12 tests) — both SQLite/mock-backed, no live services
- **Everything else under `tests/integration/` and `tests/security/`**: requires live auth-service + app-service instances running on localhost, or exercises code paths not covered by current fixtures — expect these to fail or need live services rather than treating a failure as something broken
- **CI** (`.github/workflows/ci.yml`) runs all of the above self-contained suites on every push/PR, plus a separate job that boots the real `docker-compose.separated.yml` stack (real Postgres) and smoke-tests register → login → cross-service JWT validation
- **Full user-journey demo against real Postgres** (`./scripts/demo-user-journey.sh`): register → login → upload a photo → create an album → add photo to album → create a share link → resolve it → download via the signed URL → comment → tag → check analytics. Run `./scripts/quickstart.sh` first, then this script. Manually verified, not (yet) part of the CI gate.

### Quick Test Commands
```bash
# REQUIRED: Activate Python environment first
source .venv/bin/activate

# What CI runs (all self-contained, no live services needed)
uv run pytest tests/unit/ -v
uv run pytest tests/integration/test_media_endpoints.py tests/security/test_waf_protection.py -v
uv run python services/photoshare/tests/test_albums_e2e.py
uv run python services/photoshare/tests/test_shares_comments_tags_analytics_e2e.py
uv run python services/photoshare/tests/test_share_download_e2e.py

# Everything else in tests/integration/ and tests/security/ needs live services --
# start them first (./scripts/quickstart.sh), then:
uv run pytest tests/integration/ tests/security/ -v
```

---

## 🛠️ Common Operations

### Service Management
```bash
# Check service status
docker compose -f docker-compose.separated.yml ps

# View service logs
docker compose -f docker-compose.separated.yml logs -f auth-service
docker compose -f docker-compose.separated.yml logs -f photo-share-app

# Restart specific service
docker compose -f docker-compose.separated.yml restart auth-service
```

### Database Operations
```bash
# Access auth database
docker compose -f docker-compose.separated.yml exec auth-db \
  psql -U auth_user -d photo_share_auth

# Access app database  
docker compose -f docker-compose.separated.yml exec app-db \
  psql -U app_user -d photo_share_app
```

### Security Operations
```bash
# Check security status
curl -s http://localhost:8000/api/platform/security | jq '.'

# View recent security events
curl -s http://localhost:8000/api/security/events | jq '.'

# Check system health
curl -s http://localhost:8001/health && curl -s http://localhost:8000/health
```

---

## 🔧 Troubleshooting

### Common Issues & Quick Fixes

#### Services Won't Start
```bash
# Check Docker resources
docker system df

# Clean up if needed
docker system prune -f

# Rebuild from scratch
docker compose -f docker-compose.separated.yml down
docker compose -f docker-compose.separated.yml up --build -d
```

#### JWT Token Issues
```bash
# Verify JWT secrets match
grep JWT_SECRET .env.auth-service
grep JWT_SECRET .env.application

# If different, fix and restart
docker compose -f docker-compose.separated.yml restart auth-service photo-share-app
```

#### Database Connection Issues
```bash
# Test database health
docker exec photoshare-auth-db pg_isready -U auth_user
docker exec photoshare-app-db pg_isready -U app_user

# Restart databases if needed
docker compose -f docker-compose.separated.yml restart auth-db app-db
```

**📖 Complete troubleshooting guide available in [USER_GUIDE.md](./USER_GUIDE.md#-troubleshooting)**

---

## 📈 System Requirements

### Minimum Requirements
- **Docker**: Version 20.0+ with Docker Compose V2
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 20GB free space
- **Network**: Broadband internet

### Recommended Production
- **CPU**: 8+ cores  
- **RAM**: 16GB+
- **Storage**: 100GB+ SSD
- **Network**: High-bandwidth, low-latency connection

---

## 🤝 Support & Resources

### Documentation Priority
1. **[USER_GUIDE.md](./USER_GUIDE.md)** - Start here for comprehensive information
2. **[WEBAPP_ADMIN_SECURITY_GUIDE.md](./WEBAPP_ADMIN_SECURITY_GUIDE.md)** - For security operations
3. **[THREAT_MODEL.md](./THREAT_MODEL.md)** - For security architecture questions
4. **[CLAUDE.md](./CLAUDE.md)** - For development guidance

### Quick Help
- ❓ **Setup Issues**: Check [USER_GUIDE.md - Development Setup](./USER_GUIDE.md#️-development-setup)
- 🔒 **Security Questions**: Check [WEBAPP_ADMIN_SECURITY_GUIDE.md](./WEBAPP_ADMIN_SECURITY_GUIDE.md)  
- 🐛 **Bugs & Issues**: Check [USER_GUIDE.md - Troubleshooting](./USER_GUIDE.md#-troubleshooting)
- 📚 **API Integration**: Check [USER_GUIDE.md - API Reference](./USER_GUIDE.md#-api-reference)

### System Status
- ✅ **Core product features working and tested**: photo/video upload, albums, sharing, comments, tags, analytics
- ⚠️ **Not production-hardened**: no independent security audit; see [Current State](#-current-state)
- ⚠️ **STRIDE analysis in THREAT_MODEL.md is a design-time exercise**, not a verification that the implementation matches the model
- 🔧 **Monitoring/caching scaffolding present** (Prometheus metrics, middleware) — not validated under load

---

## 🏆 Project Status

PhotoShare is under active development. What's real:

- 🔐 **Auth scaffolding**: SSO, 2FA, RBAC, JWT — extensive, not independently audited
- 📷 **Core product features**: upload, albums, sharing, comments, tags, analytics — tested, working
- 🧪 **Test coverage**: solid at the unit and Phase-1-product-API level; integration/security tests need live services and mostly aren't run in CI (see [Current State](#-current-state))
- 🚀 **Deployment**: `docker compose` based; a genuinely one-command fresh-clone setup and CI running the full suite are tracked as open work, not yet done

---

**🚀 Ready to get started?** Follow the [5-minute setup](#-5-minute-setup) above, and read [Current State](#-current-state) first so you know what's actually been verified.
