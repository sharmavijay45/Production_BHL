#!/usr/bin/env python3
"""
EMS Service - Employee Management System Integration
===================================================

Main service for handling EMS integration, activity logging, and employee management.
"""

import os
import sys
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.shared.base_service import BaseService
from security.auth import get_current_user
from security.rbac import require_permission, Permission
from security.audit import audit_log
from utils.logger import get_logger

logger = get_logger(__name__)

class EMSActivityLog(BaseModel):
    """EMS Activity Log Entry"""
    employee_id: str
    activity_type: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: str = Field(default="info")  # info, warning, error, critical
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AIMSSubmission(BaseModel):
    """AIMS Submission Data"""
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    incident_type: str
    severity: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="open")
    assigned_to: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EmployeeAlert(BaseModel):
    """Employee Alert Data"""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    alert_type: str
    message: str
    priority: str = Field(default="medium")  # low, medium, high, critical
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    read: bool = Field(default=False)
    action_required: bool = Field(default=False)

class EMSService(BaseService):
    """EMS Service for employee management and activity tracking"""
    
    def __init__(self):
        super().__init__()
        self.service_name = "ems_service"
        self.version = "1.0.0"
        
        # In-memory storage for demo (in production, use database)
        self.activity_logs: List[EMSActivityLog] = []
        self.aims_submissions: List[AIMSSubmission] = []
        self.employee_alerts: List[EmployeeAlert] = []
        
        # Employee registry (demo data)
        self.employees = {
            "emp_001": {"name": "John Doe", "department": "IT", "role": "Developer"},
            "emp_002": {"name": "Jane Smith", "department": "HR", "role": "Manager"},
            "emp_003": {"name": "Mike Johnson", "department": "Security", "role": "Analyst"},
            "emp_004": {"name": "Sarah Wilson", "department": "Operations", "role": "Coordinator"}
        }
        
        logger.info("✅ EMS Service initialized")

    def log_activity(self, activity: EMSActivityLog) -> Dict[str, Any]:
        """Log employee activity"""
        try:
            # Validate employee exists
            if activity.employee_id not in self.employees:
                raise ValueError(f"Employee {activity.employee_id} not found")
            
            # Store activity log
            self.activity_logs.append(activity)
            
            # Auto-escalate to AIMS if critical
            if activity.severity == "critical":
                aims_submission = AIMSSubmission(
                    employee_id=activity.employee_id,
                    incident_type="critical_activity",
                    severity="high",
                    description=f"Critical activity logged: {activity.description}",
                    metadata={"source_activity": activity.dict()}
                )
                self.submit_to_aims(aims_submission)
            
            # Create employee alert if warning or error
            if activity.severity in ["warning", "error", "critical"]:
                alert = EmployeeAlert(
                    employee_id=activity.employee_id,
                    alert_type="activity_alert",
                    message=f"Activity alert: {activity.description}",
                    priority="high" if activity.severity == "critical" else "medium",
                    action_required=activity.severity in ["error", "critical"]
                )
                self.create_employee_alert(alert)
            
            logger.info(f"✅ Activity logged for employee {activity.employee_id}: {activity.activity_type}")
            
            return {
                "status": "success",
                "message": "Activity logged successfully",
                "activity_id": str(uuid.uuid4()),
                "escalations": {
                    "aims_submitted": activity.severity == "critical",
                    "alert_created": activity.severity in ["warning", "error", "critical"]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to log activity: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to log activity: {str(e)}"
            }

    def submit_to_aims(self, submission: AIMSSubmission) -> Dict[str, Any]:
        """Submit incident to AIMS"""
        try:
            # Store AIMS submission
            self.aims_submissions.append(submission)
            
            # Auto-assign based on incident type
            if submission.incident_type == "security_incident":
                submission.assigned_to = "security_team"
            elif submission.incident_type == "hr_incident":
                submission.assigned_to = "hr_team"
            else:
                submission.assigned_to = "ops_team"
            
            logger.info(f"✅ AIMS submission created: {submission.incident_id}")
            
            return {
                "status": "success",
                "incident_id": submission.incident_id,
                "assigned_to": submission.assigned_to,
                "message": "Incident submitted to AIMS successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to submit to AIMS: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to submit to AIMS: {str(e)}"
            }

    def create_employee_alert(self, alert: EmployeeAlert) -> Dict[str, Any]:
        """Create employee alert"""
        try:
            # Store alert
            self.employee_alerts.append(alert)
            
            # Send notification (stub - in production, integrate with notification service)
            self._send_notification(alert)
            
            logger.info(f"✅ Employee alert created: {alert.alert_id}")
            
            return {
                "status": "success",
                "alert_id": alert.alert_id,
                "message": "Employee alert created successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create employee alert: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to create employee alert: {str(e)}"
            }

    def _send_notification(self, alert: EmployeeAlert):
        """Send notification to employee (stub implementation)"""
        employee = self.employees.get(alert.employee_id, {})
        logger.info(f"📧 Notification sent to {employee.get('name', alert.employee_id)}: {alert.message}")

    def get_employee_activities(self, employee_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get activities for specific employee"""
        activities = [
            activity.dict() for activity in self.activity_logs 
            if activity.employee_id == employee_id
        ]
        return sorted(activities, key=lambda x: x['timestamp'], reverse=True)[:limit]

    def get_aims_submissions(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get AIMS submissions"""
        submissions = [sub.dict() for sub in self.aims_submissions]
        if status:
            submissions = [sub for sub in submissions if sub['status'] == status]
        return sorted(submissions, key=lambda x: x['timestamp'], reverse=True)[:limit]

    def get_employee_alerts(self, employee_id: Optional[str] = None, unread_only: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
        """Get employee alerts"""
        alerts = [alert.dict() for alert in self.employee_alerts]
        
        if employee_id:
            alerts = [alert for alert in alerts if alert['employee_id'] == employee_id]
        
        if unread_only:
            alerts = [alert for alert in alerts if not alert['read']]
        
        return sorted(alerts, key=lambda x: x['timestamp'], reverse=True)[:limit]

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get EMS dashboard statistics"""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        # Count recent activities by severity
        recent_activities = [log for log in self.activity_logs if log.timestamp >= last_24h]
        severity_counts = {}
        for activity in recent_activities:
            severity_counts[activity.severity] = severity_counts.get(activity.severity, 0) + 1
        
        # Count open AIMS submissions
        open_aims = len([sub for sub in self.aims_submissions if sub.status == "open"])
        
        # Count unread alerts
        unread_alerts = len([alert for alert in self.employee_alerts if not alert.read])
        
        return {
            "total_employees": len(self.employees),
            "total_activities": len(self.activity_logs),
            "recent_activities_24h": len(recent_activities),
            "severity_breakdown": severity_counts,
            "open_aims_submissions": open_aims,
            "unread_alerts": unread_alerts,
            "timestamp": now.isoformat()
        }

# FastAPI app for EMS service
app = FastAPI(title="EMS Service", version="1.0.0")
ems_service = EMSService()

@app.post("/activity/log")
async def log_activity(
    activity: EMSActivityLog,
    current_user = Depends(get_current_user)
):
    """Log employee activity"""
    result = ems_service.log_activity(activity)
    
    # Audit log the action
    await audit_log(
        action="log_activity",
        user_id=current_user.get("sub", "unknown"),
        details={
            "employee_id": activity.employee_id,
            "activity_type": activity.activity_type,
            "severity": activity.severity
        }
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@app.post("/aims/submit")
async def submit_to_aims(
    submission: AIMSSubmission,
    current_user = Depends(get_current_user)
):
    """Submit incident to AIMS"""
    result = ems_service.submit_to_aims(submission)
    
    # Audit log the action
    await audit_log(
        action="aims_submission",
        user_id=current_user.get("sub", "unknown"),
        details={
            "incident_id": submission.incident_id,
            "incident_type": submission.incident_type,
            "severity": submission.severity
        }
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@app.post("/alerts/create")
async def create_alert(
    alert: EmployeeAlert,
    current_user = Depends(get_current_user)
):
    """Create employee alert"""
    result = ems_service.create_employee_alert(alert)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@app.get("/activities/{employee_id}")
async def get_activities(
    employee_id: str,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """Get activities for employee"""
    return ems_service.get_employee_activities(employee_id, limit)

@app.get("/aims/submissions")
async def get_aims_submissions(
    status: Optional[str] = None,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """Get AIMS submissions"""
    return ems_service.get_aims_submissions(status, limit)

@app.get("/alerts")
async def get_alerts(
    employee_id: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """Get employee alerts"""
    return ems_service.get_employee_alerts(employee_id, unread_only, limit)

@app.get("/dashboard/stats")
async def get_dashboard_stats(current_user = Depends(get_current_user)):
    """Get EMS dashboard statistics"""
    return ems_service.get_dashboard_stats()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "ems_service",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
