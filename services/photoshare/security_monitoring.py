#!/usr/bin/env python3
"""
Security Monitoring System
==========================

Comprehensive security monitoring with real-time threat detection,
incident logging, alerting, and security event correlation.
"""

import asyncio
import logging
import time
import json
import hashlib
import smtplib
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import queue
from pathlib import Path


logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Security alert severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH" 
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ThreatType(Enum):
    """Types of security threats."""
    AUTHENTICATION_FAILURE = "authentication_failure"
    BRUTE_FORCE_ATTACK = "brute_force_attack"
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    MALICIOUS_FILE_UPLOAD = "malicious_file_upload"
    SUSPICIOUS_USER_AGENT = "suspicious_user_agent"
    RATE_LIMIT_VIOLATION = "rate_limit_violation"
    HONEYPOT_ACCESS = "honeypot_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"


@dataclass
class SecurityIncident:
    """Security incident data structure."""
    incident_id: str
    timestamp: float
    severity: AlertSeverity
    threat_type: ThreatType
    source_ip: str
    user_id: Optional[str]
    endpoint: str
    method: str
    description: str
    details: Dict[str, Any]
    user_agent: str
    resolved: bool = False
    resolution_notes: str = ""


@dataclass
class SecurityMetrics:
    """Security metrics tracking."""
    timestamp: float
    total_requests: int
    blocked_requests: int
    unique_attackers: int
    incidents_by_severity: Dict[str, int]
    incidents_by_type: Dict[str, int]
    top_attacked_endpoints: Dict[str, int]
    geographic_distribution: Dict[str, int]


class SecurityMonitor:
    """Comprehensive security monitoring system."""
    
    def __init__(self):
        self.incidents = deque(maxlen=10000)  # Keep last 10K incidents
        self.active_threats = {}  # IP -> threat info
        self.blocked_ips = set()  # Currently blocked IPs
        self.suspicious_patterns = defaultdict(list)  # Pattern -> incidents
        
        # Real-time metrics
        self.metrics_history = deque(maxlen=288)  # 24 hours at 5-min intervals
        self.current_metrics = SecurityMetrics(
            timestamp=time.time(),
            total_requests=0,
            blocked_requests=0,
            unique_attackers=0,
            incidents_by_severity=defaultdict(int),
            incidents_by_type=defaultdict(int),
            top_attacked_endpoints=defaultdict(int),
            geographic_distribution=defaultdict(int)
        )
        
        # Alert thresholds
        self.alert_thresholds = {
            "failed_logins_per_hour": 10,
            "blocked_requests_per_hour": 50,
            "unique_attackers_per_hour": 5,
            "critical_incidents_per_hour": 1,
            "high_incidents_per_hour": 5
        }
        
        # Notification settings
        self.notification_config = {
            "email_enabled": os.getenv("SECURITY_EMAIL_ENABLED", "false").lower() == "true",
            "email_smtp_host": os.getenv("SMTP_HOST", "localhost"),
            "email_smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "email_username": os.getenv("SMTP_USERNAME", ""),
            "email_password": os.getenv("SMTP_PASSWORD", ""),
            "email_from": os.getenv("SECURITY_EMAIL_FROM", "security@photoshare.local"),
            "email_to": os.getenv("SECURITY_EMAIL_TO", "admin@photoshare.local").split(","),
            "webhook_url": os.getenv("SECURITY_WEBHOOK_URL", ""),
            "slack_webhook": os.getenv("SLACK_WEBHOOK_URL", "")
        }
        
        # Behavioral analysis
        self.user_baselines = {}  # user_id -> behavioral profile
        self.ip_reputation = {}  # IP -> reputation score
        
        # Background monitoring thread
        self.monitoring_active = True
        self.alert_queue = queue.Queue()
        self.monitoring_thread = None
        
        # Auto-correlation patterns
        self.correlation_rules = [
            self._detect_coordinated_attack,
            self._detect_privilege_escalation_attempt,
            self._detect_data_exfiltration,
            self._detect_anomalous_behavior
        ]
        
        # Initialize monitoring thread in a delayed, safe manner
        self._thread_start_attempted = False
        self._thread_initialized = False
        
        # Disable automatic thread startup to avoid threading errors
        # Thread will be started on first security event if needed
        logger.debug("Security monitoring initialized without background thread (will start on demand)")
        
        logger.info("Security monitoring system initialized")
    
    def _start_monitoring_thread(self):
        """Start the background monitoring thread safely."""
        if self._thread_initialized:
            return  # Already started
            
        try:
            # Ensure the monitoring worker method is available and callable
            if not hasattr(self, '_monitoring_worker') or not callable(getattr(self, '_monitoring_worker', None)):
                logger.warning("Monitoring worker method not available or not callable")
                return
                
            # Start monitoring thread directly with the method
            self.monitoring_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
            self.monitoring_thread.start()
            self._thread_initialized = True
            logger.info("Security monitoring thread started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start security monitoring thread: {e}")
            self.monitoring_active = False
    
    def log_incident(self, 
                    severity: AlertSeverity,
                    threat_type: ThreatType,
                    source_ip: str,
                    endpoint: str,
                    method: str,
                    description: str,
                    details: Dict[str, Any],
                    user_agent: str = "",
                    user_id: Optional[str] = None) -> str:
        """Log a security incident."""
        
        # Start monitoring thread on first security event if not already started
        if not self._thread_start_attempted:
            self._thread_start_attempted = True
            try:
                self._start_monitoring_thread()
            except Exception as e:
                logger.debug(f"Could not start monitoring thread: {e}")
        
        incident_id = hashlib.md5(
            f"{time.time()}{source_ip}{threat_type.value}".encode()
        ).hexdigest()[:12]
        
        incident = SecurityIncident(
            incident_id=incident_id,
            timestamp=time.time(),
            severity=severity,
            threat_type=threat_type,
            source_ip=source_ip,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            description=description,
            details=details,
            user_agent=user_agent
        )
        
        # Store incident
        self.incidents.append(incident)
        
        # Update metrics
        self.current_metrics.incidents_by_severity[severity.value] += 1
        self.current_metrics.incidents_by_type[threat_type.value] += 1
        self.current_metrics.top_attacked_endpoints[endpoint] += 1
        
        # Track active threats
        self.active_threats[source_ip] = {
            "last_activity": time.time(),
            "threat_count": self.active_threats.get(source_ip, {}).get("threat_count", 0) + 1,
            "threat_types": set()
        }
        self.active_threats[source_ip]["threat_types"].add(threat_type.value)
        
        # Add to suspicious patterns for correlation
        pattern_key = f"{threat_type.value}:{endpoint}"
        self.suspicious_patterns[pattern_key].append(incident)
        
        # Queue alert if needed
        if severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
            self.alert_queue.put(incident)
        
        # Run correlation analysis
        self._analyze_correlations(incident)
        
        logger.warning(
            f"Security incident logged: {incident_id} - {severity.value} - "
            f"{threat_type.value} from {source_ip} on {endpoint}"
        )
        
        return incident_id
    
    def _analyze_correlations(self, incident: SecurityIncident):
        """Analyze incident correlations for advanced threats."""
        for rule in self.correlation_rules:
            try:
                rule(incident)
            except Exception as e:
                logger.error(f"Correlation rule error: {e}")
    
    def _detect_coordinated_attack(self, incident: SecurityIncident):
        """Detect coordinated attacks from multiple IPs."""
        recent_time = time.time() - 300  # Last 5 minutes
        
        # Get recent incidents of same type
        same_type_incidents = [
            i for i in self.incidents 
            if (i.threat_type == incident.threat_type and 
                i.timestamp > recent_time and
                i.endpoint == incident.endpoint)
        ]
        
        # Check for multiple unique IPs
        unique_ips = set(i.source_ip for i in same_type_incidents)
        
        if len(unique_ips) >= 3:  # 3+ IPs attacking same endpoint
            self.log_incident(
                AlertSeverity.CRITICAL,
                ThreatType.ANOMALOUS_BEHAVIOR,
                "multiple",
                incident.endpoint,
                "COORDINATED",
                f"Coordinated attack detected: {len(unique_ips)} IPs targeting {incident.endpoint}",
                {
                    "attack_type": incident.threat_type.value,
                    "attacking_ips": list(unique_ips),
                    "incident_count": len(same_type_incidents)
                }
            )
    
    def _detect_privilege_escalation_attempt(self, incident: SecurityIncident):
        """Detect privilege escalation attempts."""
        if not incident.user_id:
            return
        
        # Look for admin endpoint access after authentication issues
        recent_time = time.time() - 1800  # Last 30 minutes
        
        user_incidents = [
            i for i in self.incidents
            if (i.user_id == incident.user_id and 
                i.timestamp > recent_time)
        ]
        
        # Check pattern: auth failure -> admin access attempts
        auth_failures = [i for i in user_incidents if i.threat_type == ThreatType.AUTHENTICATION_FAILURE]
        admin_attempts = [i for i in user_incidents if "admin" in i.endpoint.lower()]
        
        if len(auth_failures) > 2 and len(admin_attempts) > 0:
            self.log_incident(
                AlertSeverity.HIGH,
                ThreatType.PRIVILEGE_ESCALATION,
                incident.source_ip,
                incident.endpoint,
                incident.method,
                f"Privilege escalation attempt: User {incident.user_id} attempting admin access after auth failures",
                {
                    "user_id": incident.user_id,
                    "auth_failures": len(auth_failures),
                    "admin_attempts": len(admin_attempts)
                }
            )
    
    def _detect_data_exfiltration(self, incident: SecurityIncident):
        """Detect data exfiltration patterns."""
        if "download" not in incident.endpoint and "export" not in incident.endpoint:
            return
        
        recent_time = time.time() - 3600  # Last hour
        
        # Check for excessive download activity
        download_incidents = [
            i for i in self.incidents
            if (i.source_ip == incident.source_ip and
                i.timestamp > recent_time and
                ("download" in i.endpoint or "export" in i.endpoint))
        ]
        
        if len(download_incidents) > 20:  # More than 20 downloads per hour
            self.log_incident(
                AlertSeverity.HIGH,
                ThreatType.DATA_EXFILTRATION,
                incident.source_ip,
                incident.endpoint,
                incident.method,
                f"Potential data exfiltration: {len(download_incidents)} downloads from {incident.source_ip}",
                {
                    "download_count": len(download_incidents),
                    "endpoints": list(set(i.endpoint for i in download_incidents))
                }
            )
    
    def _detect_anomalous_behavior(self, incident: SecurityIncident):
        """Detect anomalous behavioral patterns."""
        # Check user behavioral baselines
        if incident.user_id:
            baseline = self.user_baselines.get(incident.user_id, {})
            
            # Example: User accessing system at unusual hours
            current_hour = datetime.now().hour
            usual_hours = baseline.get("usual_hours", set())
            
            if usual_hours and current_hour not in usual_hours:
                if len(usual_hours) > 5:  # Only if we have enough baseline data
                    self.log_incident(
                        AlertSeverity.MEDIUM,
                        ThreatType.ANOMALOUS_BEHAVIOR,
                        incident.source_ip,
                        incident.endpoint,
                        incident.method,
                        f"User {incident.user_id} accessing system at unusual hour: {current_hour}:00",
                        {
                            "user_id": incident.user_id,
                            "current_hour": current_hour,
                            "usual_hours": list(usual_hours)
                        }
                    )
    
    def update_user_baseline(self, user_id: str, activity_data: Dict):
        """Update user behavioral baseline."""
        if user_id not in self.user_baselines:
            self.user_baselines[user_id] = {
                "usual_hours": set(),
                "common_endpoints": defaultdict(int),
                "avg_session_duration": 0,
                "typical_user_agents": set()
            }
        
        baseline = self.user_baselines[user_id]
        
        # Update usual hours
        current_hour = datetime.now().hour
        baseline["usual_hours"].add(current_hour)
        
        # Update common endpoints
        if "endpoint" in activity_data:
            baseline["common_endpoints"][activity_data["endpoint"]] += 1
        
        # Update user agents
        if "user_agent" in activity_data:
            baseline["typical_user_agents"].add(activity_data["user_agent"][:50])  # First 50 chars
    
    def _monitoring_worker(self):
        """Background monitoring worker thread."""
        while self.monitoring_active:
            try:
                # Process alert queue
                while not self.alert_queue.empty():
                    try:
                        incident = self.alert_queue.get_nowait()
                        self._send_alert(incident)
                    except queue.Empty:
                        break
                    except Exception as e:
                        logger.error(f"Alert processing error: {e}")
                
                # Check thresholds and generate alerts
                self._check_alert_thresholds()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Update metrics
                self._update_metrics()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Monitoring worker error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _send_alert(self, incident: SecurityIncident):
        """Send security alert notifications."""
        try:
            # Send email alert
            if self.notification_config["email_enabled"]:
                self._send_email_alert(incident)
            
            # Send webhook alert
            if self.notification_config["webhook_url"]:
                self._send_webhook_alert(incident)
            
            # Log alert
            logger.critical(f"SECURITY ALERT: {incident.severity.value} - {incident.description}")
            
        except Exception as e:
            logger.error(f"Alert sending failed: {e}")
    
    def _send_email_alert(self, incident: SecurityIncident):
        """Send email security alert."""
        if not self.notification_config["email_to"]:
            return
        
        subject = f"PhotoShare Security Alert - {incident.severity.value} - {incident.threat_type.value}"
        
        body = f"""
PHOTOSHARE SECURITY ALERT
========================

Incident ID: {incident.incident_id}
Severity: {incident.severity.value}
Threat Type: {incident.threat_type.value}
Timestamp: {datetime.fromtimestamp(incident.timestamp, tz=timezone.utc)}

Source IP: {incident.source_ip}
User ID: {incident.user_id or 'N/A'}
Endpoint: {incident.endpoint}
Method: {incident.method}
User Agent: {incident.user_agent}

Description: {incident.description}

Details:
{json.dumps(incident.details, indent=2)}

--
PhotoShare Security Monitoring System
        """
        
        msg = MIMEMultipart()
        msg['From'] = self.notification_config["email_from"]
        msg['To'] = ", ".join(self.notification_config["email_to"])
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            server = smtplib.SMTP(
                self.notification_config["email_smtp_host"], 
                self.notification_config["email_smtp_port"]
            )
            server.starttls()
            
            if self.notification_config["email_username"]:
                server.login(
                    self.notification_config["email_username"],
                    self.notification_config["email_password"]
                )
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Security alert email sent for incident {incident.incident_id}")
            
        except Exception as e:
            logger.error(f"Email alert failed: {e}")
    
    def _send_webhook_alert(self, incident: SecurityIncident):
        """Send webhook security alert."""
        # Implementation would depend on webhook service
        # This is a placeholder for integration with external systems
        pass
    
    def _check_alert_thresholds(self):
        """Check if alert thresholds are exceeded."""
        current_time = time.time()
        hour_ago = current_time - 3600
        
        # Get incidents from last hour
        recent_incidents = [
            i for i in self.incidents 
            if i.timestamp > hour_ago
        ]
        
        # Check thresholds
        failed_logins = len([
            i for i in recent_incidents 
            if i.threat_type == ThreatType.AUTHENTICATION_FAILURE
        ])
        
        critical_incidents = len([
            i for i in recent_incidents 
            if i.severity == AlertSeverity.CRITICAL
        ])
        
        high_incidents = len([
            i for i in recent_incidents 
            if i.severity == AlertSeverity.HIGH
        ])
        
        unique_attackers = len(set(i.source_ip for i in recent_incidents))
        
        # Generate threshold alerts
        if failed_logins > self.alert_thresholds["failed_logins_per_hour"]:
            self._generate_threshold_alert(
                "Excessive Authentication Failures",
                f"{failed_logins} failed logins in the last hour"
            )
        
        if critical_incidents > self.alert_thresholds["critical_incidents_per_hour"]:
            self._generate_threshold_alert(
                "Critical Incident Threshold Exceeded",
                f"{critical_incidents} critical incidents in the last hour"
            )
        
        if unique_attackers > self.alert_thresholds["unique_attackers_per_hour"]:
            self._generate_threshold_alert(
                "Multiple Unique Attackers",
                f"{unique_attackers} unique attackers detected in the last hour"
            )
    
    def _generate_threshold_alert(self, title: str, description: str):
        """Generate a threshold-based alert."""
        incident_id = self.log_incident(
            AlertSeverity.HIGH,
            ThreatType.ANOMALOUS_BEHAVIOR,
            "system",
            "/security/monitoring",
            "THRESHOLD",
            f"Threshold Alert: {title} - {description}",
            {"threshold_type": title}
        )
        
        logger.warning(f"Threshold alert generated: {incident_id} - {title}")
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        current_time = time.time()
        week_ago = current_time - (7 * 24 * 3600)  # 1 week
        
        # Clean up old active threats
        expired_threats = [
            ip for ip, data in self.active_threats.items()
            if data["last_activity"] < week_ago
        ]
        
        for ip in expired_threats:
            del self.active_threats[ip]
        
        # Clean up old suspicious patterns
        for pattern, incidents in list(self.suspicious_patterns.items()):
            self.suspicious_patterns[pattern] = [
                i for i in incidents if i.timestamp > week_ago
            ]
            
            if not self.suspicious_patterns[pattern]:
                del self.suspicious_patterns[pattern]
    
    def _update_metrics(self):
        """Update security metrics."""
        current_time = time.time()
        
        # Save current metrics to history
        self.current_metrics.timestamp = current_time
        self.current_metrics.unique_attackers = len(self.active_threats)
        
        # Add to metrics history
        self.metrics_history.append(SecurityMetrics(**asdict(self.current_metrics)))
        
        # Reset counters for next interval
        self.current_metrics = SecurityMetrics(
            timestamp=current_time,
            total_requests=0,
            blocked_requests=0,
            unique_attackers=len(self.active_threats),
            incidents_by_severity=defaultdict(int),
            incidents_by_type=defaultdict(int),
            top_attacked_endpoints=defaultdict(int),
            geographic_distribution=defaultdict(int)
        )
    
    def get_security_dashboard(self) -> Dict:
        """Get security dashboard data."""
        current_time = time.time()
        hour_ago = current_time - 3600
        day_ago = current_time - (24 * 3600)
        
        # Recent incidents
        recent_incidents = [i for i in self.incidents if i.timestamp > hour_ago]
        daily_incidents = [i for i in self.incidents if i.timestamp > day_ago]
        
        # Top threats
        threat_counts = defaultdict(int)
        for incident in daily_incidents:
            threat_counts[incident.threat_type.value] += 1
        
        # Top attacking IPs
        ip_counts = defaultdict(int)
        for incident in daily_incidents:
            ip_counts[incident.source_ip] += 1
        
        return {
            "current_status": {
                "active_threats": len(self.active_threats),
                "blocked_ips": len(self.blocked_ips),
                "incidents_last_hour": len(recent_incidents),
                "incidents_last_24h": len(daily_incidents)
            },
            "recent_incidents": [
                {
                    "id": i.incident_id,
                    "timestamp": i.timestamp,
                    "severity": i.severity.value,
                    "type": i.threat_type.value,
                    "source_ip": i.source_ip,
                    "endpoint": i.endpoint,
                    "description": i.description
                }
                for i in sorted(recent_incidents, key=lambda x: x.timestamp, reverse=True)[:20]
            ],
            "threat_statistics": {
                "top_threats_24h": dict(sorted(threat_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                "top_attacking_ips": dict(sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                "severity_distribution": {
                    severity.value: len([i for i in daily_incidents if i.severity == severity])
                    for severity in AlertSeverity
                }
            },
            "metrics_history": [
                {
                    "timestamp": m.timestamp,
                    "total_requests": m.total_requests,
                    "blocked_requests": m.blocked_requests,
                    "unique_attackers": m.unique_attackers
                }
                for m in list(self.metrics_history)[-48:]  # Last 48 data points (4 hours)
            ]
        }
    
    def get_incident_details(self, incident_id: str) -> Optional[Dict]:
        """Get detailed incident information."""
        for incident in self.incidents:
            if incident.incident_id == incident_id:
                return {
                    "incident_id": incident.incident_id,
                    "timestamp": incident.timestamp,
                    "severity": incident.severity.value,
                    "threat_type": incident.threat_type.value,
                    "source_ip": incident.source_ip,
                    "user_id": incident.user_id,
                    "endpoint": incident.endpoint,
                    "method": incident.method,
                    "description": incident.description,
                    "details": incident.details,
                    "user_agent": incident.user_agent,
                    "resolved": incident.resolved,
                    "resolution_notes": incident.resolution_notes
                }
        return None
    
    def resolve_incident(self, incident_id: str, resolution_notes: str) -> bool:
        """Mark an incident as resolved."""
        for incident in self.incidents:
            if incident.incident_id == incident_id:
                incident.resolved = True
                incident.resolution_notes = resolution_notes
                logger.info(f"Incident {incident_id} marked as resolved")
                return True
        return False
    
    def update_request_metrics(self, blocked: bool = False):
        """Update request metrics."""
        self.current_metrics.total_requests += 1
        if blocked:
            self.current_metrics.blocked_requests += 1
    
    def shutdown(self):
        """Shutdown monitoring system."""
        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        logger.info("Security monitoring system shutdown")


# Global security monitor instance
security_monitor = SecurityMonitor()


def log_security_event(severity: str, threat_type: str, source_ip: str, 
                      endpoint: str, method: str, description: str,
                      details: Dict[str, Any], user_agent: str = "", 
                      user_id: Optional[str] = None) -> str:
    """Helper function to log security events."""
    return security_monitor.log_incident(
        AlertSeverity(severity),
        ThreatType(threat_type),
        source_ip,
        endpoint,
        method,
        description,
        details,
        user_agent,
        user_id
    )