"""
BHIV Core Security - Authentication & Authorization
=================================================

JWT-based authentication and RBAC for BHIV Core services.
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "bhiv_core_secret_key_2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Security scheme
security = HTTPBearer(auto_error=False)

# User roles
class UserRole:
    ADMIN = "admin"
    OPS = "ops"
    SALES = "sales"
    CUSTOMER = "customer"
    SUPPORT = "support"

# Default users for demo
DEFAULT_USERS = {
    "admin": {
        "username": "admin",
        "password_hash": bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        "role": UserRole.ADMIN,
        "permissions": ["read", "write", "delete", "admin"]
    },
    "customer": {
        "username": "customer",
        "password_hash": bcrypt.hashpw("customer123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        "role": UserRole.CUSTOMER,
        "permissions": ["read"]
    }
}

def create_access_token(user_data: Dict[str, Any]) -> str:
    """Create JWT access token"""
    try:
        # Token payload
        payload = {
            "sub": user_data.get("username", "anonymous"),
            "role": user_data.get("role", UserRole.CUSTOMER),
            "permissions": user_data.get("permissions", ["read"]),
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow()
        }
        
        # Create token
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.info(f"🎫 Created access token for user: {user_data.get('username')}")
        
        return token
        
    except Exception as e:
        logger.error(f"❌ Error creating access token: {e}")
        raise HTTPException(status_code=500, detail="Token creation failed")

def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        # Decode token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Extract user info
        user_info = {
            "username": payload.get("sub"),
            "role": payload.get("role"),
            "permissions": payload.get("permissions", []),
            "exp": payload.get("exp"),
            "iat": payload.get("iat")
        }
        
        logger.info(f"✅ Token verified for user: {user_info['username']}")
        return user_info
        
    except jwt.ExpiredSignatureError:
        logger.warning("⚠️ Token has expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"⚠️ Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"❌ Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed")

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with username and password"""
    try:
        # Check if user exists
        if username not in DEFAULT_USERS:
            logger.warning(f"⚠️ Authentication failed: User '{username}' not found")
            return None
        
        user = DEFAULT_USERS[username]
        
        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
            logger.info(f"✅ User '{username}' authenticated successfully")
            return {
                "username": user["username"],
                "role": user["role"],
                "permissions": user["permissions"]
            }
        else:
            logger.warning(f"⚠️ Authentication failed: Invalid password for user '{username}'")
            return None
            
    except Exception as e:
        logger.error(f"❌ Authentication error: {e}")
        return None

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """Get current authenticated user from token"""
    if not credentials:
        return None
    
    try:
        return verify_token(credentials.credentials)
    except HTTPException:
        return None

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Require authentication (raises exception if not authenticated)"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    return verify_token(credentials.credentials)

def require_role(required_role: str):
    """Decorator to require specific role"""
    def role_checker(user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
        if user["role"] != required_role and user["role"] != UserRole.ADMIN:
            raise HTTPException(
                status_code=403, 
                detail=f"Role '{required_role}' required"
            )
        return user
    return role_checker

def require_permission(required_permission: str):
    """Decorator to require specific permission"""
    def permission_checker(user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
        if required_permission not in user.get("permissions", []):
            raise HTTPException(
                status_code=403, 
                detail=f"Permission '{required_permission}' required"
            )
        return user
    return permission_checker

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

# Demo function for testing
def create_demo_token() -> str:
    """Create a demo token for testing"""
    demo_user = {
        "username": "demo_user",
        "role": UserRole.CUSTOMER,
        "permissions": ["read"]
    }
    return create_access_token(demo_user)

if __name__ == "__main__":
    # Test the authentication system
    print("🧪 Testing BHIV Core Authentication System")
    print("=" * 50)
    
    # Test token creation
    demo_token = create_demo_token()
    print(f"📝 Demo token created: {demo_token[:50]}...")
    
    # Test token verification
    user_info = verify_token(demo_token)
    print(f"✅ Token verified: {user_info}")
    
    # Test user authentication
    auth_result = authenticate_user("admin", "admin123")
    print(f"🔐 Admin authentication: {auth_result}")
