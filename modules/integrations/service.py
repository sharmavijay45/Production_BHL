"""
BHIV Core Integrations Microservice
==================================

Handles external API integrations and third-party service connections:
- External API management
- Webhook handling
- Data synchronization
- Integration monitoring
- API rate limiting
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum
import json
import aiohttp
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.shared.base_service import BaseService
from security.auth import get_current_user
from security.rbac import require_permission, Permission
from security.audit import audit_log

logger = logging.getLogger(__name__)

# Enums
class IntegrationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"

class IntegrationType(str, Enum):
    REST_API = "rest_api"
    WEBHOOK = "webhook"
    DATABASE = "database"
    FILE_SYNC = "file_sync"
    MESSAGING = "messaging"

class SyncStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"

# Pydantic Models
class Integration(BaseModel):
    """External integration configuration"""
    id: Optional[str] = None
    name: str = Field(..., description="Integration name")
    integration_type: IntegrationType = Field(..., description="Type of integration")
    description: Optional[str] = None
    endpoint_url: Optional[HttpUrl] = None
    api_key: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    status: IntegrationStatus = Field(default=IntegrationStatus.INACTIVE)
    rate_limit: int = Field(default=100, description="Requests per minute")
    timeout_seconds: int = Field(default=30)
    retry_attempts: int = Field(default=3)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None

class APIRequest(BaseModel):
    """API request model"""
    id: Optional[str] = None
    integration_id: str = Field(..., description="Integration ID")
    method: str = Field(..., description="HTTP method")
    endpoint: str = Field(..., description="API endpoint")
    headers: Dict[str, str] = Field(default_factory=dict)
    payload: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    status_code: Optional[int] = None
    success: bool = Field(default=False)
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    created_at: Optional[datetime] = None

class Webhook(BaseModel):
    """Webhook configuration"""
    id: Optional[str] = None
    integration_id: str = Field(..., description="Integration ID")
    name: str = Field(..., description="Webhook name")
    url: HttpUrl = Field(..., description="Webhook URL")
    secret: Optional[str] = None
    events: List[str] = Field(..., description="Events to trigger webhook")
    active: bool = Field(default=True)
    retry_on_failure: bool = Field(default=True)
    created_at: Optional[datetime] = None

class SyncJob(BaseModel):
    """Data synchronization job"""
    id: Optional[str] = None
    integration_id: str = Field(..., description="Integration ID")
    job_type: str = Field(..., description="Type of sync job")
    source: str = Field(..., description="Data source")
    destination: str = Field(..., description="Data destination")
    status: SyncStatus = Field(default=SyncStatus.PENDING)
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    records_processed: int = Field(default=0)
    records_total: Optional[int] = None
    error_count: int = Field(default=0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    next_run: Optional[datetime] = None

class IntegrationsService(BaseService):
    """Integrations microservice"""
    
    def __init__(self):
        super().__init__(
            service_name="Integrations",
            service_version="1.0.0",
            port=8005
        )
        
        # In-memory storage (replace with database in production)
        self.integrations: Dict[str, Integration] = {}
        self.api_requests: Dict[str, APIRequest] = {}
        self.webhooks: Dict[str, Webhook] = {}
        self.sync_jobs: Dict[str, SyncJob] = {}
        
        # Rate limiting tracking
        self.rate_limits: Dict[str, List[datetime]] = {}
        
        self._setup_routes()
        self._initialize_sample_data()
    
    def _get_service_capabilities(self) -> List[str]:
        """Get integrations service capabilities"""
        return super()._get_service_capabilities() + [
            "external_api_management",
            "webhook_handling",
            "data_synchronization",
            "integration_monitoring",
            "rate_limiting",
            "error_handling"
        ]
    
    def _get_service_dependencies(self) -> List[str]:
        """Get service dependencies"""
        return []
    
    def _setup_routes(self):
        """Setup integration routes"""
        
        # Integration Management Routes
        @self.app.get("/integrations", tags=["integrations"])
        async def list_integrations(
            status: Optional[IntegrationStatus] = Query(None, description="Filter by status"),
            integration_type: Optional[IntegrationType] = Query(None, description="Filter by type"),
            current_user: dict = Depends(get_current_user)
        ):
            """List integrations"""
            if not require_permission(current_user, Permission.INTEGRATIONS_READ):
                raise HTTPException(status_code=403, detail="Integrations read permission required")
            
            integrations = list(self.integrations.values())
            
            if status:
                integrations = [i for i in integrations if i.status == status]
            
            if integration_type:
                integrations = [i for i in integrations if i.integration_type == integration_type]
            
            return {
                "integrations": integrations,
                "total_count": len(integrations),
                "active_count": len([i for i in self.integrations.values() if i.status == IntegrationStatus.ACTIVE])
            }
        
        @self.app.post("/integrations", tags=["integrations"])
        async def create_integration(
            integration: Integration,
            current_user: dict = Depends(get_current_user)
        ):
            """Create new integration"""
            if not require_permission(current_user, Permission.INTEGRATIONS_WRITE):
                raise HTTPException(status_code=403, detail="Integrations write permission required")
            
            integration.id = f"int_{len(self.integrations) + 1:06d}"
            integration.created_at = datetime.now()
            integration.updated_at = datetime.now()
            
            self.integrations[integration.id] = integration
            
            await audit_log(
                action="integration_create",
                resource="integrations",
                user_id=current_user.get("user_id"),
                details={"integration_id": integration.id, "type": integration.integration_type}
            )
            
            return {"success": True, "integration": integration}
        
        @self.app.put("/integrations/{integration_id}/test", tags=["integrations"])
        async def test_integration(
            integration_id: str,
            current_user: dict = Depends(get_current_user)
        ):
            """Test integration connection"""
            if not require_permission(current_user, Permission.INTEGRATIONS_WRITE):
                raise HTTPException(status_code=403, detail="Integrations write permission required")
            
            if integration_id not in self.integrations:
                raise HTTPException(status_code=404, detail="Integration not found")
            
            integration = self.integrations[integration_id]
            
            try:
                # Test connection based on integration type
                test_result = await self._test_integration_connection(integration)
                
                # Update integration status
                integration.status = IntegrationStatus.ACTIVE if test_result["success"] else IntegrationStatus.ERROR
                integration.updated_at = datetime.now()
                
                await audit_log(
                    action="integration_test",
                    resource="integrations",
                    user_id=current_user.get("user_id"),
                    details={"integration_id": integration_id, "test_result": test_result["success"]}
                )
                
                return test_result
                
            except Exception as e:
                integration.status = IntegrationStatus.ERROR
                integration.updated_at = datetime.now()
                
                return {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        # API Request Routes
        @self.app.post("/integrations/{integration_id}/request", tags=["api"])
        async def make_api_request(
            integration_id: str,
            request_data: Dict[str, Any],
            background_tasks: BackgroundTasks,
            current_user: dict = Depends(get_current_user)
        ):
            """Make API request through integration"""
            if not require_permission(current_user, Permission.INTEGRATIONS_WRITE):
                raise HTTPException(status_code=403, detail="Integrations write permission required")
            
            if integration_id not in self.integrations:
                raise HTTPException(status_code=404, detail="Integration not found")
            
            integration = self.integrations[integration_id]
            
            if integration.status != IntegrationStatus.ACTIVE:
                raise HTTPException(status_code=400, detail="Integration is not active")
            
            # Check rate limiting
            if not self._check_rate_limit(integration_id, integration.rate_limit):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            # Create API request
            api_request = APIRequest(
                id=f"req_{len(self.api_requests) + 1:06d}",
                integration_id=integration_id,
                method=request_data.get("method", "GET"),
                endpoint=request_data.get("endpoint", ""),
                headers=request_data.get("headers", {}),
                payload=request_data.get("payload"),
                created_at=datetime.now()
            )
            
            self.api_requests[api_request.id] = api_request
            
            # Execute request in background
            background_tasks.add_task(self._execute_api_request, api_request.id, integration)
            
            return {"success": True, "request_id": api_request.id, "status": "processing"}
        
        @self.app.get("/integrations/{integration_id}/requests", tags=["api"])
        async def list_api_requests(
            integration_id: str,
            limit: int = Query(50, ge=1, le=1000),
            current_user: dict = Depends(get_current_user)
        ):
            """List API requests for integration"""
            if not require_permission(current_user, Permission.INTEGRATIONS_READ):
                raise HTTPException(status_code=403, detail="Integrations read permission required")
            
            if integration_id not in self.integrations:
                raise HTTPException(status_code=404, detail="Integration not found")
            
            requests = [r for r in self.api_requests.values() if r.integration_id == integration_id]
            requests.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
            requests = requests[:limit]
            
            return {
                "requests": requests,
                "total_count": len(requests),
                "success_count": len([r for r in requests if r.success]),
                "error_count": len([r for r in requests if not r.success])
            }
        
        # Webhook Routes
        @self.app.post("/integrations/{integration_id}/webhooks", tags=["webhooks"])
        async def create_webhook(
            integration_id: str,
            webhook: Webhook,
            current_user: dict = Depends(get_current_user)
        ):
            """Create webhook for integration"""
            if not require_permission(current_user, Permission.INTEGRATIONS_WRITE):
                raise HTTPException(status_code=403, detail="Integrations write permission required")
            
            if integration_id not in self.integrations:
                raise HTTPException(status_code=404, detail="Integration not found")
            
            webhook.id = f"hook_{len(self.webhooks) + 1:06d}"
            webhook.integration_id = integration_id
            webhook.created_at = datetime.now()
            
            self.webhooks[webhook.id] = webhook
            
            await audit_log(
                action="webhook_create",
                resource="webhooks",
                user_id=current_user.get("user_id"),
                details={"webhook_id": webhook.id, "integration_id": integration_id}
            )
            
            return {"success": True, "webhook": webhook}
        
        @self.app.post("/webhooks/{webhook_id}/trigger", tags=["webhooks"])
        async def trigger_webhook(
            webhook_id: str,
            payload: Dict[str, Any],
            background_tasks: BackgroundTasks,
            current_user: dict = Depends(get_current_user)
        ):
            """Trigger webhook manually"""
            if not require_permission(current_user, Permission.INTEGRATIONS_WRITE):
                raise HTTPException(status_code=403, detail="Integrations write permission required")
            
            if webhook_id not in self.webhooks:
                raise HTTPException(status_code=404, detail="Webhook not found")
            
            webhook = self.webhooks[webhook_id]
            
            if not webhook.active:
                raise HTTPException(status_code=400, detail="Webhook is not active")
            
            # Trigger webhook in background
            background_tasks.add_task(self._trigger_webhook, webhook_id, payload)
            
            return {"success": True, "webhook_id": webhook_id, "status": "triggered"}
        
        # Data Synchronization Routes
        @self.app.post("/integrations/{integration_id}/sync", tags=["sync"])
        async def create_sync_job(
            integration_id: str,
            sync_config: Dict[str, Any],
            background_tasks: BackgroundTasks,
            current_user: dict = Depends(get_current_user)
        ):
            """Create data synchronization job"""
            if not require_permission(current_user, Permission.INTEGRATIONS_WRITE):
                raise HTTPException(status_code=403, detail="Integrations write permission required")
            
            if integration_id not in self.integrations:
                raise HTTPException(status_code=404, detail="Integration not found")
            
            sync_job = SyncJob(
                id=f"sync_{len(self.sync_jobs) + 1:06d}",
                integration_id=integration_id,
                job_type=sync_config.get("job_type", "full_sync"),
                source=sync_config.get("source", ""),
                destination=sync_config.get("destination", ""),
                records_total=sync_config.get("records_total"),
                started_at=datetime.now()
            )
            
            self.sync_jobs[sync_job.id] = sync_job
            
            # Start sync job in background
            background_tasks.add_task(self._execute_sync_job, sync_job.id)
            
            await audit_log(
                action="sync_job_create",
                resource="sync_jobs",
                user_id=current_user.get("user_id"),
                details={"sync_job_id": sync_job.id, "integration_id": integration_id}
            )
            
            return {"success": True, "sync_job": sync_job}
        
        @self.app.get("/sync-jobs", tags=["sync"])
        async def list_sync_jobs(
            integration_id: Optional[str] = Query(None, description="Filter by integration"),
            status: Optional[SyncStatus] = Query(None, description="Filter by status"),
            current_user: dict = Depends(get_current_user)
        ):
            """List synchronization jobs"""
            if not require_permission(current_user, Permission.INTEGRATIONS_READ):
                raise HTTPException(status_code=403, detail="Integrations read permission required")
            
            jobs = list(self.sync_jobs.values())
            
            if integration_id:
                jobs = [j for j in jobs if j.integration_id == integration_id]
            
            if status:
                jobs = [j for j in jobs if j.status == status]
            
            jobs.sort(key=lambda x: x.started_at or datetime.min, reverse=True)
            
            return {
                "sync_jobs": jobs,
                "total_count": len(jobs),
                "in_progress_count": len([j for j in self.sync_jobs.values() if j.status == SyncStatus.IN_PROGRESS])
            }
        
        # Analytics Routes
        @self.app.get("/analytics/dashboard", tags=["analytics"])
        async def integrations_dashboard(
            current_user: dict = Depends(get_current_user)
        ):
            """Get integrations analytics dashboard"""
            if not require_permission(current_user, Permission.INTEGRATIONS_READ):
                raise HTTPException(status_code=403, detail="Integrations read permission required")
            
            # Integration metrics
            total_integrations = len(self.integrations)
            active_integrations = len([i for i in self.integrations.values() if i.status == IntegrationStatus.ACTIVE])
            
            # API request metrics (last 24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            recent_requests = [r for r in self.api_requests.values() if r.created_at and r.created_at > cutoff]
            successful_requests = len([r for r in recent_requests if r.success])
            
            # Sync job metrics
            total_sync_jobs = len(self.sync_jobs)
            active_sync_jobs = len([j for j in self.sync_jobs.values() if j.status == SyncStatus.IN_PROGRESS])
            
            # Webhook metrics
            total_webhooks = len(self.webhooks)
            active_webhooks = len([w for w in self.webhooks.values() if w.active])
            
            return {
                "integrations": {
                    "total": total_integrations,
                    "active": active_integrations,
                    "inactive": total_integrations - active_integrations
                },
                "api_requests_24h": {
                    "total": len(recent_requests),
                    "successful": successful_requests,
                    "failed": len(recent_requests) - successful_requests,
                    "success_rate": (successful_requests / max(len(recent_requests), 1)) * 100
                },
                "sync_jobs": {
                    "total": total_sync_jobs,
                    "active": active_sync_jobs,
                    "completed": len([j for j in self.sync_jobs.values() if j.status == SyncStatus.SUCCESS])
                },
                "webhooks": {
                    "total": total_webhooks,
                    "active": active_webhooks
                }
            }
    
    async def _test_integration_connection(self, integration: Integration) -> Dict[str, Any]:
        """Test integration connection"""
        try:
            if integration.integration_type == IntegrationType.REST_API:
                # Test REST API connection
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        str(integration.endpoint_url),
                        timeout=aiohttp.ClientTimeout(total=integration.timeout_seconds)
                    ) as response:
                        return {
                            "success": response.status < 400,
                            "status_code": response.status,
                            "response_time_ms": 100,  # Mock value
                            "timestamp": datetime.now().isoformat()
                        }
            
            elif integration.integration_type == IntegrationType.DATABASE:
                # Mock database connection test
                await asyncio.sleep(0.1)  # Simulate connection test
                return {
                    "success": True,
                    "connection_status": "connected",
                    "timestamp": datetime.now().isoformat()
                }
            
            else:
                # Generic success for other types
                return {
                    "success": True,
                    "message": f"Integration type {integration.integration_type} test passed",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_rate_limit(self, integration_id: str, rate_limit: int) -> bool:
        """Check if request is within rate limit"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        if integration_id not in self.rate_limits:
            self.rate_limits[integration_id] = []
        
        # Clean old requests
        self.rate_limits[integration_id] = [
            req_time for req_time in self.rate_limits[integration_id]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.rate_limits[integration_id]) >= rate_limit:
            return False
        
        # Add current request
        self.rate_limits[integration_id].append(now)
        return True
    
    async def _execute_api_request(self, request_id: str, integration: Integration):
        """Execute API request"""
        try:
            if request_id not in self.api_requests:
                return
            
            api_request = self.api_requests[request_id]
            start_time = datetime.now()
            
            # Mock API request execution
            await asyncio.sleep(0.2)  # Simulate network delay
            
            # Mock successful response
            api_request.status_code = 200
            api_request.success = True
            api_request.response_data = {
                "status": "success",
                "data": {"message": "API request completed successfully"},
                "timestamp": datetime.now().isoformat()
            }
            api_request.execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update integration last sync
            integration.last_sync = datetime.now()
            
            logger.info(f"✅ API request {request_id} completed successfully")
            
        except Exception as e:
            if request_id in self.api_requests:
                api_request = self.api_requests[request_id]
                api_request.success = False
                api_request.error_message = str(e)
                api_request.status_code = 500
            
            logger.error(f"❌ API request {request_id} failed: {e}")
    
    async def _trigger_webhook(self, webhook_id: str, payload: Dict[str, Any]):
        """Trigger webhook"""
        try:
            if webhook_id not in self.webhooks:
                return
            
            webhook = self.webhooks[webhook_id]
            
            # Mock webhook trigger
            await asyncio.sleep(0.1)
            
            logger.info(f"✅ Webhook {webhook_id} triggered successfully")
            
        except Exception as e:
            logger.error(f"❌ Webhook {webhook_id} failed: {e}")
    
    async def _execute_sync_job(self, sync_job_id: str):
        """Execute synchronization job"""
        try:
            if sync_job_id not in self.sync_jobs:
                return
            
            sync_job = self.sync_jobs[sync_job_id]
            sync_job.status = SyncStatus.IN_PROGRESS
            
            # Mock sync process
            total_records = sync_job.records_total or 100
            
            for i in range(total_records):
                await asyncio.sleep(0.01)  # Simulate processing
                
                sync_job.records_processed = i + 1
                sync_job.progress_percentage = ((i + 1) / total_records) * 100
                
                # Simulate occasional errors
                if i % 20 == 19:  # Every 20th record has an error
                    sync_job.error_count += 1
            
            sync_job.status = SyncStatus.SUCCESS
            sync_job.completed_at = datetime.now()
            
            logger.info(f"✅ Sync job {sync_job_id} completed successfully")
            
        except Exception as e:
            if sync_job_id in self.sync_jobs:
                sync_job = self.sync_jobs[sync_job_id]
                sync_job.status = SyncStatus.FAILED
                sync_job.completed_at = datetime.now()
            
            logger.error(f"❌ Sync job {sync_job_id} failed: {e}")
    
    def _initialize_sample_data(self):
        """Initialize with sample data"""
        # Sample integrations
        sample_integrations = [
            Integration(
                id="int_000001",
                name="Salesforce CRM",
                integration_type=IntegrationType.REST_API,
                description="Salesforce CRM integration for customer data sync",
                endpoint_url="https://api.salesforce.com/services/data/v54.0",
                status=IntegrationStatus.ACTIVE,
                rate_limit=200,
                config={"version": "v54.0", "sandbox": False},
                created_at=datetime.now() - timedelta(days=10),
                updated_at=datetime.now()
            ),
            Integration(
                id="int_000002",
                name="Slack Notifications",
                integration_type=IntegrationType.WEBHOOK,
                description="Slack webhook for notifications",
                endpoint_url="https://hooks.slack.com/services",
                status=IntegrationStatus.ACTIVE,
                rate_limit=50,
                config={"channel": "#alerts"},
                created_at=datetime.now() - timedelta(days=5),
                updated_at=datetime.now()
            ),
            Integration(
                id="int_000003",
                name="PostgreSQL Database",
                integration_type=IntegrationType.DATABASE,
                description="Main PostgreSQL database connection",
                status=IntegrationStatus.ACTIVE,
                config={"host": "localhost", "port": 5432, "database": "bhiv_core"},
                created_at=datetime.now() - timedelta(days=15),
                updated_at=datetime.now()
            )
        ]
        
        for integration in sample_integrations:
            self.integrations[integration.id] = integration
        
        logger.info("✅ Integrations service initialized with sample data")

# Create service instance
integrations_service = IntegrationsService()

if __name__ == "__main__":
    integrations_service.run(debug=True)
