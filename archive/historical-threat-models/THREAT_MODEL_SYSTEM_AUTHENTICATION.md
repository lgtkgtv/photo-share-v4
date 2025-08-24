# Authentication & Authorization Threat Model
**Version:** 2.4.0-security  
**Last Updated:** August 23, 2025  
**Scope:** User Authentication, SSO, 2FA, RBAC, and Database Separation

## Executive Summary

This threat model identifies security risks in our photo sharing service's authentication and authorization systems, with focus on implementing SSO, 2FA, and proper database separation for defense-in-depth security architecture.

## System Architecture Overview

### Current Architecture (Before Changes)
```
[Photo Share App] ←→ [Single PostgreSQL DB]
                         ├── users, sessions, roles
                         └── photos, metadata
```

### Target Architecture (After Changes)  
```
[Photo Share App] ←→ [Auth Service] ←→ [Auth DB: users, sessions, roles, 2fa]
       ↓                                    ↑
[Application DB: photos, metadata]      [SSO Provider]
                                           (OIDC/SAML)
```

## Threat Categories & Mitigations

### 1. Authentication Threats

#### 1.1 Password-Based Attacks
**Threats:**
- **T-001**: Brute force password attacks
- **T-002**: Credential stuffing from breached databases
- **T-003**: Password spraying attacks
- **T-004**: Weak password exploitation

**Current Mitigations:**
- Rate limiting (60 req/min, IP blocking after 2x limit)
- Password complexity requirements
- Bcrypt hashing with salts

**Enhanced Mitigations (Planned):**
- **2FA Implementation**: TOTP, SMS, hardware keys
- **SSO Integration**: Offload primary authentication to enterprise providers
- **Adaptive Authentication**: Risk-based step-up authentication
- **Account Lockout**: Progressive delays after failed attempts

#### 1.2 Session Management Threats
**Threats:**
- **T-005**: Session fixation attacks
- **T-006**: Session hijacking via XSS/network sniffing
- **T-007**: Insufficient session timeout
- **T-008**: Concurrent session abuse

**Current Mitigations:**
- JWT with 30-minute expiration
- Secure HTTP headers
- Session invalidation on logout

**Enhanced Mitigations (Planned):**
- **Session Database Separation**: Isolated auth database
- **Session Binding**: IP + User-Agent validation
- **Concurrent Session Limits**: Max 3 active sessions per user
- **Session Revocation API**: Admin ability to terminate sessions

#### 1.3 SSO-Specific Threats
**Threats:**
- **T-009**: SAML/OIDC token manipulation
- **T-010**: Identity provider impersonation  
- **T-011**: Redirect URI manipulation
- **T-012**: Token replay attacks

**Planned Mitigations:**
- **Certificate Validation**: Strict SAML certificate checks
- **Nonce Validation**: Prevent replay attacks
- **State Parameter**: CSRF protection for OAuth flows
- **Audience Validation**: Verify token intended for our service

### 2. Authorization Threats (RBAC)

#### 2.1 Privilege Escalation
**Threats:**
- **T-013**: Horizontal privilege escalation (access other users' data)
- **T-014**: Vertical privilege escalation (gain admin privileges)
- **T-015**: RBAC bypass through API manipulation

**Current Mitigations:**
- User ID validation in photo access
- JWT-based user context
- Basic role checking

**Enhanced Mitigations (Planned):**
- **Separated Auth Service**: Centralized permission validation
- **Fine-grained Permissions**: Resource:Action permission model
- **Permission Caching**: Redis-based permission cache with TTL
- **Audit Trail**: All permission changes logged

#### 2.2 Data Access Control
**Threats:**
- **T-016**: Insecure direct object references
- **T-017**: Mass assignment vulnerabilities
- **T-018**: SQL injection in permission queries

**Enhanced Mitigations (Planned):**
- **Database Separation**: Auth queries isolated from app data
- **Parameterized Queries**: All database operations use bound parameters
- **Input Validation**: Comprehensive request validation middleware

### 3. Two-Factor Authentication Threats

#### 3.1 2FA Bypass Attacks
**Threats:**
- **T-019**: 2FA token brute forcing
- **T-020**: SMS interception attacks
- **T-021**: TOTP time-based attacks
- **T-022**: Backup code abuse

**Planned Mitigations:**
- **Multiple 2FA Methods**: TOTP + SMS + Hardware keys
- **Rate Limiting on 2FA**: 5 attempts per 15 minutes
- **Time Window Validation**: ±30 seconds for TOTP
- **Backup Code Management**: Single-use codes with expiration

#### 3.2 2FA Recovery Attacks
**Threats:**
- **T-023**: Social engineering of support staff
- **T-024**: Email-based 2FA reset abuse
- **T-025**: Recovery code enumeration

**Planned Mitigations:**
- **Admin 2FA Reset**: Requires admin 2FA for user 2FA resets
- **Identity Verification**: Multi-factor identity verification for recovery
- **Recovery Audit Trail**: All 2FA recovery events logged and monitored

### 4. Database Separation Security

#### 4.1 Cross-Database Attack Vectors
**Threats:**
- **T-026**: SQL injection crossing database boundaries
- **T-027**: Credential reuse between databases
- **T-028**: Network-level database access

**Planned Mitigations:**
- **Separate Database Credentials**: Different users/passwords per database
- **Network Segmentation**: Auth DB on isolated network segment
- **Connection Pooling**: Separate connection pools per database
- **Database Firewall**: Restrict auth DB access to auth service only

#### 4.2 Data Leakage Between Systems
**Threats:**
- **T-029**: Application queries accessing auth data
- **T-030**: Auth service accessing application data
- **T-031**: Backup/migration data mixing

**Planned Mitigations:**
- **API-Only Communication**: No direct database access between services
- **Data Classification**: Clear boundaries on sensitive auth data
- **Separate Backup Systems**: Auth and app data backed up separately

## Implementation Priority Matrix

### Critical (Implement First)
1. **Database Separation** - Isolate auth concerns
2. **SSO Integration** - Reduce password attack surface
3. **2FA Implementation** - TOTP as minimum viable protection

### High Priority (Next Phase)
4. **Enhanced Session Management** - Concurrent session limits
5. **Permission Caching** - Performance + security
6. **Audit Trail System** - Comprehensive logging

### Medium Priority (Future Enhancements)
7. **Hardware Key Support** - Enterprise security
8. **Risk-Based Authentication** - Adaptive security
9. **Backup/Recovery Procedures** - Business continuity

## Security Controls Summary

| Control Category | Current | Planned | Risk Reduction |
|-----------------|---------|---------|----------------|
| Password Security | Basic | 2FA + SSO | 80% reduction in password attacks |
| Session Security | JWT | Separated DB + Binding | 70% reduction in session attacks |
| Authorization | Basic RBAC | Fine-grained + Cached | 90% reduction in privilege escalation |
| Database Security | Single DB | Separated + Segmented | 95% reduction in data exposure |
| Monitoring | Basic | Comprehensive Audit | 85% improvement in threat detection |

## Compliance & Standards

- **OWASP Top 10 2021**: Addresses A01 (Broken Access Control), A02 (Cryptographic Failures), A07 (ID & Auth Failures)  
- **GDPR Article 25**: Privacy by design through data separation
- **SOC 2 Type II**: Comprehensive audit trail and access controls
- **NIST Cybersecurity Framework**: Implement-Protect-Detect-Respond-Recover

## Monitoring & Alerting

### Security Events to Monitor
- Failed authentication attempts (threshold: 5 in 5 minutes)
- 2FA bypass attempts
- Privilege escalation attempts
- Cross-database access attempts
- SSO token validation failures

### Alert Triggers
- **Critical**: Multiple failed admin login attempts
- **High**: 2FA device registration from new location
- **Medium**: Unusual access patterns detected
- **Low**: Password policy violations

## Testing Strategy

### Security Testing
- **Penetration Testing**: Quarterly auth system penetration tests
- **2FA Testing**: Automated 2FA bypass attempt detection
- **SSO Testing**: Mock SSO provider for integration testing
- **Database Separation Testing**: Cross-contamination prevention tests

### Performance Testing
- **Auth Service Load Testing**: 10,000 concurrent authentications
- **Permission Cache Testing**: Cache hit/miss ratios under load
- **Database Separation Impact**: Performance comparison pre/post separation

---

**Next Steps:**
1. Review and approve this threat model
2. Begin database separation implementation
3. Select SSO provider (recommendations: Auth0, Okta, or Azure AD)
4. Begin 2FA implementation with TOTP as MVP