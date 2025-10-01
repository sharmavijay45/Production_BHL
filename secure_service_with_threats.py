"""
BHIV Core Secure Service with Threat Mitigation
==============================================

Production-ready secure service integrating:
- Day 1: JWT Authentication & RBAC
- Day 3: Threat Detection & Response Agents
- Proactive Security Monitoring

This service provides comprehensive security with real-time threat protection.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

# Import security components
from security.auth import get_current_user, verify_token
from security.rbac import require_permission, Permission
from security.audit import audit_log
from security.middleware import SecurityMiddleware

# Import threat mitigation agents
from agents.proactive_monitor import security_monitor, process_request, get_security_dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="BHIV Core Secure Service with Threat Mitigation",
    description="Production-grade secure API with intelligent threat protection",
    version="2.0.0"
)

# Security middleware
app.add_middleware(SecurityMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

@app.middleware("http")
async def threat_detection_middleware(request: Request, call_next):
    """Middleware for threat detection and response"""
    start_time = time.time()
    
    # Extract request information
    client_ip = request.client.host
    method = request.method
    endpoint = str(request.url.path)
    headers = dict(request.headers)
    
    # Get request body for analysis
    payload = None
    if method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                payload = body.decode('utf-8')
        except Exception:
            payload = None
    
    # Process through security pipeline
    try:
        is_allowed = await process_request(client_ip, method, endpoint, headers, payload)
        
        if not is_allowed:
            # Log blocked request
            await audit_log(
                action="request_blocked",
                resource=endpoint,
                user_id="system",
                ip_address=client_ip,
                details={
                    "method": method,
                    "endpoint": endpoint,
                    "reason": "threat_detected"
                }
            )
            
            raise HTTPException(
                status_code=403,
                detail="Request blocked due to security policy"
            )
        
        # Process request
        response = await call_next(request)
        
        # Log successful request
        processing_time = time.time() - start_time
        logger.info(f"Request processed: {method} {endpoint} - {response.status_code} - {processing_time:.3f}s")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in threat detection middleware: {e}")
        # Allow request to proceed if middleware fails (fail-open for availability)
        return await call_next(request)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize security monitoring on startup"""
    logger.info("🚀 Starting BHIV Core Secure Service with Threat Mitigation")
    
    # Start security monitoring
    await security_monitor.start_monitoring()
    logger.info("🛡️ Security monitoring activated")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down BHIV Core Secure Service")
    
    # Stop security monitoring
    await security_monitor.stop_monitoring()
    logger.info("🛡️ Security monitoring deactivated")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "security": {
            "authentication": "active",
            "threat_detection": security_monitor.monitoring_active,
            "agents": {
                "detection": security_monitor.detection_agent.running,
                "response": security_monitor.response_agent.running
            }
        }
    }

# Security dashboard endpoint
@app.get("/security/dashboard")
async def security_dashboard(current_user: dict = Depends(get_current_user)):
    """Get security monitoring dashboard"""
    # Require admin permission
    if not require_permission(current_user, Permission.ADMIN_ACCESS):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    dashboard_data = get_security_dashboard()
    
    await audit_log(
        action="security_dashboard_accessed",
        resource="security_dashboard",
        user_id=current_user.get("user_id"),
        ip_address="system",
        details={"dashboard_status": dashboard_data.get("status")}
    )
    
    return dashboard_data

# Threat intelligence endpoint
@app.get("/security/threats")
async def get_threats(
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get recent threat events"""
    # Require security permission
    if not require_permission(current_user, Permission.SECURITY_MANAGE):
        raise HTTPException(status_code=403, detail="Security management permission required")
    
    from agents.threat_detection import get_recent_threats
    threats = get_recent_threats(limit)
    
    await audit_log(
        action="threats_accessed",
        resource="threat_intelligence",
        user_id=current_user.get("user_id"),
        ip_address="system",
        details={"threat_count": len(threats)}
    )
    
    return {
        "threats": threats,
        "count": len(threats),
        "timestamp": datetime.now().isoformat()
    }

# Response statistics endpoint
@app.get("/security/responses")
async def get_response_stats(current_user: dict = Depends(get_current_user)):
    """Get threat response statistics"""
    # Require security permission
    if not require_permission(current_user, Permission.SECURITY_MANAGE):
        raise HTTPException(status_code=403, detail="Security management permission required")
    
    from agents.threat_response import get_response_stats
    stats = get_response_stats()
    
    return {
        "response_stats": stats,
        "timestamp": datetime.now().isoformat()
    }

# Manual IP blocking endpoint
@app.post("/security/block-ip")
async def block_ip(
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Manually block an IP address"""
    # Require admin permission
    if not require_permission(current_user, Permission.ADMIN_ACCESS):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    ip_address = request_data.get("ip_address")
    duration_minutes = request_data.get("duration_minutes", 60)
    reason = request_data.get("reason", "Manual block")
    
    if not ip_address:
        raise HTTPException(status_code=400, detail="IP address required")
    
    # Block the IP
    await security_monitor.response_agent._block_ip(ip_address, duration_minutes)
    
    await audit_log(
        action="manual_ip_block",
        resource="ip_blocking",
        user_id=current_user.get("user_id"),
        ip_address="system",
        details={
            "blocked_ip": ip_address,
            "duration_minutes": duration_minutes,
            "reason": reason
        }
    )
    
    return {
        "success": True,
        "message": f"IP {ip_address} blocked for {duration_minutes} minutes",
        "timestamp": datetime.now().isoformat()
    }

# Unblock IP endpoint
@app.post("/security/unblock-ip")
async def unblock_ip(
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Manually unblock an IP address"""
    # Require admin permission
    if not require_permission(current_user, Permission.ADMIN_ACCESS):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    ip_address = request_data.get("ip_address")
    
    if not ip_address:
        raise HTTPException(status_code=400, detail="IP address required")
    
    # Unblock the IP
    if ip_address in security_monitor.response_agent.blocked_ips:
        security_monitor.response_agent.blocked_ips.remove(ip_address)
        
        await audit_log(
            action="manual_ip_unblock",
            resource="ip_blocking",
            user_id=current_user.get("user_id"),
            ip_address="system",
            details={"unblocked_ip": ip_address}
        )
        
        return {
            "success": True,
            "message": f"IP {ip_address} unblocked",
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(status_code=404, detail="IP not currently blocked")

# Protected LLM endpoint with threat protection
@app.post("/secure/compose")
async def secure_compose(
    request: Request,
    request_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Secure LLM composition endpoint with threat protection"""
    # Check permissions
    if not require_permission(current_user, Permission.LLM_ACCESS):
        raise HTTPException(status_code=403, detail="LLM access permission required")
    
    # Extract and validate input
    prompt = request_data.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    
    # Additional threat analysis on LLM input
    client_ip = request.client.host
    headers = dict(request.headers)
    
    from agents.threat_detection import analyze_request
    threats = analyze_request(client_ip, "POST", "/secure/compose", headers, json.dumps(request_data))
    
    # Block if high-risk threats detected
    high_risk_threats = [t for t in threats if t.threat_level.value in ["high", "critical"]]
    if high_risk_threats:
        await audit_log(
            action="llm_request_blocked",
            resource="llm_compose",
            user_id=current_user.get("user_id"),
            ip_address=client_ip,
            details={
                "threats_detected": len(high_risk_threats),
                "threat_types": [t.threat_type.value for t in high_risk_threats]
            }
        )
        raise HTTPException(status_code=403, detail="Request blocked due to security policy")
    
    # Process LLM request (mock response)
    response = {
        "response": f"Enhanced secure response to: {prompt[:100]}...",
        "model": "secure-llm-v2",
        "timestamp": datetime.now().isoformat(),
        "security": {
            "threats_analyzed": len(threats),
            "user_verified": True,
            "content_filtered": True
        }
    }
    
    await audit_log(
        action="llm_compose",
        resource="llm_compose",
        user_id=current_user.get("user_id"),
        ip_address=client_ip,
        details={
            "prompt_length": len(prompt),
            "threats_detected": len(threats),
            "response_generated": True
        }
    )
    
    return response

# Import and include authentication endpoints
from security.auth import router as auth_router
app.include_router(auth_router, prefix="/auth", tags=["authentication"])

if __name__ == "__main__":
    # Run the secure service
    uvicorn.run(
        "secure_service_with_threats:app",
        host="0.0.0.0",
        port=8080,
        reload=False,  # Disable in production
        log_level="info"
    )
