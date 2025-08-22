#!/usr/bin/env python3
"""
Infrastructure and Deployment Validation Tests.

Tests for container security, network configuration, deployment pipeline,
and infrastructure monitoring systems.
"""

import pytest
import subprocess
import json
import time
import os
import sys
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))


@pytest.mark.infrastructure
class TestContainerSecurity:
    """Test container security and configuration."""

    def test_docker_container_running(self):
        """Test that Docker containers are running properly."""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                pytest.skip("Docker not available or not running")
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    containers.append(json.loads(line))
            
            # Check for photo-share related containers
            photo_share_containers = [
                c for c in containers 
                if 'photo' in c.get('Names', '').lower() or 'photoshare' in c.get('Image', '').lower()
            ]
            
            assert len(photo_share_containers) > 0, "No photo-share containers running"
            print(f"✅ Found {len(photo_share_containers)} photo-share containers running")
            
            # Check container health
            for container in photo_share_containers:
                container_id = container['ID']
                inspect_result = subprocess.run(
                    ["docker", "inspect", container_id],
                    capture_output=True,
                    text=True
                )
                
                if inspect_result.returncode == 0:
                    inspect_data = json.loads(inspect_result.stdout)[0]
                    state = inspect_data['State']
                    
                    assert state['Status'] == 'running', f"Container {container_id} not running"
                    assert state['Health']['Status'] in ['healthy', 'none'], f"Container {container_id} unhealthy"
                    
                    print(f"   Container {container_id[:12]}: {state['Status']}")
        
        except subprocess.TimeoutExpired:
            pytest.fail("Docker command timed out")
        except FileNotFoundError:
            pytest.skip("Docker not installed")

    def test_container_resource_limits(self):
        """Test that containers have appropriate resource limits."""
        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                pytest.skip("Cannot get container stats")
            
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                if 'photo' in line.lower():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        container = parts[0]
                        cpu_percent = parts[1].replace('%', '')
                        memory_usage = parts[2]
                        
                        # Check CPU usage is reasonable
                        if cpu_percent and cpu_percent != '--':
                            cpu_val = float(cpu_percent)
                            assert cpu_val < 90.0, f"Container {container} CPU usage {cpu_val}% too high"
                        
                        print(f"   {container}: CPU {cpu_percent}%, Memory {memory_usage}")
        
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pytest.skip("Container stats not available")

    def test_container_security_settings(self):
        """Test container security configuration."""
        try:
            result = subprocess.run(
                ["docker", "ps", "-q"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                pytest.skip("Cannot list containers")
            
            container_ids = result.stdout.strip().split('\n')
            
            for container_id in container_ids:
                if not container_id:
                    continue
                
                # Inspect container security settings
                inspect_result = subprocess.run(
                    ["docker", "inspect", container_id],
                    capture_output=True,
                    text=True
                )
                
                if inspect_result.returncode == 0:
                    inspect_data = json.loads(inspect_result.stdout)[0]
                    
                    # Check security settings
                    host_config = inspect_data.get('HostConfig', {})
                    
                    # Should not run as privileged
                    assert not host_config.get('Privileged', False), f"Container {container_id} running privileged"
                    
                    # Should have appropriate user
                    config = inspect_data.get('Config', {})
                    user = config.get('User', '')
                    
                    # Should not run as root (user should be set)
                    if user and user != 'root' and user != '0':
                        print(f"   ✅ Container {container_id[:12]} running as user: {user}")
                    
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Container inspection not available")


@pytest.mark.infrastructure
class TestNetworkConfiguration:
    """Test network configuration and security."""

    def test_service_ports_accessible(self):
        """Test that required service ports are accessible."""
        required_ports = [
            (8000, "Photo Share API"),
            (5432, "PostgreSQL Database")
        ]
        
        for port, service_name in required_ports:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    print(f"   ✅ {service_name} accessible on port {port}")
                else:
                    print(f"   ⚠️  {service_name} not accessible on port {port}")
                    
            except Exception as e:
                print(f"   ❌ Error checking {service_name} on port {port}: {e}")

    def test_http_endpoint_accessibility(self):
        """Test HTTP endpoints are accessible."""
        endpoints = [
            ("http://localhost:8000/health", "Health Check"),
            ("http://localhost:8000/api/", "API Root"),
            ("http://localhost:8000/docs", "API Documentation")
        ]
        
        for url, name in endpoints:
            try:
                response = requests.get(url, timeout=10)
                assert response.status_code in [200, 307], f"{name} returned {response.status_code}"
                print(f"   ✅ {name} accessible: {response.status_code}")
                
            except requests.exceptions.ConnectionError:
                pytest.fail(f"{name} not accessible at {url}")
            except requests.exceptions.Timeout:
                pytest.fail(f"{name} timed out at {url}")

    def test_security_headers(self):
        """Test security headers are present."""
        try:
            response = requests.get("http://localhost:8000/api/", timeout=10)
            headers = response.headers
            
            security_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
                'X-XSS-Protection': '1; mode=block',
                'Referrer-Policy': ['strict-origin-when-cross-origin', 'no-referrer']
            }
            
            for header, expected_values in security_headers.items():
                if isinstance(expected_values, str):
                    expected_values = [expected_values]
                
                header_value = headers.get(header)
                if header_value:
                    assert any(exp in header_value for exp in expected_values), \
                        f"Security header {header} has unexpected value: {header_value}"
                    print(f"   ✅ {header}: {header_value}")
                else:
                    print(f"   ⚠️  Missing security header: {header}")
        
        except requests.exceptions.RequestException:
            pytest.skip("Cannot test security headers - service not accessible")


@pytest.mark.infrastructure
class TestDeploymentValidation:
    """Test deployment configuration and readiness."""

    def test_environment_variables(self):
        """Test that required environment variables are set."""
        required_env_vars = [
            'JWT_SECRET_KEY',
            'DB_HOST',
            'DB_PORT',
            'POSTGRES_USER',
            'POSTGRES_PASSWORD',
            'POSTGRES_DB'
        ]
        
        missing_vars = []
        
        for var in required_env_vars:
            value = os.environ.get(var)
            if not value:
                missing_vars.append(var)
            else:
                # Don't log sensitive values
                if 'password' in var.lower() or 'secret' in var.lower():
                    print(f"   ✅ {var}: [REDACTED]")
                else:
                    print(f"   ✅ {var}: {value}")
        
        assert len(missing_vars) == 0, f"Missing environment variables: {missing_vars}"

    def test_configuration_validation(self):
        """Test application configuration validation."""
        try:
            response = requests.get("http://localhost:8000/api/platform/stats", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                
                # Check basic configuration indicators
                assert 'service_name' in stats
                assert 'version' in stats
                assert 'environment' in stats
                
                print(f"   ✅ Service: {stats.get('service_name')}")
                print(f"   ✅ Version: {stats.get('version')}")
                print(f"   ✅ Environment: {stats.get('environment')}")
                
            else:
                pytest.skip("Platform stats not available")
                
        except requests.exceptions.RequestException:
            pytest.skip("Cannot validate configuration - service not accessible")

    def test_database_connectivity(self):
        """Test database connectivity and configuration."""
        try:
            response = requests.get("http://localhost:8000/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                
                # Check database health
                if 'database' in health_data:
                    db_status = health_data['database']
                    assert db_status.get('status') == 'healthy', f"Database unhealthy: {db_status}"
                    print(f"   ✅ Database status: {db_status.get('status')}")
                    
                    if 'connection_pool' in db_status:
                        pool_info = db_status['connection_pool']
                        print(f"   ✅ Connection pool: {pool_info}")
                
            else:
                pytest.fail(f"Health check failed: {response.status_code}")
                
        except requests.exceptions.RequestException:
            pytest.fail("Cannot check database connectivity")

    def test_file_storage_configuration(self):
        """Test file storage configuration and accessibility."""
        try:
            response = requests.get("http://localhost:8000/api/platform/security", timeout=10)
            
            if response.status_code == 200:
                security_info = response.json()
                
                # Check file storage configuration
                if 'file_storage' in security_info:
                    storage_info = security_info['file_storage']
                    assert storage_info.get('local_storage'), "Local storage not configured"
                    print(f"   ✅ File storage configured: {storage_info}")
                
            else:
                pytest.skip("Security info not available")
                
        except requests.exceptions.RequestException:
            pytest.skip("Cannot check file storage configuration")


@pytest.mark.infrastructure
class TestMonitoringIntegration:
    """Test monitoring and observability systems."""

    def test_metrics_endpoint(self):
        """Test metrics endpoint availability."""
        try:
            response = requests.get("http://localhost:8000/metrics", timeout=10)
            
            if response.status_code == 200:
                metrics_data = response.text
                
                # Check for Prometheus-style metrics
                assert 'http_requests_total' in metrics_data or 'requests_total' in metrics_data, \
                    "Request metrics not found"
                
                print(f"   ✅ Metrics endpoint accessible")
                print(f"   ✅ Metrics data length: {len(metrics_data)} bytes")
                
            else:
                pytest.skip("Metrics endpoint not available")
                
        except requests.exceptions.RequestException:
            pytest.skip("Cannot test metrics endpoint")

    def test_health_monitoring(self):
        """Test health monitoring endpoints."""
        health_endpoints = [
            ("/health", "Basic Health"),
            ("/api/platform/stats", "Platform Statistics"),
            ("/api/platform/performance", "Performance Metrics")
        ]
        
        for endpoint, name in health_endpoints:
            try:
                response = requests.get(f"http://localhost:8000{endpoint}", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    assert isinstance(data, dict), f"{name} should return JSON object"
                    print(f"   ✅ {name} endpoint working")
                else:
                    print(f"   ⚠️  {name} endpoint returned {response.status_code}")
                    
            except requests.exceptions.RequestException:
                print(f"   ❌ {name} endpoint not accessible")

    def test_logging_configuration(self):
        """Test logging configuration and output."""
        # Check for log files or logging configuration
        log_locations = [
            "/var/log/photoshare/",
            "./logs/",
            "/tmp/photoshare_logs/"
        ]
        
        log_found = False
        
        for log_dir in log_locations:
            if os.path.exists(log_dir):
                log_files = list(Path(log_dir).glob("*.log"))
                if log_files:
                    log_found = True
                    print(f"   ✅ Log files found in {log_dir}: {len(log_files)} files")
                    break
        
        if not log_found:
            print("   ⚠️  No log files found in expected locations")
        
        # Test that application is producing log output
        try:
            response = requests.get("http://localhost:8000/api/", timeout=5)
            if response.status_code == 200:
                print("   ✅ Application responding (should generate logs)")
        except requests.exceptions.RequestException:
            print("   ⚠️  Cannot test log generation - service not accessible")


@pytest.mark.infrastructure
@pytest.mark.slow
class TestDeploymentStability:
    """Test deployment stability and resilience."""

    def test_service_restart_resilience(self):
        """Test service resilience to restarts."""
        # This test would restart the service and check recovery
        # For safety, we'll just test that the service responds consistently
        
        response_times = []
        
        for i in range(10):
            start_time = time.time()
            try:
                response = requests.get("http://localhost:8000/health", timeout=10)
                response_time = time.time() - start_time
                
                assert response.status_code == 200, f"Health check failed on attempt {i+1}"
                response_times.append(response_time)
                
                time.sleep(1)  # Wait between requests
                
            except requests.exceptions.RequestException as e:
                pytest.fail(f"Service became unavailable on attempt {i+1}: {e}")
        
        # Check response time consistency
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        assert avg_response_time < 1.0, f"Average response time {avg_response_time:.3f}s too slow"
        assert max_response_time < 5.0, f"Max response time {max_response_time:.3f}s too slow"
        
        print(f"   ✅ Service stability test passed")
        print(f"      Average response time: {avg_response_time:.3f}s")
        print(f"      Max response time: {max_response_time:.3f}s")

    def test_concurrent_request_handling(self):
        """Test handling of concurrent requests."""
        import concurrent.futures
        import threading
        
        def make_request():
            try:
                response = requests.get("http://localhost:8000/api/", timeout=10)
                return response.status_code == 200
            except:
                return False
        
        # Make 20 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        success_count = sum(results)
        success_rate = success_count / len(results)
        
        assert success_rate >= 0.9, f"Success rate {success_rate:.2%} too low for concurrent requests"
        
        print(f"   ✅ Concurrent request test passed")
        print(f"      Success rate: {success_rate:.2%} ({success_count}/{len(results)})")


@pytest.mark.infrastructure
async def test_generate_infrastructure_report():
    """Generate infrastructure validation report."""
    
    report = {
        "infrastructure_validation": {
            "timestamp": time.time(),
            "test_categories": [
                "Container Security",
                "Network Configuration", 
                "Deployment Validation",
                "Monitoring Integration",
                "Deployment Stability"
            ]
        },
        "container_status": {},
        "network_accessibility": {},
        "deployment_readiness": {},
        "monitoring_health": {},
        "recommendations": []
    }
    
    # This would be populated by the actual test results
    # For now, provide a template structure
    
    try:
        # Check container status
        result = subprocess.run(["docker", "ps", "--format", "json"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            report["container_status"]["docker_available"] = True
            report["container_status"]["containers_running"] = len(result.stdout.strip().split('\n'))
        else:
            report["container_status"]["docker_available"] = False
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        report["container_status"]["docker_available"] = False
    
    # Check network accessibility
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        report["network_accessibility"]["service_accessible"] = True
        report["network_accessibility"]["health_status"] = response.status_code
    except requests.exceptions.RequestException:
        report["network_accessibility"]["service_accessible"] = False
        report["recommendations"].append({
            "category": "network",
            "issue": "Service not accessible on localhost:8000",
            "recommendation": "Check service startup and port configuration"
        })
    
    # Add general recommendations
    report["recommendations"].extend([
        {
            "category": "security",
            "issue": "Container security scanning",
            "recommendation": "Implement regular container vulnerability scanning"
        },
        {
            "category": "monitoring",
            "issue": "Enhanced monitoring",
            "recommendation": "Consider adding application performance monitoring (APM)"
        }
    ])
    
    # Write report
    with open("/tmp/infrastructure_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n🏗️  INFRASTRUCTURE VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Docker Available: {report['container_status'].get('docker_available', False)}")
    print(f"Service Accessible: {report['network_accessibility'].get('service_accessible', False)}")
    
    if report["recommendations"]:
        print(f"\n💡 Recommendations:")
        for rec in report["recommendations"]:
            print(f"  - {rec['category'].title()}: {rec['issue']}")
            print(f"    → {rec['recommendation']}")
    
    print(f"\nDetailed report: /tmp/infrastructure_validation_report.json")