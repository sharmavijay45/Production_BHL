"""
BHIV Core Observability - Metrics Collection
===========================================

Prometheus metrics collection for all BHIV Core services.
Provides comprehensive monitoring of business and technical metrics.
"""

import time
import logging
from typing import Dict, Optional, Callable, Any
from functools import wraps
from prometheus_client import (
    Counter, Histogram, Gauge, Info, 
    CollectorRegistry, generate_latest,
    start_http_server, CONTENT_TYPE_LATEST
)
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse
import psutil
import asyncio

logger = logging.getLogger(__name__)

class BHIVMetrics:
    """BHIV Core metrics collector"""
    
    def __init__(self, service_name: str, registry: Optional[CollectorRegistry] = None):
        self.service_name = service_name
        self.registry = registry or CollectorRegistry()
        
        # Initialize metrics
        self._init_http_metrics()
        self._init_business_metrics()
        self._init_system_metrics()
        self._init_custom_metrics()
    
    def _init_http_metrics(self):
        """Initialize HTTP-related metrics"""
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.http_request_size_bytes = Histogram(
            'http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.http_response_size_bytes = Histogram(
            'http_response_size_bytes',
            'HTTP response size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
    
    def _init_business_metrics(self):
        """Initialize business logic metrics"""
        # Authentication metrics
        self.auth_attempts_total = Counter(
            'bhiv_auth_attempts_total',
            'Total authentication attempts',
            ['result'],
            registry=self.registry
        )
        
        self.auth_failures_total = Counter(
            'bhiv_auth_failures_total',
            'Total authentication failures',
            ['reason'],
            registry=self.registry
        )
        
        # Threat detection metrics
        self.threats_detected_total = Counter(
            'bhiv_threats_detected_total',
            'Total threats detected',
            ['threat_type', 'severity'],
            registry=self.registry
        )
        
        self.threats_blocked_total = Counter(
            'bhiv_threats_blocked_total',
            'Total threats blocked',
            ['threat_type', 'action'],
            registry=self.registry
        )
        
        # Business operations metrics
        self.business_operations_total = Counter(
            'bhiv_business_operations_total',
            'Total business operations',
            ['operation_type', 'status'],
            registry=self.registry
        )
        
        self.business_operation_duration_seconds = Histogram(
            'bhiv_business_operation_duration_seconds',
            'Business operation duration in seconds',
            ['operation_type'],
            registry=self.registry
        )
        
        # LLM Query metrics
        self.llm_queries_total = Counter(
            'bhiv_llm_queries_total',
            'Total LLM queries',
            ['model', 'status'],
            registry=self.registry
        )
        
        self.llm_query_duration_seconds = Histogram(
            'bhiv_llm_query_duration_seconds',
            'LLM query duration in seconds',
            ['model'],
            registry=self.registry
        )
        
        self.llm_tokens_used_total = Counter(
            'bhiv_llm_tokens_used_total',
            'Total LLM tokens used',
            ['model'],
            registry=self.registry
        )
        
        self.llm_query_failures_total = Counter(
            'bhiv_llm_query_failures_total',
            'Total LLM query failures',
            ['model', 'error_type'],
            registry=self.registry
        )
    
    def _init_system_metrics(self):
        """Initialize system-level metrics"""
        self.system_cpu_usage = Gauge(
            'bhiv_system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'bhiv_system_memory_usage_bytes',
            'System memory usage in bytes',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'bhiv_system_disk_usage_bytes',
            'System disk usage in bytes',
            ['device'],
            registry=self.registry
        )
        
        self.active_connections = Gauge(
            'bhiv_active_connections',
            'Number of active connections',
            registry=self.registry
        )
        
        self.database_connections = Gauge(
            'bhiv_database_connections',
            'Number of database connections',
            ['pool'],
            registry=self.registry
        )
    
    def _init_custom_metrics(self):
        """Initialize service-specific custom metrics"""
        # Service info
        self.service_info = Info(
            'bhiv_service_info',
            'Service information',
            registry=self.registry
        )
        
        self.service_info.info({
            'service_name': self.service_name,
            'version': '1.0.0',
            'environment': 'production'
        })
        
        # Service uptime
        self.service_start_time = Gauge(
            'bhiv_service_start_time_seconds',
            'Service start time in seconds since epoch',
            registry=self.registry
        )
        
        self.service_start_time.set_to_current_time()
        
        # Custom business metrics based on service
        if self.service_name == 'logistics':
            self.inventory_items_total = Gauge(
                'bhiv_inventory_items_total',
                'Total inventory items',
                registry=self.registry
            )
            
            self.low_stock_items = Gauge(
                'bhiv_low_stock_items',
                'Number of low stock items',
                registry=self.registry
            )
            
        elif self.service_name == 'crm':
            self.customers_total = Gauge(
                'bhiv_customers_total',
                'Total number of customers',
                ['status'],
                registry=self.registry
            )
            
            self.leads_total = Gauge(
                'bhiv_leads_total',
                'Total number of leads',
                ['status'],
                registry=self.registry
            )
            
        elif self.service_name == 'agent_orchestration':
            self.agents_total = Gauge(
                'bhiv_agents_total',
                'Total number of agents',
                ['status'],
                registry=self.registry
            )
            
            self.tasks_queued = Gauge(
                'bhiv_tasks_queued',
                'Number of queued tasks',
                registry=self.registry
            )
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, 
                           duration: float, request_size: int = 0, response_size: int = 0):
        """Record HTTP request metrics"""
        self.http_requests_total.labels(
            method=method, 
            endpoint=endpoint, 
            status=str(status_code)
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method, 
            endpoint=endpoint
        ).observe(duration)
        
        if request_size > 0:
            self.http_request_size_bytes.labels(
                method=method, 
                endpoint=endpoint
            ).observe(request_size)
        
        if response_size > 0:
            self.http_response_size_bytes.labels(
                method=method, 
                endpoint=endpoint
            ).observe(response_size)
    
    def record_auth_attempt(self, success: bool, failure_reason: str = None):
        """Record authentication attempt"""
        result = "success" if success else "failure"
        self.auth_attempts_total.labels(result=result).inc()
        
        if not success and failure_reason:
            self.auth_failures_total.labels(reason=failure_reason).inc()
    
    def record_threat_detection(self, threat_type: str, severity: str, blocked: bool = False):
        """Record threat detection"""
        self.threats_detected_total.labels(
            threat_type=threat_type, 
            severity=severity
        ).inc()
        
        if blocked:
            self.threats_blocked_total.labels(
                threat_type=threat_type, 
                action="blocked"
            ).inc()
    
    def record_business_operation(self, operation_type: str, duration: float, success: bool):
        """Record business operation"""
        status = "success" if success else "failure"
        self.business_operations_total.labels(
            operation_type=operation_type, 
            status=status
        ).inc()
        
        self.business_operation_duration_seconds.labels(
            operation_type=operation_type
        ).observe(duration)
    
    def record_llm_query(self, model: str, duration: float, tokens_used: int, 
                        success: bool, error_type: str = None):
        """Record LLM query metrics"""
        status = "success" if success else "failure"
        self.llm_queries_total.labels(model=model, status=status).inc()
        
        if success:
            self.llm_query_duration_seconds.labels(model=model).observe(duration)
            self.llm_tokens_used_total.labels(model=model).inc(tokens_used)
        else:
            self.llm_query_failures_total.labels(
                model=model, 
                error_type=error_type or "unknown"
            ).inc()
    
    def update_system_metrics(self):
        """Update system-level metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.system_memory_usage.set(memory.used)
            
            # Disk usage
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    self.system_disk_usage.labels(device=partition.device).set(usage.used)
                except PermissionError:
                    continue
            
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')

# Global metrics instance
_metrics_instance: Optional[BHIVMetrics] = None

def init_metrics(service_name: str) -> BHIVMetrics:
    """Initialize metrics for a service"""
    global _metrics_instance
    _metrics_instance = BHIVMetrics(service_name)
    return _metrics_instance

def get_metrics() -> Optional[BHIVMetrics]:
    """Get the global metrics instance"""
    return _metrics_instance

def metrics_middleware():
    """FastAPI middleware for automatic metrics collection"""
    async def middleware(request: Request, call_next):
        start_time = time.time()
        
        # Get request size
        request_size = 0
        if hasattr(request, 'body'):
            try:
                body = await request.body()
                request_size = len(body) if body else 0
            except:
                pass
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Get response size
        response_size = 0
        if hasattr(response, 'body'):
            try:
                response_size = len(response.body) if response.body else 0
            except:
                pass
        
        # Record metrics
        if _metrics_instance:
            _metrics_instance.record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration,
                request_size=request_size,
                response_size=response_size
            )
        
        return response
    
    return middleware

def metrics_endpoint():
    """FastAPI endpoint for Prometheus metrics"""
    async def endpoint():
        if _metrics_instance:
            # Update system metrics before serving
            _metrics_instance.update_system_metrics()
            metrics_data = _metrics_instance.get_metrics()
            return PlainTextResponse(metrics_data, media_type=CONTENT_TYPE_LATEST)
        else:
            return PlainTextResponse("# No metrics available\n", media_type=CONTENT_TYPE_LATEST)
    
    return endpoint

def monitor_function(operation_type: str):
    """Decorator to monitor function execution"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                if _metrics_instance:
                    _metrics_instance.record_business_operation(
                        operation_type=operation_type,
                        duration=duration,
                        success=success
                    )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                if _metrics_instance:
                    _metrics_instance.record_business_operation(
                        operation_type=operation_type,
                        duration=duration,
                        success=success
                    )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

def trace_business_operation(operation_name: str, **metadata):
    """Decorator to trace business operations with distributed tracing"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            trace_id = f"trace_{int(start_time * 1000)}"
            
            # Log trace start
            logger.info(f"🔍 Starting trace: {trace_id} for operation: {operation_name}")
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                logger.error(f"❌ Trace {trace_id} failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                status = "success" if success else "failure"
                
                # Record metrics
                if _metrics_instance:
                    _metrics_instance.record_business_operation(
                        operation_type=operation_name,
                        duration=duration,
                        success=success
                    )
                
                # Log trace completion
                logger.info(f"✅ Completed trace: {trace_id} - {status} in {duration:.3f}s")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            trace_id = f"trace_{int(start_time * 1000)}"
            
            # Log trace start
            logger.info(f"🔍 Starting trace: {trace_id} for operation: {operation_name}")
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                logger.error(f"❌ Trace {trace_id} failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                status = "success" if success else "failure"
                
                # Record metrics
                if _metrics_instance:
                    _metrics_instance.record_business_operation(
                        operation_type=operation_name,
                        duration=duration,
                        success=success
                    )
                
                # Log trace completion
                logger.info(f"✅ Completed trace: {trace_id} - {status} in {duration:.3f}s")
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

async def start_metrics_updater():
    """Start background task to update metrics periodically"""
    while True:
        try:
            if _metrics_instance:
                _metrics_instance.update_system_metrics()
            await asyncio.sleep(30)  # Update every 30 seconds
        except Exception as e:
            logger.error(f"Error in metrics updater: {e}")
            await asyncio.sleep(60)  # Wait longer on error
