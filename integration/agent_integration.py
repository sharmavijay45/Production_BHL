"""
BHIV Core Agent Integration
==========================

Integrates all existing BHIV Core agents with the new production-grade infrastructure:
- Security (JWT, RBAC, Audit)
- Observability (Metrics, Tracing, Alerting)
- Threat Detection & Response
- Microservices Architecture
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import existing agents
from agents.vedas_agent import VedasAgent
from agents.edumentor_agent import EduMentorAgent
from agents.wellness_agent import WellnessAgent
from agents.KnowledgeAgent import KnowledgeAgent
from agents.image_agent import ImageAgent
from agents.audio_agent import AudioAgent
from agents.text_agent import TextAgent
from agents.qna_agent import QnAAgent
from agents.summarizer_agent import SummarizerAgent
from agents.planner_agent import PlannerAgent
from agents.file_search_agent import FileSearchAgent
from agents.agent_orchestrator import AgentOrchestrator

# Import observability components
from observability.metrics import get_metrics, monitor_function, trace_business_operation
from observability.tracing import get_tracing, trace_agent_operation
from observability.alerting import send_alert, AlertSeverity

# Import security components
from security.auth import verify_token, get_current_user
from security.rbac import check_permission, Permission
from security.audit import audit_log

logger = logging.getLogger(__name__)

class EnhancedAgentWrapper:
    """Wrapper to add observability and security to existing agents"""
    
    def __init__(self, agent, agent_name: str):
        self.agent = agent
        self.agent_name = agent_name
        self.metrics = get_metrics()
        self.tracing = get_tracing()
        
    @trace_agent_operation("agent_process", "query")
    @monitor_function("agent_query_processing")
    async def process_query(self, query: str, context: Dict[str, Any] = None, user_token: str = None):
        """Enhanced query processing with security and observability"""
        start_time = datetime.utcnow()
        
        try:
            # Security check
            if user_token:
                user_payload = verify_token(user_token)
                if not user_payload:
                    await send_alert(
                        name="UnauthorizedAgentAccess",
                        severity=AlertSeverity.WARNING,
                        message=f"Unauthorized access attempt to {self.agent_name}",
                        service=f"agent_{self.agent_name}"
                    )
                    raise Exception("Unauthorized access")
                
                # Add user context
                context = context or {}
                context['user_id'] = user_payload.get('sub')
                context['user_role'] = user_payload.get('role')
            
            # Audit log
            await audit_log(
                action=f"agent_query_{self.agent_name}",
                user_id=context.get('user_id', 'anonymous') if context else 'anonymous',
                details={
                    "agent": self.agent_name,
                    "query_length": len(query),
                    "has_context": context is not None
                }
            )
            
            # Process query based on agent type
            result = await self._process_with_agent(query, context)
            
            # Record success metrics
            if self.metrics:
                self.metrics.record_business_operation(
                    operation_type=f"agent_{self.agent_name}_query",
                    duration=(datetime.utcnow() - start_time).total_seconds(),
                    success=True
                )
            
            # Add tracing attributes
            if self.tracing:
                self.tracing.set_attribute("agent.name", self.agent_name)
                self.tracing.set_attribute("query.length", len(query))
                self.tracing.set_attribute("result.success", True)
            
            return {
                "agent": self.agent_name,
                "query": query,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "success": True
            }
            
        except Exception as e:
            # Record failure metrics
            if self.metrics:
                self.metrics.record_business_operation(
                    operation_type=f"agent_{self.agent_name}_query",
                    duration=(datetime.utcnow() - start_time).total_seconds(),
                    success=False
                )
            
            # Send alert for failures
            await send_alert(
                name="AgentProcessingError",
                severity=AlertSeverity.WARNING,
                message=f"Agent {self.agent_name} processing failed: {str(e)}",
                service=f"agent_{self.agent_name}",
                labels={"error_type": type(e).__name__}
            )
            
            # Add tracing error
            if self.tracing:
                self.tracing.record_exception(e)
            
            logger.error(f"❌ Agent {self.agent_name} processing failed: {e}")
            
            return {
                "agent": self.agent_name,
                "query": query,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "success": False
            }
    
    async def _process_with_agent(self, query: str, context: Dict[str, Any] = None):
        """Process query with the specific agent"""
        try:
            # Handle different agent interfaces
            if hasattr(self.agent, 'process_query'):
                return await self.agent.process_query(query, context)
            elif hasattr(self.agent, 'process'):
                return await self.agent.process(query, context)
            elif hasattr(self.agent, 'ask'):
                return await self.agent.ask(query, context)
            elif hasattr(self.agent, 'generate'):
                return await self.agent.generate(query, context)
            elif callable(self.agent):
                return await self.agent(query, context)
            else:
                # Try common method names
                for method_name in ['handle', 'execute', 'run']:
                    if hasattr(self.agent, method_name):
                        method = getattr(self.agent, method_name)
                        if callable(method):
                            return await method(query, context)
                
                raise Exception(f"No suitable processing method found for agent {self.agent_name}")
                
        except Exception as e:
            logger.error(f"Error processing with agent {self.agent_name}: {e}")
            raise

class BHIVAgentRegistry:
    """Enhanced agent registry with security and observability"""
    
    def __init__(self):
        self.agents: Dict[str, EnhancedAgentWrapper] = {}
        self.agent_stats: Dict[str, Dict] = {}
        
    async def initialize(self):
        """Initialize all agents with enhancements"""
        logger.info("🤖 Initializing BHIV Agent Registry...")
        
        # Define agents to initialize
        agent_configs = [
            {"class": VedasAgent, "name": "vedas", "description": "Spiritual guidance and Vedic wisdom"},
            {"class": EduMentorAgent, "name": "edumentor", "description": "Educational content and learning support"},
            {"class": WellnessAgent, "name": "wellness", "description": "Mental health and wellness guidance"},
            {"class": KnowledgeAgent, "name": "knowledge", "description": "Knowledge retrieval and analysis"},
            {"class": ImageAgent, "name": "image", "description": "Image analysis and description"},
            {"class": AudioAgent, "name": "audio", "description": "Audio processing and transcription"},
            {"class": TextAgent, "name": "text", "description": "Text processing and analysis"},
            {"class": QnAAgent, "name": "qna", "description": "Question and answer processing"},
            {"class": SummarizerAgent, "name": "summarizer", "description": "Content summarization"},
            {"class": PlannerAgent, "name": "planner", "description": "Task planning and organization"},
            {"class": FileSearchAgent, "name": "file_search", "description": "File search and retrieval"},
            {"class": AgentOrchestrator, "name": "orchestrator", "description": "Agent coordination and routing"}
        ]
        
        # Initialize each agent
        for config in agent_configs:
            try:
                # Create agent instance
                agent_instance = config["class"]()
                
                # Initialize if method exists
                if hasattr(agent_instance, 'initialize'):
                    await agent_instance.initialize()
                
                # Wrap with enhancements
                enhanced_agent = EnhancedAgentWrapper(agent_instance, config["name"])
                self.agents[config["name"]] = enhanced_agent
                
                # Initialize stats
                self.agent_stats[config["name"]] = {
                    "description": config["description"],
                    "total_queries": 0,
                    "successful_queries": 0,
                    "failed_queries": 0,
                    "average_response_time": 0.0,
                    "last_used": None
                }
                
                logger.info(f"✅ {config['name']} agent initialized")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize {config['name']} agent: {e}")
                
                # Send alert for initialization failure
                await send_alert(
                    name="AgentInitializationFailed",
                    severity=AlertSeverity.CRITICAL,
                    message=f"Failed to initialize {config['name']} agent: {str(e)}",
                    service="agent_registry"
                )
        
        logger.info(f"✅ Agent registry initialized with {len(self.agents)} agents")
    
    async def process_query(self, agent_name: str, query: str, context: Dict[str, Any] = None, user_token: str = None):
        """Process query with specified agent"""
        if agent_name not in self.agents:
            raise Exception(f"Agent '{agent_name}' not found")
        
        # Update stats
        self.agent_stats[agent_name]["total_queries"] += 1
        self.agent_stats[agent_name]["last_used"] = datetime.utcnow().isoformat()
        
        # Process with agent
        result = await self.agents[agent_name].process_query(query, context, user_token)
        
        # Update success/failure stats
        if result.get("success", False):
            self.agent_stats[agent_name]["successful_queries"] += 1
        else:
            self.agent_stats[agent_name]["failed_queries"] += 1
        
        # Update average response time
        processing_time = result.get("processing_time", 0)
        current_avg = self.agent_stats[agent_name]["average_response_time"]
        total_queries = self.agent_stats[agent_name]["total_queries"]
        
        self.agent_stats[agent_name]["average_response_time"] = (
            (current_avg * (total_queries - 1) + processing_time) / total_queries
        )
        
        return result
    
    def get_agent_list(self) -> List[Dict[str, Any]]:
        """Get list of available agents"""
        return [
            {
                "name": name,
                "description": stats["description"],
                "stats": {
                    "total_queries": stats["total_queries"],
                    "success_rate": (
                        stats["successful_queries"] / stats["total_queries"] 
                        if stats["total_queries"] > 0 else 0
                    ),
                    "average_response_time": stats["average_response_time"],
                    "last_used": stats["last_used"]
                }
            }
            for name, stats in self.agent_stats.items()
        ]
    
    def get_agent_stats(self, agent_name: str = None) -> Dict[str, Any]:
        """Get agent statistics"""
        if agent_name:
            return self.agent_stats.get(agent_name, {})
        return self.agent_stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for all agents"""
        health_status = {
            "status": "healthy",
            "total_agents": len(self.agents),
            "agents": {}
        }
        
        for name, agent in self.agents.items():
            try:
                # Basic health check - try to process a simple query
                test_result = await agent.process_query("health check", {"test": True})
                
                health_status["agents"][name] = {
                    "status": "healthy" if test_result.get("success", False) else "unhealthy",
                    "last_response_time": test_result.get("processing_time", 0),
                    "stats": self.agent_stats[name]
                }
                
            except Exception as e:
                health_status["agents"][name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "stats": self.agent_stats[name]
                }
        
        # Overall health
        unhealthy_agents = [
            name for name, status in health_status["agents"].items() 
            if status["status"] == "unhealthy"
        ]
        
        if unhealthy_agents:
            health_status["status"] = "degraded"
            health_status["unhealthy_agents"] = unhealthy_agents
        
        return health_status

# Global agent registry
_agent_registry: Optional[BHIVAgentRegistry] = None

def get_agent_registry() -> BHIVAgentRegistry:
    """Get or create agent registry"""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = BHIVAgentRegistry()
    return _agent_registry

async def main():
    """Test agent integration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    registry = get_agent_registry()
    
    try:
        # Initialize agents
        await registry.initialize()
        
        # Test agent processing
        test_queries = [
            {"agent": "vedas", "query": "What is dharma?"},
            {"agent": "edumentor", "query": "Explain machine learning"},
            {"agent": "wellness", "query": "How to reduce stress?"},
            {"agent": "knowledge", "query": "Tell me about quantum computing"}
        ]
        
        for test in test_queries:
            try:
                result = await registry.process_query(
                    test["agent"], 
                    test["query"],
                    context={"test": True}
                )
                logger.info(f"✅ {test['agent']}: {result.get('success', False)}")
            except Exception as e:
                logger.error(f"❌ {test['agent']}: {e}")
        
        # Get health check
        health = await registry.health_check()
        logger.info(f"System health: {health['status']}")
        
        # Get agent stats
        stats = registry.get_agent_stats()
        logger.info(f"Agent stats: {json.dumps(stats, indent=2)}")
        
        logger.info("🎉 Agent integration test completed!")
        
    except Exception as e:
        logger.error(f"❌ Agent integration test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
