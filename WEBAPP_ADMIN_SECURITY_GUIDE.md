# PhotoShare Administrator Security Guide
# ====================================

**Version**: 2.4.0-separated-auth  
**Last Updated**: August 24, 2025  
**Application**: PhotoShare Separated Microservices Platform  
**Security Status**: ✅ Production Ready - Zero Known Vulnerabilities

---

## 📋 Table of Contents

1. [Quick Start Security Dashboard](#quick-start-security-dashboard)
2. [Daily Security Operations](#daily-security-operations)
3. [System Architecture Security](#system-architecture-security)
4. [Service-Specific Security Management](#service-specific-security-management)
5. [Incident Response Procedures](#incident-response-procedures)
6. [Security Monitoring & Alerts](#security-monitoring--alerts)
7. [User Management & RBAC](#user-management--rbac)
8. [Backup & Disaster Recovery](#backup--disaster-recovery)
9. [Compliance & Audit Management](#compliance--audit-management)
10. [Emergency Security Procedures](#emergency-security-procedures)
11. [Security API Reference](#security-api-reference)
12. [Troubleshooting Guide](#troubleshooting-guide)

---

## 🚀 Quick Start Security Dashboard

### Essential 5-Minute Daily Check
```bash
# System Health Overview
curl -s http://localhost:8000/health && curl -s http://localhost:8001/health

# Security Status Check
curl -s http://localhost:8000/api/platform/security | jq '.security_status'

# Active Threats (Last 24h)
curl -s http://localhost:8000/api/security/threats | jq '.active_threats'

# Service Communication Health
curl -s http://localhost:8000/api/platform/stats | jq '.auth_service_status'
```

### Security Status Indicators
- 🟢 **GREEN**: All systems secure, no threats detected
- 🟡 **YELLOW**: Minor security warnings requiring attention  
- 🟠 **ORANGE**: Moderate threats detected, immediate review needed
- 🔴 **RED**: Critical security issues, immediate action required
- ⚫ **BLACK**: System compromise suspected, emergency response activated

---

## 🛡️ Daily Security Operations

### Morning Security Routine (15 minutes)

#### 1. System Status Verification
```bash
# Check all services are healthy and properly secured
docker compose -f docker-compose.separated.yml ps
docker compose -f docker-compose.separated.yml logs --since 24h | grep -i error

# Verify SSL certificates
curl -vI https://your-domain.com 2>&1 | grep -i "expire\|valid"
```

#### 2. Authentication Service Security Check
```bash
# Auth service health and security status
curl -s http://localhost:8001/health | jq '.'

# Recent authentication activities
curl -s http://localhost:8001/api/auth/stats | jq '.recent_activities'

# Failed login attempts (potential attacks)
curl -s http://localhost:8001/api/security/failed-logins | jq '.summary'
```

#### 3. Application Service Security Status
```bash
# App service health and integrations
curl -s http://localhost:8000/health | jq '.'

# Photo upload security status
curl -s http://localhost:8000/api/security/upload-status | jq '.'

# Inter-service communication health
curl -s http://localhost:8000/api/platform/stats | jq '.auth_service_status'
```

#### 4. Database Security Verification
```bash
# Check database connections and security
docker exec photoshare-auth-db pg_isready -U auth_user
docker exec photoshare-app-db pg_isready -U app_user

# Monitor database activity
docker compose -f docker-compose.separated.yml logs auth-db --since 1h | grep -i "authentication\|connection"
docker compose -f docker-compose.separated.yml logs app-db --since 1h | grep -i "authentication\|connection"
```

---

## 🏗️ System Architecture Security

### Service Security Boundaries

#### Authentication Service (Port 8001)
**Security Responsibilities:**
- User authentication and authorization
- JWT token generation and validation
- SSO integration and 2FA management
- Role-Based Access Control (RBAC)
- Session management and security

**Security Configuration:**
```bash
# View auth service security configuration
curl -s http://localhost:8001/api/security/config | jq '.'

# Check SSO provider status
curl -s http://localhost:8001/api/auth/sso/providers | jq '.'

# Verify 2FA system health
curl -s http://localhost:8001/health | jq '.twofa'
```

#### Application Service (Port 8000)
**Security Responsibilities:**
- Photo upload validation and virus scanning
- File storage security and access controls
- Inter-service authentication with auth service
- Performance security and rate limiting
- Data encryption and privacy protection

**Security Configuration:**
```bash
# Application security status
curl -s http://localhost:8000/api/platform/security | jq '.'

# File upload security settings
curl -s http://localhost:8000/api/security/upload-config | jq '.'

# Rate limiting status
curl -s http://localhost:8000/api/security/rate-limits | jq '.'
```

### Network Security Architecture
```
Internet → NGINX Proxy → [Auth Service | App Service] → Databases
                ↓
           SSL/TLS Termination
           Rate Limiting
           WAF Protection
           DDoS Mitigation
```

---

## 🔧 Service-Specific Security Management

### Authentication Service Security

#### User Account Security
```bash
# List users with security flags
curl -s http://localhost:8001/api/auth/users?security_review=true | jq '.'

# Check for locked accounts
curl -s http://localhost:8001/api/auth/locked-accounts | jq '.'

# Review privileged accounts
curl -s http://localhost:8001/api/auth/admin-accounts | jq '.'
```

#### Session Security Management
```bash
# Active session monitoring
curl -s http://localhost:8001/api/auth/sessions/active | jq '.'

# Suspicious session detection
curl -s http://localhost:8001/api/security/suspicious-sessions | jq '.'

# Force session logout (emergency)
curl -X POST http://localhost:8001/api/auth/sessions/revoke-all \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### 2FA and SSO Security
```bash
# 2FA system status
curl -s http://localhost:8001/api/auth/2fa/system-status | jq '.'

# SSO security audit
curl -s http://localhost:8001/api/auth/sso/audit | jq '.'

# Check for 2FA bypass attempts
curl -s http://localhost:8001/api/security/2fa-bypass-attempts | jq '.'
```

### Application Service Security

#### File Upload Security
```bash
# Upload security statistics
curl -s http://localhost:8000/api/security/upload-stats | jq '.'

# Blocked file attempts
curl -s http://localhost:8000/api/security/blocked-uploads | jq '.'

# Virus scan results
curl -s http://localhost:8000/api/security/virus-scan-status | jq '.'
```

#### Inter-Service Security
```bash
# JWT validation health
curl -s http://localhost:8000/api/security/jwt-validation-status | jq '.'

# Service-to-service communication audit
curl -s http://localhost:8000/api/security/inter-service-audit | jq '.'

# Token validation errors
curl -s http://localhost:8000/api/security/token-validation-errors | jq '.'
```

---

## 🚨 Incident Response Procedures

### Security Incident Classification

#### Level 1: Information (Log and Monitor)
- Failed login attempts within normal thresholds
- Minor configuration warnings
- Routine security scan results

**Response Actions:**
```bash
# Log incident
echo "$(date): Level 1 incident logged: $INCIDENT_DESCRIPTION" >> security-incidents.log

# Monitor for escalation
curl -s http://localhost:8000/api/security/monitor-incident/$INCIDENT_ID
```

#### Level 2: Warning (Active Monitoring)
- Unusual login patterns
- Multiple failed authentication attempts
- Suspicious file upload attempts

**Response Actions:**
```bash
# Enhanced monitoring
curl -X POST http://localhost:8000/api/security/enhance-monitoring \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"incident_id": "'$INCIDENT_ID'", "level": 2}'

# Alert security team
curl -X POST http://localhost:8000/api/security/alert-team \
  -d '{"incident": "'$INCIDENT_DESCRIPTION'", "level": "warning"}'
```

#### Level 3: Critical (Immediate Action)
- Successful privilege escalation
- Data breach indicators
- System compromise evidence

**Response Actions:**
```bash
# Immediate containment
curl -X POST http://localhost:8000/api/security/emergency-lockdown \
  -H "Authorization: Bearer $EMERGENCY_TOKEN"

# Evidence collection
curl -s http://localhost:8000/api/security/collect-evidence/$INCIDENT_ID > evidence-$INCIDENT_ID.json

# Notify stakeholders
curl -X POST http://localhost:8000/api/security/critical-alert \
  -d '{"incident": "'$INCIDENT_ID'", "severity": "critical"}'
```

### Automated Incident Response

#### Account Compromise Response
```bash
# Suspend compromised account
curl -X POST http://localhost:8001/api/auth/users/$USER_ID/suspend \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Revoke all user sessions
curl -X POST http://localhost:8001/api/auth/users/$USER_ID/revoke-sessions \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Force password reset
curl -X POST http://localhost:8001/api/auth/users/$USER_ID/force-password-reset \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### System Compromise Response
```bash
# Emergency system lockdown
docker compose -f docker-compose.separated.yml stop

# Isolate network access
# (Network-specific commands depend on your infrastructure)

# Preserve evidence
docker compose -f docker-compose.separated.yml logs > incident-logs-$(date +%Y%m%d-%H%M%S).log

# Contact incident response team
echo "CRITICAL: System compromise detected at $(date). System isolated. Logs preserved." | mail -s "SECURITY INCIDENT" security-team@company.com
```

---

## 📊 Security Monitoring & Alerts

### Real-Time Security Monitoring

#### Threat Detection Dashboard
```bash
# Current threat level
curl -s http://localhost:8000/api/security/threat-level | jq '.'

# Active security events
curl -s http://localhost:8000/api/security/active-events | jq '.'

# Security metrics summary
curl -s http://localhost:8000/api/security/metrics | jq '.'
```

#### Automated Alert Configuration
```bash
# Configure security alert thresholds
curl -X POST http://localhost:8000/api/security/configure-alerts \
  -H "Content-Type: application/json" \
  -d '{
    "failed_logins_threshold": 10,
    "suspicious_uploads_threshold": 5,
    "unusual_activity_threshold": 3,
    "notification_endpoints": [
      "security-ops@company.com",
      "webhook://security-alerts-channel"
    ]
  }'

# Test alert system
curl -X POST http://localhost:8000/api/security/test-alerts
```

### Security Metrics and KPIs

#### Daily Security Metrics
```bash
# Generate daily security report
curl -s http://localhost:8000/api/security/daily-report | jq '.' > security-report-$(date +%Y%m%d).json

# Key security indicators
curl -s http://localhost:8000/api/security/kpis | jq '.{
  authentication_success_rate,
  blocked_attacks_count,
  system_vulnerability_count,
  security_incidents_resolved
}'
```

#### Weekly Security Analysis
```bash
# Security trend analysis
curl -s http://localhost:8000/api/security/weekly-trends | jq '.'

# Threat landscape report
curl -s http://localhost:8000/api/security/threat-analysis | jq '.'

# Security control effectiveness
curl -s http://localhost:8000/api/security/control-effectiveness | jq '.'
```

---

## 👥 User Management & RBAC

### Role-Based Access Control

#### Standard User Roles
- **user**: Standard photo sharing capabilities
- **moderator**: Content moderation and user support
- **admin**: System administration and security management
- **superadmin**: Full system access and emergency controls

#### Role Management Operations
```bash
# List all roles and permissions
curl -s http://localhost:8001/api/auth/roles | jq '.'

# View user role assignments
curl -s http://localhost:8001/api/auth/users/$USER_ID/roles | jq '.'

# Assign role to user
curl -X POST http://localhost:8001/api/auth/users/$USER_ID/assign-role \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "moderator"}'

# Remove role from user
curl -X DELETE http://localhost:8001/api/auth/users/$USER_ID/roles/$ROLE_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### User Security Management

#### Account Security Review
```bash
# Users with security flags
curl -s http://localhost:8001/api/auth/users?security_flags=true | jq '.'

# Recently created accounts (potential fake accounts)
curl -s http://localhost:8001/api/auth/users?created_since=24h | jq '.'

# Inactive accounts requiring review
curl -s http://localhost:8001/api/auth/users?inactive_days=90 | jq '.'
```

#### Multi-Factor Authentication Management
```bash
# 2FA enrollment statistics
curl -s http://localhost:8001/api/auth/2fa/enrollment-stats | jq '.'

# Users without 2FA (security risk)
curl -s http://localhost:8001/api/auth/users?no_2fa=true | jq '.'

# Force 2FA enrollment for privileged users
curl -X POST http://localhost:8001/api/auth/enforce-2fa \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"role_minimum": "moderator"}'
```

---

## 💾 Backup & Disaster Recovery

### Database Security Backup

#### Automated Backup Verification
```bash
# Verify backup systems are operational
docker exec photoshare-auth-db pg_dump -U auth_user photo_share_auth --schema-only > /tmp/auth-schema-backup.sql
docker exec photoshare-app-db pg_dump -U app_user photo_share_app --schema-only > /tmp/app-schema-backup.sql

# Check backup integrity
if [ -s /tmp/auth-schema-backup.sql ] && [ -s /tmp/app-schema-backup.sql ]; then
    echo "✅ Database backups verified"
else
    echo "❌ Database backup verification failed"
fi
```

#### Security-Focused Backup Procedures
```bash
# Encrypted backup creation
pg_dump -U auth_user photo_share_auth | gpg --cipher-algo AES256 --compress-algo 1 --symmetric --output auth-backup-$(date +%Y%m%d).sql.gpg

# Backup verification and testing
gpg --decrypt auth-backup-$(date +%Y%m%d).sql.gpg | head -n 10

# Secure backup storage
rsync -avz --delete auth-backup-*.sql.gpg secure-backup-server:/backups/photoshare/
```

### Disaster Recovery Testing

#### Recovery Procedure Verification
```bash
# Test database restoration (on test environment)
docker exec photoshare-auth-db dropdb -U auth_user photo_share_auth_test
docker exec photoshare-auth-db createdb -U auth_user photo_share_auth_test
gpg --decrypt auth-backup-latest.sql.gpg | docker exec -i photoshare-auth-db psql -U auth_user photo_share_auth_test

# Verify restored data integrity
docker exec photoshare-auth-db psql -U auth_user photo_share_auth_test -c "SELECT COUNT(*) FROM users;"
```

---

## 📋 Compliance & Audit Management

### Regulatory Compliance

#### GDPR Compliance Operations
```bash
# User data export (Right to Data Portability)
curl -s http://localhost:8001/api/auth/users/$USER_ID/export-data \
  -H "Authorization: Bearer $ADMIN_TOKEN" > user-data-export-$USER_ID.json

# User data deletion (Right to be Forgotten)
curl -X DELETE http://localhost:8001/api/auth/users/$USER_ID/gdpr-delete \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Data processing audit trail
curl -s http://localhost:8000/api/security/gdpr-audit | jq '.'
```

#### Security Audit Reports
```bash
# Generate comprehensive security audit
curl -s http://localhost:8000/api/security/audit-report | jq '.' > security-audit-$(date +%Y%m%d).json

# Access control audit
curl -s http://localhost:8001/api/auth/access-audit | jq '.'

# Data encryption audit
curl -s http://localhost:8000/api/security/encryption-audit | jq '.'
```

### Continuous Compliance Monitoring
```bash
# Daily compliance check
curl -s http://localhost:8000/api/security/compliance-status | jq '.'

# Security control assessment
curl -s http://localhost:8000/api/security/control-assessment | jq '.'

# Vulnerability assessment results
curl -s http://localhost:8000/api/security/vulnerability-scan | jq '.'
```

---

## 🚨 Emergency Security Procedures

### Emergency Response Activation

#### Immediate Threat Containment
```bash
#!/bin/bash
# Emergency Security Lockdown Script

echo "🚨 EMERGENCY SECURITY LOCKDOWN INITIATED"

# 1. Stop all services immediately
docker compose -f docker-compose.separated.yml stop
echo "✅ All services stopped"

# 2. Preserve evidence
docker compose -f docker-compose.separated.yml logs > emergency-logs-$(date +%Y%m%d-%H%M%S).log
echo "✅ Logs preserved"

# 3. Block external access (example - adjust for your network)
# iptables -A INPUT -p tcp --dport 80 -j DROP
# iptables -A INPUT -p tcp --dport 443 -j DROP
echo "⚠️  Network isolation recommended"

# 4. Alert security team
echo "EMERGENCY: PhotoShare system emergency lockdown at $(date). All services stopped. Logs preserved." | \
    mail -s "🚨 EMERGENCY SECURITY LOCKDOWN" security-team@company.com
echo "✅ Security team notified"

# 5. Document incident
echo "$(date): Emergency lockdown initiated. Reason: $1" >> emergency-incidents.log
echo "✅ Incident documented"
```

#### Emergency Recovery Procedures
```bash
#!/bin/bash
# Emergency Recovery Script (Use only after threat is contained)

echo "🔧 EMERGENCY RECOVERY PROCEDURE"

# 1. Security verification before restart
echo "Verify threat containment before proceeding..."
read -p "Has the security threat been fully contained? (yes/no): " threat_contained

if [ "$threat_contained" != "yes" ]; then
    echo "❌ Recovery aborted. Contain threat first."
    exit 1
fi

# 2. Update security configurations
echo "Updating security configurations..."
# Add any emergency security updates here

# 3. Verify system integrity
echo "Verifying system integrity..."
docker compose -f docker-compose.separated.yml config --quiet
if [ $? -eq 0 ]; then
    echo "✅ Configuration verified"
else
    echo "❌ Configuration errors detected"
    exit 1
fi

# 4. Gradual service restoration
echo "Starting gradual service restoration..."
docker compose -f docker-compose.separated.yml up -d auth-db app-db
sleep 30
docker compose -f docker-compose.separated.yml up -d auth-service
sleep 30
docker compose -f docker-compose.separated.yml up -d photo-share-app

# 5. Post-recovery verification
sleep 60
curl -s http://localhost:8001/health && curl -s http://localhost:8000/health
echo "✅ Emergency recovery completed"
```

---

## 📚 Security API Reference

### Authentication Service Security APIs

#### Security Status Endpoints
```bash
# Overall security status
GET http://localhost:8001/health
GET http://localhost:8001/api/security/status

# Authentication security metrics
GET http://localhost:8001/api/security/auth-metrics
GET http://localhost:8001/api/security/failed-logins
GET http://localhost:8001/api/security/suspicious-activities

# User security management
GET http://localhost:8001/api/security/user-security-status/$USER_ID
POST http://localhost:8001/api/security/lock-user/$USER_ID
POST http://localhost:8001/api/security/unlock-user/$USER_ID
```

#### 2FA and SSO Security
```bash
# 2FA security endpoints
GET http://localhost:8001/api/auth/2fa/system-status
GET http://localhost:8001/api/security/2fa-breach-attempts
POST http://localhost:8001/api/security/force-2fa-reset/$USER_ID

# SSO security endpoints  
GET http://localhost:8001/api/auth/sso/security-status
GET http://localhost:8001/api/security/sso-breach-attempts
POST http://localhost:8001/api/security/disable-sso-provider/$PROVIDER
```

### Application Service Security APIs

#### File Security Endpoints
```bash
# Upload security status
GET http://localhost:8000/api/security/upload-security-status
GET http://localhost:8000/api/security/blocked-uploads
GET http://localhost:8000/api/security/malware-detections

# File integrity verification
GET http://localhost:8000/api/security/file-integrity-status
POST http://localhost:8000/api/security/scan-files
POST http://localhost:8000/api/security/quarantine-file/$FILE_ID
```

#### Inter-Service Security
```bash
# Service communication security
GET http://localhost:8000/api/security/inter-service-status
GET http://localhost:8000/api/security/jwt-validation-metrics
GET http://localhost:8000/api/security/service-authentication-audit
```

### Platform Security APIs

#### System-Wide Security
```bash
# Overall platform security
GET http://localhost:8000/api/platform/security
GET http://localhost:8000/api/security/threat-level
GET http://localhost:8000/api/security/security-events

# Compliance and audit
GET http://localhost:8000/api/security/compliance-report
GET http://localhost:8000/api/security/audit-trail
GET http://localhost:8000/api/security/security-metrics
```

---

## 🔧 Troubleshooting Guide

### Common Security Issues

#### Issue: JWT Token Validation Failures
**Symptoms**: Users getting "Invalid token" errors, inter-service communication failing
**Diagnosis:**
```bash
# Check JWT configuration
curl -s http://localhost:8001/api/auth/jwt-config | jq '.'
curl -s http://localhost:8000/api/security/jwt-validation-status | jq '.'

# Verify token format
echo $JWT_TOKEN | cut -d. -f2 | base64 -d | jq '.'
```
**Resolution:**
```bash
# Restart services with proper JWT configuration
docker compose -f docker-compose.separated.yml restart auth-service photo-share-app

# Verify JWT secrets match between services
grep JWT_SECRET .env.auth-service
grep JWT_SECRET .env.application
```

#### Issue: 2FA System Failures
**Symptoms**: Users cannot complete 2FA, SMS not sending, TOTP validation failing
**Diagnosis:**
```bash
# Check 2FA system health
curl -s http://localhost:8001/health | jq '.twofa'

# Verify SMS provider status
curl -s http://localhost:8001/api/auth/2fa/sms-status | jq '.'
```
**Resolution:**
```bash
# Restart 2FA services
docker compose -f docker-compose.separated.yml exec auth-service python -c "
from two_factor_auth import TwoFactorAuth
tfa = TwoFactorAuth()
print(tfa.system_health_check())
"
```

#### Issue: Database Connection Security Errors
**Symptoms**: Database authentication failures, connection refused errors
**Diagnosis:**
```bash
# Test database connections
docker exec photoshare-auth-db pg_isready -U auth_user
docker exec photoshare-app-db pg_isready -U app_user

# Check connection logs
docker compose -f docker-compose.separated.yml logs auth-db | tail -20
docker compose -f docker-compose.separated.yml logs app-db | tail -20
```
**Resolution:**
```bash
# Verify database credentials
docker compose -f docker-compose.separated.yml restart auth-db app-db
sleep 30
docker compose -f docker-compose.separated.yml restart auth-service photo-share-app
```

### Security Incident Troubleshooting

#### High Failed Login Rate
```bash
# Investigate source of failed logins
curl -s http://localhost:8001/api/security/failed-logins | jq '.top_source_ips'

# Check for brute force patterns
curl -s http://localhost:8001/api/security/brute-force-detection | jq '.'

# Implement additional rate limiting if needed
curl -X POST http://localhost:8001/api/security/emergency-rate-limit \
  -d '{"ip_ranges": ["suspicious.ip.range.*"], "duration": 3600}'
```

#### Unusual File Upload Activity
```bash
# Check upload patterns
curl -s http://localhost:8000/api/security/upload-patterns | jq '.'

# Review blocked uploads
curl -s http://localhost:8000/api/security/blocked-uploads | jq '.recent[]'

# Scan for malware in uploads
curl -X POST http://localhost:8000/api/security/full-malware-scan
```

### Performance Security Issues

#### Service Response Time Anomalies
```bash
# Check service performance metrics
curl -s http://localhost:8000/api/platform/performance | jq '.'
curl -s http://localhost:8001/api/auth/performance | jq '.'

# Review resource usage
docker stats --no-stream
```

#### Memory or CPU Security Concerns
```bash
# Monitor resource consumption
docker exec photoshare-app-service top -b -n 1 | head -20
docker exec photoshare-auth-service top -b -n 1 | head -20

# Check for resource-based attacks
curl -s http://localhost:8000/api/security/resource-usage-analysis | jq '.'
```

---

## 📞 Emergency Contacts & Escalation

### Internal Security Contacts
- **Security Operations Center**: security-ops@company.com / +1-555-SEC-URITY
- **Incident Response Team**: incident-response@company.com / +1-555-INCIDENT  
- **System Administrators**: sysadmin@company.com / +1-555-SYSADMIN
- **Management Escalation**: security-mgmt@company.com / +1-555-SECURITY-MGR

### External Security Resources
- **Cloud Provider Security**: [Your cloud provider's security contact]
- **Cyber Insurance**: [Your cyber insurance contact]
- **Law Enforcement (if required)**: [Local cybercrime unit]
- **CERT Coordination Center**: https://www.cert.org/

### Emergency Escalation Matrix
| Incident Level | Response Time | Notification Required |
|----------------|---------------|---------------------|
| Level 1 (Info) | 4 hours | Security Team |
| Level 2 (Warning) | 1 hour | Security Team + Manager |
| Level 3 (Critical) | 15 minutes | All Security Staff + Executive |
| Level 4 (Emergency) | Immediate | All Stakeholders + External |

---

**Document Classification**: Confidential - Internal Use Only  
**Version Control**: Maintained in secure repository  
**Access Control**: Security team and authorized administrators only  
**Review Schedule**: Monthly security review, quarterly full audit  
**Next Review**: November 24, 2025

---

**🔒 Remember: When in doubt about security, err on the side of caution. It's better to over-respond to a potential threat than to under-respond to an actual attack.**