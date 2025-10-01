"""
Security Middleware
==================

Comprehensive security middleware for FastAPI applications.
"""

import time
import json
import uuid
from typing import Dict, Set, Optional, Callable
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
from collections import defaultdict, deque
import asyncio
import ipaddress
from .models import User, SecurityEvent, ThreatLevel
from .database import DatabaseTransaction
from .auth import verify_token, TokenData
import re

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration settings"""
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = 100  # requests per window
    RATE_LIMIT_WINDOW = 300    # window in seconds (5 minutes)
    RATE_LIMIT_BURST = 20      # burst requests allowed
    
    # Authentication
    AUTH_REQUIRED_PATHS = ["/admin", "/api/v1"]
    AUTH_EXCLUDED_PATHS = ["/health", "/docs", "/openapi.json", "/login", "/register"]
    
    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }
    
    # Threat detection
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 1800  # 30 minutes
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\bor\b.*=.*)",
        r"(\band\b.*=.*)",
        r"(--|#|/\*|\*/)",
        r"(\bexec\b|\bexecute\b)",
        r"(\bsp_\w+)",
        r"(\bxp_\w+)"
    ]
    
    # IP blocking
    BLOCKED_IPS: Set[str] = set()
    TRUSTED_IPS: Set[str] = {"127.0.0.1", "::1"}

class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, datetime] = {}
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed based on rate limiting"""
        now = datetime.utcnow()
        
        # Check if IP is temporarily blocked
        if client_ip in self.blocked_ips:
            if now < self.blocked_ips[client_ip]:
                return False
            else:
                del self.blocked_ips[client_ip]
        
        # Clean old requests
        window_start = now - timedelta(seconds=self.config.RATE_LIMIT_WINDOW)
        client_requests = self.requests[client_ip]
        
        while client_requests and client_requests[0] < window_start:
            client_requests.popleft()
        
        # Check rate limit
        if len(client_requests) >= self.config.RATE_LIMIT_REQUESTS:
            # Block IP temporarily
            self.blocked_ips[client_ip] = now + timedelta(seconds=300)  # 5 minutes
            logger.warning(f"Rate limit exceeded for IP {client_ip}, blocking temporarily")
            return False
        
        # Add current request
        client_requests.append(now)
        return True
    
    def get_remaining_requests(self, client_ip: str) -> int:
        """Get remaining requests for client"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.config.RATE_LIMIT_WINDOW)
        client_requests = self.requests[client_ip]
        
        # Clean old requests
        while client_requests and client_requests[0] < window_start:
            client_requests.popleft()
        
        return max(0, self.config.RATE_LIMIT_REQUESTS - len(client_requests))

class ThreatDetector:
    """Threat detection system"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.sql_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in config.SQL_INJECTION_PATTERNS]
        self.failed_attempts: Dict[str, int] = defaultdict(int)
        self.locked_ips: Dict[str, datetime] = {}
    
    def detect_sql_injection(self, request: Request) -> bool:
        """Detect SQL injection attempts"""
        try:
            # Check query parameters
            for param, value in request.query_params.items():
                if self._contains_sql_injection(str(value)):
                    return True
            
            # Check path parameters
            if self._contains_sql_injection(request.url.path):
                return True
            
            # Check headers (some attacks use headers)
            suspicious_headers = ["user-agent", "referer", "x-forwarded-for"]
            for header in suspicious_headers:
                value = request.headers.get(header, "")
                if self._contains_sql_injection(value):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in SQL injection detection: {e}")
            return False
    
    def _contains_sql_injection(self, text: str) -> bool:
        """Check if text contains SQL injection patterns"""
        if not text:
            return False
        
        text_lower = text.lower()
        return any(pattern.search(text_lower) for pattern in self.sql_patterns)
    
    def detect_brute_force(self, client_ip: str, failed: bool = False) -> bool:
        """Detect brute force attacks"""
        if failed:
            self.failed_attempts[client_ip] += 1
            
            if self.failed_attempts[client_ip] >= self.config.MAX_FAILED_ATTEMPTS:
                # Lock IP
                self.locked_ips[client_ip] = datetime.utcnow() + timedelta(seconds=self.config.LOCKOUT_DURATION)
                logger.warning(f"Brute force detected from {client_ip}, locking for {self.config.LOCKOUT_DURATION} seconds")
                return True
        else:
            # Reset on successful login
            self.failed_attempts[client_ip] = 0
        
        return False
    
    def is_ip_locked(self, client_ip: str) -> bool:
        """Check if IP is locked due to brute force"""
        if client_ip in self.locked_ips:
            if datetime.utcnow() < self.locked_ips[client_ip]:
                return True
            else:
                del self.locked_ips[client_ip]
                del self.failed_attempts[client_ip]
        
        return False
    
    def detect_anomalous_behavior(self, request: Request) -> Optional[str]:
        """Detect anomalous behavior patterns"""
        anomalies = []
        
        # Check for suspicious user agents
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "masscan", "zap"]
        if any(agent in user_agent for agent in suspicious_agents):
            anomalies.append("suspicious_user_agent")
        
        # Check for directory traversal
        path = request.url.path
        if "../" in path or "..%2f" in path.lower() or "..%5c" in path.lower():
            anomalies.append("directory_traversal")
        
        # Check for XSS attempts
        query_string = str(request.query_params)
        xss_patterns = ["<script", "javascript:", "onerror=", "onload=", "alert("]
        if any(pattern in query_string.lower() for pattern in xss_patterns):
            anomalies.append("xss_attempt")
        
        # Check for command injection
        cmd_patterns = ["|", "&", ";", "`", "$", "(", ")", "{", "}"]
        if any(pattern in query_string for pattern in cmd_patterns):
            anomalies.append("command_injection")
        
        return ",".join(anomalies) if anomalies else None

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""
    
    def __init__(self, app, config: SecurityConfig = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.rate_limiter = RateLimiter(self.config)
        self.threat_detector = ThreatDetector(self.config)
        self.security_bearer = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware dispatch method"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        try:
            # 1. IP Blocking Check
            if client_ip in self.config.BLOCKED_IPS:
                return self._create_error_response(
                    "IP address blocked",
                    status.HTTP_403_FORBIDDEN
                )
            
            # 2. Brute Force Protection
            if self.threat_detector.is_ip_locked(client_ip):
                return self._create_error_response(
                    "IP address temporarily locked due to suspicious activity",
                    status.HTTP_423_LOCKED
                )
            
            # 3. Rate Limiting
            if not self.rate_limiter.is_allowed(client_ip):
                return self._create_error_response(
                    "Rate limit exceeded",
                    status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # 4. Threat Detection
            threat_detected = await self._detect_threats(request, client_ip)
            if threat_detected:
                return self._create_error_response(
                    "Security threat detected",
                    status.HTTP_403_FORBIDDEN
                )
            
            # 5. Authentication Check
            auth_result = await self._check_authentication(request)
            if isinstance(auth_result, Response):
                return auth_result
            
            # Add user info to request state
            if auth_result:
                request.state.user = auth_result
                request.state.user_id = auth_result.user_id
            
            # 6. Process Request
            response = await call_next(request)
            
            # 7. Add Security Headers
            self._add_security_headers(response)
            
            # 8. Log Security Event
            await self._log_security_event(request, response, client_ip, time.time() - start_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return self._create_error_response(
                "Internal security error",
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _detect_threats(self, request: Request, client_ip: str) -> bool:
        """Detect various security threats"""
        threats_detected = []
        
        # SQL Injection Detection
        if self.threat_detector.detect_sql_injection(request):
            threats_detected.append("sql_injection")
        
        # Anomalous Behavior Detection
        anomaly = self.threat_detector.detect_anomalous_behavior(request)
        if anomaly:
            threats_detected.append(anomaly)
        
        # Log threats if detected
        if threats_detected:
            await self._log_threat_event(request, client_ip, threats_detected)
            return True
        
        return False
    
    async def _check_authentication(self, request: Request) -> Optional[TokenData]:
        """Check authentication requirements"""
        path = request.url.path
        
        # Check if path requires authentication
        requires_auth = any(auth_path in path for auth_path in self.config.AUTH_REQUIRED_PATHS)
        is_excluded = any(excluded in path for excluded in self.config.AUTH_EXCLUDED_PATHS)
        
        if not requires_auth or is_excluded:
            return None
        
        # Extract token
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"}
            )
        
        token = authorization.split(" ")[1]
        
        try:
            # Verify token
            token_data = verify_token(token)
            return token_data
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        for header, value in self.config.SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Add rate limiting headers
        response.headers["X-RateLimit-Limit"] = str(self.config.RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Window"] = str(self.config.RATE_LIMIT_WINDOW)
    
    def _create_error_response(self, message: str, status_code: int) -> JSONResponse:
        """Create standardized error response"""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": message,
                "timestamp": datetime.utcnow().isoformat(),
                "status_code": status_code
            }
        )
    
    async def _log_security_event(self, request: Request, response: Response, client_ip: str, duration: float):
        """Log security events asynchronously"""
        try:
            event_data = {
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
                "status_code": response.status_code,
                "duration_ms": int(duration * 1000),
                "user_agent": request.headers.get("user-agent", ""),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Log to file
            logger.info("Security Event", extra={"security_event": event_data})
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    async def _log_threat_event(self, request: Request, client_ip: str, threats: list):
        """Log threat detection events"""
        try:
            with DatabaseTransaction() as db:
                security_event = SecurityEvent(
                    event_type="threat_detected",
                    severity=ThreatLevel.HIGH.value,
                    ip_address=client_ip,
                    description=f"Threats detected: {', '.join(threats)}",
                    details={
                        "threats": threats,
                        "method": request.method,
                        "path": request.url.path,
                        "user_agent": request.headers.get("user-agent", ""),
                        "query_params": dict(request.query_params)
                    }
                )
                db.add(security_event)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to log threat event: {e}")

class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced CORS middleware with security controls"""
    
    def __init__(self, app, allowed_origins: list = None, allowed_methods: list = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["http://localhost:3000", "http://localhost:8080"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, origin)
            return response
        
        response = await call_next(request)
        self._add_cors_headers(response, origin)
        return response
    
    def _add_cors_headers(self, response: Response, origin: str):
        """Add CORS headers with security validation"""
        if origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            response.headers["Access-Control-Allow-Origin"] = "null"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
        response.headers["Access-Control-Max-Age"] = "3600"
        response.headers["Access-Control-Allow-Credentials"] = "true"

# Export main components
__all__ = [
    "SecurityConfig",
    "SecurityMiddleware", 
    "CORSSecurityMiddleware",
    "RateLimiter",
    "ThreatDetector"
]
