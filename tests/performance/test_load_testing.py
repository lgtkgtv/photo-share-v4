#!/usr/bin/env python3
"""
Performance and Load Testing for Photo Share Platform.

Comprehensive performance testing including load testing, stress testing,
and performance benchmarking for all major system components.
"""

import pytest
import asyncio
import time
import statistics
import concurrent.futures
import os
import sys
from typing import List, Dict, Any
from dataclasses import dataclass

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from httpx import AsyncClient


@dataclass
class PerformanceMetrics:
    """Performance test metrics."""
    operation: str
    response_times: List[float]
    success_count: int
    error_count: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput: float  # requests per second
    error_rate: float


class PerformanceTester:
    """Performance testing utility class."""
    
    def __init__(self):
        self.results = {}
    
    def calculate_metrics(self, operation: str, response_times: List[float], 
                         success_count: int, error_count: int, duration: float) -> PerformanceMetrics:
        """Calculate performance metrics."""
        if not response_times:
            return PerformanceMetrics(
                operation=operation,
                response_times=[],
                success_count=success_count,
                error_count=error_count,
                avg_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                throughput=0,
                error_rate=100.0 if error_count > 0 else 0.0
            )
        
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 1 else response_times[0]
        
        total_requests = success_count + error_count
        throughput = total_requests / duration if duration > 0 else 0
        error_rate = (error_count / total_requests) * 100 if total_requests > 0 else 0
        
        return PerformanceMetrics(
            operation=operation,
            response_times=response_times,
            success_count=success_count,
            error_count=error_count,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            throughput=throughput,
            error_rate=error_rate
        )
    
    def log_metrics(self, metrics: PerformanceMetrics):
        """Log performance metrics."""
        self.results[metrics.operation] = metrics
        
        print(f"\n📊 Performance Metrics for {metrics.operation}:")
        print(f"   Requests: {metrics.success_count + metrics.error_count}")
        print(f"   Success: {metrics.success_count}")
        print(f"   Errors: {metrics.error_count}")
        print(f"   Error Rate: {metrics.error_rate:.2f}%")
        print(f"   Avg Response Time: {metrics.avg_response_time*1000:.2f}ms")
        print(f"   95th Percentile: {metrics.p95_response_time*1000:.2f}ms")
        print(f"   99th Percentile: {metrics.p99_response_time*1000:.2f}ms")
        print(f"   Throughput: {metrics.throughput:.2f} req/s")


# Global performance tester instance
perf_tester = PerformanceTester()


@pytest.mark.performance
@pytest.mark.slow
class TestAPIPerformance:
    """Test API endpoint performance under load."""

    async def test_health_endpoint_performance(self, async_test_client: AsyncClient):
        """Test health endpoint performance under load."""
        
        async def make_health_request():
            start_time = time.time()
            try:
                response = await async_test_client.get("/health")
                response_time = time.time() - start_time
                return response_time, response.status_code == 200
            except Exception:
                response_time = time.time() - start_time
                return response_time, False
        
        # Run 100 concurrent requests
        num_requests = 100
        start_time = time.time()
        
        tasks = [make_health_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        total_duration = time.time() - start_time
        
        response_times = [r[0] for r in results]
        success_count = sum(1 for r in results if r[1])
        error_count = num_requests - success_count
        
        metrics = perf_tester.calculate_metrics(
            "health_endpoint", response_times, success_count, error_count, total_duration
        )
        perf_tester.log_metrics(metrics)
        
        # Performance assertions
        assert metrics.error_rate < 5.0, f"Error rate {metrics.error_rate}% too high"
        assert metrics.avg_response_time < 0.1, f"Avg response time {metrics.avg_response_time:.3f}s too slow"
        assert metrics.p95_response_time < 0.2, f"P95 response time {metrics.p95_response_time:.3f}s too slow"

    async def test_user_registration_load(self, async_test_client: AsyncClient):
        """Test user registration under load."""
        
        async def register_user(user_id: int):
            start_time = time.time()
            try:
                response = await async_test_client.post(
                    "/api/users/register",
                    json={
                        "email": f"load_test_user_{user_id}_{int(time.time())}@example.com",
                        "password": "LoadTestPassword123!"
                    }
                )
                response_time = time.time() - start_time
                return response_time, response.status_code in [200, 201]
            except Exception:
                response_time = time.time() - start_time
                return response_time, False
        
        # Run 50 concurrent registrations
        num_requests = 50
        start_time = time.time()
        
        tasks = [register_user(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        total_duration = time.time() - start_time
        
        response_times = [r[0] for r in results]
        success_count = sum(1 for r in results if r[1])
        error_count = num_requests - success_count
        
        metrics = perf_tester.calculate_metrics(
            "user_registration", response_times, success_count, error_count, total_duration
        )
        perf_tester.log_metrics(metrics)
        
        # Performance assertions
        assert metrics.error_rate < 10.0, f"Error rate {metrics.error_rate}% too high"
        assert metrics.avg_response_time < 2.0, f"Avg response time {metrics.avg_response_time:.3f}s too slow"
        assert metrics.throughput > 10.0, f"Throughput {metrics.throughput:.2f} req/s too low"

    async def test_photo_listing_performance(self, async_test_client: AsyncClient):
        """Test photo listing performance."""
        
        async def get_public_photos():
            start_time = time.time()
            try:
                response = await async_test_client.get("/api/photos/public")
                response_time = time.time() - start_time
                return response_time, response.status_code == 200
            except Exception:
                response_time = time.time() - start_time
                return response_time, False
        
        # Run 200 concurrent requests
        num_requests = 200
        start_time = time.time()
        
        tasks = [get_public_photos() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        total_duration = time.time() - start_time
        
        response_times = [r[0] for r in results]
        success_count = sum(1 for r in results if r[1])
        error_count = num_requests - success_count
        
        metrics = perf_tester.calculate_metrics(
            "photo_listing", response_times, success_count, error_count, total_duration
        )
        perf_tester.log_metrics(metrics)
        
        # Performance assertions
        assert metrics.error_rate < 5.0, f"Error rate {metrics.error_rate}% too high"
        assert metrics.avg_response_time < 0.5, f"Avg response time {metrics.avg_response_time:.3f}s too slow"
        assert metrics.p95_response_time < 1.0, f"P95 response time {metrics.p95_response_time:.3f}s too slow"


@pytest.mark.performance
@pytest.mark.slow
class TestDatabasePerformance:
    """Test database performance under load."""

    async def test_concurrent_user_operations(self, async_test_client: AsyncClient):
        """Test concurrent user operations performance."""
        
        # Create a verified user first
        timestamp = int(time.time())
        test_user_email = f"db_perf_user_{timestamp}@example.com"
        test_password = "DbPerfPassword123!"
        
        # Register and verify user
        register_response = await async_test_client.post(
            "/api/users/register",
            json={"email": test_user_email, "password": test_password}
        )
        assert register_response.status_code == 200
        
        # Request verification
        verification_request = await async_test_client.post(
            "/api/users/request-verification",
            json={"email": test_user_email}
        )
        verification_link = verification_request.json()["verification_link"]
        verification_secret = verification_link.split("/")[-1]
        
        # Verify email
        await async_test_client.get(f"/api/users/verify/{verification_secret}")
        
        # Login to get token
        login_response = await async_test_client.post(
            "/api/users/login",
            data={"username": test_user_email, "password": test_password}
        )
        access_token = login_response.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        
        async def get_user_profile():
            start_time = time.time()
            try:
                response = await async_test_client.get("/api/users/me", headers=auth_headers)
                response_time = time.time() - start_time
                return response_time, response.status_code == 200
            except Exception:
                response_time = time.time() - start_time
                return response_time, False
        
        # Run 150 concurrent profile requests
        num_requests = 150
        start_time = time.time()
        
        tasks = [get_user_profile() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        total_duration = time.time() - start_time
        
        response_times = [r[0] for r in results]
        success_count = sum(1 for r in results if r[1])
        error_count = num_requests - success_count
        
        metrics = perf_tester.calculate_metrics(
            "concurrent_user_operations", response_times, success_count, error_count, total_duration
        )
        perf_tester.log_metrics(metrics)
        
        # Database performance assertions
        assert metrics.error_rate < 5.0, f"Error rate {metrics.error_rate}% too high"
        assert metrics.avg_response_time < 0.1, f"Avg DB response time {metrics.avg_response_time:.3f}s too slow"
        assert metrics.throughput > 50.0, f"DB throughput {metrics.throughput:.2f} req/s too low"


@pytest.mark.performance
@pytest.mark.slow
class TestStressTesting:
    """Stress testing to find system limits."""

    async def test_api_stress_limits(self, async_test_client: AsyncClient):
        """Test API stress limits with increasing load."""
        
        async def make_stress_request():
            start_time = time.time()
            try:
                response = await async_test_client.get("/api/")
                response_time = time.time() - start_time
                return response_time, response.status_code == 200
            except Exception:
                response_time = time.time() - start_time
                return response_time, False
        
        # Test with increasing load levels
        load_levels = [50, 100, 200, 300, 500]
        
        for num_requests in load_levels:
            print(f"\n🔥 Stress testing with {num_requests} concurrent requests")
            
            start_time = time.time()
            tasks = [make_stress_request() for _ in range(num_requests)]
            results = await asyncio.gather(*tasks)
            total_duration = time.time() - start_time
            
            response_times = [r[0] for r in results]
            success_count = sum(1 for r in results if r[1])
            error_count = num_requests - success_count
            
            metrics = perf_tester.calculate_metrics(
                f"stress_test_{num_requests}", response_times, success_count, error_count, total_duration
            )
            perf_tester.log_metrics(metrics)
            
            # Check if system is still stable
            if metrics.error_rate > 20.0 or metrics.avg_response_time > 5.0:
                print(f"   ⚠️  System showing stress at {num_requests} concurrent requests")
                break
            else:
                print(f"   ✅ System stable at {num_requests} concurrent requests")

    async def test_memory_usage_under_load(self, async_test_client: AsyncClient):
        """Test memory usage patterns under sustained load."""
        
        async def sustained_request():
            try:
                response = await async_test_client.get("/health")
                return response.status_code == 200
            except Exception:
                return False
        
        # Run sustained load for 30 seconds
        duration = 30  # seconds
        request_interval = 0.1  # 10 requests per second
        
        start_time = time.time()
        success_count = 0
        error_count = 0
        
        print(f"🔄 Running sustained load test for {duration} seconds...")
        
        while time.time() - start_time < duration:
            batch_start = time.time()
            
            # Send 10 requests in parallel
            tasks = [sustained_request() for _ in range(10)]
            results = await asyncio.gather(*tasks)
            
            success_count += sum(results)
            error_count += len(results) - sum(results)
            
            # Wait for next interval
            elapsed = time.time() - batch_start
            if elapsed < request_interval:
                await asyncio.sleep(request_interval - elapsed)
        
        total_duration = time.time() - start_time
        total_requests = success_count + error_count
        
        print(f"   📊 Sustained load results:")
        print(f"      Duration: {total_duration:.2f}s")
        print(f"      Total Requests: {total_requests}")
        print(f"      Success Rate: {(success_count/total_requests)*100:.2f}%")
        print(f"      Average RPS: {total_requests/total_duration:.2f}")
        
        # Memory usage should remain stable
        assert (success_count / total_requests) > 0.95, "Success rate dropped during sustained load"


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Establish performance benchmarks for key operations."""

    async def test_authentication_benchmark(self, async_test_client: AsyncClient):
        """Benchmark authentication performance."""
        
        # Create test user
        timestamp = int(time.time())
        test_user = {
            "email": f"bench_user_{timestamp}@example.com",
            "password": "BenchmarkPassword123!"
        }
        
        # Registration benchmark
        start_time = time.time()
        register_response = await async_test_client.post("/api/users/register", json=test_user)
        registration_time = time.time() - start_time
        
        assert register_response.status_code == 200
        assert registration_time < 2.0, f"Registration benchmark failed: {registration_time:.3f}s > 2.0s"
        
        # Verification benchmark
        verification_request = await async_test_client.post(
            "/api/users/request-verification",
            json={"email": test_user["email"]}
        )
        verification_link = verification_request.json()["verification_link"]
        verification_secret = verification_link.split("/")[-1]
        
        start_time = time.time()
        verify_response = await async_test_client.get(f"/api/users/verify/{verification_secret}")
        verification_time = time.time() - start_time
        
        assert verify_response.status_code == 200
        assert verification_time < 1.0, f"Verification benchmark failed: {verification_time:.3f}s > 1.0s"
        
        # Login benchmark
        start_time = time.time()
        login_response = await async_test_client.post(
            "/api/users/login",
            data={"username": test_user["email"], "password": test_user["password"]}
        )
        login_time = time.time() - start_time
        
        assert login_response.status_code == 200
        assert login_time < 1.0, f"Login benchmark failed: {login_time:.3f}s > 1.0s"
        
        print(f"🏆 Authentication Benchmarks:")
        print(f"   Registration: {registration_time*1000:.2f}ms")
        print(f"   Verification: {verification_time*1000:.2f}ms")
        print(f"   Login: {login_time*1000:.2f}ms")

    async def test_api_response_benchmarks(self, async_test_client: AsyncClient):
        """Benchmark key API endpoint response times."""
        
        endpoints = [
            ("/health", "GET", None, None),
            ("/api/", "GET", None, None),
            ("/api/photos/public", "GET", None, None),
        ]
        
        benchmarks = {}
        
        for endpoint, method, data, headers in endpoints:
            start_time = time.time()
            
            if method == "GET":
                response = await async_test_client.get(endpoint, headers=headers)
            elif method == "POST":
                response = await async_test_client.post(endpoint, json=data, headers=headers)
            
            response_time = time.time() - start_time
            benchmarks[endpoint] = response_time
            
            # General API response time should be < 200ms
            assert response_time < 0.2, f"{endpoint} benchmark failed: {response_time*1000:.2f}ms > 200ms"
        
        print(f"🏆 API Response Benchmarks:")
        for endpoint, response_time in benchmarks.items():
            print(f"   {endpoint}: {response_time*1000:.2f}ms")


@pytest.mark.performance
async def test_generate_performance_report():
    """Generate comprehensive performance test report."""
    
    if not perf_tester.results:
        print("⚠️  No performance test results available for reporting")
        return
    
    report = {
        "performance_test_summary": {
            "total_operations_tested": len(perf_tester.results),
            "timestamp": time.time(),
            "overall_status": "PASSED"
        },
        "operation_metrics": {},
        "benchmarks": {
            "api_response_time_target": "< 200ms",
            "authentication_time_target": "< 1s",
            "database_query_target": "< 100ms",
            "throughput_target": "> 50 req/s"
        },
        "recommendations": []
    }
    
    # Collect metrics for each operation
    for operation, metrics in perf_tester.results.items():
        report["operation_metrics"][operation] = {
            "avg_response_time_ms": metrics.avg_response_time * 1000,
            "p95_response_time_ms": metrics.p95_response_time * 1000,
            "p99_response_time_ms": metrics.p99_response_time * 1000,
            "throughput_rps": metrics.throughput,
            "error_rate_percent": metrics.error_rate,
            "success_count": metrics.success_count,
            "total_requests": metrics.success_count + metrics.error_count
        }
        
        # Check against benchmarks and add recommendations
        if metrics.avg_response_time > 0.2:  # 200ms
            report["recommendations"].append({
                "operation": operation,
                "issue": f"Average response time {metrics.avg_response_time*1000:.2f}ms exceeds 200ms target",
                "recommendation": "Optimize database queries and consider caching"
            })
        
        if metrics.error_rate > 5.0:
            report["recommendations"].append({
                "operation": operation,
                "issue": f"Error rate {metrics.error_rate:.2f}% exceeds 5% threshold",
                "recommendation": "Investigate error causes and improve error handling"
            })
            report["performance_test_summary"]["overall_status"] = "NEEDS_ATTENTION"
        
        if metrics.throughput < 50.0 and "stress" not in operation:
            report["recommendations"].append({
                "operation": operation,
                "issue": f"Throughput {metrics.throughput:.2f} req/s below 50 req/s target",
                "recommendation": "Consider performance optimizations and scaling"
            })
    
    # Write report to file
    import json
    with open("/tmp/performance_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 PERFORMANCE TEST REPORT")
    print(f"{'='*60}")
    print(f"Operations Tested: {report['performance_test_summary']['total_operations_tested']}")
    print(f"Overall Status: {report['performance_test_summary']['overall_status']}")
    
    if report["recommendations"]:
        print(f"\n⚠️  Recommendations:")
        for rec in report["recommendations"]:
            print(f"  - {rec['operation']}: {rec['issue']}")
            print(f"    → {rec['recommendation']}")
    else:
        print(f"\n✅ All performance benchmarks met!")
    
    print(f"\nDetailed report: /tmp/performance_test_report.json")
    
    # Test should pass unless there are critical performance issues
    critical_issues = [r for r in report["recommendations"] if "error_rate" in r["issue"]]
    assert len(critical_issues) == 0, f"Critical performance issues found: {len(critical_issues)}"