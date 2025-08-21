# Python Vulnerable Test Dataset

This test dataset contains intentionally vulnerable Python packages for demonstrating the SBOM Agent's vulnerability detection and remediation capabilities.

## ⚠️ WARNING

**DO NOT USE THESE PACKAGE VERSIONS IN PRODUCTION**

This dataset contains packages with known security vulnerabilities and is intended solely for testing and demonstration purposes.

## Test Scenarios

### Scenario 1: Initial Vulnerability Detection
```bash
# Analyze the vulnerable requirements
python tools/sbom-agent/src/cli.py analyze tools/sbom-agent/tests/test_datasets/python-vulnerable/ \
  --scan-vulnerabilities --baseline --output-dir ./security-reports/
```

Expected results:
- 10 vulnerable packages detected
- Multiple critical and high-severity vulnerabilities
- Low security score (< 30/100)

### Scenario 2: Progressive Analysis with Remediation
```bash
# Run progressive analysis workflow
python tools/sbom-agent/src/cli.py progressive-analysis tools/sbom-agent/tests/test_datasets/python-vulnerable/ \
  --auto-remediate --output-dir ./security-reports/
```

Expected results:
- Automatic remediation suggestions
- Package version updates to secure versions
- Improved security score (95+/100)
- Before/after comparison report

### Scenario 3: Manual Remediation Testing
```bash
# Copy vulnerable requirements to test remediation
cp requirements.txt requirements_test.txt

# Apply remediations
python tools/sbom-agent/src/cli.py remediate . --auto-fix --backup

# Verify improvements
python tools/sbom-agent/src/cli.py analyze . --scan-vulnerabilities --compare-with baseline
```

## Known Vulnerabilities

| Package | Vulnerable Version | CVE | Severity | Fixed Version |
|---------|-------------------|-----|----------|---------------|
| jinja2 | 2.10.1 | CVE-2019-10906 | Critical | 3.1.6 |
| pyyaml | 3.13 | CVE-2017-18342 | Critical | 6.0.1 |
| requests | 2.18.4 | CVE-2018-18074 | High | 2.31.0 |
| flask | 0.12.2 | CVE-2018-1000656 | High | 2.3.3 |
| django | 1.11.0 | CVE-2018-14574 | High | 4.2.7 |
| pillow | 5.2.0 | CVE-2019-16865 | High | 10.0.1 |
| urllib3 | 1.24.1 | CVE-2019-11324 | Medium | 2.0.7 |
| werkzeug | 0.14.1 | CVE-2019-14806 | Medium | 2.3.7 |
| cryptography | 2.1.4 | CVE-2018-10903 | Medium | 41.0.7 |
| click | 7.0 | Various | Low | 8.1.7 |

## File Structure

```
python-vulnerable/
├── README.md                 # This documentation
├── requirements.txt          # Vulnerable package versions
├── requirements_fixed.txt    # Secure package versions
└── test_app.py              # Simple Python app for testing
```

## Usage in CI/CD

This dataset can be used to test CI/CD integration:

```yaml
# GitHub Actions example
- name: Test Security Scanning
  run: |
    python tools/sbom-agent/src/cli.py quick-scan \
      tools/sbom-agent/tests/test_datasets/python-vulnerable/ \
      --threshold critical
```

## Validation

To validate the SBOM Agent is working correctly:

1. **Detection**: Should find all 10 vulnerabilities
2. **Severity**: Should correctly classify critical, high, medium, low
3. **Remediation**: Should suggest appropriate version updates
4. **Verification**: Post-remediation scan should show significant improvement

## Security Testing Best Practices

When using this dataset:

1. ✅ **Isolated Environment**: Use only in isolated test environments
2. ✅ **No Network Access**: Don't install these packages on networked systems  
3. ✅ **Version Control**: Don't commit these vulnerable versions to production repos
4. ✅ **Documentation**: Always document the testing purpose
5. ✅ **Cleanup**: Remove test installations after testing

---

*This test dataset is part of the SBOM Agent v2.1.0 enterprise security tools ecosystem.*