"""
BHIV Core Security - Role-Based Access Control (RBAC)
====================================================

Role-based access control system for BHIV Core services.
"""

from enum import Enum
from typing import Dict, List, Set, Callable, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class Permission(Enum):
    """System permissions"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"
    MONITOR = "monitor"
    CONFIGURE = "configure"
    
    # Additional permissions for production
    READ_ACCESS = "read_access"
    WRITE_ACCESS = "write_access"
    ADMIN_ACCESS = "admin_access"

class Role(Enum):
    """System roles"""
    ADMIN = "admin"
    OPS = "ops"
    SALES = "sales"
    CUSTOMER = "customer"
    SUPPORT = "support"

# Role-Permission mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.ADMIN,
        Permission.EXECUTE,
        Permission.MONITOR,
        Permission.CONFIGURE,
        Permission.READ_ACCESS,
        Permission.WRITE_ACCESS,
        Permission.ADMIN_ACCESS
    },
    Role.OPS: {
        Permission.READ,
        Permission.WRITE,
        Permission.EXECUTE,
        Permission.MONITOR,
        Permission.CONFIGURE,
        Permission.READ_ACCESS,
        Permission.WRITE_ACCESS
    },
    Role.SALES: {
        Permission.READ,
        Permission.WRITE,
        Permission.MONITOR,
        Permission.READ_ACCESS,
        Permission.WRITE_ACCESS
    },
    Role.CUSTOMER: {
        Permission.READ,
        Permission.READ_ACCESS
    },
    Role.SUPPORT: {
        Permission.READ,
        Permission.MONITOR,
        Permission.READ_ACCESS
    }
}

def has_permission(user_role: str, required_permission: str) -> bool:
    """Check if a role has a specific permission"""
    try:
        role = Role(user_role)
        permission = Permission(required_permission)
        
        result = permission in ROLE_PERMISSIONS.get(role, set())
        logger.debug(f"Permission check: {user_role} -> {required_permission} = {result}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"Invalid role or permission: {e}")
        return False

def get_role_permissions(user_role: str) -> List[str]:
    """Get all permissions for a role"""
    try:
        role = Role(user_role)
        permissions = ROLE_PERMISSIONS.get(role, set())
        return [p.value for p in permissions]
        
    except ValueError as e:
        logger.warning(f"Invalid role: {e}")
        return []

def can_access_resource(user_role: str, resource: str, action: str) -> bool:
    """Check if a role can perform an action on a resource"""
    
    # Resource-specific permission mapping
    resource_permissions = {
        "agents": {
            "read": Permission.READ,
            "execute": Permission.EXECUTE,
            "configure": Permission.CONFIGURE
        },
        "metrics": {
            "read": Permission.MONITOR,
            "write": Permission.CONFIGURE
        },
        "logs": {
            "read": Permission.MONITOR,
            "delete": Permission.ADMIN
        },
        "users": {
            "read": Permission.READ,
            "write": Permission.ADMIN,
            "delete": Permission.ADMIN
        },
        "system": {
            "configure": Permission.ADMIN,
            "monitor": Permission.MONITOR
        }
    }
    
    try:
        role = Role(user_role)
        
        # Get required permission for resource/action
        if resource not in resource_permissions:
            logger.warning(f"Unknown resource: {resource}")
            return False
            
        if action not in resource_permissions[resource]:
            logger.warning(f"Unknown action '{action}' for resource '{resource}'")
            return False
            
        required_permission = resource_permissions[resource][action]
        
        # Check if role has permission
        result = required_permission in ROLE_PERMISSIONS.get(role, set())
        
        logger.info(f"Access check: {user_role} -> {resource}:{action} = {result}")
        return result
        
    except ValueError as e:
        logger.warning(f"Invalid role: {e}")
        return False

def check_permission(user_role: str, required_permission: str) -> bool:
    """Check if a role has a specific permission (alias for has_permission)"""
    return has_permission(user_role, required_permission)

def get_accessible_resources(user_role: str) -> Dict[str, List[str]]:
    """Get all resources and actions accessible to a role"""
    
    accessible = {}
    
    # All possible resources and actions
    all_resources = {
        "agents": ["read", "execute", "configure"],
        "metrics": ["read", "write"],
        "logs": ["read", "delete"],
        "users": ["read", "write", "delete"],
        "system": ["configure", "monitor"]
    }
    
    for resource, actions in all_resources.items():
        accessible_actions = []
        for action in actions:
            if can_access_resource(user_role, resource, action):
                accessible_actions.append(action)
        
        if accessible_actions:
            accessible[resource] = accessible_actions
    
    return accessible

def require_permission(required_permission: Permission):
    """Decorator to require specific permission for function access"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # In a real implementation, you would extract user role from request context
            # For now, we'll assume it's passed as a parameter or available in context
            user_role = kwargs.get('user_role', 'customer')  # Default to least privileged
            
            if isinstance(user_role, str):
                if has_permission(user_role, required_permission.value):
                    return func(*args, **kwargs)
                else:
                    logger.warning(f"Permission denied: {user_role} lacks {required_permission.value}")
                    raise PermissionError(f"Insufficient permissions: {required_permission.value} required")
            else:
                logger.error("Invalid user role format")
                raise ValueError("Invalid user role")
        
        return wrapper
    return decorator

class RBACError(Exception):
    """RBAC-specific exception"""
    pass

class PermissionDeniedError(RBACError):
    """Permission denied exception"""
    pass

if __name__ == "__main__":
    # Test RBAC system
    print("🧪 Testing BHIV Core RBAC System")
    print("=" * 50)
    
    test_roles = ["admin", "customer", "ops"]
    
    for role in test_roles:
        print(f"\n👤 Role: {role}")
        permissions = get_role_permissions(role)
        print(f"   Permissions: {permissions}")
        
        # Test specific access
        print(f"   Can read agents: {can_access_resource(role, 'agents', 'read')}")
        print(f"   Can configure system: {can_access_resource(role, 'system', 'configure')}")
        print(f"   Can delete users: {can_access_resource(role, 'users', 'delete')}")
