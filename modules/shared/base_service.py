"""
Base Service Class for BHIV Core Microservices
==============================================

Common functionality and patterns for all microservices including:
- Security integration
- Threat protection
- Health checks
- Logging
- Metrics
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn

# Import shared security components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from security.auth import get_current_user, verify_token
from security.rbac import require_permission, Permission
from security.audit import audit_log
from security.middleware import SecurityMiddleware
from agents.proactive_monitor import process_request

logger = logging.getLogger(__name__)

class BaseService:
    """Base class for all BHIV Core microservices"""
    
    def __init__(self, 
                 service_name: str,
                 service_version: str = "1.0.0",
                 port: int = 8000,
                 enable_security: bool = True,
                 enable_threat_protection: bool = True,
                 enable_observability: bool = True):
        
        self.service_name = service_name
        self.service_version = service_version
        self.port = port
        self.enable_security = enable_security
        self.enable_threat_protection = enable_threat_protection
        self.enable_observability = enable_observability
        
        # Initialize observability
        if self.enable_observability:
            self._setup_observability()
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title=f"BHIV Core {service_name} Service",
            description=f"Microservice for {service_name.lower()} operations",
            version=service_version,
            openapi_tags=self._get_openapi_tags()
        )
        
        # Setup middleware and security
        self._setup_middleware()
        self._setup_security()
        self._setup_base_routes()
        
        # Setup observability routes
        if self.enable_observability:
            self._setup_observability_routes()
    
    def _get_openapi_tags(self) -> List[Dict]:
        """Get OpenAPI tags for the service"""
        return [
            {
                "name": "health",
                "description": "Service health and status endpoints"
            },
            {
                "name": "security",
                "description": "Security and authentication endpoints"
            },
            {
                "name": self.service_name.lower(),
                "description": f"{self.service_name} business logic endpoints"
            }
        ]
    
    def _setup_middleware(self):
        """Setup common middleware"""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Observability middleware
        if self.enable_observability:
            self.app.add_middleware(TracingMiddleware)
            self.app.middleware("http")(metrics_middleware())
        
        # Security middleware
        if self.enable_security:
            self.app.add_middleware(SecurityMiddleware)
        
        # Threat protection middleware
        if self.enable_threat_protection:
            self.app.middleware("http")(self._threat_protection_middleware)
    
    async def _threat_protection_middleware(self, request: Request, call_next):
        """Threat protection middleware"""
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
                logger.warning(f" blocked request from {client_ip} to {endpoint}")
                raise HTTPException(
                    status_code=403,
                    detail="Request blocked due to security policy"
                )
            
            # Process request
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in threat protection middleware: {e}")
            # Fail-open for availability
            return await call_next(request)
    
    def _setup_security(self):
        """Setup security components"""
        if self.enable_security:
            self.security = HTTPBearer()
    
    def _setup_base_routes(self):
        """Setup common routes for all services"""
        
        @self.app.get("/health", tags=["health"])
        async def health_check():
            """Service health check"""
            return {
                "service": self.service_name,
                "version": self.service_version,
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "security_enabled": self.enable_security,
                "threat_protection": self.enable_threat_protection
            }
        
        @self.app.get("/info", tags=["health"])
        async def service_info():
            """Service information"""
            return {
                "service": self.service_name,
                "version": self.service_version,
                "description": f"BHIV Core {self.service_name} microservice",
                "openapi_url": f"/openapi.json",
                "docs_url": f"/docs",
                "capabilities": self._get_service_capabilities(),
                "dependencies": self._get_service_dependencies()
            }
        
        if self.enable_security:
            @self.app.get("/auth/verify", tags=["security"])
            async def verify_auth(current_user: dict = Depends(get_current_user)):
                """Verify authentication token"""
                return {
                    "authenticated": True,
                    "user": current_user,
                    "service": self.service_name,
                    "timestamp": datetime.now().isoformat()
                }
    
    def _get_service_capabilities(self) -> List[str]:
        """Get service capabilities - override in subclasses"""
        return [
            "health_monitoring",
            "authentication" if self.enable_security else None,
            "threat_protection" if self.enable_threat_protection else None
        ]
    
    def _get_service_dependencies(self) -> List[str]:
        """Get service dependencies - override in subclasses"""
        return []
    
    def add_route(self, path: str, methods: List[str], handler, **kwargs):
        """Add a route to the service"""
        for method in methods:
            self.app.add_api_route(path, handler, methods=[method], **kwargs)
    
    def include_router(self, router, **kwargs):
        """Include a router in the service"""
        self.app.include_router(router, **kwargs)
    
    def run(self, host: str = "0.0.0.0", debug: bool = False):
        """Run the service"""
        logger.info(f" Starting {self.service_name} service on {host}:{self.port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=self.port,
            reload=debug,
            log_level="info"
        )
    
    async def startup(self):
        """Service startup tasks - override in subclasses"""
        logger.info(f" {self.service_name} service started successfully")
    
    async def shutdown(self):
        """Service shutdown tasks - override in subclasses"""
        logger.info(f" {self.service_name} service shutting down")

class ServiceRegistry:
    """Simple service registry for microservices discovery"""
    
    def __init__(self):
        self.services: Dict[str, Dict] = {}
    
    def register_service(self, name: str, host: str, port: int, health_endpoint: str = "/health"):
        """Register a service"""
        self.services[name] = {
            "name": name,
            "host": host,
            "port": port,
            "url": f"http://{host}:{port}",
            "health_endpoint": health_endpoint,
            "registered_at": datetime.now().isoformat(),
            "status": "registered"
        }
        logger.info(f"📋 Registered service: {name} at {host}:{port}")
    
    def get_service(self, name: str) -> Optional[Dict]:
        """Get service information"""
        return self.services.get(name)
    
    def list_services(self) -> Dict[str, Dict]:
        """List all registered services"""
        return self.services
    
    def unregister_service(self, name: str):
        """Unregister a service"""
        if name in self.services:
            del self.services[name]
            logger.info(f"📋 Unregistered service: {name}")

# Global service registry
service_registry = ServiceRegistry()

def get_service_registry() -> ServiceRegistry:
    """Get the global service registry"""
    return service_registry
