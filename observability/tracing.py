"""
BHIV Core Observability - Distributed Tracing
============================================

OpenTelemetry distributed tracing for BHIV Core microservices.
Provides end-to-end request tracing across service boundaries.
"""

import logging
import time
from typing import Dict, Optional, Any, Callable
from functools import wraps
from contextlib import contextmanager

from opentelemetry import trace, baggage, propagate
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace.status import Status, StatusCode

logger = logging.getLogger(__name__)

class BHIVTracing:
    """BHIV Core distributed tracing manager"""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        self.service_name = service_name
        self.service_version = service_version
        self.tracer_provider = None
        self.tracer = None
        
        self._setup_tracing()
    
    def _setup_tracing(self):
        """Setup OpenTelemetry tracing"""
        try:
            # Create resource
            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: self.service_name,
                ResourceAttributes.SERVICE_VERSION: self.service_version,
                ResourceAttributes.SERVICE_NAMESPACE: "bhiv-core",
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: "production"
            })
            
            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)
            
            # Setup exporters
            self._setup_exporters()
            
            # Setup propagators
            propagate.set_global_textmap(B3MultiFormat())
            
            # Get tracer
            self.tracer = trace.get_tracer(__name__)
            
            # Auto-instrument libraries
            self._setup_auto_instrumentation()
            
            logger.info(f"✅ Tracing initialized for {self.service_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize tracing: {e}")
    
    def _setup_exporters(self):
        """Setup trace exporters"""
        try:
            # For development/production without external services, use console exporter
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            
            # Console exporter for development
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
            
            logger.info("✅ Console trace exporter configured")
            
            # Only try external exporters if environment variables are set
            import os
            if os.getenv("JAEGER_ENDPOINT"):
                try:
                    jaeger_exporter = JaegerExporter(
                        agent_host_name=os.getenv("JAEGER_HOST", "localhost"),
                        agent_port=int(os.getenv("JAEGER_PORT", "6831")),
                    )
                    self.tracer_provider.add_span_processor(
                        BatchSpanProcessor(jaeger_exporter)
                    )
                    logger.info("✅ Jaeger exporter configured")
                except Exception as e:
                    logger.warning(f"⚠️ Jaeger exporter failed: {e}")
            
            if os.getenv("OTLP_ENDPOINT"):
                try:
                    otlp_exporter = OTLPSpanExporter(
                        endpoint=os.getenv("OTLP_ENDPOINT"),
                        insecure=True
                    )
                    self.tracer_provider.add_span_processor(
                        BatchSpanProcessor(otlp_exporter)
                    )
                    logger.info("✅ OTLP exporter configured")
                except Exception as e:
                    logger.warning(f"⚠️ OTLP exporter failed: {e}")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not setup exporters: {e}")
    
    def _setup_auto_instrumentation(self):
        """Setup automatic instrumentation for common libraries"""
        try:
            # HTTP client instrumentation
            HTTPXClientInstrumentor().instrument()
            
            # Database instrumentation
            Psycopg2Instrumentor().instrument()
            
            # Redis instrumentation
            RedisInstrumentor().instrument()
            
            logger.info("✅ Auto-instrumentation setup complete")
            
        except Exception as e:
            logger.warning(f"⚠️ Auto-instrumentation setup failed: {e}")
    
    def instrument_fastapi(self, app):
        """Instrument FastAPI application"""
        try:
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=self.tracer_provider,
                excluded_urls="/health,/metrics"
            )
            logger.info("✅ FastAPI instrumentation complete")
        except Exception as e:
            logger.error(f"❌ FastAPI instrumentation failed: {e}")
    
    @contextmanager
    def start_span(self, name: str, **kwargs):
        """Start a new span with context manager"""
        with self.tracer.start_as_current_span(name, **kwargs) as span:
            yield span
    
    def trace_function(self, span_name: Optional[str] = None, 
                      attributes: Optional[Dict[str, Any]] = None):
        """Decorator to trace function execution"""
        def decorator(func: Callable) -> Callable:
            nonlocal span_name
            if span_name is None:
                span_name = f"{func.__module__}.{func.__qualname__}"
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.start_span(span_name) as span:
                    # Add function attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    
                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.start_span(span_name) as span:
                    # Add function attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    
                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        raise
            
            import asyncio
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    def add_baggage(self, key: str, value: str):
        """Add baggage to current context"""
        baggage.set_baggage(key, value)
    
    def get_baggage(self, key: str) -> Optional[str]:
        """Get baggage from current context"""
        return baggage.get_baggage(key)
    
    def get_current_span(self):
        """Get current active span"""
        return trace.get_current_span()
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add event to current span"""
        span = self.get_current_span()
        if span:
            span.add_event(name, attributes or {})
    
    def set_attribute(self, key: str, value: Any):
        """Set attribute on current span"""
        span = self.get_current_span()
        if span:
            span.set_attribute(key, value)
    
    def record_exception(self, exception: Exception):
        """Record exception on current span"""
        span = self.get_current_span()
        if span:
            span.record_exception(exception)
            span.set_status(Status(StatusCode.ERROR, str(exception)))

# Global tracing instance
_tracing_instance: Optional[BHIVTracing] = None

def init_tracing(service_name: str, service_version: str = "1.0.0") -> BHIVTracing:
    """Initialize tracing for a service"""
    global _tracing_instance
    _tracing_instance = BHIVTracing(service_name, service_version)
    return _tracing_instance

def get_tracing() -> Optional[BHIVTracing]:
    """Get the global tracing instance"""
    return _tracing_instance

def trace_business_operation(operation_name: str, **attributes):
    """Decorator for tracing business operations"""
    def decorator(func: Callable) -> Callable:
        if _tracing_instance:
            return _tracing_instance.trace_function(
                span_name=f"business.{operation_name}",
                attributes={
                    "operation.type": "business",
                    "operation.name": operation_name,
                    **attributes
                }
            )(func)
        return func
    return decorator

def trace_database_operation(table_name: str, operation: str):
    """Decorator for tracing database operations"""
    def decorator(func: Callable) -> Callable:
        if _tracing_instance:
            return _tracing_instance.trace_function(
                span_name=f"db.{table_name}.{operation}",
                attributes={
                    "db.table": table_name,
                    "db.operation": operation,
                    "component": "database"
                }
            )(func)
        return func
    return decorator

def trace_external_api(service_name: str, endpoint: str):
    """Decorator for tracing external API calls"""
    def decorator(func: Callable) -> Callable:
        if _tracing_instance:
            return _tracing_instance.trace_function(
                span_name=f"external.{service_name}.{endpoint}",
                attributes={
                    "external.service": service_name,
                    "external.endpoint": endpoint,
                    "component": "external_api"
                }
            )(func)
        return func
    return decorator

def trace_llm_operation(model_name: str, operation_type: str):
    """Decorator for tracing LLM operations"""
    def decorator(func: Callable) -> Callable:
        if _tracing_instance:
            return _tracing_instance.trace_function(
                span_name=f"llm.{model_name}.{operation_type}",
                attributes={
                    "llm.model": model_name,
                    "llm.operation": operation_type,
                    "component": "llm"
                }
            )(func)
        return func
    return decorator

def trace_agent_operation(agent_name: str, task_type: str):
    """Decorator for tracing agent operations"""
    def decorator(func: Callable) -> Callable:
        if _tracing_instance:
            return _tracing_instance.trace_function(
                span_name=f"agent.{agent_name}.{task_type}",
                attributes={
                    "agent.name": agent_name,
                    "agent.task_type": task_type,
                    "component": "agent"
                }
            )(func)
        return func
    return decorator

class TracingMiddleware:
    """Custom tracing middleware for additional context"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract trace context from headers
        if _tracing_instance:
            span = _tracing_instance.get_current_span()
            if span:
                # Add request context
                span.set_attribute("http.method", scope.get("method", ""))
                span.set_attribute("http.url", str(scope.get("path", "")))
                span.set_attribute("http.scheme", scope.get("scheme", ""))
                
                # Add user context if available
                headers = dict(scope.get("headers", []))
                user_id = headers.get(b"x-user-id")
                if user_id:
                    span.set_attribute("user.id", user_id.decode())
                
                # Add correlation ID
                correlation_id = headers.get(b"x-correlation-id")
                if correlation_id:
                    span.set_attribute("correlation.id", correlation_id.decode())
                    _tracing_instance.add_baggage("correlation.id", correlation_id.decode())
        
        await self.app(scope, receive, send)

def create_correlation_id() -> str:
    """Create a new correlation ID for request tracing"""
    import uuid
    return str(uuid.uuid4())

def propagate_trace_context(headers: Dict[str, str]) -> Dict[str, str]:
    """Propagate trace context to outgoing requests"""
    if _tracing_instance:
        # Inject trace context into headers
        propagate.inject(headers)
    return headers
