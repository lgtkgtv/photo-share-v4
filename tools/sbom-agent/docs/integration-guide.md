# 🔧 Integration Guide - SBOM Agent

## Quick Integration Checklist

✅ **Environment Validation**
```bash
python tools/scripts/validate-environment.py
```

✅ **Tool Installation**  
```bash
cd tools/sbom-agent && pip install -r requirements.txt
```

✅ **Basic Analysis**
```bash
python src/cli.py analyze /path/to/project
```

✅ **Vulnerability Scanning**
```bash
python src/cli.py analyze /path/to/project --scan-vulnerabilities
```

✅ **Progressive Analysis**
```bash
python src/cli.py progressive-analysis /path/to/project --auto-remediate
```

## Integration Scenarios

### 1. Development Workflow Integration

#### Pre-commit Hook Setup
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
echo "🔍 Running security pre-commit checks..."

# Quick security scan on staged files only
cd tools/sbom-agent
python src/cli.py quick-scan --staged-files --threshold medium

if [ $? -ne 0 ]; then
    echo "❌ Security issues detected in staged files."
    echo "Run 'python tools/sbom-agent/src/cli.py analyze .' for details"
    exit 1
fi

echo "✅ Pre-commit security check passed"
exit 0
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

#### IDE Integration

##### VS Code Configuration
Create `.vscode/tasks.json`:
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "SBOM Security Scan",
            "type": "shell",
            "command": "python",
            "args": [
                "tools/sbom-agent/src/cli.py",
                "analyze",
                "${workspaceFolder}",
                "--format",
                "vscode"
            ],
            "group": {
                "kind": "build",
                "isDefault": false
            },
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared",
                "showReuseMessage": true,
                "clear": false
            },
            "options": {
                "cwd": "${workspaceFolder}"
            },
            "problemMatcher": {
                "pattern": {
                    "regexp": "^(ERROR|WARNING)\\s+(.*):(\\d+):(\\d+)\\s+(.*)$",
                    "file": 2,
                    "line": 3,
                    "column": 4,
                    "severity": 1,
                    "message": 5
                }
            }
        },
        {
            "label": "SBOM Progressive Analysis",
            "type": "shell",
            "command": "python",
            "args": [
                "tools/sbom-agent/src/cli.py",
                "progressive-analysis",
                "${workspaceFolder}",
                "--interactive"
            ],
            "group": "build"
        }
    ]
}
```

Create `.vscode/launch.json` for debugging:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug SBOM Analysis",
            "type": "python",
            "request": "launch",
            "program": "tools/sbom-agent/src/cli.py",
            "args": ["analyze", ".", "--debug"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/tools"
            }
        }
    ]
}
```

##### IntelliJ/PyCharm Configuration
1. Go to **File → Settings → Tools → External Tools**
2. Click **+** to add new tool:
   - **Name**: SBOM Security Scan
   - **Program**: `python`
   - **Arguments**: `tools/sbom-agent/src/cli.py analyze $ProjectFileDir$`
   - **Working directory**: `$ProjectFileDir$`

### 2. CI/CD Pipeline Integration

#### GitHub Actions
Create `.github/workflows/security-analysis.yml`:
```yaml
name: Security Analysis with SBOM Agent
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    # Run weekly security scan
    - cron: '0 2 * * 1'

jobs:
  security-analysis:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
      
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Cache SBOM tools
        uses: actions/cache@v3
        with:
          path: |
            tools/sbom-agent/.cache
            ~/.cache/pip
          key: sbom-tools-${{ hashFiles('tools/sbom-agent/requirements.txt') }}
          
      - name: Install SBOM Agent
        run: |
          cd tools/sbom-agent
          pip install -r requirements.txt
          
      - name: Validate Environment
        run: python tools/scripts/validate-environment.py --quiet
        
      - name: Run Security Analysis
        run: |
          python tools/sbom-agent/src/cli.py progressive-analysis . \
            --output-dir ./security-reports \
            --format github-actions \
            --fail-on-high
            
      - name: Upload SBOM Artifacts
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-reports
          path: security-reports/
          retention-days: 30
          
      - name: Upload SARIF Results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: security-reports/sarif-results.json
          
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('security-reports/pr-comment.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```

#### GitLab CI/CD
Create `.gitlab-ci.yml`:
```yaml
stages:
  - security
  - report

variables:
  SBOM_CACHE_DIR: ".cache/sbom-agent"

security_analysis:
  stage: security
  image: python:3.11-slim
  cache:
    key: sbom-tools-$CI_COMMIT_REF_SLUG
    paths:
      - .cache/
      - .pip-cache/
  before_script:
    - apt-get update && apt-get install -y git
    - pip install --cache-dir .pip-cache -r tools/sbom-agent/requirements.txt
  script:
    - python tools/scripts/validate-environment.py --quiet
    - python tools/sbom-agent/src/cli.py progressive-analysis . 
        --output-dir security-reports 
        --format gitlab-ci
        --cache-dir $SBOM_CACHE_DIR
  artifacts:
    reports:
      sast: security-reports/sast-report.json
      cyclonedx: security-reports/cyclonedx_sbom.json
      dependency_scanning: security-reports/dependency-scan.json
    paths:
      - security-reports/
    expire_in: 30 days
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_PIPELINE_SOURCE == "schedule"

security_report:
  stage: report  
  image: alpine:latest
  dependencies:
    - security_analysis
  script:
    - echo "Security analysis completed"
    - cat security-reports/summary.txt
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
      when: always
```

#### Jenkins Pipeline
Create `Jenkinsfile`:
```groovy
pipeline {
    agent any
    
    environment {
        SBOM_CACHE = "${WORKSPACE}/.cache/sbom-agent"
        PYTHON_ENV = "${WORKSPACE}/.venv"
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv ${PYTHON_ENV}
                    . ${PYTHON_ENV}/bin/activate
                    pip install -r tools/sbom-agent/requirements.txt
                '''
            }
        }
        
        stage('Environment Validation') {
            steps {
                sh '''
                    . ${PYTHON_ENV}/bin/activate
                    python tools/scripts/validate-environment.py --json --output env-check.json
                '''
                archiveArtifacts artifacts: 'env-check.json'
            }
        }
        
        stage('Security Analysis') {
            steps {
                sh '''
                    . ${PYTHON_ENV}/bin/activate
                    python tools/sbom-agent/src/cli.py progressive-analysis . \
                        --output-dir security-reports \
                        --format jenkins \
                        --cache-dir ${SBOM_CACHE}
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'security-reports/**/*'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'security-reports',
                        reportFiles: 'security-report.html',
                        reportName: 'Security Report'
                    ])
                }
                failure {
                    emailext (
                        subject: "Security Analysis Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                        body: "Security analysis failed. Check console output at ${env.BUILD_URL}",
                        to: "${env.CHANGE_AUTHOR_EMAIL}"
                    )
                }
            }
        }
        
        stage('Security Gate') {
            when {
                anyOf {
                    branch 'main'
                    branch 'release/*'
                }
            }
            steps {
                script {
                    def securityReport = readJSON file: 'security-reports/summary.json'
                    if (securityReport.vulnerabilities.critical > 0) {
                        error("Critical vulnerabilities detected. Deployment blocked.")
                    }
                    if (securityReport.vulnerabilities.high > 5) {
                        error("Too many high-severity vulnerabilities. Deployment blocked.")
                    }
                }
            }
        }
    }
    
    post {
        cleanup {
            deleteDir()
        }
    }
}
```

#### Azure DevOps
Create `azure-pipelines.yml`:
```yaml
trigger:
  branches:
    include:
      - main
      - develop
  paths:
    exclude:
      - docs/*
      - README.md

schedules:
  - cron: "0 2 * * 1"
    displayName: Weekly security scan
    branches:
      include:
        - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  python.version: '3.11'
  sbom.cacheDir: '$(Pipeline.Workspace)/.cache/sbom-agent'

stages:
  - stage: SecurityAnalysis
    displayName: 'Security Analysis'
    jobs:
      - job: SBOMAnalysis
        displayName: 'SBOM Generation and Vulnerability Scanning'
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '$(python.version)'
            displayName: 'Use Python $(python.version)'
            
          - task: Cache@2
            inputs:
              key: 'sbom-tools | "$(Agent.OS)" | tools/sbom-agent/requirements.txt'
              restoreKeys: |
                sbom-tools | "$(Agent.OS)"
                sbom-tools
              path: $(sbom.cacheDir)
            displayName: 'Cache SBOM tools'
            
          - script: |
              python -m pip install --upgrade pip
              pip install -r tools/sbom-agent/requirements.txt
            displayName: 'Install SBOM Agent'
            
          - script: |
              python tools/scripts/validate-environment.py --quiet
            displayName: 'Validate Environment'
            
          - script: |
              python tools/sbom-agent/src/cli.py progressive-analysis . \
                --output-dir $(Agent.TempDirectory)/security-reports \
                --format azure-devops \
                --cache-dir $(sbom.cacheDir)
            displayName: 'Run Security Analysis'
            
          - task: PublishTestResults@2
            condition: succeededOrFailed()
            inputs:
              testResultsFiles: '$(Agent.TempDirectory)/security-reports/test-results.xml'
              testRunTitle: 'Security Test Results'
              
          - task: PublishBuildArtifacts@1
            condition: always()
            inputs:
              pathToPublish: '$(Agent.TempDirectory)/security-reports'
              artifactName: 'SecurityReports'
              
          - task: PublishSecurityAnalysisLogs@3
            condition: always()
            inputs:
              artifactName: 'CodeAnalysisLogs'
              allTools: false
              toolLogsNotFoundAction: 'Standard'
```

### 3. Container Integration

#### Docker Development Environment
Create `docker-compose.override.yml` for development:
```yaml
version: '3.8'
services:
  security-scanner:
    build:
      context: tools/
      dockerfile: Dockerfile.tools
    volumes:
      - .:/workspace:ro
      - ./security-reports:/reports:rw
      - sbom-cache:/cache
    environment:
      - WORKSPACE_DIR=/workspace
      - REPORTS_DIR=/reports
      - CACHE_DIR=/cache
    command: ["python", "sbom-agent/src/cli.py", "monitor", "/workspace", "--continuous"]

volumes:
  sbom-cache:
```

#### Production Scanning Service
Create `security-scanner.dockerfile`:
```dockerfile
FROM python:3.11-slim as security-scanner

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install tools
WORKDIR /opt/security-tools
COPY tools/requirements.txt .
COPY tools/sbom-agent/requirements.txt ./sbom-agent/
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r sbom-agent/requirements.txt

# Copy source code
COPY tools/ ./

# Create non-root user
RUN useradd -m -u 1000 scanner && \
    chown -R scanner:scanner /opt/security-tools
USER scanner

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python scripts/validate-environment.py --quiet || exit 1

ENTRYPOINT ["python", "sbom-agent/src/cli.py"]
CMD ["--help"]
```

#### Kubernetes Deployment
Create `k8s/security-scanner.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: security-scanner
  labels:
    app: security-scanner
spec:
  replicas: 1
  selector:
    matchLabels:
      app: security-scanner
  template:
    metadata:
      labels:
        app: security-scanner
    spec:
      containers:
      - name: scanner
        image: security-scanner:latest
        command: ["python", "sbom-agent/src/cli.py", "server", "--host", "0.0.0.0"]
        ports:
        - containerPort: 8080
        env:
        - name: CACHE_DIR
          value: "/cache"
        - name: WORKSPACE_DIR
          value: "/workspace"
        volumeMounts:
        - name: cache-volume
          mountPath: /cache
        - name: workspace-volume
          mountPath: /workspace
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: cache-volume
        persistentVolumeClaim:
          claimName: scanner-cache-pvc
      - name: workspace-volume
        persistentVolumeClaim:
          claimName: workspace-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: security-scanner-service
spec:
  selector:
    app: security-scanner
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: ClusterIP
```

### 4. API Integration

#### REST API Client Example
```python
import requests
import json

class SBOMAgentClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        
    def analyze_project(self, project_path, scan_vulnerabilities=True):
        """Submit project for analysis"""
        data = {
            "project_path": project_path,
            "scan_vulnerabilities": scan_vulnerabilities,
            "output_formats": ["spdx", "cyclonedx", "json"]
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/analyze",
            json=data
        )
        return response.json()
    
    def get_analysis_status(self, analysis_id):
        """Check analysis status"""
        response = requests.get(
            f"{self.base_url}/api/v1/analysis/{analysis_id}/status"
        )
        return response.json()
    
    def get_analysis_results(self, analysis_id):
        """Get analysis results"""
        response = requests.get(
            f"{self.base_url}/api/v1/analysis/{analysis_id}/results"
        )
        return response.json()
    
    def progressive_analysis(self, project_path, auto_remediate=False):
        """Run progressive analysis workflow"""
        data = {
            "project_path": project_path,
            "auto_remediate": auto_remediate,
            "compare_with_history": True
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/progressive-analysis",
            json=data
        )
        return response.json()

# Usage example
client = SBOMAgentClient()
result = client.analyze_project("/path/to/project")
print(f"Analysis ID: {result['analysis_id']}")
```

### 5. Configuration Management

#### Environment Configuration
Create `.env.security-tools`:
```bash
# SBOM Agent Configuration
SBOM_AGENT_VERSION=2.1.0
SBOM_CACHE_DIR=/tmp/sbom-cache
SBOM_REPORTS_DIR=./security-reports

# Vulnerability Scanning
OSV_API_ENDPOINT=https://api.osv.dev/v1
VULNERABILITY_CACHE_TTL=3600
SCAN_TIMEOUT=300

# Analysis Settings
DEFAULT_OUTPUT_FORMATS=spdx,cyclonedx,json
FAIL_ON_CRITICAL=true
FAIL_ON_HIGH_COUNT=5

# Integration Settings
GITHUB_TOKEN=${GITHUB_TOKEN}
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
EMAIL_NOTIFICATIONS=true
```

#### Tool Configuration File
Create `tools/sbom-agent/config.yml`:
```yaml
# SBOM Agent Configuration
agent:
  version: "2.1.0"
  cache_dir: "${SBOM_CACHE_DIR:-.cache}"
  reports_dir: "${SBOM_REPORTS_DIR:-./reports}"
  log_level: "INFO"

# Vulnerability Scanning
vulnerability_scanning:
  enabled: true
  osv_api:
    endpoint: "https://api.osv.dev/v1"
    timeout: 30
    cache_ttl: 3600
  severity_threshold: "medium"
  
# Output Configuration  
output:
  formats: ["spdx", "cyclonedx", "json", "html"]
  spdx:
    version: "2.3"
    include_files: true
  cyclonedx:
    version: "1.5"
    include_licenses: true
    
# Ecosystem Configuration
ecosystems:
  python:
    enabled: true
    package_managers: ["pip", "poetry", "conda"]
    requirements_files: ["requirements*.txt", "pyproject.toml"]
  javascript:
    enabled: true
    package_managers: ["npm", "yarn", "pnpm"]
    manifests: ["package.json"]
  java:
    enabled: true
    build_tools: ["maven", "gradle"]
    manifests: ["pom.xml", "build.gradle"]

# Remediation Settings
remediation:
  auto_fix: false
  backup_before_changes: true
  test_after_changes: true
  conflict_resolution: "conservative"
  
# Integration Settings
integrations:
  github:
    enabled: "${GITHUB_TOKEN:+true}"
    create_issues: false
  slack:
    enabled: "${SLACK_WEBHOOK_URL:+true}"
    channel: "#security"
  email:
    enabled: false
```

## Troubleshooting Common Issues

### Environment Issues
```bash
# Check Python environment
python tools/scripts/validate-environment.py --verbose

# Fix virtual environment issues
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install in clean environment
pip install -r tools/sbom-agent/requirements.txt
```

### Permission Issues
```bash
# Fix file permissions
chmod +x tools/scripts/*.sh
chmod +x .git/hooks/pre-commit

# Docker permission issues
sudo usermod -aG docker $USER
newgrp docker
```

### Network Issues
```bash
# Test OSV API connectivity
curl -X POST https://api.osv.dev/v1/query \
  -H "Content-Type: application/json" \
  -d '{"package":{"name":"requests","ecosystem":"PyPI"},"version":"2.18.4"}'

# Configure proxy if needed
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
```

### Performance Issues
```bash
# Enable caching
export SBOM_CACHE_DIR=~/.cache/sbom-agent

# Increase timeouts for large projects
export SCAN_TIMEOUT=600

# Use parallel scanning
python tools/sbom-agent/src/cli.py analyze . --parallel-workers 4
```

This integration guide provides comprehensive setup instructions for various environments and use cases, ensuring the SBOM Agent can be effectively deployed in any development workflow.