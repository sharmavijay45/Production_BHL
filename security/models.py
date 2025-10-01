"""
BHIV Core Security Models
========================

Data models for security-related entities.
"""

from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import uuid

class ThreatLevel(Enum):
    """Threat severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class UserStatus(Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LOCKED = "locked"

class SecurityEventType(Enum):
    """Types of security events"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    THREAT_DETECTED = "threat_detected"
    THREAT_BLOCKED = "threat_blocked"
    ADMIN_ACTION = "admin_action"

@dataclass
class User:
    """User model for authentication and authorization"""
    id: str
    username: str
    email: str
    role: str
    status: UserStatus = UserStatus.ACTIVE
    created_at: datetime = None
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "failed_login_attempts": self.failed_login_attempts,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user from dictionary"""
        return cls(
            id=data.get("id"),
            username=data["username"],
            email=data["email"],
            role=data["role"],
            status=UserStatus(data.get("status", "active")),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            last_login=datetime.fromisoformat(data["last_login"]) if data.get("last_login") else None,
            failed_login_attempts=data.get("failed_login_attempts", 0),
            metadata=data.get("metadata", {})
        )

@dataclass
class SecurityEvent:
    """Security event model for audit logging"""
    id: str
    event_type: SecurityEventType
    user_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    success: bool
    threat_level: ThreatLevel = ThreatLevel.LOW
    details: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert security event to dictionary"""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource": self.resource,
            "action": self.action,
            "success": self.success,
            "threat_level": self.threat_level.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityEvent':
        """Create security event from dictionary"""
        return cls(
            id=data.get("id"),
            event_type=SecurityEventType(data["event_type"]),
            user_id=data.get("user_id"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            resource=data.get("resource"),
            action=data.get("action"),
            success=data["success"],
            threat_level=ThreatLevel(data.get("threat_level", "low")),
            details=data.get("details", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None
        )

@dataclass
class ThreatEvent:
    """Threat detection event model"""
    id: str
    threat_type: str
    severity: ThreatLevel
    source_ip: str
    target_resource: str
    description: str
    detected_at: datetime = None
    blocked: bool = False
    response_actions: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()
        if self.response_actions is None:
            self.response_actions = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert threat event to dictionary"""
        return {
            "id": self.id,
            "threat_type": self.threat_type,
            "severity": self.severity.value,
            "source_ip": self.source_ip,
            "target_resource": self.target_resource,
            "description": self.description,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "blocked": self.blocked,
            "response_actions": self.response_actions,
            "metadata": self.metadata
        }

@dataclass
class AuditLog:
    """Audit log entry model"""
    id: str
    user_id: str
    action: str
    resource: str
    resource_id: Optional[str]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime = None
    success: bool = True
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "success": self.success
        }

# Demo/Test data
DEMO_USERS = [
    User(
        id="admin-001",
        username="admin",
        email="admin@bhiv.com",
        role="admin",
        status=UserStatus.ACTIVE
    ),
    User(
        id="ops-001", 
        username="ops_user",
        email="ops@bhiv.com",
        role="ops",
        status=UserStatus.ACTIVE
    ),
    User(
        id="customer-001",
        username="demo_customer",
        email="customer@example.com", 
        role="customer",
        status=UserStatus.ACTIVE
    )
]

def get_demo_user(role: str) -> Optional[User]:
    """Get a demo user by role"""
    for user in DEMO_USERS:
        if user.role == role:
            return user
    return None

def create_security_event(
    event_type: SecurityEventType,
    user_id: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None
) -> SecurityEvent:
    """Create a security event"""
    return SecurityEvent(
        id=str(uuid.uuid4()),
        event_type=event_type,
        user_id=user_id,
        ip_address="127.0.0.1",  # Demo IP
        success=success,
        details=details or {}
    )

def create_threat_event(
    threat_type: str,
    severity: ThreatLevel,
    source_ip: str,
    description: str
) -> ThreatEvent:
    """Create a threat event"""
    return ThreatEvent(
        id=str(uuid.uuid4()),
        threat_type=threat_type,
        severity=severity,
        source_ip=source_ip,
        target_resource="/api/v1",
        description=description
    )
