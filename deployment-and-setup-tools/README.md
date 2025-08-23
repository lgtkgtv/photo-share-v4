# Deployment and Setup Tools

**Purpose**: Production deployment, environment setup, and maintenance automation

These tools handle the setup, configuration, deployment, and ongoing maintenance of the PhotoShare application infrastructure.

## Setup and Configuration Tools

### Environment Setup
- `setup-environment.py` - Complete environment initialization
  - Database setup and migration
  - Security system initialization
  - Configuration validation

- `generate-jwt-secrets.py` - JWT secret generation and rotation
  - Generate cryptographically secure JWT signing keys
  - Set up key rotation schedules
  - Update environment configuration

- `validate-config.py` - Configuration validation
  - Verify all required environment variables
  - Check configuration consistency
  - Validate security settings

### Deployment Tools
- `deploy-production.sh` - Production deployment automation
  - Build and deploy services
  - Run database migrations
  - Perform health checks
  - Zero-downtime deployment

### Maintenance and Operations
- `backup-databases.py` - Database backup automation
  - Encrypted database backups
  - Backup integrity verification
  - Automated backup scheduling

- `security-scan-containers.py` - Container security scanning
  - Vulnerability assessment
  - Security compliance checking
  - Generate security reports

- `run-automated-tests.sh` - Automated test execution
  - Run complete test suites
  - Generate test reports
  - Integration with CI/CD

## Usage Scenarios

### Initial Setup (New Installation)
```bash
# 1. Environment setup
python deployment-and-setup-tools/setup-environment.py

# 2. Generate secrets
python deployment-and-setup-tools/generate-jwt-secrets.py --update-env .env

# 3. Validate configuration
python deployment-and-setup-tools/validate-config.py --env .env

# 4. Deploy application
bash deployment-and-setup-tools/deploy-production.sh
```

### Regular Maintenance
```bash
# Daily: Database backup
python deployment-and-setup-tools/backup-databases.py

# Weekly: Security scan
python deployment-and-setup-tools/security-scan-containers.py

# Monthly: Full automated test suite
bash deployment-and-setup-tools/run-automated-tests.sh
```

### Production Updates
```bash
# 1. Validate configuration
python deployment-and-setup-tools/validate-config.py

# 2. Run pre-deployment tests
bash deployment-and-setup-tools/run-automated-tests.sh

# 3. Deploy with zero downtime
bash deployment-and-setup-tools/deploy-production.sh

# 4. Post-deployment validation
python deployment-and-setup-tools/security-scan-containers.py
```

## Tool Categories

### 🔧 Setup Tools
Tools for initial system setup and configuration:
- Environment initialization
- Secret generation
- Configuration validation

### 🚀 Deployment Tools  
Tools for application deployment:
- Production deployment automation
- Zero-downtime updates
- Health check validation

### 🛡️ Security Tools
Tools for security maintenance:
- Container vulnerability scanning
- Security compliance checking
- Backup encryption validation

### 📊 Maintenance Tools
Tools for ongoing operations:
- Database backups
- Automated testing
- System health monitoring

## Integration with Operations

These tools integrate with:
- **CI/CD Pipelines**: Automated deployment and testing
- **Monitoring Systems**: Health checks and alerting
- **Backup Systems**: Automated backup and recovery
- **Security Operations**: Vulnerability management

## Key Differences from Other Tool Types

| Tool Type | Purpose | Usage Frequency | User |
|-----------|---------|-----------------|------|
| Deployment Tools (this directory) | Setup/Deploy/Maintain | During setup/updates | DevOps/Platform teams |
| API Integration Tests | End-to-end validation | After deployments | QA/Development teams |
| Operational Security Validation | Security monitoring | Daily operations | Security/Operations teams |
| Development Tests (`/tests`) | Code quality | During development | Developers |

## Adding New Tools

When adding new deployment or setup tools:

1. Follow the naming convention: `{action}-{component}.{ext}`
2. Include comprehensive error handling
3. Provide detailed logging and progress feedback
4. Support both interactive and automated execution
5. Include rollback capabilities where applicable

### Tool Script Template
```python
#!/usr/bin/env python3
# new-tool.py

import sys
import logging
import argparse

def main():
    parser = argparse.ArgumentParser(description="New deployment tool")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without executing")
    args = parser.parse_args()
    
    try:
        # Tool logic here
        print("🎉 Tool completed successfully")
        return 0
    except Exception as e:
        logging.error(f"Tool failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```