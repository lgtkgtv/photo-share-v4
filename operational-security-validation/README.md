# Operational Security Validation Tools

**Purpose**: Daily security system validation tools for production operations

These tools are designed to be run regularly (daily/hourly) by operations teams to validate that all 15 security systems are functioning correctly in production. They are **not** unit tests, but operational verification tools.

## Security System Validation Tools

### Comprehensive Security Validation
- `test-security-improvements.py` - Complete validation of all 15 security systems
- `test-security-monitoring.py` - SIEM and monitoring system validation

### Individual System Validators
- `test-audit-trail.py` - Tamper-proof audit trail integrity verification
- `test-backup-encryption.sh` - Backup encryption system validation
- `test-certificate-security.py` - Certificate management and PKI validation
- `test-database-monitoring.py` - Database activity monitoring validation
- `test-exif-security.py` - EXIF data privacy protection validation
- `test-inter-service-security.py` - mTLS inter-service communication validation
- `test-jwt-security.py` - JWT secret management and rotation validation
- `test-session-security.py` - Session security and anomaly detection validation
- `test-upload-security.py` - File upload security validation
- `test-waf-protection.sh` - Web Application Firewall validation

## Usage in Production Operations

### Daily Security Validation (Run Every Morning)
```bash
# Complete security system validation
python operational-security-validation/test-security-improvements.py

# Monitoring system validation
python operational-security-validation/test-security-monitoring.py
```

### Weekly Deep Validation (Run Every Monday)
```bash
# Run all individual validators
for validator in operational-security-validation/test-*.py; do
    echo "Running $validator..."
    python "$validator"
done

for validator in operational-security-validation/test-*.sh; do
    echo "Running $validator..."
    bash "$validator"
done
```

### Integration with Web App Administrator Guide
These tools complement the monitoring procedures documented in `WEBAPP_ADMIN_SECURITY_GUIDE.md`. While the admin guide focuses on API-based monitoring, these tools provide deeper system-level validation.

## Key Differences from Development Tests

| Aspect | Development Tests (`/tests`) | Operational Validation (`/operational-security-validation`) |
|--------|------------------------------|-------------------------------------------------------------|
| Purpose | Code quality validation | Production system verification |
| When to Run | Before code commits/deploys | Daily operations monitoring |
| What they Test | Code units and integration | Live security system health |
| Audience | Developers | Operations/Security teams |
| Failure Impact | Block deployment | Alert operations team |

## Adding New Validators

When implementing new security systems, add corresponding validation tools here following the naming pattern:
- `test-{security-system-name}.py` for Python validators
- `test-{security-system-name}.sh` for shell script validators

Each validator should:
1. Test the security system's core functionality
2. Verify configuration integrity
3. Check for security policy compliance
4. Generate clear pass/fail results with detailed output
5. Include performance and health metrics