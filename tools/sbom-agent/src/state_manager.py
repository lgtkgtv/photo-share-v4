#!/usr/bin/env python3
"""
SBOM Agent State Management System
==================================

Manages analysis history, tracks changes, and enables progressive analysis
with before/after comparisons for demonstrating tool effectiveness.

Key Features:
- Analysis history tracking
- State persistence across runs
- Before/after comparison capabilities
- Progress metrics and reporting
- Remediation tracking
"""

import os
import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import uuid


@dataclass
class AnalysisRun:
    """Represents a single analysis run."""
    run_id: str
    timestamp: datetime
    project_path: str
    project_hash: str
    sbom_data: Dict[str, Any]
    vulnerabilities: List[Dict[str, Any]]
    security_score: float
    tool_version: str
    analysis_type: str  # 'initial', 'post_remediation', 'scheduled'
    metadata: Dict[str, Any]


@dataclass
class RemediationAction:
    """Represents a remediation action taken."""
    action_id: str
    run_id: str
    timestamp: datetime
    action_type: str  # 'package_update', 'config_change', 'code_fix'
    description: str
    target_package: Optional[str]
    from_version: Optional[str]
    to_version: Optional[str]
    vulnerability_ids: List[str]
    success: bool
    metadata: Dict[str, Any]


class StateManager:
    """Manages SBOM analysis state and history."""
    
    def __init__(self, state_dir: Path = None):
        self.state_dir = state_dir or Path.home() / ".security-tools" / "sbom-agent"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "analysis_history.db"
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for state management."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    project_path TEXT NOT NULL,
                    project_hash TEXT NOT NULL,
                    sbom_data TEXT NOT NULL,
                    vulnerabilities TEXT NOT NULL,
                    security_score REAL NOT NULL,
                    tool_version TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS remediation_actions (
                    action_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    target_package TEXT,
                    from_version TEXT,
                    to_version TEXT,
                    vulnerability_ids TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    metadata TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES analysis_runs (run_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_path 
                ON analysis_runs (project_path)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON analysis_runs (timestamp)
            """)
            
            conn.commit()
    
    def calculate_project_hash(self, project_path: Path) -> str:
        """Calculate hash of project state for change detection."""
        hash_sources = []
        
        # Include key files that affect security analysis
        key_patterns = [
            "**/requirements*.txt",
            "**/package.json",
            "**/pom.xml",
            "**/build.gradle",
            "**/go.mod",
            "**/Cargo.toml",
            "**/composer.json",
            "**/Gemfile"
        ]
        
        for pattern in key_patterns:
            for file_path in project_path.rglob(pattern):
                try:
                    if file_path.is_file():
                        with open(file_path, 'rb') as f:
                            content = f.read()
                        hash_sources.append(f"{file_path.relative_to(project_path)}:{hashlib.md5(content).hexdigest()}")
                except Exception:
                    continue
        
        # Create combined hash
        combined = "\n".join(sorted(hash_sources))
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def save_analysis_run(self, analysis_run: AnalysisRun) -> str:
        """Save analysis run to state database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO analysis_runs 
                (run_id, timestamp, project_path, project_hash, sbom_data, 
                 vulnerabilities, security_score, tool_version, analysis_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis_run.run_id,
                analysis_run.timestamp.isoformat(),
                str(analysis_run.project_path),
                analysis_run.project_hash,
                json.dumps(analysis_run.sbom_data),
                json.dumps(analysis_run.vulnerabilities),
                analysis_run.security_score,
                analysis_run.tool_version,
                analysis_run.analysis_type,
                json.dumps(analysis_run.metadata)
            ))
            conn.commit()
        
        return analysis_run.run_id
    
    def save_remediation_action(self, action: RemediationAction) -> str:
        """Save remediation action to state database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO remediation_actions
                (action_id, run_id, timestamp, action_type, description,
                 target_package, from_version, to_version, vulnerability_ids,
                 success, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action.action_id,
                action.run_id,
                action.timestamp.isoformat(),
                action.action_type,
                action.description,
                action.target_package,
                action.from_version,
                action.to_version,
                json.dumps(action.vulnerability_ids),
                action.success,
                json.dumps(action.metadata)
            ))
            conn.commit()
        
        return action.action_id
    
    def get_latest_analysis(self, project_path: str) -> Optional[AnalysisRun]:
        """Get the most recent analysis for a project."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM analysis_runs 
                WHERE project_path = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (str(project_path),))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_analysis_run(row)
        
        return None
    
    def get_analysis_history(self, project_path: str, limit: int = 10) -> List[AnalysisRun]:
        """Get analysis history for a project."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM analysis_runs 
                WHERE project_path = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (str(project_path), limit))
            
            return [self._row_to_analysis_run(row) for row in cursor.fetchall()]
    
    def get_analysis_by_id(self, run_id: str) -> Optional[AnalysisRun]:
        """Get specific analysis run by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM analysis_runs WHERE run_id = ?
            """, (run_id,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_analysis_run(row)
        
        return None
    
    def get_remediation_actions(self, run_id: str) -> List[RemediationAction]:
        """Get remediation actions for a specific analysis run."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM remediation_actions 
                WHERE run_id = ? 
                ORDER BY timestamp
            """, (run_id,))
            
            return [self._row_to_remediation_action(row) for row in cursor.fetchall()]
    
    def create_analysis_run(self, project_path: Path, sbom_data: Dict[str, Any], 
                          vulnerabilities: List[Dict[str, Any]], security_score: float,
                          tool_version: str, analysis_type: str = "initial",
                          metadata: Dict[str, Any] = None) -> AnalysisRun:
        """Create a new analysis run object."""
        return AnalysisRun(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            project_path=str(project_path),
            project_hash=self.calculate_project_hash(project_path),
            sbom_data=sbom_data,
            vulnerabilities=vulnerabilities,
            security_score=security_score,
            tool_version=tool_version,
            analysis_type=analysis_type,
            metadata=metadata or {}
        )
    
    def create_remediation_action(self, run_id: str, action_type: str, description: str,
                                target_package: str = None, from_version: str = None,
                                to_version: str = None, vulnerability_ids: List[str] = None,
                                success: bool = True, metadata: Dict[str, Any] = None) -> RemediationAction:
        """Create a new remediation action object."""
        return RemediationAction(
            action_id=str(uuid.uuid4()),
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            action_type=action_type,
            description=description,
            target_package=target_package,
            from_version=from_version,
            to_version=to_version,
            vulnerability_ids=vulnerability_ids or [],
            success=success,
            metadata=metadata or {}
        )
    
    def compare_analyses(self, before_run_id: str, after_run_id: str) -> Dict[str, Any]:
        """Compare two analysis runs to show progress."""
        before = self.get_analysis_by_id(before_run_id)
        after = self.get_analysis_by_id(after_run_id)
        
        if not before or not after:
            raise ValueError("One or both analysis runs not found")
        
        comparison = {
            "metadata": {
                "before_run_id": before_run_id,
                "after_run_id": after_run_id,
                "before_timestamp": before.timestamp.isoformat(),
                "after_timestamp": after.timestamp.isoformat(),
                "time_elapsed": (after.timestamp - before.timestamp).total_seconds()
            },
            "security_score": {
                "before": before.security_score,
                "after": after.security_score,
                "improvement": after.security_score - before.security_score,
                "improvement_percentage": ((after.security_score - before.security_score) / before.security_score) * 100 if before.security_score > 0 else 0
            },
            "vulnerabilities": {
                "before_count": len(before.vulnerabilities),
                "after_count": len(after.vulnerabilities),
                "resolved_count": len(before.vulnerabilities) - len(after.vulnerabilities),
                "new_vulnerabilities": self._find_new_vulnerabilities(before.vulnerabilities, after.vulnerabilities),
                "resolved_vulnerabilities": self._find_resolved_vulnerabilities(before.vulnerabilities, after.vulnerabilities)
            },
            "packages": {
                "before_count": self._count_packages(before.sbom_data),
                "after_count": self._count_packages(after.sbom_data),
                "updated_packages": self._find_updated_packages(before.sbom_data, after.sbom_data)
            },
            "remediation_actions": self.get_remediation_actions(after_run_id)
        }
        
        return comparison
    
    def get_progress_metrics(self, project_path: str) -> Dict[str, Any]:
        """Get progress metrics for a project over time."""
        history = self.get_analysis_history(project_path, limit=50)
        
        if len(history) < 2:
            return {"error": "Insufficient analysis history for progress metrics"}
        
        metrics = {
            "total_analyses": len(history),
            "first_analysis": history[-1].timestamp.isoformat(),
            "latest_analysis": history[0].timestamp.isoformat(),
            "security_score_trend": [run.security_score for run in reversed(history)],
            "vulnerability_count_trend": [len(run.vulnerabilities) for run in reversed(history)],
            "overall_improvement": {
                "security_score": history[0].security_score - history[-1].security_score,
                "vulnerabilities_resolved": len(history[-1].vulnerabilities) - len(history[0].vulnerabilities)
            },
            "analysis_frequency": self._calculate_analysis_frequency(history)
        }
        
        return metrics
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old analysis data beyond retention period."""
        cutoff_date = datetime.now(timezone.utc).replace(days=-days_to_keep)
        
        with sqlite3.connect(self.db_path) as conn:
            # Delete old remediation actions first (foreign key constraint)
            conn.execute("""
                DELETE FROM remediation_actions 
                WHERE run_id IN (
                    SELECT run_id FROM analysis_runs 
                    WHERE timestamp < ?
                )
            """, (cutoff_date.isoformat(),))
            
            # Delete old analysis runs
            conn.execute("""
                DELETE FROM analysis_runs WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            conn.commit()
    
    def _row_to_analysis_run(self, row) -> AnalysisRun:
        """Convert database row to AnalysisRun object."""
        return AnalysisRun(
            run_id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            project_path=row[2],
            project_hash=row[3],
            sbom_data=json.loads(row[4]),
            vulnerabilities=json.loads(row[5]),
            security_score=row[6],
            tool_version=row[7],
            analysis_type=row[8],
            metadata=json.loads(row[9])
        )
    
    def _row_to_remediation_action(self, row) -> RemediationAction:
        """Convert database row to RemediationAction object."""
        return RemediationAction(
            action_id=row[0],
            run_id=row[1],
            timestamp=datetime.fromisoformat(row[2]),
            action_type=row[3],
            description=row[4],
            target_package=row[5],
            from_version=row[6],
            to_version=row[7],
            vulnerability_ids=json.loads(row[8]),
            success=bool(row[9]),
            metadata=json.loads(row[10])
        )
    
    def _find_new_vulnerabilities(self, before: List[Dict], after: List[Dict]) -> List[Dict]:
        """Find vulnerabilities that appeared in the after analysis."""
        before_ids = {v.get('vulnerability_id') for v in before}
        return [v for v in after if v.get('vulnerability_id') not in before_ids]
    
    def _find_resolved_vulnerabilities(self, before: List[Dict], after: List[Dict]) -> List[Dict]:
        """Find vulnerabilities that were resolved between analyses."""
        after_ids = {v.get('vulnerability_id') for v in after}
        return [v for v in before if v.get('vulnerability_id') not in after_ids]
    
    def _count_packages(self, sbom_data: Dict[str, Any]) -> int:
        """Count total packages in SBOM data."""
        count = 0
        if "universal_sbom" in sbom_data:
            ecosystems = sbom_data["universal_sbom"].get("ecosystems", {})
            for ecosystem_data in ecosystems.values():
                count += len(ecosystem_data)
        return count
    
    def _find_updated_packages(self, before_sbom: Dict, after_sbom: Dict) -> List[Dict]:
        """Find packages that were updated between analyses."""
        updated = []
        
        # Simplified comparison - would need enhancement for different SBOM formats
        before_packages = {}
        after_packages = {}
        
        # Extract package info from universal SBOM format
        if "universal_sbom" in before_sbom:
            ecosystems = before_sbom["universal_sbom"].get("ecosystems", {})
            for ecosystem_data in ecosystems.values():
                for pkg_name, pkg_info in ecosystem_data.items():
                    before_packages[pkg_name] = pkg_info.get("version", "unknown")
        
        if "universal_sbom" in after_sbom:
            ecosystems = after_sbom["universal_sbom"].get("ecosystems", {})
            for ecosystem_data in ecosystems.values():
                for pkg_name, pkg_info in ecosystem_data.items():
                    after_packages[pkg_name] = pkg_info.get("version", "unknown")
        
        # Find updates
        for pkg_name, after_version in after_packages.items():
            before_version = before_packages.get(pkg_name)
            if before_version and before_version != after_version:
                updated.append({
                    "package": pkg_name,
                    "from_version": before_version,
                    "to_version": after_version
                })
        
        return updated
    
    def _calculate_analysis_frequency(self, history: List[AnalysisRun]) -> Dict[str, float]:
        """Calculate analysis frequency metrics."""
        if len(history) < 2:
            return {"average_days_between_analyses": 0}
        
        intervals = []
        for i in range(1, len(history)):
            interval = (history[i-1].timestamp - history[i].timestamp).total_seconds() / 86400
            intervals.append(interval)
        
        return {
            "average_days_between_analyses": sum(intervals) / len(intervals),
            "min_days_between_analyses": min(intervals),
            "max_days_between_analyses": max(intervals)
        }


def main():
    """Command-line interface for state management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SBOM Agent State Manager")
    parser.add_argument("--history", help="Show analysis history for project")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE_ID", "AFTER_ID"), help="Compare two analysis runs")
    parser.add_argument("--metrics", help="Show progress metrics for project")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", help="Cleanup data older than N days")
    
    args = parser.parse_args()
    
    state_manager = StateManager()
    
    if args.history:
        history = state_manager.get_analysis_history(args.history)
        print(f"Analysis history for {args.history}:")
        for run in history:
            print(f"  {run.timestamp} - {run.run_id} - Score: {run.security_score}")
    
    elif args.compare:
        before_id, after_id = args.compare
        comparison = state_manager.compare_analyses(before_id, after_id)
        print(json.dumps(comparison, indent=2, default=str))
    
    elif args.metrics:
        metrics = state_manager.get_progress_metrics(args.metrics)
        print(json.dumps(metrics, indent=2, default=str))
    
    elif args.cleanup:
        state_manager.cleanup_old_data(args.cleanup)
        print(f"✅ Cleaned up data older than {args.cleanup} days")
    
    else:
        print("Use --help for available commands")


if __name__ == "__main__":
    main()