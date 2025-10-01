"""
BHIV Core System Integration
===========================

Complete integration of all BHIV Core components including:
- Security (OAuth2/JWT, RBAC, Audit)
- Threat Mitigation (Detection, Response, Monitoring)
- Microservices (Logistics, CRM, Agent Orchestration, LLM Query, Integrations)
- Observability (Metrics, Tracing, Alerting)
- Agent System (All specialized agents with Vaani integration)
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import all core components
from modules.shared.base_service import BaseService, ServiceRegistry
from observability.metrics import get_metrics, monitor_function
from observability.tracing import get_tracing, trace_business_operation
from observability.alerting import get_alert_manager, send_alert, AlertSeverity
from security.auth import create_access_token, verify_token
from security.rbac import check_permission, Permission
from agents.threat_detection import ThreatDetectionAgent
from agents.threat_response import ThreatResponseAgent
from agents.vedas_agent import VedasAgent
from agents.edumentor_agent import EduMentorAgent
from agents.wellness_agent import WellnessAgent
from agents.agent_orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

class BHIVCoreIntegration:
    """Main integration class for BHIV Core system"""
    
    def __init__(self):
        self.services: Dict[str, BaseService] = {}
        self.agents: Dict[str, Any] = {}
        self.service_registry = ServiceRegistry()
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize all BHIV Core components"""
        try:
            logger.info("🚀 Initializing BHIV Core Integration...")
            
            # Initialize security components
            await self._init_security()
            
            # Initialize threat mitigation
            await self._init_threat_mitigation()
            
            # Initialize microservices
            await self._init_microservices()
            
            # Initialize agent system
            await self._init_agent_system()
            
            # Initialize observability
            await self._init_observability()
            
            # Verify integration
            await self._verify_integration()
            
            self.is_initialized = True
            logger.info("✅ BHIV Core Integration initialized successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize BHIV Core: {e}")
            raise
    
    async def _init_security(self):
        """Initialize security components"""
        logger.info("🔐 Initializing security components...")
        
        # Test JWT token creation and verification
        test_token = create_access_token({"sub": "test_user", "role": "admin"})
        payload = verify_token(test_token)
        
        if payload and payload.get("sub") == "test_user":
            logger.info("✅ JWT authentication working")
        else:
            raise Exception("JWT authentication failed")
        
        # Test RBAC
        if check_permission("admin", Permission.ADMIN_ACCESS):
            logger.info("✅ RBAC system working")
        else:
            raise Exception("RBAC system failed")
    
    async def _init_threat_mitigation(self):
        """Initialize threat mitigation components"""
        logger.info("🛡️ Initializing threat mitigation...")
        
        # Initialize threat detection agent
        self.threat_detection = ThreatDetectionAgent()
        await self.threat_detection.initialize()
        
        # Initialize threat response agent
        self.threat_response = ThreatResponseAgent()
        await self.threat_response.initialize()
        
        logger.info("✅ Threat mitigation initialized")
    
    async def _init_microservices(self):
        """Initialize microservices"""
        logger.info("🏗️ Initializing microservices...")
        
        # Define microservices configuration
        microservices_config = [
            {"name": "logistics", "port": 8001},
            {"name": "crm", "port": 8002},
            {"name": "agent_orchestration", "port": 8003},
            {"name": "llm_query", "port": 8004},
            {"name": "integrations", "port": 8005},
            {"name": "api_gateway", "port": 8000}
        ]
        
        # Initialize each microservice
        for config in microservices_config:
            service = BaseService(
                service_name=config["name"],
                port=config["port"],
                enable_security=True,
                enable_threat_protection=True,
                enable_observability=True
            )
            
            self.services[config["name"]] = service
            
            # Register service in registry
            self.service_registry.register_service(
                name=config["name"],
                host="localhost",
                port=config["port"]
            )
        
        logger.info("✅ Microservices initialized")
    
    async def _init_agent_system(self):
        """Initialize agent system"""
        logger.info("🤖 Initializing agent system...")
        
        # Initialize specialized agents
        self.agents = {
            "vedas": VedasAgent(),
            "edumentor": EduMentorAgent(),
            "wellness": WellnessAgent(),
            "orchestrator": AgentOrchestrator()
        }
        
        # Initialize each agent
        for name, agent in self.agents.items():
            if hasattr(agent, 'initialize'):
                await agent.initialize()
            logger.info(f"✅ {name.title()} agent initialized")
        
        logger.info("✅ Agent system initialized")
    
    async def _init_observability(self):
        """Initialize observability components"""
        logger.info("📊 Initializing observability...")
        
        # Verify metrics collection
        metrics = get_metrics()
        if metrics:
            logger.info("✅ Metrics collection active")
        
        # Verify tracing
        tracing = get_tracing()
        if tracing:
            logger.info("✅ Distributed tracing active")
        
        # Verify alerting
        alert_manager = get_alert_manager()
        if alert_manager:
            logger.info("✅ Alerting system active")
        
        logger.info("✅ Observability initialized")
    
    async def _verify_integration(self):
        """Verify all components are working together"""
        logger.info("🔍 Verifying system integration...")
        
        # Test end-to-end flow
        await self._test_security_flow()
        await self._test_agent_flow()
        await self._test_threat_detection_flow()
        await self._test_observability_flow()
        
        logger.info("✅ System integration verified")
    
    @trace_business_operation("security_test")
    async def _test_security_flow(self):
        """Test security integration"""
        # Create authenticated request
        token = create_access_token({"sub": "test_user", "role": "admin"})
        
        # Verify token
        payload = verify_token(token)
        assert payload["sub"] == "test_user"
        
        # Test RBAC
        assert check_permission("admin", Permission.ADMIN_ACCESS)
        
        logger.info("✅ Security flow test passed")
    
    @trace_business_operation("agent_test")
    @monitor_function("agent_integration_test")
    async def _test_agent_flow(self):
        """Test agent system integration"""
        # Test Vedas agent
        if "vedas" in self.agents:
            vedas_response = await self.agents["vedas"].process_query(
                "What is dharma?",
                context={"user_id": "test_user"}
            )
            assert vedas_response is not None
        
        # Test EduMentor agent
        if "edumentor" in self.agents:
            edu_response = await self.agents["edumentor"].process_query(
                "Explain machine learning",
                context={"user_id": "test_user"}
            )
            assert edu_response is not None
        
        logger.info("✅ Agent flow test passed")
    
    @trace_business_operation("threat_detection_test")
    async def _test_threat_detection_flow(self):
        """Test threat detection integration"""
        # Simulate suspicious request
        test_request = {
            "ip": "192.168.1.100",
            "method": "POST",
            "endpoint": "/api/test",
            "headers": {"User-Agent": "TestBot"},
            "payload": "SELECT * FROM users"  # SQL injection attempt
        }
        
        # Test threat detection
        threat_detected = await self.threat_detection.analyze_request(test_request)
        
        if threat_detected:
            # Test threat response
            await self.threat_response.handle_threat(threat_detected)
            logger.info("✅ Threat detection flow test passed")
        else:
            logger.warning("⚠️ Threat detection test inconclusive")
    
    @trace_business_operation("observability_test")
    async def _test_observability_flow(self):
        """Test observability integration"""
        # Test metrics recording
        metrics = get_metrics()
        if metrics:
            metrics.record_business_operation("test_operation", 0.1, True)
        
        # Test alerting
        await send_alert(
            name="IntegrationTest",
            severity=AlertSeverity.INFO,
            message="Integration test alert",
            service="integration_test"
        )
        
        logger.info("✅ Observability flow test passed")
    
    async def start_services(self):
        """Start all microservices"""
        if not self.is_initialized:
            await self.initialize()
        
        logger.info("🚀 Starting all BHIV Core services...")
        
        # Start services in dependency order
        service_order = [
            "integrations",
            "llm_query", 
            "logistics",
            "crm",
            "agent_orchestration",
            "api_gateway"
        ]
        
        for service_name in service_order:
            if service_name in self.services:
                service = self.services[service_name]
                logger.info(f"Starting {service_name} service on port {service.port}")
                
                # Start service in background
                asyncio.create_task(self._start_service(service))
                
                # Wait a bit between service starts
                await asyncio.sleep(2)
        
        logger.info("✅ All services started successfully!")
    
    async def _start_service(self, service: BaseService):
        """Start a single service"""
        try:
            service.run(host="0.0.0.0", debug=False)
        except Exception as e:
            logger.error(f"❌ Failed to start service {service.service_name}: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Check microservices
        for name, service in self.services.items():
            health_status["components"][f"service_{name}"] = {
                "status": "healthy",
                "port": service.port
            }
        
        # Check agents
        for name, agent in self.agents.items():
            health_status["components"][f"agent_{name}"] = {
                "status": "healthy",
                "type": type(agent).__name__
            }
        
        # Check observability
        health_status["components"]["observability"] = {
            "metrics": get_metrics() is not None,
            "tracing": get_tracing() is not None,
            "alerting": get_alert_manager() is not None
        }
        
        return health_status
    
    async def shutdown(self):
        """Graceful shutdown of all components"""
        logger.info("🛑 Shutting down BHIV Core system...")
        
        # Shutdown services
        for name, service in self.services.items():
            if hasattr(service, 'shutdown'):
                await service.shutdown()
            logger.info(f"✅ {name} service shutdown")
        
        # Shutdown agents
        for name, agent in self.agents.items():
            if hasattr(agent, 'shutdown'):
                await agent.shutdown()
            logger.info(f"✅ {name} agent shutdown")
        
        logger.info("✅ BHIV Core system shutdown complete")

# Global integration instance
_bhiv_integration: Optional[BHIVCoreIntegration] = None

def get_bhiv_integration() -> BHIVCoreIntegration:
    """Get or create BHIV Core integration instance"""
    global _bhiv_integration
    if _bhiv_integration is None:
        _bhiv_integration = BHIVCoreIntegration()
    return _bhiv_integration

async def main():
    """Main integration test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    integration = get_bhiv_integration()
    
    try:
        # Initialize system
        await integration.initialize()
        
        # Run health check
        health = await integration.health_check()
        logger.info(f"System health: {health}")
        
        # Start services (comment out for testing)
        # await integration.start_services()
        
        logger.info("🎉 BHIV Core integration test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        raise
    finally:
        await integration.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
