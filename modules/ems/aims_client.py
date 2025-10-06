#!/usr/bin/env python3
"""
AIMS Client - Alert and Incident Management System Client
=========================================================

Client for interacting with AIMS (Alert and Incident Management System).
Handles incident submissions, status tracking, and escalation management.
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from utils.logger import get_logger

logger = get_logger(__name__)

class IncidentSeverity(Enum):
    """Incident severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IncidentStatus(Enum):
    """Incident status types"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"

class IncidentType(Enum):
    """Incident types"""
    SECURITY_INCIDENT = "security_incident"
    HR_INCIDENT = "hr_incident"
    OPERATIONAL_INCIDENT = "operational_incident"
    COMPLIANCE_INCIDENT = "compliance_incident"
    TECHNICAL_INCIDENT = "technical_incident"

@dataclass
class AIMSIncident:
    """AIMS Incident data structure"""
    incident_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str = ""
    incident_type: IncidentType = IncidentType.OPERATIONAL_INCIDENT
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    title: str = ""
    description: str = ""
    status: IncidentStatus = IncidentStatus.OPEN
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    escalation_level: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "incident_id": self.incident_id,
            "employee_id": self.employee_id,
            "incident_type": self.incident_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata,
            "tags": self.tags,
            "escalation_level": self.escalation_level
        }

class AIMSClient:
    """Client for AIMS integration"""
    
    def __init__(self):
        self.client_name = "AIMS_Client"
        self.version = "1.0.0"
        
        # In-memory storage for demo (in production, use database/API)
        self.incidents: Dict[str, AIMSIncident] = {}
        self.escalation_rules = self._setup_escalation_rules()
        self.assignment_rules = self._setup_assignment_rules()
        
        logger.info("✅ AIMS Client initialized")
    
    def _setup_escalation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Setup escalation rules"""
        return {
            "critical": {"escalate_after_minutes": 15, "max_level": 3},
            "high": {"escalate_after_minutes": 60, "max_level": 2},
            "medium": {"escalate_after_minutes": 240, "max_level": 1},
            "low": {"escalate_after_minutes": 1440, "max_level": 1}  # 24 hours
        }
    
    def _setup_assignment_rules(self) -> Dict[str, str]:
        """Setup automatic assignment rules"""
        return {
            "security_incident": "security_team",
            "hr_incident": "hr_team",
            "operational_incident": "ops_team",
            "compliance_incident": "compliance_team",
            "technical_incident": "tech_team"
        }
    
    def submit_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit new incident to AIMS"""
        try:
            # Create incident object
            incident = AIMSIncident(
                employee_id=incident_data.get("employee_id", ""),
                incident_type=IncidentType(incident_data.get("incident_type", "operational_incident")),
                severity=IncidentSeverity(incident_data.get("severity", "medium")),
                title=incident_data.get("title", ""),
                description=incident_data.get("description", ""),
                metadata=incident_data.get("metadata", {}),
                tags=incident_data.get("tags", [])
            )
            
            # Auto-assign based on incident type
            incident.assigned_to = self.assignment_rules.get(
                incident.incident_type.value, 
                "ops_team"
            )
            
            # Store incident
            self.incidents[incident.incident_id] = incident
            
            # Check for immediate escalation (critical incidents)
            if incident.severity == IncidentSeverity.CRITICAL:
                self._escalate_incident(incident.incident_id)
            
            logger.info(f"✅ AIMS incident submitted: {incident.incident_id}")
            
            return {
                "status": "success",
                "incident_id": incident.incident_id,
                "assigned_to": incident.assigned_to,
                "message": "Incident submitted successfully",
                "escalated": incident.severity == IncidentSeverity.CRITICAL
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to submit AIMS incident: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to submit incident: {str(e)}"
            }
    
    def update_incident_status(self, incident_id: str, status: str, notes: str = "") -> Dict[str, Any]:
        """Update incident status"""
        try:
            if incident_id not in self.incidents:
                return {
                    "status": "error",
                    "message": f"Incident {incident_id} not found"
                }
            
            incident = self.incidents[incident_id]
            old_status = incident.status
            incident.status = IncidentStatus(status)
            incident.updated_at = datetime.utcnow()
            
            # Set resolved timestamp if resolved
            if incident.status in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]:
                incident.resolved_at = datetime.utcnow()
            
            # Add notes to metadata
            if notes:
                if "status_updates" not in incident.metadata:
                    incident.metadata["status_updates"] = []
                incident.metadata["status_updates"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "old_status": old_status.value,
                    "new_status": status,
                    "notes": notes
                })
            
            logger.info(f"✅ AIMS incident {incident_id} status updated: {old_status.value} -> {status}")
            
            return {
                "status": "success",
                "incident_id": incident_id,
                "old_status": old_status.value,
                "new_status": status,
                "message": "Incident status updated successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to update AIMS incident status: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to update incident status: {str(e)}"
            }
    
    def _escalate_incident(self, incident_id: str) -> bool:
        """Escalate incident to next level"""
        try:
            if incident_id not in self.incidents:
                return False
            
            incident = self.incidents[incident_id]
            escalation_rule = self.escalation_rules.get(incident.severity.value, {})
            max_level = escalation_rule.get("max_level", 1)
            
            if incident.escalation_level < max_level:
                incident.escalation_level += 1
                incident.status = IncidentStatus.ESCALATED
                incident.updated_at = datetime.utcnow()
                
                # Add escalation to metadata
                if "escalations" not in incident.metadata:
                    incident.metadata["escalations"] = []
                incident.metadata["escalations"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": incident.escalation_level,
                    "reason": "automatic_escalation"
                })
                
                logger.warning(f"🚨 AIMS incident {incident_id} escalated to level {incident.escalation_level}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to escalate AIMS incident: {str(e)}")
            return False
    
    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get incident by ID"""
        incident = self.incidents.get(incident_id)
        return incident.to_dict() if incident else None
    
    def get_incidents_by_employee(self, employee_id: str) -> List[Dict[str, Any]]:
        """Get all incidents for an employee"""
        return [
            incident.to_dict() 
            for incident in self.incidents.values() 
            if incident.employee_id == employee_id
        ]
    
    def get_incidents_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get incidents by status"""
        return [
            incident.to_dict() 
            for incident in self.incidents.values() 
            if incident.status.value == status
        ]
    
    def get_incidents_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """Get incidents by severity"""
        return [
            incident.to_dict() 
            for incident in self.incidents.values() 
            if incident.severity.value == severity
        ]
    
    def get_escalated_incidents(self) -> List[Dict[str, Any]]:
        """Get all escalated incidents"""
        return [
            incident.to_dict() 
            for incident in self.incidents.values() 
            if incident.escalation_level > 0
        ]
    
    def check_escalations(self) -> List[str]:
        """Check for incidents that need escalation"""
        escalated_ids = []
        now = datetime.utcnow()
        
        for incident_id, incident in self.incidents.items():
            if incident.status in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]:
                continue
            
            escalation_rule = self.escalation_rules.get(incident.severity.value, {})
            escalate_after = escalation_rule.get("escalate_after_minutes", 240)
            
            # Check if incident is old enough for escalation
            time_since_created = (now - incident.created_at).total_seconds() / 60
            time_since_updated = (now - incident.updated_at).total_seconds() / 60
            
            if (time_since_created >= escalate_after or time_since_updated >= escalate_after):
                if self._escalate_incident(incident_id):
                    escalated_ids.append(incident_id)
        
        return escalated_ids
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get AIMS statistics"""
        now = datetime.utcnow()
        
        # Count by status
        status_counts = {}
        for status in IncidentStatus:
            status_counts[status.value] = len([
                i for i in self.incidents.values() 
                if i.status == status
            ])
        
        # Count by severity
        severity_counts = {}
        for severity in IncidentSeverity:
            severity_counts[severity.value] = len([
                i for i in self.incidents.values() 
                if i.severity == severity
            ])
        
        # Count escalated
        escalated_count = len([
            i for i in self.incidents.values() 
            if i.escalation_level > 0
        ])
        
        # Recent incidents (last 24 hours)
        last_24h = now - timedelta(hours=24)
        recent_count = len([
            i for i in self.incidents.values() 
            if i.created_at >= last_24h
        ])
        
        return {
            "total_incidents": len(self.incidents),
            "status_breakdown": status_counts,
            "severity_breakdown": severity_counts,
            "escalated_incidents": escalated_count,
            "recent_incidents_24h": recent_count,
            "timestamp": now.isoformat()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for AIMS client"""
        return {
            "client": self.client_name,
            "version": self.version,
            "status": "healthy",
            "total_incidents": len(self.incidents),
            "timestamp": datetime.utcnow().isoformat()
        }
