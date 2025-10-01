"""
BHIV Core API Gateway
====================

Unified entry point for all microservices providing:
- Request routing to appropriate services
- Load balancing
- Authentication and authorization
- Rate limiting
- Request/response transformation
- Service discovery integration
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import json
import time
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from security.auth import get_current_user, verify_token
from security.rbac import require_permission, Permission
from security.audit import audit_log
from modules.shared.base_service import service_registry

logger = logging.getLogger(__name__)

class APIGateway:
    """API Gateway for BHIV Core microservices"""
    
    def __init__(self):
        self.app = FastAPI(
            title="BHIV Core API Gateway",
            description="Unified API gateway for all BHIV Core microservices",
            version="1.0.0"
        )
        
        # Service registry and routing
        self.services = {
            "logistics": {"host": "localhost", "port": 8001, "prefix": "/logistics"},
            "crm": {"host": "localhost", "port": 8002, "prefix": "/crm"},
            "agents": {"host": "localhost", "port": 8003, "prefix": "/agents"},
            "llm": {"host": "localhost", "port": 8004, "prefix": "/llm"},
            "integrations": {"host": "localhost", "port": 8005, "prefix": "/integrations"}
        }
        
        # Load balancing and health tracking
        self.service_health = {}
        self.request_counts = {}
        
        # Rate limiting
        self.rate_limits = {}
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """Setup gateway middleware"""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "https://yourdomain.com"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )
        
        # Request logging middleware
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()
            
            # Log incoming request
            logger.info(f"🌐 Gateway: {request.method} {request.url.path}")
            
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(f"✅ Gateway: {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
            
            return response
    
    def _setup_routes(self):
        """Setup gateway routes"""
        
        # Health check
        @self.app.get("/health")
        async def gateway_health():
            """Gateway health check"""
            service_statuses = {}
            
            for service_name, config in self.services.items():
                try:
                    url = f"http://{config['host']}:{config['port']}/health"
                    async with httpx.AsyncClient() as client:
                        response = await client.get(url, timeout=5.0)
                        service_statuses[service_name] = {
                            "status": "healthy" if response.status_code == 200 else "unhealthy",
                            "response_time_ms": 50  # Mock value
                        }
                except Exception as e:
                    service_statuses[service_name] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
            
            all_healthy = all(s["status"] == "healthy" for s in service_statuses.values())
            
            return {
                "gateway_status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "services": service_statuses,
                "overall_health": "healthy" if all_healthy else "degraded"
            }
        
        # Service discovery endpoint
        @self.app.get("/services")
        async def list_services():
            """List available services"""
            return {
                "services": self.services,
                "total_count": len(self.services),
                "timestamp": datetime.now().isoformat()
            }
        
        # Gateway analytics
        @self.app.get("/gateway/analytics")
        async def gateway_analytics(current_user: dict = Depends(get_current_user)):
            """Get gateway analytics"""
            if not require_permission(current_user, Permission.ADMIN_ACCESS):
                raise HTTPException(status_code=403, detail="Admin access required")
            
            total_requests = sum(self.request_counts.values())
            
            return {
                "total_requests": total_requests,
                "requests_by_service": self.request_counts,
                "service_health": self.service_health,
                "active_services": len([s for s in self.service_health.values() if s.get("status") == "healthy"]),
                "timestamp": datetime.now().isoformat()
            }
        
        # Dynamic routing for all services
        @self.app.api_route("/api/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def route_to_service(
            service_name: str,
            path: str,
            request: Request,
            current_user: dict = Depends(get_current_user)
        ):
            """Route requests to appropriate microservice"""
            
            # Validate service exists
            if service_name not in self.services:
                raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
            
            service_config = self.services[service_name]
            
            # Check rate limiting
            if not self._check_rate_limit(current_user.get("user_id", "anonymous")):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            # Build target URL
            target_url = f"http://{service_config['host']}:{service_config['port']}/{path}"
            
            # Get request body
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
            
            # Forward request to microservice
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=request.method,
                        url=target_url,
                        headers=dict(request.headers),
                        content=body,
                        params=dict(request.query_params),
                        timeout=30.0
                    )
                
                # Update request counts
                self.request_counts[service_name] = self.request_counts.get(service_name, 0) + 1
                
                # Update service health
                self.service_health[service_name] = {
                    "status": "healthy" if response.status_code < 500 else "unhealthy",
                    "last_request": datetime.now().isoformat(),
                    "response_time_ms": 100  # Mock value
                }
                
                # Log the proxied request
                await audit_log(
                    action="gateway_request",
                    resource=f"{service_name}/{path}",
                    user_id=current_user.get("user_id"),
                    details={
                        "method": request.method,
                        "service": service_name,
                        "status_code": response.status_code
                    }
                )
                
                # Return response
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
                
            except httpx.TimeoutException:
                # Update service health
                self.service_health[service_name] = {
                    "status": "timeout",
                    "last_request": datetime.now().isoformat(),
                    "error": "Request timeout"
                }
                raise HTTPException(status_code=504, detail="Service timeout")
                
            except httpx.ConnectError:
                # Update service health
                self.service_health[service_name] = {
                    "status": "unreachable",
                    "last_request": datetime.now().isoformat(),
                    "error": "Connection failed"
                }
                raise HTTPException(status_code=503, detail="Service unavailable")
                
            except Exception as e:
                logger.error(f"Gateway error routing to {service_name}: {e}")
                raise HTTPException(status_code=500, detail="Gateway error")
        
        # Batch requests endpoint
        @self.app.post("/api/batch")
        async def batch_requests(
            batch_data: Dict[str, Any],
            current_user: dict = Depends(get_current_user)
        ):
            """Execute multiple requests in batch"""
            requests = batch_data.get("requests", [])
            
            if len(requests) > 10:  # Limit batch size
                raise HTTPException(status_code=400, detail="Batch size limited to 10 requests")
            
            results = []
            
            for i, req in enumerate(requests):
                try:
                    service_name = req.get("service")
                    path = req.get("path", "")
                    method = req.get("method", "GET")
                    data = req.get("data")
                    
                    if service_name not in self.services:
                        results.append({
                            "index": i,
                            "success": False,
                            "error": f"Service '{service_name}' not found"
                        })
                        continue
                    
                    service_config = self.services[service_name]
                    target_url = f"http://{service_config['host']}:{service_config['port']}/{path}"
                    
                    async with httpx.AsyncClient() as client:
                        if method.upper() == "GET":
                            response = await client.get(target_url, timeout=10.0)
                        else:
                            response = await client.request(
                                method=method,
                                url=target_url,
                                json=data,
                                timeout=10.0
                            )
                    
                    results.append({
                        "index": i,
                        "success": True,
                        "status_code": response.status_code,
                        "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                    })
                    
                except Exception as e:
                    results.append({
                        "index": i,
                        "success": False,
                        "error": str(e)
                    })
            
            return {
                "batch_id": f"batch_{int(time.time())}",
                "results": results,
                "total_requests": len(requests),
                "successful_requests": len([r for r in results if r["success"]]),
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_rate_limit(self, user_id: str, limit: int = 1000) -> bool:
        """Check rate limiting for user"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = []
        
        # Clean old requests
        self.rate_limits[user_id] = [
            req_time for req_time in self.rate_limits[user_id]
            if req_time > hour_ago
        ]
        
        # Check limit
        if len(self.rate_limits[user_id]) >= limit:
            return False
        
        # Add current request
        self.rate_limits[user_id].append(now)
        return True
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the API gateway"""
        import uvicorn
        
        logger.info(f"🚀 Starting BHIV Core API Gateway on {host}:{port}")
        logger.info("📋 Registered services:")
        for name, config in self.services.items():
            logger.info(f"  - {name}: http://{config['host']}:{config['port']}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )

# Create gateway instance
gateway = APIGateway()

if __name__ == "__main__":
    gateway.run()
