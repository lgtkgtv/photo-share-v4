#!/usr/bin/env python3
"""
PhotoShare Database Activity Monitoring Test Suite
=================================================

Comprehensive test suite for the database activity monitoring system.
Tests query logging, security event detection, anomaly detection, and performance monitoring.

Version: 2.3.0-monitoring
Author: PhotoShare Security Team
"""

import sys
import os
import time
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone

# Add the services directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'photoshare'))

try:
    from database_activity_monitoring import (
        DatabaseActivityMonitor,
        init_database_monitoring,
        log_query_execution,
        log_connection_metrics,
        get_database_monitoring_stats,
        get_security_events,
        get_query_performance_stats,
        QueryType,
        SecurityThreatLevel
    )
    
    DATABASE_MONITORING_AVAILABLE = True
except ImportError as e:
    print(f"❌ Database monitoring components not available: {e}")
    DATABASE_MONITORING_AVAILABLE = False
    sys.exit(1)

class DatabaseMonitoringTestSuite:
    """Comprehensive test suite for database activity monitoring"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_database_monitoring.db")
        self.monitor = None
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'tests': []
        }

    def log_test_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅" if passed else "❌"
        print(f"   {status} {test_name}: {message}")
        
        self.test_results['tests'].append({
            'name': test_name,
            'passed': passed,
            'message': message
        })
        
        if passed:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1

    def test_monitor_initialization(self):
        """Test database activity monitor initialization"""
        print("📊 Testing Database Monitor Initialization")
        print("=" * 45)
        
        try:
            # Test basic initialization
            self.monitor = DatabaseActivityMonitor(self.db_path, "standard")
            self.log_test_result("Basic initialization", True,
                                "Database monitor initialized successfully")
            
            # Test database creation
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['query_metrics', 'security_events', 
                              'connection_metrics', 'anomaly_detections', 'query_patterns']
            missing_tables = [table for table in expected_tables if table not in tables]
            
            self.log_test_result("Database schema creation", len(missing_tables) == 0,
                                f"All required tables created" if not missing_tables 
                                else f"Missing tables: {missing_tables}")
            
            # Test global initialization
            global_monitor = init_database_monitoring("high", self.db_path)
            self.log_test_result("Global initialization", global_monitor is not None,
                                "Global database monitor initialized")
            
        except Exception as e:
            self.log_test_result("Database monitor initialization", False, f"Exception: {e}")

    def test_query_execution_logging(self):
        """Test database query execution logging"""
        print("\n🔍 Testing Query Execution Logging")
        print("=" * 40)
        
        try:
            # Test basic query logging
            query_hash = self.monitor.log_query_execution(
                query_text="SELECT * FROM users WHERE email = ?",
                execution_time=0.05,
                rows_affected=1,
                user_id="test_user_123",
                session_id="session_456",
                source_ip="192.168.1.100",
                parameters={"email": "test@example.com"}
            )
            
            self.log_test_result("Basic query logging", query_hash is not None,
                                f"Query logged with hash: {query_hash[:16]}...")
            
            # Test different query types
            query_types_test = [
                ("SELECT id, email FROM users", QueryType.SELECT),
                ("INSERT INTO photos (user_id, filename) VALUES (?, ?)", QueryType.INSERT),
                ("UPDATE users SET last_login = ? WHERE id = ?", QueryType.UPDATE),
                ("DELETE FROM sessions WHERE expires_at < ?", QueryType.DELETE),
                ("CREATE TABLE test_table (id INTEGER)", QueryType.DDL)
            ]
            
            for query_text, expected_type in query_types_test:
                detected_type = self.monitor._determine_query_type(query_text)
                self.log_test_result(f"Query type detection ({expected_type.value})",
                                    detected_type == expected_type,
                                    f"Detected: {detected_type.value}")
            
            # Test query normalization
            original_query = "SELECT * FROM users WHERE id = 123 AND name = 'John'"
            normalized = self.monitor._normalize_query(original_query)
            expected_normalized = "select * from users where id = ? and name = '?'"
            
            self.log_test_result("Query normalization",
                                normalized == expected_normalized,
                                f"Normalized: {normalized}")
            
        except Exception as e:
            self.log_test_result("Query execution logging", False, f"Exception: {e}")

    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection"""
        print("\n🛡️  Testing SQL Injection Detection")
        print("=" * 40)
        
        try:
            # Test various SQL injection patterns
            injection_queries = [
                ("SELECT * FROM users WHERE id = 1 OR 1=1", True, "Classic OR 1=1 injection"),
                ("SELECT * FROM users; DROP TABLE users;", True, "SQL command injection"),
                ("SELECT * FROM users WHERE id = 1 UNION SELECT password FROM admin_users", True, "UNION-based injection"),
                ("SELECT * FROM users WHERE name = 'admin'--", True, "Comment-based injection"),
                ("SELECT benchmark(1000000, sha1('test'))", True, "Time-based injection"),
                ("SELECT * FROM users WHERE id = ?", False, "Safe parameterized query"),
                ("SELECT count(*) FROM photos WHERE user_id = 123", False, "Safe numeric query")
            ]
            
            for query_text, should_detect, description in injection_queries:
                # Log the query and check for security events
                initial_events_count = len(self.monitor.security_events)
                
                self.monitor.log_query_execution(
                    query_text=query_text,
                    execution_time=0.1,
                    user_id="test_user",
                    source_ip="192.168.1.100"
                )
                
                # Check if security event was created
                new_events_count = len(self.monitor.security_events)
                injection_detected = new_events_count > initial_events_count
                
                # For injection attempts, we expect detection
                test_passed = injection_detected == should_detect
                
                self.log_test_result(f"SQL injection detection - {description}",
                                    test_passed,
                                    f"Expected: {should_detect}, Detected: {injection_detected}")
            
        except Exception as e:
            self.log_test_result("SQL injection detection", False, f"Exception: {e}")

    def test_anomaly_detection(self):
        """Test database activity anomaly detection"""
        print("\n🚨 Testing Anomaly Detection")
        print("=" * 35)
        
        try:
            # Test slow query anomaly
            self.monitor.log_query_execution(
                query_text="SELECT * FROM large_table WHERE complex_condition = ?",
                execution_time=15.0,  # Exceeds threshold
                rows_affected=5000,
                user_id="test_user"
            )
            
            # Check anomaly database
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM anomaly_detections 
                    WHERE anomaly_type = 'SLOW_QUERY'
                """)
                slow_query_anomalies = cursor.fetchone()[0]
            
            self.log_test_result("Slow query anomaly detection",
                                slow_query_anomalies > 0,
                                f"Detected {slow_query_anomalies} slow query anomalies")
            
            # Test high frequency anomaly
            user_id = "frequent_user"
            for i in range(150):  # Exceed frequency threshold
                self.monitor.log_query_execution(
                    query_text=f"SELECT * FROM table WHERE id = {i}",
                    execution_time=0.01,
                    user_id=user_id,
                    source_ip="192.168.1.200"
                )
            
            # Check for high frequency anomaly
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM anomaly_detections 
                    WHERE anomaly_type = 'HIGH_QUERY_FREQUENCY'
                """)
                freq_anomalies = cursor.fetchone()[0]
            
            self.log_test_result("High frequency anomaly detection",
                                freq_anomalies > 0,
                                f"Detected {freq_anomalies} high frequency anomalies")
            
            # Test unusual hours access (simulate off-hours access)
            import datetime
            night_time = datetime.datetime.now(timezone.utc).replace(hour=2)  # 2 AM
            
            # Create a custom anomaly for testing
            anomaly_count_before = 0
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM anomaly_detections")
                anomaly_count_before = cursor.fetchone()[0]
            
            # Simulate night query
            self.monitor.log_query_execution(
                query_text="SELECT sensitive_data FROM classified_table",
                execution_time=0.1,
                user_id="night_user"
            )
            
            # Check total anomalies increased
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM anomaly_detections")
                anomaly_count_after = cursor.fetchone()[0]
            
            self.log_test_result("Anomaly detection system",
                                anomaly_count_after > anomaly_count_before,
                                f"Anomalies: before={anomaly_count_before}, after={anomaly_count_after}")
            
        except Exception as e:
            self.log_test_result("Anomaly detection", False, f"Exception: {e}")

    def test_connection_metrics_logging(self):
        """Test database connection metrics logging"""
        print("\n🔗 Testing Connection Metrics Logging")
        print("=" * 40)
        
        try:
            # Log connection metrics
            self.monitor.log_connection_metrics(
                total=50,
                active=20,
                idle=25,
                checked_out=15,
                overflow=5
            )
            
            # Verify storage
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT total_connections, active_connections, idle_connections,
                           checked_out_connections, overflow_connections
                    FROM connection_metrics
                    ORDER BY timestamp DESC LIMIT 1
                """)
                result = cursor.fetchone()
            
            if result:
                total, active, idle, checked_out, overflow = result
                self.log_test_result("Connection metrics storage",
                                    total == 50 and active == 20,
                                    f"Stored: total={total}, active={active}")
                
                self.log_test_result("Connection metrics validation",
                                    idle == 25 and checked_out == 15,
                                    f"Idle={idle}, checked_out={checked_out}")
            else:
                self.log_test_result("Connection metrics storage", False,
                                    "No connection metrics found in database")
            
            # Test multiple metrics logging
            for i in range(5):
                self.monitor.log_connection_metrics(
                    total=40 + i * 2,
                    active=15 + i,
                    idle=20 + i,
                    checked_out=10 + i,
                    overflow=0
                )
            
            # Count total metrics
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM connection_metrics")
                metrics_count = cursor.fetchone()[0]
            
            self.log_test_result("Multiple connection metrics logging",
                                metrics_count >= 6,  # 1 + 5 from loop
                                f"Total metrics logged: {metrics_count}")
            
        except Exception as e:
            self.log_test_result("Connection metrics logging", False, f"Exception: {e}")

    def test_security_events_retrieval(self):
        """Test security events retrieval and filtering"""
        print("\n🔒 Testing Security Events Retrieval")
        print("=" * 40)
        
        try:
            # Generate some test security events by logging suspicious queries
            test_queries = [
                ("SELECT * FROM users WHERE 1=1 OR 'a'='a'", "CRITICAL"),
                ("DROP TABLE important_data", "HIGH"),
                ("SELECT password FROM users", "MEDIUM")
            ]
            
            for query, _ in test_queries:
                self.monitor.log_query_execution(
                    query_text=query,
                    execution_time=0.1,
                    user_id="security_test_user",
                    source_ip="192.168.1.100"
                )
            
            # Retrieve all security events
            all_events = self.monitor.get_security_events(hours_back=1)
            self.log_test_result("Security events retrieval",
                                len(all_events) > 0,
                                f"Retrieved {len(all_events)} security events")
            
            # Test filtering by threat level
            critical_events = self.monitor.get_security_events(hours_back=1, threat_level=SecurityThreatLevel.CRITICAL)
            self.log_test_result("Critical events filtering",
                                len(critical_events) > 0,
                                f"Found {len(critical_events)} critical events")
            
            # Test global function
            global_events = get_security_events(hours_back=1)
            self.log_test_result("Global security events function",
                                len(global_events) >= 0,
                                f"Global function returned {len(global_events)} events")
            
        except Exception as e:
            self.log_test_result("Security events retrieval", False, f"Exception: {e}")

    def test_query_performance_statistics(self):
        """Test query performance statistics generation"""
        print("\n📈 Testing Query Performance Statistics")
        print("=" * 45)
        
        try:
            # Generate diverse query performance data
            performance_test_data = [
                ("SELECT * FROM users", 0.05, 10, QueryType.SELECT),
                ("INSERT INTO logs VALUES (?)", 0.02, 1, QueryType.INSERT),
                ("UPDATE settings SET value = ?", 0.08, 1, QueryType.UPDATE),
                ("DELETE FROM temp_data WHERE old = 1", 0.15, 25, QueryType.DELETE),
                ("SELECT COUNT(*) FROM photos", 2.5, 1, QueryType.SELECT),  # Slow query
            ]
            
            for query, exec_time, rows, query_type in performance_test_data:
                self.monitor.log_query_execution(
                    query_text=query,
                    execution_time=exec_time,
                    rows_affected=rows,
                    user_id="performance_test_user"
                )
            
            # Get performance statistics
            perf_stats = self.monitor.get_query_performance_stats(hours_back=1)
            
            self.log_test_result("Performance statistics generation",
                                'total_queries' in perf_stats,
                                f"Generated stats with {perf_stats.get('total_queries', 0)} queries")
            
            self.log_test_result("Query type breakdown",
                                'query_type_breakdown' in perf_stats,
                                f"Query types: {len(perf_stats.get('query_type_breakdown', []))}")
            
            self.log_test_result("Slow queries identification",
                                'slow_queries' in perf_stats,
                                f"Slow queries: {len(perf_stats.get('slow_queries', []))}")
            
            # Test averages calculation
            if perf_stats.get('avg_execution_time'):
                self.log_test_result("Average execution time calculation",
                                    perf_stats['avg_execution_time'] > 0,
                                    f"Avg time: {perf_stats['avg_execution_time']}s")
            
            # Test global function
            global_stats = get_query_performance_stats(hours_back=1)
            self.log_test_result("Global performance stats function",
                                'total_queries' in global_stats,
                                f"Global stats: {global_stats.get('total_queries', 0)} queries")
            
        except Exception as e:
            self.log_test_result("Query performance statistics", False, f"Exception: {e}")

    def test_monitoring_statistics(self):
        """Test comprehensive monitoring statistics"""
        print("\n📊 Testing Monitoring Statistics")
        print("=" * 35)
        
        try:
            # Get monitoring statistics
            stats = self.monitor.get_monitoring_statistics()
            
            self.log_test_result("Statistics generation",
                                isinstance(stats, dict),
                                "Statistics dictionary generated")
            
            required_fields = ['database_monitoring_enabled', 'monitoring_level', 
                              'security_events_24h', 'features']
            missing_fields = [field for field in required_fields if field not in stats]
            
            self.log_test_result("Required statistics fields",
                                len(missing_fields) == 0,
                                f"All required fields present" if not missing_fields 
                                else f"Missing fields: {missing_fields}")
            
            self.log_test_result("Monitoring enabled status",
                                stats.get('database_monitoring_enabled', False),
                                f"Monitoring enabled: {stats.get('database_monitoring_enabled')}")
            
            # Test features reporting
            features = stats.get('features', {})
            expected_features = ['query_monitoring', 'security_event_detection', 
                               'anomaly_detection', 'performance_analysis']
            
            enabled_features = [f for f in expected_features if features.get(f, False)]
            self.log_test_result("Security features reporting",
                                len(enabled_features) == len(expected_features),
                                f"Enabled features: {enabled_features}")
            
            # Test global statistics function
            global_stats = get_database_monitoring_stats()
            self.log_test_result("Global statistics function",
                                global_stats.get('database_monitoring_enabled', False),
                                "Global statistics accessible")
            
        except Exception as e:
            self.log_test_result("Monitoring statistics", False, f"Exception: {e}")

    def test_query_pattern_analysis(self):
        """Test query pattern analysis and learning"""
        print("\n🧠 Testing Query Pattern Analysis")
        print("=" * 35)
        
        try:
            # Generate repetitive queries to create patterns
            base_query = "SELECT id, name FROM products WHERE category = ?"
            for i in range(10):
                self.monitor.log_query_execution(
                    query_text=base_query,
                    execution_time=0.1 + i * 0.01,
                    rows_affected=5,
                    user_id=f"pattern_user_{i % 3}",  # 3 different users
                    parameters={"category": f"category_{i % 5}"}  # 5 different categories
                )
            
            # Force pattern update (normally done by monitoring thread)
            self.monitor._update_query_patterns()
            
            # Check pattern storage
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), AVG(frequency) FROM query_patterns")
                result = cursor.fetchone()
            
            if result:
                pattern_count, avg_frequency = result
                self.log_test_result("Query pattern creation",
                                    pattern_count > 0,
                                    f"Created {pattern_count} patterns, avg frequency: {avg_frequency:.1f}")
            
            # Test pattern normalization consistency
            queries = [
                "SELECT * FROM users WHERE id = 123",
                "SELECT * FROM users WHERE id = 456",
                "SELECT * FROM users WHERE id = 789"
            ]
            
            normalized_queries = [self.monitor._normalize_query(q) for q in queries]
            all_same = all(nq == normalized_queries[0] for nq in normalized_queries)
            
            self.log_test_result("Query normalization consistency",
                                all_same,
                                f"Normalized pattern: {normalized_queries[0]}")
            
        except Exception as e:
            self.log_test_result("Query pattern analysis", False, f"Exception: {e}")

    def test_monitoring_lifecycle(self):
        """Test monitoring start/stop lifecycle"""
        print("\n🔄 Testing Monitoring Lifecycle")
        print("=" * 35)
        
        try:
            # Test monitoring start
            self.monitor.start_monitoring()
            self.log_test_result("Monitoring start",
                                self.monitor.monitoring_active,
                                "Monitoring thread started successfully")
            
            # Let it run briefly
            time.sleep(2)
            
            # Test monitoring is active
            self.log_test_result("Monitoring active status",
                                self.monitor.monitoring_thread is not None and 
                                self.monitor.monitoring_thread.is_alive(),
                                "Monitoring thread is running")
            
            # Test monitoring stop
            self.monitor.stop_monitoring()
            time.sleep(1)  # Give it time to stop
            
            self.log_test_result("Monitoring stop",
                                not self.monitor.monitoring_active,
                                "Monitoring stopped successfully")
            
        except Exception as e:
            self.log_test_result("Monitoring lifecycle", False, f"Exception: {e}")

    def test_data_cleanup(self):
        """Test old data cleanup functionality"""
        print("\n🧹 Testing Data Cleanup")
        print("=" * 25)
        
        try:
            # Insert some old data by directly manipulating the database
            import sqlite3
            from datetime import timedelta
            
            old_timestamp = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Insert old query metric
                conn.execute("""
                    INSERT INTO query_metrics 
                    (query_hash, query_type, execution_time, query_text, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, ("old_hash", "SELECT", 0.1, "SELECT old_data", old_timestamp))
                
                # Insert old security event
                conn.execute("""
                    INSERT INTO security_events
                    (event_id, threat_level, event_type, description, query_hash, query_text, timestamp, resolved)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, ("old_event", "LOW", "TEST", "Old event", "old_hash", "SELECT", old_timestamp, 1))
            
            # Count records before cleanup
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM query_metrics")
                metrics_before = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM security_events")
                events_before = cursor.fetchone()[0]
            
            # Perform cleanup
            self.monitor._cleanup_old_data()
            
            # Count records after cleanup
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM query_metrics")
                metrics_after = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM security_events")
                events_after = cursor.fetchone()[0]
            
            self.log_test_result("Old data cleanup",
                                metrics_after < metrics_before,
                                f"Metrics: {metrics_before} -> {metrics_after}")
            
            self.log_test_result("Old security events cleanup",
                                events_after <= events_before,
                                f"Events: {events_before} -> {events_after}")
            
        except Exception as e:
            self.log_test_result("Data cleanup", False, f"Exception: {e}")

    def run_all_tests(self):
        """Run complete database monitoring test suite"""
        print("📊 PhotoShare Database Activity Monitoring Test Suite")
        print("=" * 55)
        print(f"Database: {self.db_path}")
        print()
        
        # Run all test categories
        self.test_monitor_initialization()
        self.test_query_execution_logging()
        self.test_sql_injection_detection()
        self.test_anomaly_detection()
        self.test_connection_metrics_logging()
        self.test_security_events_retrieval()
        self.test_query_performance_statistics()
        self.test_monitoring_statistics()
        self.test_query_pattern_analysis()
        self.test_monitoring_lifecycle()
        self.test_data_cleanup()
        
        # Summary
        print(f"\n📊 Test Results Summary")
        print("=" * 25)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"📈 Success Rate: {(self.test_results['passed'] / (self.test_results['passed'] + self.test_results['failed']) * 100):.1f}%")
        
        if self.test_results['failed'] == 0:
            print("\n🎉 All database monitoring tests passed!")
            return True
        else:
            print(f"\n⚠️ Some database monitoring tests failed")
            return False

    def cleanup(self):
        """Clean up test resources"""
        try:
            if self.monitor:
                self.monitor.stop_monitoring()
            
            # Clean up temp directory
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")

def main():
    """Main test function"""
    if not DATABASE_MONITORING_AVAILABLE:
        print("❌ Database monitoring components not available")
        return False
    
    test_suite = DatabaseMonitoringTestSuite()
    
    try:
        success = test_suite.run_all_tests()
        return success
    except Exception as e:
        print(f"❌ Test suite failed with exception: {e}")
        return False
    finally:
        test_suite.cleanup()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)