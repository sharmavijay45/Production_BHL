#!/usr/bin/env python3
"""
Activity Logger - EMS Activity Logging and Routing
==================================================

Handles activity logging, routing to orchestrator, and integration with AIMS.
Provides comprehensive activity tracking for employee management.
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from utils.logger import get_logger

logger = get_logger(__name__)

class ActivityType(Enum):
    """Activity types"""
    LOGIN = "login"
    LOGOUT = "logout"
    FILE_ACCESS = "file_access"
    SYSTEM_ACCESS = "system_access"
    POLICY_VIOLATION = "policy_violation"
    TRAINING_COMPLETION = "training_completion"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_CHECK = "compliance_check"
    PERFORMANCE_METRIC = "performance_metric"
    ALERT_GENERATED = "alert_generated"

class ActivitySeverity(Enum):
    """Activity severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ActivityLog:
    """Activity log entry"""
    log_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str = ""
    activity_type: ActivityType = ActivityType.SYSTEM_ACCESS
    severity: ActivitySeverity = ActivitySeverity.INFO
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_system: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    orchestrator_routed: bool = False
    aims_submitted: bool = False
    alert_generated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "log_id": self.log_id,
            "employee_id": self.employee_id,
            "activity_type": self.activity_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "source_system": self.source_system,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "tags": self.tags,
            "orchestrator_routed": self.orchestrator_routed,
            "aims_submitted": self.aims_submitted,
            "alert_generated": self.alert_generated
        }

class ActivityLogger:
    """Activity logger with orchestrator integration"""
    
    def __init__(self):
        self.logger_name = "ActivityLogger"
        self.version = "1.0.0"
        
        # In-memory storage for demo (in production, use database)
        self.activity_logs: Dict[str, ActivityLog] = {}
        self.routing_rules = self._setup_routing_rules()
        self.escalation_rules = self._setup_escalation_rules()
        
        logger.info("✅ Activity Logger initialized")
    
    def _setup_routing_rules(self) -> Dict[str, Dict[str, Any]]:
        """Setup routing rules for orchestrator integration"""
        return {
            "policy_violation": {
                "route_to_orchestrator": True,
                "submit_to_aims": True,
                "generate_alert": True,
                "priority": "high"
            },
            "security_event": {
                "route_to_orchestrator": True,
                "submit_to_aims": True,
                "generate_alert": True,
                "priority": "critical"
            },
            "login": {
                "route_to_orchestrator": False,
                "submit_to_aims": False,
                "generate_alert": False,
                "priority": "low"
            },
            "file_access": {
                "route_to_orchestrator": True,
                "submit_to_aims": False,
                "generate_alert": False,
                "priority": "medium"
            },
            "compliance_check": {
                "route_to_orchestrator": True,
                "submit_to_aims": True,
                "generate_alert": True,
                "priority": "high"
            }
        }
    
    def _setup_escalation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Setup escalation rules based on severity"""
        return {
            "critical": {
                "immediate_aims": True,
                "immediate_alert": True,
                "orchestrator_priority": "high",
                "notification_channels": ["email", "sms", "slack"]
            },
            "error": {
                "immediate_aims": True,
                "immediate_alert": True,
                "orchestrator_priority": "medium",
                "notification_channels": ["email", "slack"]
            },
            "warning": {
                "immediate_aims": False,
                "immediate_alert": True,
                "orchestrator_priority": "low",
                "notification_channels": ["email"]
            },
            "info": {
                "immediate_aims": False,
                "immediate_alert": False,
                "orchestrator_priority": "low",
                "notification_channels": []
            }
        }
    
    def log_activity(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log activity and handle routing"""
        try:
            # Create activity log
            activity = ActivityLog(
                employee_id=activity_data.get("employee_id", ""),
                activity_type=ActivityType(activity_data.get("activity_type", "system_access")),
                severity=ActivitySeverity(activity_data.get("severity", "info")),
                description=activity_data.get("description", ""),
                source_system=activity_data.get("source_system", "unknown"),
                ip_address=activity_data.get("ip_address"),
                user_agent=activity_data.get("user_agent"),
                session_id=activity_data.get("session_id"),
                metadata=activity_data.get("metadata", {}),
                tags=activity_data.get("tags", [])
            )
            
            # Store activity log
            self.activity_logs[activity.log_id] = activity
            
            # Process routing based on rules
            routing_result = self._process_routing(activity)
            
            logger.info(f"✅ Activity logged: {activity.log_id} - {activity.activity_type.value}")
            
            return {
                "status": "success",
                "log_id": activity.log_id,
                "message": "Activity logged successfully",
                "routing_result": routing_result
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to log activity: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to log activity: {str(e)}"
            }
    
    def _process_routing(self, activity: ActivityLog) -> Dict[str, Any]:
        """Process routing based on activity type and severity"""
        routing_result = {
            "orchestrator_routed": False,
            "aims_submitted": False,
            "alert_generated": False,
            "actions_taken": []
        }
        
        try:
            # Get routing rules for activity type
            activity_rules = self.routing_rules.get(activity.activity_type.value, {})
            severity_rules = self.escalation_rules.get(activity.severity.value, {})
            
            # Route to orchestrator if needed
            if activity_rules.get("route_to_orchestrator", False):
                orchestrator_result = self._route_to_orchestrator(activity)
                if orchestrator_result["success"]:
                    activity.orchestrator_routed = True
                    routing_result["orchestrator_routed"] = True
                    routing_result["actions_taken"].append("orchestrator_routing")
            
            # Submit to AIMS if needed
            if (activity_rules.get("submit_to_aims", False) or 
                severity_rules.get("immediate_aims", False)):
                aims_result = self._submit_to_aims(activity)
                if aims_result["success"]:
                    activity.aims_submitted = True
                    routing_result["aims_submitted"] = True
                    routing_result["actions_taken"].append("aims_submission")
            
            # Generate alert if needed
            if (activity_rules.get("generate_alert", False) or 
                severity_rules.get("immediate_alert", False)):
                alert_result = self._generate_alert(activity)
                if alert_result["success"]:
                    activity.alert_generated = True
                    routing_result["alert_generated"] = True
                    routing_result["actions_taken"].append("alert_generation")
            
            return routing_result
            
        except Exception as e:
            logger.error(f"❌ Failed to process routing: {str(e)}")
            return routing_result
    
    def _route_to_orchestrator(self, activity: ActivityLog) -> Dict[str, Any]:
        """Route activity to orchestrator for processing"""
        try:
            # In a real implementation, this would call the orchestrator
            # For now, we'll simulate the routing
            
            orchestrator_query = self._build_orchestrator_query(activity)
            
            # Simulate orchestrator processing
            logger.info(f"🎭 Routing to orchestrator: {orchestrator_query[:100]}...")
            
            # In production, you would call:
            # from agents.agent_orchestrator import AgentOrchestrator
            # orchestrator = AgentOrchestrator()
            # result = orchestrator.process_query(orchestrator_query, context={
            #     "source": "ems_activity_logger",
            #     "activity_id": activity.log_id,
            #     "employee_id": activity.employee_id
            # })
            
            return {
                "success": True,
                "message": "Successfully routed to orchestrator",
                "query": orchestrator_query
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to route to orchestrator: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to route to orchestrator: {str(e)}"
            }
    
    def _build_orchestrator_query(self, activity: ActivityLog) -> str:
        """Build query for orchestrator based on activity"""
        query_templates = {
            "policy_violation": f"Analyze policy violation by employee {activity.employee_id}: {activity.description}",
            "security_event": f"Investigate security event for employee {activity.employee_id}: {activity.description}",
            "compliance_check": f"Review compliance issue for employee {activity.employee_id}: {activity.description}",
            "file_access": f"Analyze file access pattern for employee {activity.employee_id}: {activity.description}",
            "performance_metric": f"Evaluate performance metric for employee {activity.employee_id}: {activity.description}"
        }
        
        return query_templates.get(
            activity.activity_type.value,
            f"Analyze activity for employee {activity.employee_id}: {activity.description}"
        )
    
    def _submit_to_aims(self, activity: ActivityLog) -> Dict[str, Any]:
        """Submit activity to AIMS"""
        try:
            # In a real implementation, this would call the AIMS client
            # For now, we'll simulate the submission
            
            aims_data = {
                "employee_id": activity.employee_id,
                "incident_type": self._map_activity_to_incident_type(activity.activity_type),
                "severity": activity.severity.value,
                "title": f"Activity Alert: {activity.activity_type.value}",
                "description": activity.description,
                "metadata": {
                    "source_activity_id": activity.log_id,
                    "source_system": activity.source_system,
                    **activity.metadata
                }
            }
            
            logger.info(f"📋 Submitting to AIMS: {activity.activity_type.value}")
            
            # In production, you would call:
            # from modules.ems.aims_client import AIMSClient
            # aims_client = AIMSClient()
            # result = aims_client.submit_incident(aims_data)
            
            return {
                "success": True,
                "message": "Successfully submitted to AIMS",
                "aims_data": aims_data
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to submit to AIMS: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to submit to AIMS: {str(e)}"
            }
    
    def _generate_alert(self, activity: ActivityLog) -> Dict[str, Any]:
        """Generate employee alert"""
        try:
            # In a real implementation, this would call the alert manager
            # For now, we'll simulate the alert generation
            
            alert_data = {
                "employee_id": activity.employee_id,
                "alert_type": self._map_activity_to_alert_type(activity.activity_type),
                "priority": self._map_severity_to_priority(activity.severity),
                "title": f"Activity Alert: {activity.activity_type.value.title()}",
                "message": f"Alert generated from activity: {activity.description}",
                "action_required": activity.severity in [ActivitySeverity.ERROR, ActivitySeverity.CRITICAL],
                "metadata": {
                    "source_activity_id": activity.log_id,
                    "activity_type": activity.activity_type.value,
                    **activity.metadata
                }
            }
            
            logger.info(f"🚨 Generating alert for employee {activity.employee_id}")
            
            # In production, you would call:
            # from modules.ems.employee_alerts import EmployeeAlertManager
            # alert_manager = EmployeeAlertManager()
            # result = alert_manager.create_alert(alert_data)
            
            return {
                "success": True,
                "message": "Successfully generated alert",
                "alert_data": alert_data
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate alert: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to generate alert: {str(e)}"
            }
    
    def _map_activity_to_incident_type(self, activity_type: ActivityType) -> str:
        """Map activity type to AIMS incident type"""
        mapping = {
            ActivityType.POLICY_VIOLATION: "compliance_incident",
            ActivityType.SECURITY_EVENT: "security_incident",
            ActivityType.COMPLIANCE_CHECK: "compliance_incident",
            ActivityType.FILE_ACCESS: "operational_incident",
            ActivityType.PERFORMANCE_METRIC: "operational_incident"
        }
        return mapping.get(activity_type, "operational_incident")
    
    def _map_activity_to_alert_type(self, activity_type: ActivityType) -> str:
        """Map activity type to alert type"""
        mapping = {
            ActivityType.POLICY_VIOLATION: "compliance_alert",
            ActivityType.SECURITY_EVENT: "security_alert",
            ActivityType.COMPLIANCE_CHECK: "compliance_alert",
            ActivityType.FILE_ACCESS: "system_alert",
            ActivityType.PERFORMANCE_METRIC: "performance_alert"
        }
        return mapping.get(activity_type, "system_alert")
    
    def _map_severity_to_priority(self, severity: ActivitySeverity) -> str:
        """Map severity to alert priority"""
        mapping = {
            ActivitySeverity.CRITICAL: "critical",
            ActivitySeverity.ERROR: "high",
            ActivitySeverity.WARNING: "medium",
            ActivitySeverity.INFO: "low"
        }
        return mapping.get(severity, "medium")
    
    def get_activities_by_employee(self, employee_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get activities for specific employee"""
        activities = [
            activity.to_dict() 
            for activity in self.activity_logs.values() 
            if activity.employee_id == employee_id
        ]
        
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]
    
    def get_activities_by_type(self, activity_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get activities by type"""
        activities = [
            activity.to_dict() 
            for activity in self.activity_logs.values() 
            if activity.activity_type.value == activity_type
        ]
        
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]
    
    def get_activities_by_severity(self, severity: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get activities by severity"""
        activities = [
            activity.to_dict() 
            for activity in self.activity_logs.values() 
            if activity.severity.value == severity
        ]
        
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing statistics"""
        total_activities = len(self.activity_logs)
        
        if total_activities == 0:
            return {
                "total_activities": 0,
                "routing_stats": {},
                "timestamp": datetime.utcnow().isoformat()
            }
        
        orchestrator_routed = len([a for a in self.activity_logs.values() if a.orchestrator_routed])
        aims_submitted = len([a for a in self.activity_logs.values() if a.aims_submitted])
        alerts_generated = len([a for a in self.activity_logs.values() if a.alert_generated])
        
        # Count by activity type
        type_counts = {}
        for activity_type in ActivityType:
            type_counts[activity_type.value] = len([
                a for a in self.activity_logs.values() 
                if a.activity_type == activity_type
            ])
        
        # Count by severity
        severity_counts = {}
        for severity in ActivitySeverity:
            severity_counts[severity.value] = len([
                a for a in self.activity_logs.values() 
                if a.severity == severity
            ])
        
        return {
            "total_activities": total_activities,
            "routing_stats": {
                "orchestrator_routed": orchestrator_routed,
                "aims_submitted": aims_submitted,
                "alerts_generated": alerts_generated,
                "routing_percentage": {
                    "orchestrator": (orchestrator_routed / total_activities) * 100,
                    "aims": (aims_submitted / total_activities) * 100,
                    "alerts": (alerts_generated / total_activities) * 100
                }
            },
            "type_breakdown": type_counts,
            "severity_breakdown": severity_counts,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for activity logger"""
        return {
            "logger": self.logger_name,
            "version": self.version,
            "status": "healthy",
            "total_activities": len(self.activity_logs),
            "routing_rules_configured": len(self.routing_rules),
            "escalation_rules_configured": len(self.escalation_rules),
            "timestamp": datetime.utcnow().isoformat()
        }
