#!/usr/bin/env python3
"""
Employee Alert Manager
======================

Manages employee alerts, notifications, and alert routing.
Integrates with orchestrator for intelligent alert processing.
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from utils.logger import get_logger

logger = get_logger(__name__)

class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Alert types"""
    SYSTEM_ALERT = "system_alert"
    SECURITY_ALERT = "security_alert"
    COMPLIANCE_ALERT = "compliance_alert"
    PERFORMANCE_ALERT = "performance_alert"
    POLICY_ALERT = "policy_alert"
    TRAINING_ALERT = "training_alert"

class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    READ = "read"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"

@dataclass
class EmployeeAlert:
    """Employee alert data structure"""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str = ""
    alert_type: AlertType = AlertType.SYSTEM_ALERT
    priority: AlertPriority = AlertPriority.MEDIUM
    title: str = ""
    message: str = ""
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    action_required: bool = False
    action_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "employee_id": self.employee_id,
            "alert_type": self.alert_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "action_required": self.action_required,
            "action_url": self.action_url,
            "metadata": self.metadata,
            "tags": self.tags
        }

class EmployeeAlertManager:
    """Manager for employee alerts and notifications"""
    
    def __init__(self):
        self.manager_name = "EmployeeAlertManager"
        self.version = "1.0.0"
        
        # In-memory storage for demo (in production, use database)
        self.alerts: Dict[str, EmployeeAlert] = {}
        self.alert_templates = self._setup_alert_templates()
        self.notification_channels = self._setup_notification_channels()
        
        logger.info("✅ Employee Alert Manager initialized")
    
    def _setup_alert_templates(self) -> Dict[str, Dict[str, Any]]:
        """Setup alert templates"""
        return {
            "security_breach": {
                "title": "Security Alert: Potential Breach Detected",
                "priority": AlertPriority.CRITICAL,
                "action_required": True,
                "template": "A potential security breach has been detected. Immediate action required."
            },
            "compliance_violation": {
                "title": "Compliance Alert: Policy Violation",
                "priority": AlertPriority.HIGH,
                "action_required": True,
                "template": "A compliance policy violation has been detected. Please review and take corrective action."
            },
            "training_due": {
                "title": "Training Alert: Mandatory Training Due",
                "priority": AlertPriority.MEDIUM,
                "action_required": True,
                "template": "You have mandatory training that is due. Please complete by the deadline."
            },
            "system_maintenance": {
                "title": "System Alert: Scheduled Maintenance",
                "priority": AlertPriority.LOW,
                "action_required": False,
                "template": "Scheduled system maintenance will occur. Plan accordingly."
            }
        }
    
    def _setup_notification_channels(self) -> Dict[str, Dict[str, Any]]:
        """Setup notification channels"""
        return {
            "email": {"enabled": True, "priority_threshold": "low"},
            "sms": {"enabled": True, "priority_threshold": "high"},
            "push": {"enabled": True, "priority_threshold": "medium"},
            "slack": {"enabled": True, "priority_threshold": "medium"}
        }
    
    def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new employee alert"""
        try:
            # Create alert object
            alert = EmployeeAlert(
                employee_id=alert_data.get("employee_id", ""),
                alert_type=AlertType(alert_data.get("alert_type", "system_alert")),
                priority=AlertPriority(alert_data.get("priority", "medium")),
                title=alert_data.get("title", ""),
                message=alert_data.get("message", ""),
                action_required=alert_data.get("action_required", False),
                action_url=alert_data.get("action_url"),
                metadata=alert_data.get("metadata", {}),
                tags=alert_data.get("tags", [])
            )
            
            # Set expiration if specified
            if "expires_in_hours" in alert_data:
                alert.expires_at = datetime.utcnow() + timedelta(hours=alert_data["expires_in_hours"])
            
            # Store alert
            self.alerts[alert.alert_id] = alert
            
            # Send notifications
            self._send_notifications(alert)
            
            logger.info(f"✅ Employee alert created: {alert.alert_id}")
            
            return {
                "status": "success",
                "alert_id": alert.alert_id,
                "message": "Alert created successfully",
                "notifications_sent": True
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create employee alert: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to create alert: {str(e)}"
            }
    
    def create_alert_from_template(self, template_name: str, employee_id: str, 
                                 custom_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create alert from template"""
        try:
            if template_name not in self.alert_templates:
                return {
                    "status": "error",
                    "message": f"Template '{template_name}' not found"
                }
            
            template = self.alert_templates[template_name]
            custom_data = custom_data or {}
            
            alert_data = {
                "employee_id": employee_id,
                "alert_type": custom_data.get("alert_type", "system_alert"),
                "priority": template["priority"].value,
                "title": custom_data.get("title", template["title"]),
                "message": custom_data.get("message", template["template"]),
                "action_required": template["action_required"],
                "metadata": {"template_used": template_name, **custom_data.get("metadata", {})}
            }
            
            return self.create_alert(alert_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to create alert from template: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to create alert from template: {str(e)}"
            }
    
    def _send_notifications(self, alert: EmployeeAlert):
        """Send notifications through appropriate channels"""
        try:
            priority_level = alert.priority.value
            
            for channel, config in self.notification_channels.items():
                if not config["enabled"]:
                    continue
                
                # Check priority threshold
                threshold = config["priority_threshold"]
                if self._should_notify(priority_level, threshold):
                    self._send_notification_via_channel(alert, channel)
            
        except Exception as e:
            logger.error(f"❌ Failed to send notifications: {str(e)}")
    
    def _should_notify(self, alert_priority: str, threshold: str) -> bool:
        """Check if alert meets notification threshold"""
        priority_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return priority_levels.get(alert_priority, 1) >= priority_levels.get(threshold, 1)
    
    def _send_notification_via_channel(self, alert: EmployeeAlert, channel: str):
        """Send notification via specific channel (stub implementation)"""
        logger.info(f"📧 Notification sent via {channel} to {alert.employee_id}: {alert.title}")
    
    def mark_alert_read(self, alert_id: str) -> Dict[str, Any]:
        """Mark alert as read"""
        try:
            if alert_id not in self.alerts:
                return {
                    "status": "error",
                    "message": f"Alert {alert_id} not found"
                }
            
            alert = self.alerts[alert_id]
            if alert.status == AlertStatus.ACTIVE:
                alert.status = AlertStatus.READ
                alert.read_at = datetime.utcnow()
            
            return {
                "status": "success",
                "alert_id": alert_id,
                "message": "Alert marked as read"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to mark alert as read: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to mark alert as read: {str(e)}"
            }
    
    def acknowledge_alert(self, alert_id: str, notes: str = "") -> Dict[str, Any]:
        """Acknowledge alert"""
        try:
            if alert_id not in self.alerts:
                return {
                    "status": "error",
                    "message": f"Alert {alert_id} not found"
                }
            
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            
            if notes:
                alert.metadata["acknowledgment_notes"] = notes
            
            return {
                "status": "success",
                "alert_id": alert_id,
                "message": "Alert acknowledged"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to acknowledge alert: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to acknowledge alert: {str(e)}"
            }
    
    def resolve_alert(self, alert_id: str, resolution_notes: str = "") -> Dict[str, Any]:
        """Resolve alert"""
        try:
            if alert_id not in self.alerts:
                return {
                    "status": "error",
                    "message": f"Alert {alert_id} not found"
                }
            
            alert = self.alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            
            if resolution_notes:
                alert.metadata["resolution_notes"] = resolution_notes
            
            return {
                "status": "success",
                "alert_id": alert_id,
                "message": "Alert resolved"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to resolve alert: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to resolve alert: {str(e)}"
            }
    
    def get_employee_alerts(self, employee_id: str, status: Optional[str] = None, 
                          limit: int = 50) -> List[Dict[str, Any]]:
        """Get alerts for specific employee"""
        alerts = [
            alert.to_dict() 
            for alert in self.alerts.values() 
            if alert.employee_id == employee_id
        ]
        
        if status:
            alerts = [alert for alert in alerts if alert["status"] == status]
        
        # Sort by creation time (newest first)
        alerts.sort(key=lambda x: x["created_at"], reverse=True)
        
        return alerts[:limit]
    
    def get_alerts_by_priority(self, priority: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get alerts by priority"""
        alerts = [
            alert.to_dict() 
            for alert in self.alerts.values() 
            if alert.priority.value == priority
        ]
        
        alerts.sort(key=lambda x: x["created_at"], reverse=True)
        return alerts[:limit]
    
    def get_active_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        alerts = [
            alert.to_dict() 
            for alert in self.alerts.values() 
            if alert.status == AlertStatus.ACTIVE
        ]
        
        alerts.sort(key=lambda x: x["created_at"], reverse=True)
        return alerts[:limit]
    
    def cleanup_expired_alerts(self) -> int:
        """Clean up expired alerts"""
        now = datetime.utcnow()
        expired_count = 0
        
        expired_ids = []
        for alert_id, alert in self.alerts.items():
            if alert.expires_at and alert.expires_at <= now:
                expired_ids.append(alert_id)
        
        for alert_id in expired_ids:
            del self.alerts[alert_id]
            expired_count += 1
        
        if expired_count > 0:
            logger.info(f"🧹 Cleaned up {expired_count} expired alerts")
        
        return expired_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        now = datetime.utcnow()
        
        # Count by status
        status_counts = {}
        for status in AlertStatus:
            status_counts[status.value] = len([
                a for a in self.alerts.values() 
                if a.status == status
            ])
        
        # Count by priority
        priority_counts = {}
        for priority in AlertPriority:
            priority_counts[priority.value] = len([
                a for a in self.alerts.values() 
                if a.priority == priority
            ])
        
        # Count requiring action
        action_required_count = len([
            a for a in self.alerts.values() 
            if a.action_required and a.status == AlertStatus.ACTIVE
        ])
        
        # Recent alerts (last 24 hours)
        last_24h = now - timedelta(hours=24)
        recent_count = len([
            a for a in self.alerts.values() 
            if a.created_at >= last_24h
        ])
        
        return {
            "total_alerts": len(self.alerts),
            "status_breakdown": status_counts,
            "priority_breakdown": priority_counts,
            "action_required": action_required_count,
            "recent_alerts_24h": recent_count,
            "timestamp": now.isoformat()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for alert manager"""
        return {
            "manager": self.manager_name,
            "version": self.version,
            "status": "healthy",
            "total_alerts": len(self.alerts),
            "active_alerts": len([a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]),
            "timestamp": datetime.utcnow().isoformat()
        }
