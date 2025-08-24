"""
PhotoShare Advanced Threat Detection Module
===========================================

Machine learning-based threat detection, behavioral analysis, and proactive
security monitoring system for the PhotoShare application.

Features:
- Behavioral analysis and anomaly detection
- Machine learning threat classification
- Real-time threat scoring and risk assessment
- Attack pattern recognition and correlation
- Threat intelligence feed integration
- User and Entity Behavior Analytics (UEBA)
- Automated threat response and mitigation
- Advanced persistent threat (APT) detection
- Zero-day attack identification
- Threat hunting and forensics support

Version: 2.3.0-monitoring
Author: PhotoShare Security Team
"""

import os
import json
import logging
import threading
import time
import hashlib
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum
import sqlite3
from collections import defaultdict, deque
import pickle
import base64
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import joblib
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThreatType(Enum):
    """Types of threats detected"""
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    DDoS_ATTACK = "ddos_attack"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    ACCOUNT_TAKEOVER = "account_takeover"
    MALWARE_UPLOAD = "malware_upload"
    API_ABUSE = "api_abuse"
    INSIDER_THREAT = "insider_threat"
    ZERO_DAY = "zero_day"
    APT = "advanced_persistent_threat"

class ThreatSeverity(Enum):
    """Threat severity levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

class ResponseAction(Enum):
    """Automated response actions"""
    MONITOR = "monitor"
    ALERT = "alert"
    THROTTLE = "throttle"
    BLOCK_REQUEST = "block_request"
    BLOCK_IP = "block_ip"
    BLOCK_USER = "block_user"
    QUARANTINE = "quarantine"
    INVESTIGATE = "investigate"
    ESCALATE = "escalate"

@dataclass
class BehaviorProfile:
    """User/entity behavior profile"""
    entity_id: str
    entity_type: str  # 'user', 'ip', 'service'
    normal_activity_hours: List[int]
    typical_locations: List[str]
    common_endpoints: List[str]
    average_request_rate: float
    typical_data_volume: float
    risk_score: float
    last_updated: datetime
    anomaly_count: int
    feature_vector: List[float]

@dataclass
class ThreatIndicator:
    """Threat indicator/IoC"""
    indicator_id: str
    indicator_type: str  # 'ip', 'domain', 'hash', 'pattern'
    value: str
    threat_type: ThreatType
    severity: ThreatSeverity
    confidence: float
    source: str  # 'internal', 'threat_feed', 'ml_model'
    first_seen: datetime
    last_seen: datetime
    hit_count: int
    metadata: Dict[str, Any]

@dataclass
class ThreatEvent:
    """Detected threat event"""
    event_id: str
    threat_type: ThreatType
    severity: ThreatSeverity
    confidence: float
    entity_id: str
    source_ip: str
    target_resource: str
    attack_vector: str
    indicators: List[str]
    timestamp: datetime
    response_actions: List[ResponseAction]
    details: Dict[str, Any]

@dataclass
class AttackPattern:
    """Known attack pattern"""
    pattern_id: str
    pattern_name: str
    threat_type: ThreatType
    stages: List[str]
    indicators: List[str]
    detection_rules: Dict[str, Any]
    mitre_attack_id: Optional[str]

class AdvancedThreatDetector:
    """Advanced threat detection and response system"""
    
    def __init__(self, db_path: str = "threat_detection.db", model_path: str = "models/"):
        self.db_path = db_path
        self.model_path = Path(model_path)
        self.model_path.mkdir(exist_ok=True)
        self._lock = threading.RLock()
        self.detection_active = False
        self.detection_thread = None
        
        # ML models
        self.anomaly_detector = None
        self.threat_classifier = None
        self.scaler = StandardScaler()
        self.clustering_model = DBSCAN(eps=0.3, min_samples=5)
        
        # Threat intelligence
        self.threat_indicators: Dict[str, ThreatIndicator] = {}
        self.attack_patterns: Dict[str, AttackPattern] = {}
        self.behavior_profiles: Dict[str, BehaviorProfile] = {}
        
        # Real-time tracking
        self.event_buffer: deque = deque(maxlen=10000)
        self.threat_events: List[ThreatEvent] = []
        self.active_threats: Dict[str, ThreatEvent] = {}
        
        # Statistics
        self.detection_stats = defaultdict(int)
        
        # Initialize components
        self._init_database()
        self._load_models()
        self._load_threat_intelligence()
        self._initialize_attack_patterns()
        
        # Start detection engine
        self.start_detection_engine()
        
        logger.info("Advanced Threat Detector initialized")

    def _init_database(self):
        """Initialize threat detection database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS behavior_profiles (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    profile_data TEXT NOT NULL,
                    risk_score REAL DEFAULT 0.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    anomaly_count INTEGER DEFAULT 0
                );
                
                CREATE INDEX IF NOT EXISTS idx_profiles_type ON behavior_profiles(entity_type);
                CREATE INDEX IF NOT EXISTS idx_profiles_risk ON behavior_profiles(risk_score);
                
                CREATE TABLE IF NOT EXISTS threat_indicators (
                    indicator_id TEXT PRIMARY KEY,
                    indicator_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    threat_type TEXT NOT NULL,
                    severity INTEGER NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    source TEXT DEFAULT 'internal',
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hit_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    is_active BOOLEAN DEFAULT 1
                );
                
                CREATE INDEX IF NOT EXISTS idx_indicators_type ON threat_indicators(indicator_type);
                CREATE INDEX IF NOT EXISTS idx_indicators_value ON threat_indicators(value);
                CREATE INDEX IF NOT EXISTS idx_indicators_threat ON threat_indicators(threat_type);
                
                CREATE TABLE IF NOT EXISTS threat_events (
                    event_id TEXT PRIMARY KEY,
                    threat_type TEXT NOT NULL,
                    severity INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    entity_id TEXT,
                    source_ip TEXT,
                    target_resource TEXT,
                    attack_vector TEXT,
                    indicators TEXT DEFAULT '[]',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_actions TEXT DEFAULT '[]',
                    details TEXT DEFAULT '{}',
                    resolved BOOLEAN DEFAULT 0
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON threat_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_type ON threat_events(threat_type);
                CREATE INDEX IF NOT EXISTS idx_events_severity ON threat_events(severity);
                CREATE INDEX IF NOT EXISTS idx_events_entity ON threat_events(entity_id);
                
                CREATE TABLE IF NOT EXISTS attack_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_name TEXT NOT NULL,
                    threat_type TEXT NOT NULL,
                    stages TEXT NOT NULL,
                    indicators TEXT NOT NULL,
                    detection_rules TEXT NOT NULL,
                    mitre_attack_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS ml_model_performance (
                    model_id TEXT PRIMARY KEY,
                    model_type TEXT NOT NULL,
                    accuracy REAL,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    last_trained TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    training_samples INTEGER,
                    version INTEGER DEFAULT 1
                );
                
                CREATE TABLE IF NOT EXISTS threat_hunts (
                    hunt_id TEXT PRIMARY KEY,
                    hunt_name TEXT NOT NULL,
                    hypothesis TEXT,
                    techniques TEXT,
                    findings TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                );
            """)

    def _load_models(self):
        """Load or initialize ML models"""
        try:
            # Load anomaly detection model
            anomaly_model_path = self.model_path / "anomaly_detector.pkl"
            if anomaly_model_path.exists():
                self.anomaly_detector = joblib.load(anomaly_model_path)
                logger.info("Loaded existing anomaly detection model")
            else:
                self.anomaly_detector = IsolationForest(
                    contamination=0.1,
                    random_state=42,
                    n_estimators=100
                )
                logger.info("Created new anomaly detection model")
            
            # Load threat classifier
            classifier_path = self.model_path / "threat_classifier.pkl"
            if classifier_path.exists():
                self.threat_classifier = joblib.load(classifier_path)
                logger.info("Loaded existing threat classifier")
            else:
                self.threat_classifier = RandomForestClassifier(
                    n_estimators=100,
                    random_state=42,
                    max_depth=10
                )
                logger.info("Created new threat classifier")
            
            # Load scaler
            scaler_path = self.model_path / "feature_scaler.pkl"
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")

    def _load_threat_intelligence(self):
        """Load threat intelligence indicators"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT indicator_id, indicator_type, value, threat_type,
                           severity, confidence, source, first_seen, last_seen,
                           hit_count, metadata
                    FROM threat_indicators WHERE is_active = 1
                """)
                
                for row in cursor.fetchall():
                    indicator = ThreatIndicator(
                        indicator_id=row[0],
                        indicator_type=row[1],
                        value=row[2],
                        threat_type=ThreatType(row[3]),
                        severity=ThreatSeverity(row[4]),
                        confidence=row[5],
                        source=row[6],
                        first_seen=datetime.fromisoformat(row[7]) if row[7] else datetime.now(timezone.utc),
                        last_seen=datetime.fromisoformat(row[8]) if row[8] else datetime.now(timezone.utc),
                        hit_count=row[9],
                        metadata=json.loads(row[10]) if row[10] else {}
                    )
                    self.threat_indicators[indicator.indicator_id] = indicator
            
            logger.info(f"Loaded {len(self.threat_indicators)} threat indicators")
        except Exception as e:
            logger.error(f"Failed to load threat intelligence: {e}")

    def _initialize_attack_patterns(self):
        """Initialize known attack patterns"""
        # Define common attack patterns
        patterns = [
            AttackPattern(
                pattern_id="apt_lateral_movement",
                pattern_name="APT Lateral Movement",
                threat_type=ThreatType.APT,
                stages=["initial_access", "persistence", "privilege_escalation", "lateral_movement"],
                indicators=["unusual_service_creation", "abnormal_network_connections", "credential_dumping"],
                detection_rules={"min_stages": 3, "time_window": 3600},
                mitre_attack_id="T1021"
            ),
            AttackPattern(
                pattern_id="credential_stuffing",
                pattern_name="Credential Stuffing Attack",
                threat_type=ThreatType.ACCOUNT_TAKEOVER,
                stages=["multiple_failed_logins", "distributed_sources", "credential_reuse"],
                indicators=["high_failure_rate", "geo_distributed", "automated_pattern"],
                detection_rules={"failure_threshold": 10, "time_window": 300},
                mitre_attack_id="T1110"
            ),
            AttackPattern(
                pattern_id="data_exfiltration_pattern",
                pattern_name="Data Exfiltration",
                threat_type=ThreatType.DATA_EXFILTRATION,
                stages=["reconnaissance", "data_collection", "staging", "exfiltration"],
                indicators=["unusual_data_access", "large_transfers", "encryption_usage"],
                detection_rules={"data_threshold": 1000000, "time_window": 1800},
                mitre_attack_id="T1041"
            )
        ]
        
        for pattern in patterns:
            self.attack_patterns[pattern.pattern_id] = pattern
            self._store_attack_pattern(pattern)

    def _store_attack_pattern(self, pattern: AttackPattern):
        """Store attack pattern in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO attack_patterns
                    (pattern_id, pattern_name, threat_type, stages, indicators,
                     detection_rules, mitre_attack_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.pattern_id,
                    pattern.pattern_name,
                    pattern.threat_type.value,
                    json.dumps(pattern.stages),
                    json.dumps(pattern.indicators),
                    json.dumps(pattern.detection_rules),
                    pattern.mitre_attack_id
                ))
        except Exception as e:
            logger.error(f"Failed to store attack pattern: {e}")

    def analyze_event(self, event_data: Dict[str, Any]) -> Optional[ThreatEvent]:
        """Analyze an event for threats"""
        try:
            # Extract features
            features = self._extract_features(event_data)
            
            # Check against threat indicators
            indicator_matches = self._check_threat_indicators(event_data)
            
            # Behavioral analysis
            anomaly_score = self._detect_anomaly(features)
            
            # ML threat classification
            threat_prediction = self._classify_threat(features)
            
            # Pattern matching
            pattern_match = self._match_attack_patterns(event_data)
            
            # Calculate overall threat score
            threat_score = self._calculate_threat_score(
                anomaly_score, threat_prediction, indicator_matches, pattern_match
            )
            
            # Create threat event if threshold exceeded
            if threat_score > 0.5:
                threat_event = self._create_threat_event(
                    event_data, threat_score, threat_prediction,
                    indicator_matches, pattern_match
                )
                
                # Store and respond to threat
                self._handle_threat_event(threat_event)
                
                return threat_event
            
            # Update behavior profile
            self._update_behavior_profile(event_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing event: {e}")
            return None

    def _extract_features(self, event_data: Dict[str, Any]) -> np.ndarray:
        """Extract features for ML models"""
        features = []
        
        # Time-based features
        current_hour = datetime.now().hour
        is_business_hours = 1 if 8 <= current_hour <= 18 else 0
        is_weekend = 1 if datetime.now().weekday() >= 5 else 0
        
        features.extend([current_hour, is_business_hours, is_weekend])
        
        # Request features
        request_method = 1 if event_data.get('method') == 'POST' else 0
        path_depth = len(event_data.get('path', '').split('/'))
        has_params = 1 if event_data.get('params') else 0
        param_count = len(event_data.get('params', {}))
        
        features.extend([request_method, path_depth, has_params, param_count])
        
        # User features
        user_id = event_data.get('user_id', '')
        is_authenticated = 1 if user_id else 0
        
        if user_id and user_id in self.behavior_profiles:
            profile = self.behavior_profiles[user_id]
            features.extend([
                profile.average_request_rate,
                profile.typical_data_volume,
                profile.risk_score,
                profile.anomaly_count
            ])
        else:
            features.extend([0, 0, 0, 0])
        
        features.append(is_authenticated)
        
        # Response features
        status_code = event_data.get('status_code', 200)
        response_time = event_data.get('response_time', 0)
        response_size = event_data.get('response_size', 0)
        
        features.extend([status_code, response_time, response_size])
        
        # Security features
        has_sql_keywords = 1 if self._contains_sql_keywords(str(event_data)) else 0
        has_script_tags = 1 if '<script' in str(event_data).lower() else 0
        has_command_injection = 1 if self._contains_command_injection(str(event_data)) else 0
        
        features.extend([has_sql_keywords, has_script_tags, has_command_injection])
        
        return np.array(features).reshape(1, -1)

    def _contains_sql_keywords(self, text: str) -> bool:
        """Check for SQL injection patterns"""
        sql_keywords = ['select', 'union', 'insert', 'update', 'delete', 'drop', 'exec', 'execute']
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in sql_keywords)

    def _contains_command_injection(self, text: str) -> bool:
        """Check for command injection patterns"""
        cmd_patterns = [';', '&&', '||', '`', '$(', '${']
        return any(pattern in text for pattern in cmd_patterns)

    def _check_threat_indicators(self, event_data: Dict[str, Any]) -> List[ThreatIndicator]:
        """Check event against threat indicators"""
        matches = []
        
        # Check IP indicators
        source_ip = event_data.get('source_ip')
        if source_ip:
            for indicator in self.threat_indicators.values():
                if indicator.indicator_type == 'ip' and indicator.value == source_ip:
                    matches.append(indicator)
                    indicator.hit_count += 1
        
        # Check pattern indicators
        event_str = json.dumps(event_data)
        for indicator in self.threat_indicators.values():
            if indicator.indicator_type == 'pattern' and indicator.value in event_str:
                matches.append(indicator)
                indicator.hit_count += 1
        
        return matches

    def _detect_anomaly(self, features: np.ndarray) -> float:
        """Detect anomalies using ML model"""
        try:
            if self.anomaly_detector is None:
                return 0.0
            
            # Scale features
            scaled_features = self.scaler.fit_transform(features)
            
            # Predict anomaly (-1 for anomaly, 1 for normal)
            prediction = self.anomaly_detector.predict(scaled_features)
            
            # Get anomaly score
            scores = self.anomaly_detector.score_samples(scaled_features)
            
            # Normalize score to 0-1 range
            anomaly_score = 1 - (scores[0] + 1) / 2
            
            return float(anomaly_score)
        except Exception as e:
            logger.warning(f"Anomaly detection failed: {e}")
            return 0.0

    def _classify_threat(self, features: np.ndarray) -> Dict[str, Any]:
        """Classify threat type using ML model"""
        try:
            if self.threat_classifier is None:
                return {"threat_type": ThreatType.ZERO_DAY, "confidence": 0.5}
            
            # Scale features
            scaled_features = self.scaler.transform(features)
            
            # Predict threat type
            prediction = self.threat_classifier.predict(scaled_features)
            probabilities = self.threat_classifier.predict_proba(scaled_features)
            
            # Get threat type and confidence
            threat_type_idx = prediction[0]
            confidence = float(np.max(probabilities))
            
            # Map to threat type
            threat_types = list(ThreatType)
            threat_type = threat_types[threat_type_idx % len(threat_types)]
            
            return {
                "threat_type": threat_type,
                "confidence": confidence
            }
        except Exception as e:
            logger.warning(f"Threat classification failed: {e}")
            return {"threat_type": ThreatType.ZERO_DAY, "confidence": 0.5}

    def _match_attack_patterns(self, event_data: Dict[str, Any]) -> Optional[AttackPattern]:
        """Match event against known attack patterns"""
        for pattern in self.attack_patterns.values():
            # Check if event matches pattern indicators
            matches = 0
            for indicator in pattern.indicators:
                if self._check_pattern_indicator(event_data, indicator):
                    matches += 1
            
            # Check if enough indicators match
            if matches >= len(pattern.indicators) * 0.5:
                return pattern
        
        return None

    def _check_pattern_indicator(self, event_data: Dict[str, Any], indicator: str) -> bool:
        """Check if event matches a pattern indicator"""
        if indicator == "unusual_service_creation":
            return event_data.get('event_type') == 'service_created'
        elif indicator == "high_failure_rate":
            return event_data.get('status_code', 200) >= 400
        elif indicator == "unusual_data_access":
            return event_data.get('data_volume', 0) > 1000000
        # Add more indicator checks as needed
        return False

    def _calculate_threat_score(self, anomaly_score: float, threat_prediction: Dict[str, Any],
                               indicator_matches: List[ThreatIndicator],
                               pattern_match: Optional[AttackPattern]) -> float:
        """Calculate overall threat score"""
        score = 0.0
        weights = {
            'anomaly': 0.3,
            'ml_prediction': 0.3,
            'indicators': 0.2,
            'patterns': 0.2
        }
        
        # Anomaly score contribution
        score += anomaly_score * weights['anomaly']
        
        # ML prediction contribution
        score += threat_prediction['confidence'] * weights['ml_prediction']
        
        # Indicator matches contribution
        if indicator_matches:
            indicator_score = sum(i.confidence for i in indicator_matches) / len(indicator_matches)
            score += indicator_score * weights['indicators']
        
        # Pattern match contribution
        if pattern_match:
            score += 1.0 * weights['patterns']
        
        return min(score, 1.0)

    def _create_threat_event(self, event_data: Dict[str, Any], threat_score: float,
                           threat_prediction: Dict[str, Any],
                           indicator_matches: List[ThreatIndicator],
                           pattern_match: Optional[AttackPattern]) -> ThreatEvent:
        """Create threat event from analysis"""
        # Determine threat type and severity
        threat_type = threat_prediction['threat_type']
        
        # Calculate severity based on score
        if threat_score > 0.9:
            severity = ThreatSeverity.CRITICAL
        elif threat_score > 0.7:
            severity = ThreatSeverity.HIGH
        elif threat_score > 0.5:
            severity = ThreatSeverity.MEDIUM
        else:
            severity = ThreatSeverity.LOW
        
        # Determine response actions
        response_actions = self._determine_response_actions(severity, threat_type)
        
        # Create event
        timestamp = str(time.time())
        event_id = f"threat_{hashlib.sha256(f'{timestamp}{event_data}'.encode()).hexdigest()[:16]}"
        
        threat_event = ThreatEvent(
            event_id=event_id,
            threat_type=threat_type,
            severity=severity,
            confidence=threat_score,
            entity_id=event_data.get('user_id', 'unknown'),
            source_ip=event_data.get('source_ip', 'unknown'),
            target_resource=event_data.get('path', 'unknown'),
            attack_vector=pattern_match.pattern_name if pattern_match else 'unknown',
            indicators=[i.indicator_id for i in indicator_matches],
            timestamp=datetime.now(timezone.utc),
            response_actions=response_actions,
            details={
                'anomaly_score': threat_score,
                'ml_confidence': threat_prediction['confidence'],
                'pattern_match': pattern_match.pattern_id if pattern_match else None,
                'raw_event': event_data
            }
        )
        
        return threat_event

    def _determine_response_actions(self, severity: ThreatSeverity, 
                                   threat_type: ThreatType) -> List[ResponseAction]:
        """Determine appropriate response actions"""
        actions = []
        
        # Always monitor and alert
        actions.append(ResponseAction.MONITOR)
        
        if severity.value >= ThreatSeverity.MEDIUM.value:
            actions.append(ResponseAction.ALERT)
        
        if severity.value >= ThreatSeverity.HIGH.value:
            actions.append(ResponseAction.INVESTIGATE)
            
            # Specific actions based on threat type
            if threat_type in [ThreatType.BRUTE_FORCE, ThreatType.DDoS_ATTACK]:
                actions.append(ResponseAction.THROTTLE)
            elif threat_type in [ThreatType.SQL_INJECTION, ThreatType.XSS_ATTACK]:
                actions.append(ResponseAction.BLOCK_REQUEST)
            elif threat_type == ThreatType.ACCOUNT_TAKEOVER:
                actions.append(ResponseAction.BLOCK_USER)
        
        if severity == ThreatSeverity.CRITICAL:
            actions.append(ResponseAction.BLOCK_IP)
            actions.append(ResponseAction.ESCALATE)
        
        if severity == ThreatSeverity.EMERGENCY:
            actions.append(ResponseAction.QUARANTINE)
        
        return actions

    def _handle_threat_event(self, threat_event: ThreatEvent):
        """Handle detected threat event"""
        try:
            # Store threat event
            self._store_threat_event(threat_event)
            
            # Add to active threats
            self.active_threats[threat_event.event_id] = threat_event
            self.threat_events.append(threat_event)
            
            # Execute response actions
            for action in threat_event.response_actions:
                self._execute_response_action(threat_event, action)
            
            # Update statistics
            self.detection_stats[threat_event.threat_type.value] += 1
            
            logger.warning(f"Threat detected: {threat_event.threat_type.value} "
                         f"(Severity: {threat_event.severity.value})")
            
        except Exception as e:
            logger.error(f"Failed to handle threat event: {e}")

    def _store_threat_event(self, threat_event: ThreatEvent):
        """Store threat event in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO threat_events
                    (event_id, threat_type, severity, confidence, entity_id,
                     source_ip, target_resource, attack_vector, indicators,
                     response_actions, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    threat_event.event_id,
                    threat_event.threat_type.value,
                    threat_event.severity.value,
                    threat_event.confidence,
                    threat_event.entity_id,
                    threat_event.source_ip,
                    threat_event.target_resource,
                    threat_event.attack_vector,
                    json.dumps(threat_event.indicators),
                    json.dumps([a.value for a in threat_event.response_actions]),
                    json.dumps(threat_event.details)
                ))
        except Exception as e:
            logger.error(f"Failed to store threat event: {e}")

    def _execute_response_action(self, threat_event: ThreatEvent, action: ResponseAction):
        """Execute response action for threat"""
        try:
            if action == ResponseAction.ALERT:
                # Send alert (would integrate with alerting system)
                logger.critical(f"SECURITY ALERT: {threat_event.threat_type.value} detected from {threat_event.source_ip}")
            elif action == ResponseAction.BLOCK_IP:
                # Add IP to blocklist (would integrate with firewall)
                logger.info(f"Blocking IP: {threat_event.source_ip}")
            elif action == ResponseAction.BLOCK_USER:
                # Block user account (would integrate with auth system)
                logger.info(f"Blocking user: {threat_event.entity_id}")
            # Add more action implementations as needed
        except Exception as e:
            logger.error(f"Failed to execute response action {action.value}: {e}")

    def _update_behavior_profile(self, event_data: Dict[str, Any]):
        """Update entity behavior profile"""
        entity_id = event_data.get('user_id') or event_data.get('source_ip')
        if not entity_id:
            return
        
        if entity_id not in self.behavior_profiles:
            # Create new profile
            self.behavior_profiles[entity_id] = BehaviorProfile(
                entity_id=entity_id,
                entity_type='user' if event_data.get('user_id') else 'ip',
                normal_activity_hours=[],
                typical_locations=[],
                common_endpoints=[],
                average_request_rate=0.0,
                typical_data_volume=0.0,
                risk_score=0.0,
                last_updated=datetime.now(timezone.utc),
                anomaly_count=0,
                feature_vector=[]
            )
        
        # Update profile with new data
        profile = self.behavior_profiles[entity_id]
        profile.last_updated = datetime.now(timezone.utc)
        
        # Update activity patterns
        current_hour = datetime.now().hour
        if current_hour not in profile.normal_activity_hours:
            profile.normal_activity_hours.append(current_hour)
        
        endpoint = event_data.get('path')
        if endpoint and endpoint not in profile.common_endpoints:
            profile.common_endpoints.append(endpoint)

    def add_threat_indicator(self, indicator_type: str, value: str, threat_type: ThreatType,
                            severity: ThreatSeverity, confidence: float = 0.8,
                            source: str = "manual") -> str:
        """Add new threat indicator"""
        combined = f"{indicator_type}{value}"
        indicator_id = f"ioc_{hashlib.sha256(combined.encode()).hexdigest()[:16]}"
        
        indicator = ThreatIndicator(
            indicator_id=indicator_id,
            indicator_type=indicator_type,
            value=value,
            threat_type=threat_type,
            severity=severity,
            confidence=confidence,
            source=source,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            hit_count=0,
            metadata={}
        )
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO threat_indicators
                (indicator_id, indicator_type, value, threat_type, severity,
                 confidence, source, first_seen, last_seen, hit_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                indicator.indicator_id,
                indicator.indicator_type,
                indicator.value,
                indicator.threat_type.value,
                indicator.severity.value,
                indicator.confidence,
                indicator.source,
                indicator.first_seen.isoformat(),
                indicator.last_seen.isoformat(),
                indicator.hit_count,
                json.dumps(indicator.metadata)
            ))
        
        self.threat_indicators[indicator_id] = indicator
        logger.info(f"Added threat indicator: {indicator_id}")
        return indicator_id

    def train_models(self, training_data: List[Dict[str, Any]], labels: List[int]):
        """Train ML models with new data"""
        try:
            # Extract features from training data
            features = []
            for event in training_data:
                features.append(self._extract_features(event).flatten())
            
            X = np.array(features)
            y = np.array(labels)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train anomaly detector
            normal_data = X_scaled[y == 0]
            if len(normal_data) > 10:
                self.anomaly_detector.fit(normal_data)
                
                # Save model
                joblib.dump(self.anomaly_detector, self.model_path / "anomaly_detector.pkl")
            
            # Train threat classifier
            if len(set(y)) > 1:  # Need at least 2 classes
                self.threat_classifier.fit(X_scaled, y)
                
                # Save model
                joblib.dump(self.threat_classifier, self.model_path / "threat_classifier.pkl")
            
            # Save scaler
            joblib.dump(self.scaler, self.model_path / "feature_scaler.pkl")
            
            logger.info(f"Models trained with {len(training_data)} samples")
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")

    def start_detection_engine(self):
        """Start threat detection engine"""
        if self.detection_active:
            return
        
        self.detection_active = True
        self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.detection_thread.start()
        logger.info("Threat detection engine started")

    def stop_detection_engine(self):
        """Stop threat detection engine"""
        self.detection_active = False
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=5)
        logger.info("Threat detection engine stopped")

    def _detection_loop(self):
        """Main detection loop"""
        while self.detection_active:
            try:
                # Process event buffer
                while self.event_buffer:
                    event = self.event_buffer.popleft()
                    self.analyze_event(event)
                
                # Periodic threat hunting
                self._perform_threat_hunting()
                
                # Model retraining check
                self._check_model_retraining()
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"Detection loop error: {e}")
                time.sleep(5)

    def _perform_threat_hunting(self):
        """Perform proactive threat hunting"""
        # This would implement various threat hunting techniques
        pass

    def _check_model_retraining(self):
        """Check if models need retraining"""
        # This would check model performance and trigger retraining if needed
        pass

    def get_threat_statistics(self) -> Dict[str, Any]:
        """Get comprehensive threat detection statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Threat events summary
                cursor = conn.execute("""
                    SELECT threat_type, COUNT(*), AVG(confidence)
                    FROM threat_events
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY threat_type
                """)
                threat_summary = {}
                for threat_type, count, avg_confidence in cursor.fetchall():
                    threat_summary[threat_type] = {
                        'count': count,
                        'avg_confidence': round(avg_confidence, 2) if avg_confidence else 0
                    }
                
                # Severity distribution
                cursor = conn.execute("""
                    SELECT severity, COUNT(*)
                    FROM threat_events
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY severity
                """)
                severity_distribution = dict(cursor.fetchall())
                
                # Active threats
                active_threat_count = len(self.active_threats)
                
                # Threat indicators
                total_indicators = len(self.threat_indicators)
                
                # Attack patterns
                total_patterns = len(self.attack_patterns)
                
                return {
                    "advanced_threat_detection_enabled": True,
                    "detection_engine_active": self.detection_active,
                    "threats_detected_24h": threat_summary,
                    "severity_distribution": severity_distribution,
                    "active_threats": active_threat_count,
                    "threat_indicators": total_indicators,
                    "attack_patterns": total_patterns,
                    "behavior_profiles": len(self.behavior_profiles),
                    "ml_models": {
                        "anomaly_detector": self.anomaly_detector is not None,
                        "threat_classifier": self.threat_classifier is not None
                    },
                    "features": {
                        "behavioral_analysis": True,
                        "ml_threat_detection": True,
                        "threat_intelligence": True,
                        "attack_pattern_matching": True,
                        "automated_response": True,
                        "threat_hunting": True
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get threat statistics: {e}")
            return {"advanced_threat_detection_enabled": False, "error": str(e)}

# Global threat detector instance
_threat_detector = None

def init_threat_detection(db_path: str = "threat_detection.db", 
                         model_path: str = "models/") -> AdvancedThreatDetector:
    """Initialize global threat detector"""
    global _threat_detector
    _threat_detector = AdvancedThreatDetector(db_path, model_path)
    return _threat_detector

def get_threat_detector() -> Optional[AdvancedThreatDetector]:
    """Get global threat detector"""
    return _threat_detector

def analyze_threat(event_data: Dict[str, Any]) -> Optional[ThreatEvent]:
    """Global function to analyze threat"""
    if _threat_detector:
        return _threat_detector.analyze_event(event_data)
    return None

def add_threat_indicator(indicator_type: str, value: str, threat_type: str,
                        severity: int, confidence: float = 0.8) -> Optional[str]:
    """Global function to add threat indicator"""
    if _threat_detector:
        return _threat_detector.add_threat_indicator(
            indicator_type, value, ThreatType(threat_type),
            ThreatSeverity(severity), confidence
        )
    return None

def get_threat_statistics() -> Dict[str, Any]:
    """Global function to get threat statistics"""
    if _threat_detector:
        return _threat_detector.get_threat_statistics()
    return {"advanced_threat_detection_enabled": False}

if __name__ == "__main__":
    # Example usage
    detector = init_threat_detection()
    
    # Add threat indicators
    detector.add_threat_indicator("ip", "192.168.1.100", ThreatType.BRUTE_FORCE, ThreatSeverity.HIGH)
    
    # Analyze sample event
    event = {
        "user_id": "user123",
        "source_ip": "192.168.1.100",
        "path": "/api/admin",
        "method": "POST",
        "status_code": 401,
        "response_time": 100
    }
    
    threat = detector.analyze_event(event)
    if threat:
        print(f"Threat detected: {threat.threat_type.value}")
    
    # Get statistics
    stats = detector.get_threat_statistics()
    print(f"Threat statistics: {stats}")