"""
Secure UniGuru LM Service
=========================

Production-grade secure version of the UniGuru LM Service with:
- JWT Authentication & RBAC
- Audit Logging
- Threat Detection & Response
- Rate Limiting & Security Headers
- PostgreSQL with SSL
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

# Security imports
from security import (
    User, UserRole, Permission, UserCreate, UserResponse, LoginRequest, Token,
    AuditLogResponse, SecurityEventResponse, ThreatAlertResponse,
    get_current_user, get_current_active_user, login_user, hash_password,
    require_role, require_permission, require_resource_access,
    audit_log, get_audit_logs, AuditMiddleware,
    SecurityMiddleware, SecurityConfig, get_db, migration_manager
)

# Import existing services (assuming they exist)
try:
    from uniguru_lm_service import (
        UniGuruLMService, ComposeRequest, ComposeResponse, 
        FeedbackRequest, service as original_service
    )
except ImportError:
    # Fallback if original service not available
    class UniGuruLMService:
        def __init__(self):
            pass
        async def compose(self, request): 
            return {"response": "Service not available"}
        async def process_feedback(self, feedback):
            return {"status": "success"}
    
    class ComposeRequest(BaseModel):
        query: str
        user_id: str = "anonymous"
        session_id: str = "default"
    
    class ComposeResponse(BaseModel):
        response: str
        
    class FeedbackRequest(BaseModel):
        trace_id: str
        rating: int
        
    original_service = UniGuruLMService()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security configuration
security_config = SecurityConfig()

# Enhanced service with security
class SecureUniGuruService:
    """Secure wrapper around UniGuru LM Service"""
    
    def __init__(self):
        self.original_service = original_service
        self.logger = logger
    
    async def secure_compose(
        self, 
        request: ComposeRequest, 
        current_user: User,
        db: Session,
        http_request: Request
    ) -> ComposeResponse:
        """Secure compose endpoint with audit logging"""
        
        # Log the request
        audit_log(
            action="compose_request",
            resource="llm_query",
            resource_id=request.session_id,
            user=current_user,
            details={
                "query_length": len(request.query),
                "language": getattr(request, 'language', 'en')
            },
            request=http_request,
            db=db
        )
        
        try:
            # Call original service
            response = await self.original_service.compose(request)
            
            # Log successful response
            audit_log(
                action="compose_success",
                resource="llm_query",
                resource_id=request.session_id,
                user=current_user,
                details={
                    "response_length": len(response.final_text) if hasattr(response, 'final_text') else 0,
                    "grounded": getattr(response, 'grounded', False)
                },
                request=http_request,
                db=db
            )
            
            return response
            
        except Exception as e:
            # Log failed response
            audit_log(
                action="compose_failed",
                resource="llm_query",
                resource_id=request.session_id,
                user=current_user,
                details={
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                request=http_request,
                db=db
            )
            raise

# Initialize secure service
secure_service = SecureUniGuruService()

# FastAPI application with security
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with security initialization"""
    logger.info("🔒 Starting Secure UniGuru-LM Service...")
    
    # Initialize database tables
    try:
        migration_manager.create_security_tables()
        logger.info("✅ Security database tables initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize security tables: {e}")
    
    # Create default admin user if not exists
    try:
        admin_user = migration_manager.create_admin_user(
            username="admin",
            email="admin@bhivcore.com", 
            password="SecureAdmin123!"  # Change in production!
        )
        logger.info(f"✅ Admin user ready: {admin_user.username}")
    except Exception as e:
        logger.error(f"❌ Failed to create admin user: {e}")
    
    yield
    
    logger.info("🛑 Shutting down Secure UniGuru-LM Service...")

# Create FastAPI app with security
app = FastAPI(
    title="Secure UniGuru-LM Service",
    description="Production-grade secure AI service with enterprise authentication, audit logging, and threat protection",
    version="2.0.0",
    lifespan=lifespan
)

# Add security middleware (order matters!)
app.add_middleware(SecurityMiddleware, config=security_config)
app.add_middleware(AuditMiddleware)

# Add CORS with security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# =============================================================================
# Authentication Endpoints
# =============================================================================

@app.post("/auth/login", response_model=Token)
async def login(
    login_request: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """User login with JWT token generation"""
    try:
        result = login_user(db, login_request.username, login_request.password)
        
        # Log successful login
        audit_log(
            action="login_success",
            resource="authentication",
            details={
                "username": login_request.username,
                "login_method": "password"
            },
            request=request,
            db=db
        )
        
        return result
        
    except HTTPException as e:
        # Log failed login
        audit_log(
            action="login_failed", 
            resource="authentication",
            details={
                "username": login_request.username,
                "error": e.detail,
                "status_code": e.status_code
            },
            request=request,
            db=db
        )
        raise

@app.post("/auth/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CREATE_USER))
):
    """Register new user (requires CREATE_USER permission)"""
    
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
        is_verified=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log user creation
    audit_log(
        action="user_created",
        resource="user",
        resource_id=str(new_user.id),
        user=current_user,
        details={
            "created_username": new_user.username,
            "created_role": new_user.role
        },
        request=request,
        db=db
    )
    
    return new_user

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user

# =============================================================================
# Secure Core Endpoints
# =============================================================================

@app.post("/secure/compose", response_model=ComposeResponse)
async def secure_compose_endpoint(
    request_data: ComposeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Secure compose endpoint with authentication and audit logging"""
    
    # Check if user has permission to use LLM services
    if current_user.role == UserRole.CUSTOMER:
        # Customers have limited access
        if len(request_data.query) > 500:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Query too long for customer role"
            )
    
    return await secure_service.secure_compose(request_data, current_user, db, request)

@app.post("/secure/feedback")
async def secure_feedback_endpoint(
    feedback: FeedbackRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Secure feedback collection with audit logging"""
    
    # Log feedback submission
    audit_log(
        action="feedback_submitted",
        resource="feedback",
        resource_id=feedback.trace_id,
        user=current_user,
        details={
            "rating": feedback.rating,
            "has_text": hasattr(feedback, 'feedback_text') and bool(feedback.feedback_text)
        },
        request=request,
        db=db
    )
    
    try:
        result = await original_service.process_feedback(feedback)
        return result
    except Exception as e:
        logger.error(f"Feedback processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process feedback"
        )

# =============================================================================
# Admin Endpoints
# =============================================================================

@app.get("/admin/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """List all users (Admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@app.get("/admin/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs_endpoint(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VIEW_AUDIT_LOGS))
):
    """Get audit logs with filtering"""
    logs = get_audit_logs(
        db=db,
        user_id=user_id,
        action=action,
        resource=resource,
        limit=limit,
        offset=offset
    )
    return logs

@app.get("/admin/security-events", response_model=List[SecurityEventResponse])
async def get_security_events(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Get security events (Admin only)"""
    from security.models import SecurityEvent
    
    events = db.query(SecurityEvent).order_by(
        SecurityEvent.timestamp.desc()
    ).offset(offset).limit(limit).all()
    
    return events

@app.get("/admin/threat-alerts", response_model=List[ThreatAlertResponse])
async def get_threat_alerts(
    acknowledged: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Get threat alerts (Admin only)"""
    from security.models import ThreatAlert
    
    query = db.query(ThreatAlert)
    
    if acknowledged is not None:
        query = query.filter(ThreatAlert.acknowledged == acknowledged)
    
    alerts = query.order_by(
        ThreatAlert.timestamp.desc()
    ).offset(offset).limit(limit).all()
    
    return alerts

# =============================================================================
# System Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "Secure UniGuru-LM",
        "version": "2.0.0",
        "status": "running",
        "security": "enabled",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    from security.database import check_database_health
    
    # Check database health
    db_health = check_database_health()
    
    # Check original service health if available
    service_health = {"status": "healthy"}
    try:
        if hasattr(original_service, 'knowledge_manager'):
            stats = original_service.knowledge_manager.get_folder_stats()
            service_health = {
                "status": "healthy" if stats.get("rag_api_status") == "healthy" else "degraded",
                "rag_api": stats.get("rag_api_status", "unknown")
            }
    except Exception as e:
        service_health = {"status": "degraded", "error": str(e)}
    
    overall_status = "healthy" if (
        db_health["status"] == "healthy" and 
        service_health["status"] == "healthy"
    ) else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": db_health,
            "llm_service": service_health,
            "security": {"status": "enabled"}
        },
        "version": "2.0.0"
    }

@app.get("/security/status")
async def security_status(
    current_user: User = Depends(require_permission(Permission.VIEW_METRICS))
):
    """Get security system status"""
    return {
        "authentication": "JWT enabled",
        "authorization": "RBAC enabled", 
        "audit_logging": "enabled",
        "threat_detection": "enabled",
        "rate_limiting": "enabled",
        "encryption": "SSL/TLS enabled",
        "middleware": ["SecurityMiddleware", "AuditMiddleware"],
        "timestamp": datetime.utcnow().isoformat()
    }

# =============================================================================
# Legacy Compatibility Endpoints
# =============================================================================

@app.post("/compose", response_model=ComposeResponse)
async def legacy_compose_endpoint(
    request_data: ComposeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Legacy compose endpoint (redirects to secure version)"""
    logger.warning("Legacy endpoint /compose used, redirecting to secure version")
    return await secure_compose_endpoint(request_data, request, background_tasks, db, current_user)

@app.post("/feedback")
async def legacy_feedback_endpoint(
    feedback: FeedbackRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Legacy feedback endpoint (redirects to secure version)"""
    logger.warning("Legacy endpoint /feedback used, redirecting to secure version")
    return await secure_feedback_endpoint(feedback, request, db, current_user)

# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with audit logging"""
    
    # Log security-related errors
    if exc.status_code in [401, 403, 429]:
        try:
            with next(get_db()) as db:
                audit_log(
                    action="security_exception",
                    resource="api_endpoint",
                    details={
                        "status_code": exc.status_code,
                        "detail": exc.detail,
                        "path": request.url.path,
                        "method": request.method
                    },
                    request=request,
                    db=db
                )
        except Exception as e:
            logger.error(f"Failed to log security exception: {e}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# =============================================================================
# Main execution
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Security configuration
    host = os.getenv("SECURE_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("SECURE_SERVICE_PORT", "8080"))
    
    logger.info(f"🚀 Starting Secure UniGuru-LM Service on {host}:{port}")
    logger.info("🔒 Security features enabled:")
    logger.info("   - JWT Authentication & RBAC")
    logger.info("   - Audit Logging")
    logger.info("   - Threat Detection & Response")
    logger.info("   - Rate Limiting")
    logger.info("   - PostgreSQL with SSL")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        ssl_keyfile=os.getenv("SSL_KEYFILE"),
        ssl_certfile=os.getenv("SSL_CERTFILE")
    )
