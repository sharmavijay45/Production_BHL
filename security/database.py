"""
BHIV Core Security Database
==========================

Database operations for security-related data.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from security.models import User, SecurityEvent, ThreatEvent, AuditLog

logger = logging.getLogger(__name__)

class SecurityDatabase:
    """In-memory security database for demo purposes"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.security_events: List[SecurityEvent] = []
        self.threat_events: List[ThreatEvent] = []
        self.audit_logs: List[AuditLog] = []
        
        # Initialize with demo data
        self._initialize_demo_data()
    
    def _initialize_demo_data(self):
        """Initialize with demo users and events"""
        from security.models import DEMO_USERS
        
        for user in DEMO_USERS:
            self.users[user.id] = user
        
        logger.info(f"Initialized security database with {len(self.users)} demo users")
    
    # User operations
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def create_user(self, user: User) -> bool:
        """Create a new user"""
        try:
            self.users[user.id] = user
            logger.info(f"Created user: {user.username}")
            return True
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False
    
    def update_user(self, user: User) -> bool:
        """Update existing user"""
        try:
            if user.id in self.users:
                self.users[user.id] = user
                logger.info(f"Updated user: {user.username}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user"""
        try:
            if user_id in self.users:
                user = self.users.pop(user_id)
                logger.info(f"Deleted user: {user.username}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            return False
    
    # Security event operations
    def log_security_event(self, event: SecurityEvent) -> bool:
        """Log a security event"""
        try:
            self.security_events.append(event)
            logger.info(f"Logged security event: {event.event_type.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
            return False
    
    def get_security_events(
        self, 
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """Get security events with optional filtering"""
        events = self.security_events
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if event_type:
            events = [e for e in events if e.event_type.value == event_type]
        
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda x: x.timestamp, reverse=True)
        return events[:limit]
    
    # Threat event operations
    def log_threat_event(self, event: ThreatEvent) -> bool:
        """Log a threat event"""
        try:
            self.threat_events.append(event)
            logger.warning(f"Logged threat event: {event.threat_type} from {event.source_ip}")
            return True
        except Exception as e:
            logger.error(f"Failed to log threat event: {e}")
            return False
    
    def get_threat_events(
        self,
        severity: Optional[str] = None,
        blocked_only: bool = False,
        limit: int = 100
    ) -> List[ThreatEvent]:
        """Get threat events with optional filtering"""
        events = self.threat_events
        
        if severity:
            events = [e for e in events if e.severity.value == severity]
        
        if blocked_only:
            events = [e for e in events if e.blocked]
        
        # Sort by detection time (newest first) and limit
        events.sort(key=lambda x: x.detected_at, reverse=True)
        return events[:limit]
    
    # Audit log operations
    def log_audit_event(self, log: AuditLog) -> bool:
        """Log an audit event"""
        try:
            self.audit_logs.append(log)
            logger.info(f"Logged audit event: {log.action} on {log.resource}")
            return True
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False
    
    def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs with optional filtering"""
        logs = self.audit_logs
        
        if user_id:
            logs = [l for l in logs if l.user_id == user_id]
        
        if resource:
            logs = [l for l in logs if l.resource == resource]
        
        if action:
            logs = [l for l in logs if l.action == action]
        
        # Sort by timestamp (newest first) and limit
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        return logs[:limit]
    
    # Statistics and reporting
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        return {
            "total_users": len(self.users),
            "total_security_events": len(self.security_events),
            "total_threat_events": len(self.threat_events),
            "total_audit_logs": len(self.audit_logs),
            "recent_threats": len([e for e in self.threat_events if 
                                 (datetime.utcnow() - e.detected_at).days < 1]),
            "blocked_threats": len([e for e in self.threat_events if e.blocked])
        }
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a specific user"""
        user = self.get_user(user_id)
        if not user:
            return {}
        
        user_events = self.get_security_events(user_id=user_id)
        user_audits = self.get_audit_logs(user_id=user_id)
        
        return {
            "user_id": user_id,
            "username": user.username,
            "role": user.role,
            "status": user.status.value,
            "total_events": len(user_events),
            "total_audits": len(user_audits),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "failed_attempts": user.failed_login_attempts
        }

# Middleware for database transactions
class DatabaseTransactionMiddleware:
    """Middleware for handling database transactions"""
    
    def __init__(self, db: SecurityDatabase):
        self.db = db
    
    def __call__(self, request, call_next):
        """Process request with transaction handling"""
        try:
            # In a real implementation, this would start a database transaction
            response = call_next(request)
            # Commit transaction on success
            return response
        except Exception as e:
            # Rollback transaction on error
            logger.error(f"Database transaction failed: {e}")
            raise

# Global security database instance
security_db = SecurityDatabase()

def get_security_db() -> SecurityDatabase:
    """Get the global security database instance"""
    return security_db

# Convenience functions
def log_user_login(user_id: str, success: bool, ip_address: str = "127.0.0.1") -> bool:
    """Log a user login attempt"""
    from security.models import SecurityEvent, SecurityEventType, ThreatLevel
    
    event = SecurityEvent(
        id=None,  # Will be auto-generated
        event_type=SecurityEventType.LOGIN_SUCCESS if success else SecurityEventType.LOGIN_FAILURE,
        user_id=user_id,
        ip_address=ip_address,
        success=success,
        threat_level=ThreatLevel.LOW if success else ThreatLevel.MEDIUM
    )
    
    return security_db.log_security_event(event)

def log_permission_check(user_id: str, resource: str, action: str, granted: bool) -> bool:
    """Log a permission check"""
    from security.models import SecurityEvent, SecurityEventType, ThreatLevel
    
    event = SecurityEvent(
        id=None,
        event_type=SecurityEventType.PERMISSION_DENIED if not granted else SecurityEventType.ADMIN_ACTION,
        user_id=user_id,
        resource=resource,
        action=action,
        success=granted,
        threat_level=ThreatLevel.LOW if granted else ThreatLevel.MEDIUM
    )
    
    return security_db.log_security_event(event)

def log_threat_detection(threat_type: str, source_ip: str, blocked: bool = False) -> bool:
    """Log a threat detection"""
    from security.models import ThreatEvent, ThreatLevel
    
    event = ThreatEvent(
        id=None,
        threat_type=threat_type,
        severity=ThreatLevel.HIGH if blocked else ThreatLevel.MEDIUM,
        source_ip=source_ip,
        target_resource="/api",
        description=f"Detected {threat_type} from {source_ip}",
        blocked=blocked
    )
    
    return security_db.log_threat_event(event)
