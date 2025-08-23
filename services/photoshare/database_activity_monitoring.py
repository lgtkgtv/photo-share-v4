"""
PhotoShare Database Activity Monitoring Module
==============================================

Comprehensive database activity monitoring and anomaly detection system
for the PhotoShare application.

Features:
- Real-time database query monitoring and logging
- SQL injection detection and prevention
- Anomalous query pattern detection
- Database performance monitoring and alerting
- Connection pool monitoring
- Query execution time analysis and optimization suggestions
- Database security event detection
- Compliance and audit trail generation
- Data access pattern analysis

Version: 2.3.0-monitoring
Author: PhotoShare Security Team
"""

import sqlite3
import logging
import threading
import time
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, deque
from enum import Enum
import sqlalchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Database query types"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    DDL = "DDL"
    OTHER = "OTHER"

class SecurityThreatLevel(Enum):
    """Database security threat levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class QueryMetrics:
    """Database query performance metrics"""
    query_hash: str
    query_type: QueryType
    execution_time: float
    rows_affected: int
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    source_ip: Optional[str]
    query_text: str
    parameters: Dict[str, Any]
    
@dataclass
class SecurityEvent:
    """Database security event"""
    event_id: str
    threat_level: SecurityThreatLevel
    event_type: str
    description: str
    query_hash: str
    query_text: str
    user_id: Optional[str]
    session_id: Optional[str]
    source_ip: Optional[str]
    timestamp: datetime
    details: Dict[str, Any]

@dataclass
class ConnectionMetrics:
    """Database connection pool metrics"""
    total_connections: int
    active_connections: int
    idle_connections: int
    checked_out_connections: int
    overflow_connections: int
    timestamp: datetime

@dataclass
class AnomalyDetection:
    """Database activity anomaly detection result"""
    is_anomalous: bool
    anomaly_score: float
    anomaly_type: str
    description: str
    query_hash: str
    timestamp: datetime
    details: Dict[str, Any]

class DatabaseActivityMonitor:
    """Advanced database activity monitoring system"""
    
    def __init__(self, db_path: str = "database_monitoring.db", monitoring_level: str = "standard"):
        self.db_path = db_path
        self.monitoring_level = monitoring_level
        self.monitoring_active = False
        self.monitoring_thread = None
        self._lock = threading.RLock()
        
        # Monitoring data structures
        self.query_metrics: deque = deque(maxlen=10000)  # Recent query metrics
        self.security_events: List[SecurityEvent] = []
        self.connection_metrics: deque = deque(maxlen=1000)
        self.query_patterns: Dict[str, List[QueryMetrics]] = defaultdict(list)
        self.user_activity: Dict[str, List[QueryMetrics]] = defaultdict(list)
        
        # SQL injection patterns
        self.sql_injection_patterns = [
            r"(?i)\b(union\s+select|select\s+.*\s+from\s+information_schema)",
            r"(?i)\b(drop\s+table|drop\s+database|truncate\s+table)",
            r"(?i)\b(exec\s*\(|execute\s*\(|sp_executesql)",
            r"(?i)\b(xp_cmdshell|sp_oacreate|sp_oamethod)",
            r"(?i)(\'\s*;\s*--|\'\s*union|\'\s*or\s+\d+\s*=\s*\d+)",
            r"(?i)(benchmark\s*\(|sleep\s*\(|waitfor\s+delay)",
            r"(?i)(load_file\s*\(|into\s+outfile|into\s+dumpfile)",
            r"(?i)(\bor\s+\d+\s*=\s*\d+\s*--|\band\s+\d+\s*=\s*\d+\s*--)"
        ]
        self.compiled_injection_patterns = [re.compile(pattern) for pattern in self.sql_injection_patterns]
        
        # Anomaly detection thresholds
        self.anomaly_thresholds = {
            'execution_time': 10.0,  # seconds
            'query_frequency': 100,   # queries per minute
            'failed_queries': 10,     # failed queries per minute
            'data_volume': 1000000,   # bytes
            'unusual_hours': (22, 6), # 10 PM to 6 AM
        }
        
        # Initialize database
        self._init_database()
        
        # Start monitoring
        if monitoring_level in ['high', 'enterprise']:
            self.start_monitoring()
        
        logger.info(f"Database Activity Monitor initialized (level: {monitoring_level})")

    def _init_database(self):
        """Initialize monitoring database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS query_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT NOT NULL,
                    query_type TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    rows_affected INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    session_id TEXT,
                    source_ip TEXT,
                    query_text TEXT NOT NULL,
                    parameters TEXT DEFAULT '{}'
                );
                
                CREATE INDEX IF NOT EXISTS idx_query_metrics_timestamp ON query_metrics(timestamp);
                CREATE INDEX IF NOT EXISTS idx_query_metrics_user_id ON query_metrics(user_id);
                CREATE INDEX IF NOT EXISTS idx_query_metrics_query_hash ON query_metrics(query_hash);
                
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    threat_level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    query_hash TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    source_ip TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT DEFAULT '{}',
                    resolved BOOLEAN DEFAULT 0
                );
                
                CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_security_events_threat_level ON security_events(threat_level);
                CREATE INDEX IF NOT EXISTS idx_security_events_user_id ON security_events(user_id);
                
                CREATE TABLE IF NOT EXISTS connection_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_connections INTEGER NOT NULL,
                    active_connections INTEGER NOT NULL,
                    idle_connections INTEGER NOT NULL,
                    checked_out_connections INTEGER NOT NULL,
                    overflow_connections INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_connection_metrics_timestamp ON connection_metrics(timestamp);
                
                CREATE TABLE IF NOT EXISTS anomaly_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anomaly_score REAL NOT NULL,
                    anomaly_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    query_hash TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT DEFAULT '{}',
                    false_positive BOOLEAN DEFAULT 0
                );
                
                CREATE INDEX IF NOT EXISTS idx_anomaly_detections_timestamp ON anomaly_detections(timestamp);
                CREATE INDEX IF NOT EXISTS idx_anomaly_detections_score ON anomaly_detections(anomaly_score);
                
                CREATE TABLE IF NOT EXISTS query_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_hash TEXT UNIQUE NOT NULL,
                    pattern_type TEXT NOT NULL,
                    query_template TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    avg_execution_time REAL DEFAULT 0.0,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_suspicious BOOLEAN DEFAULT 0
                );
                
                CREATE INDEX IF NOT EXISTS idx_query_patterns_frequency ON query_patterns(frequency);
                CREATE INDEX IF NOT EXISTS idx_query_patterns_last_seen ON query_patterns(last_seen);
            """)

    def log_query_execution(self, query_text: str, execution_time: float, 
                          rows_affected: int = 0, user_id: Optional[str] = None,
                          session_id: Optional[str] = None, source_ip: Optional[str] = None,
                          parameters: Dict[str, Any] = None) -> str:
        """Log database query execution"""
        if parameters is None:
            parameters = {}
        
        # Generate query hash
        query_hash = hashlib.sha256(self._normalize_query(query_text).encode()).hexdigest()
        
        # Determine query type
        query_type = self._determine_query_type(query_text)
        
        # Create query metrics
        metrics = QueryMetrics(
            query_hash=query_hash,
            query_type=query_type,
            execution_time=execution_time,
            rows_affected=rows_affected,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            session_id=session_id,
            source_ip=source_ip,
            query_text=query_text,
            parameters=parameters
        )
        
        # Store in memory for real-time analysis
        with self._lock:
            self.query_metrics.append(metrics)
            self.query_patterns[query_hash].append(metrics)
            if user_id:
                self.user_activity[user_id].append(metrics)
        
        # Store in database
        self._store_query_metrics(metrics)
        
        # Perform security analysis
        self._analyze_query_security(metrics)
        
        # Perform anomaly detection
        self._detect_query_anomalies(metrics)
        
        return query_hash

    def _normalize_query(self, query_text: str) -> str:
        """Normalize query text for pattern matching"""
        # Remove extra whitespace and normalize case
        normalized = re.sub(r'\s+', ' ', query_text.strip().lower())
        
        # Replace parameter placeholders
        normalized = re.sub(r'\$\d+|\?|:\w+', '?', normalized)
        
        # Replace literal values
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        
        return normalized

    def _determine_query_type(self, query_text: str) -> QueryType:
        """Determine the type of database query"""
        query_lower = query_text.strip().lower()
        
        if query_lower.startswith(('select', 'with')):
            return QueryType.SELECT
        elif query_lower.startswith('insert'):
            return QueryType.INSERT
        elif query_lower.startswith('update'):
            return QueryType.UPDATE
        elif query_lower.startswith('delete'):
            return QueryType.DELETE
        elif query_lower.startswith(('create', 'drop', 'alter', 'truncate')):
            return QueryType.DDL
        else:
            return QueryType.OTHER

    def _store_query_metrics(self, metrics: QueryMetrics):
        """Store query metrics in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO query_metrics 
                    (query_hash, query_type, execution_time, rows_affected, timestamp,
                     user_id, session_id, source_ip, query_text, parameters)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.query_hash,
                    metrics.query_type.value,
                    metrics.execution_time,
                    metrics.rows_affected,
                    metrics.timestamp.isoformat(),
                    metrics.user_id,
                    metrics.session_id,
                    metrics.source_ip,
                    metrics.query_text,
                    json.dumps(metrics.parameters)
                ))
        except Exception as e:
            logger.error(f"Failed to store query metrics: {e}")

    def _analyze_query_security(self, metrics: QueryMetrics):
        """Analyze query for security threats"""
        events = []
        
        # Check for SQL injection patterns
        for pattern in self.compiled_injection_patterns:
            if pattern.search(metrics.query_text):
                event = self._create_security_event(
                    threat_level=SecurityThreatLevel.CRITICAL,
                    event_type="SQL_INJECTION_ATTEMPT",
                    description=f"Potential SQL injection detected in query",
                    query_hash=metrics.query_hash,
                    query_text=metrics.query_text,
                    user_id=metrics.user_id,
                    session_id=metrics.session_id,
                    source_ip=metrics.source_ip,
                    details={"pattern_matched": pattern.pattern}
                )
                events.append(event)
        
        # Check for privilege escalation attempts
        if self._check_privilege_escalation(metrics.query_text):
            event = self._create_security_event(
                threat_level=SecurityThreatLevel.HIGH,
                event_type="PRIVILEGE_ESCALATION_ATTEMPT",
                description="Potential privilege escalation attempt detected",
                query_hash=metrics.query_hash,
                query_text=metrics.query_text,
                user_id=metrics.user_id,
                session_id=metrics.session_id,
                source_ip=metrics.source_ip,
                details={"query_type": metrics.query_type.value}
            )
            events.append(event)
        
        # Check for data exfiltration patterns
        if self._check_data_exfiltration(metrics):
            event = self._create_security_event(
                threat_level=SecurityThreatLevel.HIGH,
                event_type="DATA_EXFILTRATION_ATTEMPT",
                description="Potential data exfiltration detected",
                query_hash=metrics.query_hash,
                query_text=metrics.query_text,
                user_id=metrics.user_id,
                session_id=metrics.session_id,
                source_ip=metrics.source_ip,
                details={"rows_affected": metrics.rows_affected}
            )
            events.append(event)
        
        # Store security events
        for event in events:
            self._store_security_event(event)
            with self._lock:
                self.security_events.append(event)

    def _check_privilege_escalation(self, query_text: str) -> bool:
        """Check for privilege escalation attempts"""
        escalation_patterns = [
            r"(?i)\b(grant|revoke)\s+",
            r"(?i)\bcreate\s+user\b",
            r"(?i)\balter\s+user\b",
            r"(?i)\bdrop\s+user\b",
            r"(?i)\bset\s+password\b",
            r"(?i)\bchange\s+password\b"
        ]
        
        for pattern in escalation_patterns:
            if re.search(pattern, query_text):
                return True
        return False

    def _check_data_exfiltration(self, metrics: QueryMetrics) -> bool:
        """Check for data exfiltration patterns"""
        # Large result set
        if metrics.rows_affected > self.anomaly_thresholds['data_volume']:
            return True
        
        # Unusual SELECT patterns
        if metrics.query_type == QueryType.SELECT:
            if "select *" in metrics.query_text.lower():
                return True
            
            # Multiple joins
            join_count = len(re.findall(r'\bjoin\b', metrics.query_text.lower()))
            if join_count > 3:
                return True
        
        return False

    def _detect_query_anomalies(self, metrics: QueryMetrics):
        """Detect anomalous query patterns"""
        anomalies = []
        
        # Execution time anomaly
        if metrics.execution_time > self.anomaly_thresholds['execution_time']:
            anomaly = AnomalyDetection(
                is_anomalous=True,
                anomaly_score=min(metrics.execution_time / self.anomaly_thresholds['execution_time'] * 100, 100),
                anomaly_type="SLOW_QUERY",
                description=f"Query execution time {metrics.execution_time:.2f}s exceeds threshold",
                query_hash=metrics.query_hash,
                timestamp=metrics.timestamp,
                details={"execution_time": metrics.execution_time}
            )
            anomalies.append(anomaly)
        
        # Query frequency anomaly
        if metrics.user_id:
            recent_queries = [m for m in self.user_activity[metrics.user_id] 
                            if m.timestamp > datetime.now(timezone.utc) - timedelta(minutes=1)]
            if len(recent_queries) > self.anomaly_thresholds['query_frequency']:
                anomaly = AnomalyDetection(
                    is_anomalous=True,
                    anomaly_score=len(recent_queries) / self.anomaly_thresholds['query_frequency'] * 100,
                    anomaly_type="HIGH_QUERY_FREQUENCY",
                    description=f"User {metrics.user_id} executed {len(recent_queries)} queries in 1 minute",
                    query_hash=metrics.query_hash,
                    timestamp=metrics.timestamp,
                    details={"query_count": len(recent_queries), "user_id": metrics.user_id}
                )
                anomalies.append(anomaly)
        
        # Unusual time access
        current_hour = metrics.timestamp.hour
        unusual_start, unusual_end = self.anomaly_thresholds['unusual_hours']
        if unusual_start <= current_hour or current_hour <= unusual_end:
            anomaly = AnomalyDetection(
                is_anomalous=True,
                anomaly_score=75.0,
                anomaly_type="UNUSUAL_HOURS_ACCESS",
                description=f"Database access during unusual hours ({current_hour}:00)",
                query_hash=metrics.query_hash,
                timestamp=metrics.timestamp,
                details={"access_hour": current_hour}
            )
            anomalies.append(anomaly)
        
        # Store anomalies
        for anomaly in anomalies:
            self._store_anomaly_detection(anomaly)

    def _create_security_event(self, threat_level: SecurityThreatLevel, event_type: str,
                             description: str, query_hash: str, query_text: str,
                             user_id: Optional[str], session_id: Optional[str],
                             source_ip: Optional[str], details: Dict[str, Any]) -> SecurityEvent:
        """Create a security event"""
        event_id = hashlib.sha256(f"{query_hash}-{event_type}-{time.time()}".encode()).hexdigest()[:16]
        
        return SecurityEvent(
            event_id=event_id,
            threat_level=threat_level,
            event_type=event_type,
            description=description,
            query_hash=query_hash,
            query_text=query_text,
            user_id=user_id,
            session_id=session_id,
            source_ip=source_ip,
            timestamp=datetime.now(timezone.utc),
            details=details
        )

    def _store_security_event(self, event: SecurityEvent):
        """Store security event in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO security_events 
                    (event_id, threat_level, event_type, description, query_hash,
                     query_text, user_id, session_id, source_ip, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.threat_level.value,
                    event.event_type,
                    event.description,
                    event.query_hash,
                    event.query_text,
                    event.user_id,
                    event.session_id,
                    event.source_ip,
                    event.timestamp.isoformat(),
                    json.dumps(event.details)
                ))
        except Exception as e:
            logger.error(f"Failed to store security event: {e}")

    def _store_anomaly_detection(self, anomaly: AnomalyDetection):
        """Store anomaly detection result in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO anomaly_detections 
                    (anomaly_score, anomaly_type, description, query_hash, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    anomaly.anomaly_score,
                    anomaly.anomaly_type,
                    anomaly.description,
                    anomaly.query_hash,
                    anomaly.timestamp.isoformat(),
                    json.dumps(anomaly.details)
                ))
        except Exception as e:
            logger.error(f"Failed to store anomaly detection: {e}")

    def log_connection_metrics(self, total: int, active: int, idle: int, 
                             checked_out: int, overflow: int = 0):
        """Log database connection pool metrics"""
        metrics = ConnectionMetrics(
            total_connections=total,
            active_connections=active,
            idle_connections=idle,
            checked_out_connections=checked_out,
            overflow_connections=overflow,
            timestamp=datetime.now(timezone.utc)
        )
        
        with self._lock:
            self.connection_metrics.append(metrics)
        
        # Store in database
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO connection_metrics 
                    (total_connections, active_connections, idle_connections,
                     checked_out_connections, overflow_connections, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    metrics.total_connections,
                    metrics.active_connections,
                    metrics.idle_connections,
                    metrics.checked_out_connections,
                    metrics.overflow_connections,
                    metrics.timestamp.isoformat()
                ))
        except Exception as e:
            logger.error(f"Failed to store connection metrics: {e}")

    def get_security_events(self, hours_back: int = 24, threat_level: Optional[SecurityThreatLevel] = None) -> List[Dict[str, Any]]:
        """Get recent security events"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                where_clause = "WHERE timestamp > datetime('now', '-{} hours')".format(hours_back)
                if threat_level:
                    where_clause += f" AND threat_level = '{threat_level.value}'"
                
                cursor.execute(f"""
                    SELECT event_id, threat_level, event_type, description, query_hash,
                           user_id, session_id, source_ip, timestamp, details, resolved
                    FROM security_events 
                    {where_clause}
                    ORDER BY timestamp DESC
                """)
                
                events = []
                for row in cursor.fetchall():
                    event_id, threat_level, event_type, description, query_hash, \
                    user_id, session_id, source_ip, timestamp, details, resolved = row
                    
                    events.append({
                        "event_id": event_id,
                        "threat_level": threat_level,
                        "event_type": event_type,
                        "description": description,
                        "query_hash": query_hash,
                        "user_id": user_id,
                        "session_id": session_id,
                        "source_ip": source_ip,
                        "timestamp": timestamp,
                        "details": json.loads(details),
                        "resolved": bool(resolved)
                    })
                
                return events
        except Exception as e:
            logger.error(f"Failed to get security events: {e}")
            return []

    def get_query_performance_stats(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get query performance statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Overall stats
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_queries,
                        AVG(execution_time) as avg_execution_time,
                        MAX(execution_time) as max_execution_time,
                        SUM(rows_affected) as total_rows_affected,
                        query_type,
                        COUNT(*) as type_count
                    FROM query_metrics 
                    WHERE timestamp > datetime('now', '-{} hours')
                    GROUP BY query_type
                """.format(hours_back))
                
                query_type_stats = []
                total_queries = 0
                overall_avg_time = 0
                overall_max_time = 0
                total_rows = 0
                
                for row in cursor.fetchall():
                    _, avg_time, max_time, rows, query_type, type_count = row
                    total_queries += type_count
                    overall_avg_time += avg_time * type_count
                    overall_max_time = max(overall_max_time, max_time)
                    total_rows += rows or 0
                    
                    query_type_stats.append({
                        "query_type": query_type,
                        "count": type_count,
                        "avg_execution_time": round(avg_time, 3),
                        "max_execution_time": round(max_time, 3),
                        "total_rows_affected": rows or 0
                    })
                
                overall_avg_time = overall_avg_time / total_queries if total_queries > 0 else 0
                
                # Slow queries
                cursor.execute("""
                    SELECT query_hash, query_text, execution_time, timestamp
                    FROM query_metrics
                    WHERE timestamp > datetime('now', '-{} hours')
                    AND execution_time > ?
                    ORDER BY execution_time DESC
                    LIMIT 10
                """.format(hours_back), (self.anomaly_thresholds['execution_time'],))
                
                slow_queries = []
                for row in cursor.fetchall():
                    query_hash, query_text, exec_time, timestamp = row
                    slow_queries.append({
                        "query_hash": query_hash,
                        "query_text": query_text[:200] + "..." if len(query_text) > 200 else query_text,
                        "execution_time": round(exec_time, 3),
                        "timestamp": timestamp
                    })
                
                return {
                    "total_queries": total_queries,
                    "avg_execution_time": round(overall_avg_time, 3),
                    "max_execution_time": round(overall_max_time, 3),
                    "total_rows_affected": total_rows,
                    "query_type_breakdown": query_type_stats,
                    "slow_queries": slow_queries,
                    "hours_analyzed": hours_back
                }
        except Exception as e:
            logger.error(f"Failed to get query performance stats: {e}")
            return {}

    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database monitoring statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Security events summary
                cursor.execute("""
                    SELECT threat_level, COUNT(*) 
                    FROM security_events 
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY threat_level
                """)
                security_events_summary = dict(cursor.fetchall())
                
                # Anomaly detections summary
                cursor.execute("""
                    SELECT anomaly_type, COUNT(*), AVG(anomaly_score)
                    FROM anomaly_detections
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY anomaly_type
                """)
                anomaly_summary = {}
                for anomaly_type, count, avg_score in cursor.fetchall():
                    anomaly_summary[anomaly_type] = {
                        "count": count,
                        "avg_score": round(avg_score, 2)
                    }
                
                # Query patterns
                cursor.execute("""
                    SELECT COUNT(DISTINCT pattern_hash), 
                           AVG(frequency),
                           COUNT(CASE WHEN is_suspicious = 1 THEN 1 END)
                    FROM query_patterns
                """)
                pattern_stats = cursor.fetchone()
                
                # Connection metrics (latest)
                cursor.execute("""
                    SELECT total_connections, active_connections, idle_connections,
                           checked_out_connections, overflow_connections
                    FROM connection_metrics
                    ORDER BY timestamp DESC LIMIT 1
                """)
                connection_stats = cursor.fetchone()
                
                return {
                    "database_monitoring_enabled": True,
                    "monitoring_level": self.monitoring_level,
                    "monitoring_active": self.monitoring_active,
                    "security_events_24h": security_events_summary,
                    "total_security_events_24h": sum(security_events_summary.values()),
                    "anomaly_detections_24h": anomaly_summary,
                    "query_patterns": {
                        "unique_patterns": pattern_stats[0] if pattern_stats else 0,
                        "avg_frequency": round(pattern_stats[1], 2) if pattern_stats and pattern_stats[1] else 0,
                        "suspicious_patterns": pattern_stats[2] if pattern_stats else 0
                    },
                    "current_connections": {
                        "total": connection_stats[0] if connection_stats else 0,
                        "active": connection_stats[1] if connection_stats else 0,
                        "idle": connection_stats[2] if connection_stats else 0,
                        "checked_out": connection_stats[3] if connection_stats else 0,
                        "overflow": connection_stats[4] if connection_stats else 0
                    } if connection_stats else None,
                    "features": {
                        "query_monitoring": True,
                        "security_event_detection": True,
                        "anomaly_detection": True,
                        "connection_monitoring": True,
                        "performance_analysis": True,
                        "sql_injection_detection": True
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get monitoring statistics: {e}")
            return {"database_monitoring_enabled": False, "error": str(e)}

    def start_monitoring(self):
        """Start database activity monitoring thread"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Database activity monitoring started")

    def stop_monitoring(self):
        """Stop database activity monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        logger.info("Database activity monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Cleanup old data
                self._cleanup_old_data()
                
                # Update query patterns
                self._update_query_patterns()
                
                # Check for new anomalies
                self._periodic_anomaly_check()
                
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Database monitoring error: {e}")
                time.sleep(30)  # Wait before retrying

    def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Clean up old query metrics (keep 7 days)
                conn.execute("""
                    DELETE FROM query_metrics 
                    WHERE timestamp < datetime('now', '-7 days')
                """)
                
                # Clean up old security events (keep 30 days)
                conn.execute("""
                    DELETE FROM security_events 
                    WHERE timestamp < datetime('now', '-30 days') AND resolved = 1
                """)
                
                # Clean up old connection metrics (keep 7 days)
                conn.execute("""
                    DELETE FROM connection_metrics 
                    WHERE timestamp < datetime('now', '-7 days')
                """)
                
                # Clean up old anomaly detections (keep 7 days)
                conn.execute("""
                    DELETE FROM anomaly_detections 
                    WHERE timestamp < datetime('now', '-7 days')
                """)
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")

    def _update_query_patterns(self):
        """Update query pattern analysis"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update pattern statistics
                cursor.execute("""
                    SELECT query_hash, COUNT(*) as frequency, AVG(execution_time) as avg_time
                    FROM query_metrics
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY query_hash
                """)
                
                for query_hash, frequency, avg_time in cursor.fetchall():
                    # Check if pattern is suspicious
                    is_suspicious = 0
                    if frequency > self.anomaly_thresholds['query_frequency'] * 60:  # Per hour
                        is_suspicious = 1
                    
                    # Get normalized query text
                    cursor.execute("""
                        SELECT query_text FROM query_metrics 
                        WHERE query_hash = ? LIMIT 1
                    """, (query_hash,))
                    query_text_result = cursor.fetchone()
                    query_text = query_text_result[0] if query_text_result else ""
                    normalized_query = self._normalize_query(query_text)
                    
                    # Update or insert pattern
                    conn.execute("""
                        INSERT OR REPLACE INTO query_patterns
                        (pattern_hash, pattern_type, query_template, frequency, 
                         avg_execution_time, last_seen, is_suspicious)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                    """, (query_hash, "SQL", normalized_query, frequency, avg_time, is_suspicious))
        except Exception as e:
            logger.error(f"Failed to update query patterns: {e}")

    def _periodic_anomaly_check(self):
        """Perform periodic anomaly checks"""
        try:
            # Check for unusual activity patterns
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check for spike in failed queries
                cursor.execute("""
                    SELECT COUNT(*) FROM query_metrics 
                    WHERE timestamp > datetime('now', '-5 minutes')
                    AND execution_time > ?
                """, (self.anomaly_thresholds['execution_time'] * 2,))
                
                failed_query_count = cursor.fetchone()[0]
                if failed_query_count > self.anomaly_thresholds['failed_queries']:
                    logger.warning(f"High number of slow/failed queries detected: {failed_query_count}")
        except Exception as e:
            logger.error(f"Failed periodic anomaly check: {e}")

# Global database activity monitor instance
_database_activity_monitor = None

def init_database_monitoring(monitoring_level: str = "standard", db_path: str = "database_monitoring.db") -> DatabaseActivityMonitor:
    """Initialize global database activity monitor"""
    global _database_activity_monitor
    _database_activity_monitor = DatabaseActivityMonitor(db_path, monitoring_level)
    return _database_activity_monitor

def get_database_monitor() -> Optional[DatabaseActivityMonitor]:
    """Get global database activity monitor"""
    return _database_activity_monitor

def log_query_execution(query_text: str, execution_time: float, rows_affected: int = 0,
                       user_id: Optional[str] = None, session_id: Optional[str] = None,
                       source_ip: Optional[str] = None, parameters: Dict[str, Any] = None) -> Optional[str]:
    """Global function to log database query execution"""
    if _database_activity_monitor:
        return _database_activity_monitor.log_query_execution(
            query_text, execution_time, rows_affected, user_id, session_id, source_ip, parameters
        )
    return None

def log_connection_metrics(total: int, active: int, idle: int, checked_out: int, overflow: int = 0):
    """Global function to log connection metrics"""
    if _database_activity_monitor:
        _database_activity_monitor.log_connection_metrics(total, active, idle, checked_out, overflow)

def get_database_monitoring_stats() -> Dict[str, Any]:
    """Global function to get database monitoring statistics"""
    if _database_activity_monitor:
        return _database_activity_monitor.get_monitoring_statistics()
    return {"database_monitoring_enabled": False}

def get_security_events(hours_back: int = 24, threat_level: Optional[str] = None) -> List[Dict[str, Any]]:
    """Global function to get security events"""
    if _database_activity_monitor:
        threat_level_enum = SecurityThreatLevel(threat_level) if threat_level else None
        return _database_activity_monitor.get_security_events(hours_back, threat_level_enum)
    return []

def get_query_performance_stats(hours_back: int = 24) -> Dict[str, Any]:
    """Global function to get query performance statistics"""
    if _database_activity_monitor:
        return _database_activity_monitor.get_query_performance_stats(hours_back)
    return {}

if __name__ == "__main__":
    # Example usage
    monitor = init_database_monitoring("high")
    
    # Simulate some database activity
    monitor.log_query_execution(
        "SELECT * FROM users WHERE email = ?",
        0.05, 1, "user123", "sess456", "192.168.1.100", {"email": "test@example.com"}
    )
    
    # Get statistics
    stats = monitor.get_monitoring_statistics()
    print(f"Database monitoring stats: {stats}")
    
    # Get security events
    events = monitor.get_security_events()
    print(f"Security events: {len(events)}")