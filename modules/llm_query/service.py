"""
BHIV Core LLM Query Microservice
===============================

Handles all language model interactions and AI-powered queries:
- LLM request processing
- Model management
- Response optimization
- Context management
- AI safety and filtering
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import HTTPException, Depends, Query
from pydantic import BaseModel, Field
from enum import Enum
import json
import time
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
class ModelType(str, Enum):
    GPT35_TURBO = "gpt-3.5-turbo"
    GPT4 = "gpt-4"
    CLAUDE = "claude-3"
    LLAMA = "llama-2"
    CUSTOM = "custom"

class QueryStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    FILTERED = "filtered"

class SafetyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STRICT = "strict"

# Pydantic Models
class LLMModel(BaseModel):
    """LLM Model configuration"""
    id: Optional[str] = None
    name: str = Field(..., description="Model name")
    model_type: ModelType = Field(..., description="Model type")
    endpoint: Optional[str] = None
    api_key_required: bool = Field(default=True)
    max_tokens: int = Field(default=2048)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    available: bool = Field(default=True)
    cost_per_token: float = Field(default=0.0001)
    created_at: Optional[datetime] = None

class LLMQuery(BaseModel):
    """LLM Query request"""
    id: Optional[str] = None
    user_id: Optional[str] = None
    model_id: str = Field(..., description="Model ID to use")
    prompt: str = Field(..., description="Query prompt")
    context: Optional[str] = None
    max_tokens: Optional[int] = Field(None, ge=1, le=4000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    safety_level: SafetyLevel = Field(default=SafetyLevel.MEDIUM)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

class LLMResponse(BaseModel):
    """LLM Response"""
    id: Optional[str] = None
    query_id: str = Field(..., description="Original query ID")
    model_used: str = Field(..., description="Model that generated response")
    response_text: str = Field(..., description="Generated response")
    tokens_used: int = Field(..., description="Tokens consumed")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    safety_score: float = Field(default=1.0, ge=0.0, le=1.0)
    filtered_content: bool = Field(default=False)
    cost: float = Field(default=0.0)
    created_at: Optional[datetime] = None

class ConversationContext(BaseModel):
    """Conversation context management"""
    id: Optional[str] = None
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    messages: List[Dict[str, str]] = Field(default_factory=list)
    total_tokens: int = Field(default=0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class LLMQueryService(BaseService):
    """LLM Query microservice"""
    
    def __init__(self):
        super().__init__(
            service_name="LLMQuery",
            service_version="1.0.0",
            port=8004
        )
        
        # In-memory storage (replace with database in production)
        self.models: Dict[str, LLMModel] = {}
        self.queries: Dict[str, LLMQuery] = {}
        self.responses: Dict[str, LLMResponse] = {}
        self.contexts: Dict[str, ConversationContext] = {}
        
        # Safety filters
        self.content_filters = [
            "violence", "hate", "harassment", "self-harm",
            "sexual", "illegal", "spam", "malware"
        ]
        
        self._setup_routes()
        self._initialize_sample_data()
    
    def _get_service_capabilities(self) -> List[str]:
        """Get LLM service capabilities"""
        return super()._get_service_capabilities() + [
            "llm_processing",
            "model_management",
            "context_management",
            "safety_filtering",
            "response_optimization",
            "conversation_tracking"
        ]
    
    def _get_service_dependencies(self) -> List[str]:
        """Get service dependencies"""
        return ["integrations_service"]
    
    def _setup_routes(self):
        """Setup LLM query routes"""
        
        # Model Management Routes
        @self.app.get("/models", tags=["models"])
        async def list_models(
            available_only: bool = Query(True, description="Show only available models"),
            current_user: dict = Depends(get_current_user)
        ):
            """List available LLM models"""
            if not require_permission(current_user, Permission.LLM_ACCESS):
                raise HTTPException(status_code=403, detail="LLM access permission required")
            
            models = list(self.models.values())
            
            if available_only:
                models = [m for m in models if m.available]
            
            return {
                "models": models,
                "total_count": len(models),
                "available_count": len([m for m in self.models.values() if m.available])
            }
        
        @self.app.post("/models", tags=["models"])
        async def register_model(
            model: LLMModel,
            current_user: dict = Depends(get_current_user)
        ):
            """Register new LLM model"""
            if not require_permission(current_user, Permission.ADMIN_ACCESS):
                raise HTTPException(status_code=403, detail="Admin access required")
            
            model.id = f"model_{len(self.models) + 1:06d}"
            model.created_at = datetime.now()
            
            self.models[model.id] = model
            
            await audit_log(
                action="model_register",
                resource="llm_models",
                user_id=current_user.get("user_id"),
                details={"model_id": model.id, "model_type": model.model_type}
            )
            
            return {"success": True, "model": model}
        
        # Query Processing Routes
        @self.app.post("/query", tags=["llm"])
        async def process_query(
            query: LLMQuery,
            current_user: dict = Depends(get_current_user)
        ):
            """Process LLM query"""
            if not require_permission(current_user, Permission.LLM_ACCESS):
                raise HTTPException(status_code=403, detail="LLM access permission required")
            
            # Validate model exists
            if query.model_id not in self.models:
                raise HTTPException(status_code=400, detail="Model not found")
            
            model = self.models[query.model_id]
            
            if not model.available:
                raise HTTPException(status_code=400, detail="Model not available")
            
            # Generate query ID and set user
            query.id = f"query_{len(self.queries) + 1:06d}"
            query.user_id = current_user.get("user_id")
            query.created_at = datetime.now()
            
            # Safety filtering
            if not self._is_safe_content(query.prompt, query.safety_level):
                response = LLMResponse(
                    id=f"resp_{len(self.responses) + 1:06d}",
                    query_id=query.id,
                    model_used=model.name,
                    response_text="Content filtered due to safety policy",
                    tokens_used=0,
                    processing_time_ms=0,
                    safety_score=0.0,
                    filtered_content=True,
                    cost=0.0,
                    created_at=datetime.now()
                )
                
                self.responses[response.id] = response
                
                await audit_log(
                    action="query_filtered",
                    resource="llm_queries",
                    user_id=current_user.get("user_id"),
                    details={"query_id": query.id, "reason": "safety_filter"}
                )
                
                return {"success": False, "response": response, "filtered": True}
            
            # Store query
            self.queries[query.id] = query
            
            # Process query
            start_time = time.time()
            
            try:
                # Mock LLM processing
                response_text = await self._process_llm_request(query, model)
                processing_time = (time.time() - start_time) * 1000
                
                # Calculate tokens and cost
                tokens_used = len(query.prompt.split()) + len(response_text.split())
                cost = tokens_used * model.cost_per_token
                
                # Create response
                response = LLMResponse(
                    id=f"resp_{len(self.responses) + 1:06d}",
                    query_id=query.id,
                    model_used=model.name,
                    response_text=response_text,
                    tokens_used=tokens_used,
                    processing_time_ms=processing_time,
                    safety_score=self._calculate_safety_score(response_text),
                    filtered_content=False,
                    cost=cost,
                    created_at=datetime.now()
                )
                
                self.responses[response.id] = response
                
                await audit_log(
                    action="query_process",
                    resource="llm_queries",
                    user_id=current_user.get("user_id"),
                    details={
                        "query_id": query.id,
                        "model_id": query.model_id,
                        "tokens_used": tokens_used,
                        "cost": cost
                    }
                )
                
                return {"success": True, "response": response}
                
            except Exception as e:
                logger.error(f"LLM processing failed: {e}")
                raise HTTPException(status_code=500, detail="LLM processing failed")
        
        @self.app.get("/queries", tags=["llm"])
        async def list_queries(
            user_id: Optional[str] = Query(None, description="Filter by user"),
            model_id: Optional[str] = Query(None, description="Filter by model"),
            limit: int = Query(50, ge=1, le=1000, description="Number of results"),
            current_user: dict = Depends(get_current_user)
        ):
            """List LLM queries"""
            if not require_permission(current_user, Permission.LLM_ACCESS):
                raise HTTPException(status_code=403, detail="LLM access permission required")
            
            queries = list(self.queries.values())
            
            # Filter by user (users can only see their own queries unless admin)
            if not require_permission(current_user, Permission.ADMIN_ACCESS):
                queries = [q for q in queries if q.user_id == current_user.get("user_id")]
            elif user_id:
                queries = [q for q in queries if q.user_id == user_id]
            
            if model_id:
                queries = [q for q in queries if q.model_id == model_id]
            
            # Sort by creation time (newest first) and limit
            queries.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
            queries = queries[:limit]
            
            return {
                "queries": queries,
                "total_count": len(queries),
                "has_more": len(list(self.queries.values())) > limit
            }
        
        @self.app.get("/queries/{query_id}/response", tags=["llm"])
        async def get_query_response(
            query_id: str,
            current_user: dict = Depends(get_current_user)
        ):
            """Get response for specific query"""
            if not require_permission(current_user, Permission.LLM_ACCESS):
                raise HTTPException(status_code=403, detail="LLM access permission required")
            
            if query_id not in self.queries:
                raise HTTPException(status_code=404, detail="Query not found")
            
            query = self.queries[query_id]
            
            # Check ownership
            if (query.user_id != current_user.get("user_id") and 
                not require_permission(current_user, Permission.ADMIN_ACCESS)):
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Find response
            response = None
            for resp in self.responses.values():
                if resp.query_id == query_id:
                    response = resp
                    break
            
            if not response:
                raise HTTPException(status_code=404, detail="Response not found")
            
            return {
                "query": query,
                "response": response,
                "model_info": self.models.get(query.model_id)
            }
        
        # Conversation Context Routes
        @self.app.post("/conversations", tags=["conversations"])
        async def create_conversation(
            session_id: str,
            current_user: dict = Depends(get_current_user)
        ):
            """Create new conversation context"""
            if not require_permission(current_user, Permission.LLM_ACCESS):
                raise HTTPException(status_code=403, detail="LLM access permission required")
            
            context = ConversationContext(
                id=f"ctx_{len(self.contexts) + 1:06d}",
                user_id=current_user.get("user_id"),
                session_id=session_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.contexts[context.id] = context
            
            return {"success": True, "context": context}
        
        @self.app.post("/conversations/{context_id}/message", tags=["conversations"])
        async def add_message_to_conversation(
            context_id: str,
            message: Dict[str, str],
            current_user: dict = Depends(get_current_user)
        ):
            """Add message to conversation context"""
            if not require_permission(current_user, Permission.LLM_ACCESS):
                raise HTTPException(status_code=403, detail="LLM access permission required")
            
            if context_id not in self.contexts:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            context = self.contexts[context_id]
            
            # Check ownership
            if context.user_id != current_user.get("user_id"):
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Add message
            context.messages.append({
                "role": message.get("role", "user"),
                "content": message.get("content", ""),
                "timestamp": datetime.now().isoformat()
            })
            
            context.updated_at = datetime.now()
            
            return {"success": True, "context": context}
        
        # Analytics Routes
        @self.app.get("/analytics/usage", tags=["analytics"])
        async def usage_analytics(
            days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
            current_user: dict = Depends(get_current_user)
        ):
            """Get LLM usage analytics"""
            if not require_permission(current_user, Permission.LLM_ACCESS):
                raise HTTPException(status_code=403, detail="LLM access permission required")
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Filter queries by date and user (if not admin)
            queries = list(self.queries.values())
            if not require_permission(current_user, Permission.ADMIN_ACCESS):
                queries = [q for q in queries if q.user_id == current_user.get("user_id")]
            
            recent_queries = [q for q in queries if q.created_at and q.created_at > cutoff_date]
            
            # Calculate metrics
            total_queries = len(recent_queries)
            total_tokens = sum(
                resp.tokens_used for resp in self.responses.values()
                if resp.query_id in [q.id for q in recent_queries]
            )
            total_cost = sum(
                resp.cost for resp in self.responses.values()
                if resp.query_id in [q.id for q in recent_queries]
            )
            
            # Model usage
            model_usage = {}
            for query in recent_queries:
                model_name = self.models.get(query.model_id, {}).get("name", "Unknown")
                model_usage[model_name] = model_usage.get(model_name, 0) + 1
            
            # Daily usage
            daily_usage = {}
            for query in recent_queries:
                if query.created_at:
                    date_key = query.created_at.date().isoformat()
                    daily_usage[date_key] = daily_usage.get(date_key, 0) + 1
            
            return {
                "period": f"{days} days",
                "summary": {
                    "total_queries": total_queries,
                    "total_tokens": total_tokens,
                    "total_cost": total_cost,
                    "avg_queries_per_day": total_queries / days
                },
                "model_usage": model_usage,
                "daily_usage": daily_usage,
                "top_models": sorted(model_usage.items(), key=lambda x: x[1], reverse=True)[:5]
            }
    
    async def _process_llm_request(self, query: LLMQuery, model: LLMModel) -> str:
        """Process LLM request (mock implementation)"""
        # Simulate processing delay
        await asyncio.sleep(0.5)
        
        # Mock response based on query type
        prompt_lower = query.prompt.lower()
        
        if "analyze" in prompt_lower or "analysis" in prompt_lower:
            return f"Based on my analysis of your request, here are the key insights: {query.prompt[:100]}... The data suggests several important patterns that warrant further investigation."
        
        elif "summarize" in prompt_lower or "summary" in prompt_lower:
            return f"Summary: {query.prompt[:50]}... In conclusion, the main points are clearly outlined and provide a comprehensive overview of the topic."
        
        elif "question" in prompt_lower or "?" in query.prompt:
            return f"To answer your question about '{query.prompt[:50]}...', I would say that this is a complex topic that requires careful consideration of multiple factors."
        
        else:
            return f"Thank you for your query: '{query.prompt[:50]}...'. I've processed your request using the {model.name} model and generated this comprehensive response tailored to your needs."
    
    def _is_safe_content(self, content: str, safety_level: SafetyLevel) -> bool:
        """Check if content passes safety filters"""
        content_lower = content.lower()
        
        # Basic safety filtering
        if safety_level == SafetyLevel.STRICT:
            # Very strict filtering
            unsafe_patterns = self.content_filters + ["politics", "religion", "controversy"]
        elif safety_level == SafetyLevel.HIGH:
            unsafe_patterns = self.content_filters
        elif safety_level == SafetyLevel.MEDIUM:
            unsafe_patterns = ["violence", "hate", "harassment", "illegal"]
        else:  # LOW
            unsafe_patterns = ["illegal", "malware"]
        
        for pattern in unsafe_patterns:
            if pattern in content_lower:
                return False
        
        return True
    
    def _calculate_safety_score(self, content: str) -> float:
        """Calculate safety score for content"""
        content_lower = content.lower()
        
        # Simple scoring based on presence of concerning terms
        concerning_terms = 0
        for filter_term in self.content_filters:
            if filter_term in content_lower:
                concerning_terms += 1
        
        # Score from 0.0 to 1.0 (1.0 = completely safe)
        if concerning_terms == 0:
            return 1.0
        elif concerning_terms <= 2:
            return 0.7
        elif concerning_terms <= 4:
            return 0.4
        else:
            return 0.1
    
    def _initialize_sample_data(self):
        """Initialize with sample data"""
        # Sample models
        sample_models = [
            LLMModel(
                id="model_000001",
                name="GPT-3.5 Turbo",
                model_type=ModelType.GPT35_TURBO,
                endpoint="https://api.openai.com/v1/chat/completions",
                max_tokens=4096,
                temperature=0.7,
                cost_per_token=0.0015,
                created_at=datetime.now()
            ),
            LLMModel(
                id="model_000002",
                name="GPT-4",
                model_type=ModelType.GPT4,
                endpoint="https://api.openai.com/v1/chat/completions",
                max_tokens=8192,
                temperature=0.7,
                cost_per_token=0.03,
                created_at=datetime.now()
            ),
            LLMModel(
                id="model_000003",
                name="Claude-3 Sonnet",
                model_type=ModelType.CLAUDE,
                endpoint="https://api.anthropic.com/v1/messages",
                max_tokens=4096,
                temperature=0.7,
                cost_per_token=0.003,
                created_at=datetime.now()
            )
        ]
        
        for model in sample_models:
            self.models[model.id] = model
        
        logger.info("✅ LLM Query service initialized with sample data")

# Create service instance
llm_query_service = LLMQueryService()

if __name__ == "__main__":
    llm_query_service.run(debug=True)
