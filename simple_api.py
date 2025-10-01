import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from config.settings import MODEL_CONFIG
from agents.KnowledgeAgent import KnowledgeAgent
from utils.file_utils import secure_file_access
from utils.mongo_logger import mongo_logger
from utils.rag_client import rag_client
import time
import requests
import json
from utils.logger import get_logger

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if production mode is enabled
production_mode = os.getenv('PRODUCTION_MODE', 'false').lower() == 'true'
production_imports_available = False

# Import production components conditionally
if production_mode:
    try:
        from integration.agent_integration import get_agent_registry
        from security.auth import verify_token, create_access_token
        from observability.metrics import init_metrics, get_metrics
        from observability.tracing import init_tracing
        from observability.alerting import init_alerting
        
        # Initialize observability
        init_metrics('simple_api')
        init_tracing('simple_api', '1.0.0')
        
        # Initialize alerting
        alerting_config = {
            'slack': {
                'enabled': bool(os.getenv('SLACK_WEBHOOK_URL')),
                'webhook_url': os.getenv('SLACK_WEBHOOK_URL', ''),
                'channel': '#bhiv-alerts'
            }
        }
        init_alerting(alerting_config)
        
        production_imports_available = True
        logger.info("✅ Production mode enabled with full observability")
        
    except ImportError as e:
        logger.warning(f"⚠️ Production mode requested but dependencies missing: {e}")
        logger.info("🔄 Falling back to development mode")
        production_mode = False
        production_imports_available = False
else:
    logger.info("ℹ️ Running in development mode - production features disabled")

class ModelProvider:
    def __init__(self, model_config: Dict[str, Any], endpoint: str):
        # Read Ollama settings from environment for production usage
        self.model_name = os.getenv("OLLAMA_MODEL", model_config.get("model_name", "llama3.1"))
        # Default to local Ollama; can be overridden by env
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.endpoint = endpoint
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))
        logger.info(f"Initialized Ollama model: {self.model_name} for {self.endpoint} at {self.ollama_url}")

    def generate_response(self, prompt: str, fallback: str) -> tuple[str, int]:
        try:
            # Prepare the request payload for Ollama
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            }

            headers = {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"  # Skip ngrok browser warning
            }

            logger.info(f"Calling Ollama API for {self.endpoint}...")
            response = requests.post(
                self.ollama_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("response", "").strip()
                if generated_text:
                    logger.info(f"Successfully generated response for {self.endpoint}")
                    return generated_text, 200
                else:
                    logger.warning(f"Empty response from Ollama for {self.endpoint}")
                    return fallback, 500
            else:
                logger.error(f"Ollama API error for {self.endpoint}: {response.status_code} - {response.text}")
                return fallback, 500

        except requests.exceptions.Timeout:
            logger.error(f"Ollama API timeout for {self.endpoint}")
            return fallback, 500
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request error for {self.endpoint}: {e}")
            return fallback, 500
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama for {self.endpoint}: {e}")
            return fallback, 500

class SimpleOrchestrationEngine:
    def __init__(self):
        self.vector_stores = {}
        self.embedding_model = None
        self.model_providers = {
            "vedas": ModelProvider(MODEL_CONFIG["vedas_agent"], "ask-vedas"),
            "edumentor": ModelProvider(MODEL_CONFIG["edumentor_agent"], "edumentor"),
            "wellness": ModelProvider(MODEL_CONFIG["wellness_agent"], "wellness")
        }
        self.initialize_vector_stores()
        
    def initialize_vector_stores(self):
        """Initialize RAG API client - no local vector stores needed"""
        logger.info("Initializing RAG API client...")

        # Test RAG API connection
        try:
            health = rag_client.health_check()
            if health["status"] == "healthy":
                logger.info("✅ RAG API client initialized successfully")
                logger.info(f"📊 RAG API URL: {health['api_url']}")
            else:
                logger.warning("⚠️ RAG API client initialized but health check failed")
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG API client: {str(e)}")

        # Keep minimal FAISS fallback for emergency cases
        try:
            vector_store_dir = Path("vector_stores")
            if vector_store_dir.exists():
                self.embedding_model = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                store_names = ['vedas_index', 'wellness_index', 'educational_index', 'unified_index']
                for store_name in store_names:
                    store_path = vector_store_dir / store_name
                    if store_path.exists():
                        try:
                            store = FAISS.load_local(
                                str(store_path),
                                self.embedding_model,
                                allow_dangerous_deserialization=True
                            )
                            self.vector_stores[store_name.replace('_index', '')] = store
                            logger.info(f"Loaded fallback vector store: {store_name}")
                        except Exception as e:
                            logger.warning(f"Failed to load fallback vector store {store_name}: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize fallback vector stores: {str(e)}")

        logger.info("RAG API integration ready")
    
    def generate_response(self, prompt: str, fallback: str, endpoint: str) -> tuple[str, int]:
        return self.model_providers[endpoint].generate_response(prompt, fallback)
    
    def search_documents(self, query: str, store_type: str = "unified") -> list:
        """Search documents using RAG API"""
        try:
            logger.info(f"🔍 Searching RAG API for: '{query}'")

            # Query the RAG API
            rag_result = rag_client.query(query, top_k=3)

            if rag_result["status"] == 200 and rag_result.get("response"):
                # Format results to match expected structure
                formatted_results = [
                    {
                        "text": chunk["content"][:500],
                        "source": chunk["source"],
                        "groq_answer": rag_result.get("groq_answer", "")  # Include groq_answer in first result
                    }
                    for chunk in rag_result["response"]
                ]
                logger.info(f"RAG API found {len(formatted_results)} results for '{query}'")
                return formatted_results
            else:
                logger.warning("⚠️ RAG API returned no results")
                return []

        except Exception as e:
            logger.error(f"RAG API search error: {str(e)}")

            # Fallback to file-based retriever if RAG API fails
            try:
                from utils.file_based_retriever import file_retriever
                results = file_retriever.search(query, limit=3)
                formatted_results = [{"text": doc["text"][:500], "source": doc.get("source", "file_based_kb")} for doc in results]
                logger.info(f"File-based fallback found {len(formatted_results)} results for '{query}'")
                return formatted_results
            except Exception as fallback_error:
                logger.error(f"File-based fallback error: {str(fallback_error)}")
                return []

engine = SimpleOrchestrationEngine()

class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = "anonymous"

class QueryKBRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 5
    user_id: Optional[str] = "anonymous"

class SimpleResponse(BaseModel):
    query_id: str
    query: str
    response: str
    sources: list
    timestamp: str
    endpoint: str
    status: int  # Added status field

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Simple Orchestration API...")
    engine.initialize_vector_stores()
    logger.info("Simple Orchestration API ready with RAG integration!")
    yield
    logger.info("Shutting down Simple Orchestration API...")

app = FastAPI(
    title="Simple Orchestration API",
    description="Three simple endpoints: ask-vedas, edumentor, wellness with GET and POST methods",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize enhanced agent registry if in production mode
enhanced_agent_registry = None
if production_mode:
    try:
        enhanced_agent_registry = get_agent_registry()
        logger.info("✅ Enhanced agent registry initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize enhanced agent registry: {e}")

# Authentication dependency for production mode
async def get_current_user_optional(authorization: Optional[str] = Header(None)):
    """Optional authentication - only required in production mode"""
    if not production_mode:
        return {"sub": "dev_user", "role": "admin"}  # Dev mode bypass
    
    if not authorization:
        return None
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = verify_token(token)
        return payload
    except Exception:
        return None

# Enhanced agent processing function
async def process_with_enhanced_agent(agent_name: str, query: str, user_context: dict = None):
    """Process query with enhanced agent if in production mode"""
    if production_mode and enhanced_agent_registry:
        try:
            # Create a demo token for development compatibility
            demo_token = None
            if user_context and user_context.get("sub"):
                demo_token = create_access_token(user_context)
            
            result = await enhanced_agent_registry.process_query(
                agent_name=agent_name,
                query=query,
                context={"api": "simple_api", "user_id": user_context.get("sub", "anonymous") if user_context else "anonymous"},
                user_token=demo_token
            )
            
            if result.get("success"):
                return {
                    "response": result.get("result", "No response generated"),
                    "enhanced": True,
                    "processing_time": result.get("processing_time", 0),
                    "agent": agent_name
                }
            else:
                logger.warning(f"Enhanced agent {agent_name} failed: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Enhanced agent processing failed: {e}")
            return None
    
    return None

# Health check data
health_data = {
    "startup_time": datetime.now(),
    "total_requests": 0,
    "successful_requests": 0
}

@app.get("/ask-vedas")
async def ask_vedas_get(
    query: str = Query(..., description="Your spiritual question"),
    user_id: str = Query("anonymous", description="User ID"),
    user: dict = Depends(get_current_user_optional)
):
    return await process_vedas_query(query, user_id, user)

@app.post("/ask-vedas")
async def ask_vedas_post(
    request: QueryRequest,
    user: dict = Depends(get_current_user_optional)
):
    return await process_vedas_query(request.query, request.user_id, user)

async def process_vedas_query(query: str, user_id: str, user: dict = None):
    print(f"\n🕉️  [VEDAS ENDPOINT] Received spiritual query")
    print(f"🙏 [SPIRITUAL QUERY] '{query[:100]}{'...' if len(query) > 100 else ''}'")
    
    # Try enhanced agent first if in production mode
    enhanced_result = await process_with_enhanced_agent("vedas", query, user)
    if enhanced_result:
        print(f"✨ [ENHANCED] Using production agent with security & observability")
        return SimpleResponse(
            query_id=str(uuid.uuid4()),
            query=query,
            response=enhanced_result["response"],
            sources=[{"text": "Enhanced agent response", "source": "production_vedas_agent"}],
            timestamp=datetime.now().isoformat(),
            endpoint="ask-vedas",
            status=200
        )
    
    # Fallback to original implementation
    try:
        print(f"📚 [KNOWLEDGE SEARCH] Searching for spiritual wisdom...")
        sources = engine.search_documents(query, "vedas")
        print(f"✅ [FOUND] {len(sources)} relevant sources")

        # Extract groq_answer from RAG API response if available
        groq_answer = None
        if sources and len(sources) > 0:
            # The RAG API response includes groq_answer in the first source
            first_source = sources[0]
            if "groq_answer" in first_source:
                groq_answer = first_source["groq_answer"]

        # Use groq_answer if available, otherwise use fallback
        if groq_answer:
            response_text = groq_answer
            status = 200
            print(f"✨ [RAG API] Using groq_answer from RAG API")
        else:
            # Fallback to generic response
            response_text = f"The ancient Vedic texts teach us to seek truth through self-reflection and righteous action. Regarding '{query}', remember that true wisdom comes from understanding the interconnectedness of all existence. Practice mindfulness, act with compassion, and seek the divine within yourself."
            status = 500
            print(f"⚠️ [FALLBACK] Using generic response")

        return SimpleResponse(
            query_id=str(uuid.uuid4()),
            query=query,
            response=response_text,
            sources=sources,
            timestamp=datetime.now().isoformat(),
            endpoint="ask-vedas",
            status=status
        )
    except Exception as e:
        logger.error(f"Error in ask-vedas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/edumentor")
async def edumentor_get(
    query: str = Query(..., description="Your learning question"),
    user_id: str = Query("anonymous", description="User ID")
):
    return await process_edumentor_query(query, user_id)

@app.post("/edumentor")
async def edumentor_post(request: QueryRequest):
    return await process_edumentor_query(request.query, request.user_id)

async def process_edumentor_query(query: str, user_id: str):
    try:
        # Get RAG API response which includes both chunks and groq_answer
        sources = engine.search_documents(query, "educational")

        # Extract groq_answer from RAG API response if available
        groq_answer = None
        if sources and len(sources) > 0:
            # The RAG API response includes groq_answer in the first source
            first_source = sources[0]
            if "groq_answer" in first_source:
                groq_answer = first_source["groq_answer"]

        # Use groq_answer if available, otherwise use fallback
        if groq_answer:
            response_text = groq_answer
            status = 200
        else:
            # Fallback to generic response
            response_text = f"Great question about '{query}'! This is an important topic to understand. Let me break it down for you in simple terms with practical examples that will help you learn and remember the key concepts. The main idea is to understand the fundamental principles and how they apply in real-world situations."
            status = 500

        return SimpleResponse(
            query_id=str(uuid.uuid4()),
            query=query,
            response=response_text,
            sources=sources,
            timestamp=datetime.now().isoformat(),
            endpoint="edumentor",
            status=status
        )
    except Exception as e:
        logger.error(f"Error in edumentor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/wellness")
async def wellness_get(
    query: str = Query(..., description="Your wellness concern"),
    user_id: str = Query("anonymous", description="User ID")
):
    return await process_wellness_query(query, user_id)

@app.post("/wellness")
async def wellness_post(request: QueryRequest):
    return await process_wellness_query(request.query, request.user_id)

async def process_wellness_query(query: str, user_id: str):
    try:
        sources = engine.search_documents(query, "wellness")

        # Extract groq_answer from RAG API response if available
        groq_answer = None
        if sources and len(sources) > 0:
            # The RAG API response includes groq_answer in the first source
            first_source = sources[0]
            if "groq_answer" in first_source:
                groq_answer = first_source["groq_answer"]

        # Use groq_answer if available, otherwise use fallback
        if groq_answer:
            response_text = groq_answer
            status = 200
        else:
            # Fallback to generic response
            response_text = f"Thank you for reaching out about '{query}'. It's important to take care of your wellbeing. Here are some gentle suggestions: Take time for self-care, practice deep breathing, stay connected with supportive people, and remember that small steps can lead to big improvements. If you're experiencing serious concerns, please consider speaking with a healthcare professional."
            status = 500

        return SimpleResponse(
            query_id=str(uuid.uuid4()),
            query=query,
            response=response_text,
            sources=sources,
            timestamp=datetime.now().isoformat(),
            endpoint="wellness",
            status=status
        )
    except Exception as e:
        logger.error(f"Error in wellness: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== KNOWLEDGE BASE ENDPOINTS ====================

# Initialize KnowledgeAgent with NAS support
try:
    from example.nas_retriever import NASKnowledgeRetriever
    # Try to initialize with NAS retriever first
    nas_retriever = NASKnowledgeRetriever("vedas", qdrant_url="localhost:6333")
    if nas_retriever.qdrant_available:
        logger.info("✅ NAS retriever available, initializing KnowledgeAgent with NAS support")
        knowledge_agent = KnowledgeAgent()
    else:
        logger.warning("⚠️ NAS retriever not available, using fallback KnowledgeAgent")
        knowledge_agent = KnowledgeAgent()
except Exception as e:
    logger.warning(f"Failed to initialize NAS retriever: {e}, using fallback KnowledgeAgent")
    knowledge_agent = KnowledgeAgent()

# Initialize NAS Knowledge Base
nas_kb = None

def get_nas_kb():
    """Get or initialize NAS Knowledge Base"""
    global nas_kb
    if nas_kb is None:
        from bhiv_knowledge_base import BHIVKnowledgeBase
        nas_path = os.getenv("NAS_PATH", r"\\192.168.0.94\Guruukul_DB")
        nas_kb = BHIVKnowledgeBase(nas_path, use_qdrant=True)  # Enable Qdrant
        logger.info("✅ NAS Knowledge Base initialized for API with Qdrant")
    return nas_kb

@app.get("/query-kb")
async def query_knowledge_base_get(
    query: str = Query(..., description="Your knowledge base query"),
    filters: Optional[str] = Query(None, description="JSON string of filters"),
    limit: int = Query(5, description="Number of results to return"),
    user_id: str = Query("anonymous", description="User ID")
):
    """GET method for knowledge base queries"""
    try:
        # Parse filters if provided
        parsed_filters = None
        if filters:
            import json
            parsed_filters = json.loads(filters)

        return await process_knowledge_query(query, parsed_filters, limit, user_id)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid filters JSON format")

@app.post("/query-kb")
async def query_knowledge_base_post(request: QueryKBRequest):
    """POST method for knowledge base queries"""
    return await process_knowledge_query(request.query, request.filters, request.limit, request.user_id)

async def process_knowledge_query(query: str, filters: Optional[Dict[str, Any]], limit: int, user_id: str):
    """Process knowledge base query and return enhanced response."""
    start_time = time.time()
    query_id = str(uuid.uuid4())

    try:
        # Query the knowledge base using KnowledgeAgent
        result = knowledge_agent.run(
            input_path=query,
            model="knowledge_agent",
            input_type="text",
            task_id=query_id
        )

        response_time = time.time() - start_time

        # Extract metadata for logging
        sources = result.get("sources", [])
        results_count = result.get("knowledge_base_results", 0)
        retriever_type = result.get("metadata", {}).get("retriever", "unknown")

        # Log to MongoDB for analytics
        kb_log_data = {
            'query_id': query_id,
            'user_id': user_id,
            'query': query,
            'filters': filters or {},
            'results_count': results_count,
            'sources': sources,
            'retriever_type': retriever_type,
            'response_time': response_time,
            'enhanced_by_llm': not result.get("fallback", False),
            'status': result.get("status", 200)
        }

        # Async log to MongoDB
        try:
            await mongo_logger.log_kb_query(kb_log_data)
        except Exception as log_error:
            logger.warning(f"Failed to log KB query to MongoDB: {log_error}")

        # Log the query for analytics
        logger.info(f"Knowledge base query {query_id}: {query} -> {result.get('status', 'unknown')} ({response_time:.2f}s)")

        # Update health stats
        health_data["total_requests"] += 1
        if result.get("status") == 200:
            health_data["successful_requests"] += 1

        return result

    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"Error in knowledge base query: {e}")

        # Log failed query
        try:
            await mongo_logger.log_kb_query({
                'query_id': query_id,
                'user_id': user_id,
                'query': query,
                'filters': filters or {},
                'results_count': 0,
                'sources': [],
                'retriever_type': 'error',
                'response_time': response_time,
                'enhanced_by_llm': False,
                'status': 500,
                'error': str(e)
            })
        except Exception:
            pass

        raise HTTPException(status_code=500, detail=str(e))

# ==================== NAS KNOWLEDGE BASE ENDPOINTS ====================

@app.get("/nas-kb/status")
async def get_nas_kb_status():
    """Get NAS Knowledge Base status and statistics"""
    try:
        kb = get_nas_kb()
        test_results = kb.test_system()
        stats = kb.get_stats()

        return {
            "status": "success",
            "system_tests": test_results,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting NAS KB status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nas-kb/documents")
async def list_nas_documents():
    """List all documents in the NAS Knowledge Base"""
    try:
        kb = get_nas_kb()
        documents = kb.list_documents()

        return {
            "status": "success",
            "documents": documents,
            "count": len(documents),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error listing NAS documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nas-kb/search")
async def search_nas_kb(
    query: str = Query(..., description="Search query"),
    limit: int = Query(5, description="Maximum number of results")
):
    """Search the NAS Knowledge Base"""
    try:
        kb = get_nas_kb()
        results = kb.search(query, limit=limit)

        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error searching NAS KB: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nas-kb/document/{document_id}")
async def get_nas_document(document_id: str):
    """Get content of a specific document from NAS Knowledge Base"""
    try:
        kb = get_nas_kb()
        content = kb.get_document_content(document_id)

        if content is None:
            raise HTTPException(status_code=404, detail="Document not found")

        return {
            "status": "success",
            "document_id": document_id,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting NAS document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "Simple Orchestration API",
        "version": "1.0.0",
        "endpoints": {
            "ask-vedas": {
                "GET": "/ask-vedas?query=your_question&user_id=optional",
                "POST": "/ask-vedas with JSON body"
            },
            "edumentor": {
                "GET": "/edumentor?query=your_question&user_id=optional",
                "POST": "/edumentor with JSON body"
            },
            "wellness": {
                "GET": "/wellness?query=your_question&user_id=optional",
                "POST": "/wellness with JSON body"
            },
            "query-kb": {
                "GET": "/query-kb?query=your_question&filters=optional&limit=5&user_id=optional",
                "POST": "/query-kb with JSON body including query, filters, limit, user_id"
            },
            "nas-kb": {
                "status": "/nas-kb/status - Get NAS Knowledge Base status",
                "documents": "/nas-kb/documents - List all documents",
                "search": "/nas-kb/search?query=your_query&limit=5 - Search documents",
                "document": "/nas-kb/document/{document_id} - Get specific document content"
            }
        },
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Simple API."""
    try:
        # Update request count
        health_data["total_requests"] += 1

        # Check if engine is working
        engine_status = "healthy"
        try:
            # Test RAG API health
            health = rag_client.health_check()
            if health["status"] != "healthy":
                engine_status = "degraded"
        except Exception as e:
            engine_status = f"unhealthy: {str(e)}"

        # Calculate uptime
        uptime_seconds = (datetime.now() - health_data["startup_time"]).total_seconds()

        return {
            "status": "healthy" if engine_status == "healthy" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime_seconds,
            "services": {
                "rag_api": engine_status,
                "llm_models": "healthy"  # Assuming models are working if engine works
            },
            "metrics": {
                "total_requests": health_data["total_requests"],
                "successful_requests": health_data["successful_requests"]
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/kb-analytics")
async def get_kb_analytics(hours: int = Query(24, description="Time range in hours")):
    """Get knowledge base analytics and usage statistics."""
    try:
        analytics = await mongo_logger.get_kb_analytics(hours)
        return {
            "status": "success",
            "analytics": analytics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting KB analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/kb-feedback")
async def submit_kb_feedback(feedback_data: Dict[str, Any]):
    """Submit feedback for a knowledge base query."""
    try:
        query_id = feedback_data.get("query_id")
        feedback = feedback_data.get("feedback", {})

        if not query_id:
            raise HTTPException(status_code=400, detail="query_id is required")

        success = await mongo_logger.update_kb_feedback(query_id, feedback)

        if success:
            return {
                "status": "success",
                "message": "Feedback recorded successfully",
                "query_id": query_id
            }
        else:
            return {
                "status": "error",
                "message": "Failed to record feedback",
                "query_id": query_id
            }
    except Exception as e:
        logger.error(f"Error submitting KB feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import argparse
    parser = argparse.ArgumentParser(description="Simple Orchestration API")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on (default: 0.0.0.0)")
    args = parser.parse_args()
    print("\n" + "="*60)
    print("  SIMPLE ORCHESTRATION API")
    print("="*60)
    print(f" Server URL: http://{args.host}:{args.port}")
    print(f" API Documentation: http://{args.host}:{args.port}/docs")
    print("\n Endpoints:")
    print("   GET/POST /ask-vedas - Spiritual wisdom")
    print("   GET/POST /edumentor - Educational content")
    print("   GET/POST /wellness - Health advice")
    print("="*60)
    uvicorn.run(app, host=args.host, port=args.port)



# import os
# import uuid
# import logging
# from datetime import datetime
# from typing import Optional, Dict, Any
# from pathlib import Path

# # FastAPI imports
# from fastapi import FastAPI, HTTPException, Query
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from contextlib import asynccontextmanager

# # LangChain imports
# from langchain_core.messages import HumanMessage
# from langchain_groq import ChatGroq
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_community.vectorstores import FAISS

# # Environment and settings
# from dotenv import load_dotenv
# from config.settings import MODEL_CONFIG

# # Load environment variables
# load_dotenv()

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# class ModelProvider:
#     """Model provider for Groq API using LangChain"""
#     def __init__(self, model_config: Dict[str, Any], endpoint: str):
#         self.model = None
#         self.model_name = model_config.get("model_name", "llama-3.1-8b-instruct")
#         self.api_key = os.getenv("GROQ_API_KEY")
#         self.backup_api_key = os.getenv("GROQ_API_KEY_BACKUP")
#         self.endpoint = endpoint
#         self.initialize_model()

#     def initialize_model(self):
#         """Initialize the Groq model"""
#         try:
#             if not self.api_key:
#                 raise ValueError("GROQ_API_KEY not found")
#             self.model = ChatGroq(
#                 model=self.model_name,
#                 api_key=self.api_key
#             )
#             logger.info(f"Initialized Groq model: {self.model_name} for {self.endpoint}")
#         except Exception as e:
#             logger.error(f"Failed to initialize model for {self.endpoint} with primary key: {e}")
#             if self.backup_api_key:
#                 try:
#                     logger.info(f"Trying backup API key for {self.endpoint}")
#                     self.model = ChatGroq(
#                         model=self.model_name,
#                         api_key=self.backup_api_key
#                     )
#                     logger.info(f"Initialized Groq model with backup key: {self.model_name}")
#                 except Exception as e:
#                     logger.error(f"Backup key failed for {self.endpoint}: {e}")
#                     self.model = None
#             else:
#                 self.model = None

#     def generate_response(self, prompt: str, fallback: str) -> str:
#         """Generate response using the Groq model"""
#         if not self.model:
#             logger.warning(f"No model initialized for {self.endpoint}. Using fallback response.")
#             return fallback
        
#         try:
#             response = self.model.invoke([HumanMessage(content=prompt)])
#             return response.content.strip()
#         except Exception as e:
#             logger.error(f"Model generation error for {self.endpoint}: {e}")
#             return fallback

# class SimpleOrchestrationEngine:
#     """Simple orchestration engine for the three main endpoints"""
    
#     def __init__(self):
#         self.vector_stores = {}
#         self.embedding_model = None
#         self.model_providers = {
#             "vedas": ModelProvider(MODEL_CONFIG["vedas_agent"], "ask-vedas"),
#             "edumentor": ModelProvider(MODEL_CONFIG["edumentor_agent"], "edumentor"),
#             "wellness": ModelProvider(MODEL_CONFIG["wellness_agent"], "wellness")
#         }
#         self.initialize_vector_stores()
        
#     def initialize_vector_stores(self):
#         """Initialize vector stores and embedding model"""
#         logger.info("Initializing embedding model...")
#         self.embedding_model = HuggingFaceEmbeddings(
#             model_name="sentence-transformers/all-MiniLM-L6-v2"
#         )
        
#         # Load existing vector stores
#         vector_store_dir = Path("vector_stores")
#         store_names = ['vedas_index', 'wellness_index', 'educational_index', 'unified_index']
        
#         for store_name in store_names:
#             store_path = vector_store_dir / store_name
#             if store_path.exists():
#                 try:
#                     store = FAISS.load_local(
#                         str(store_path), 
#                         self.embedding_model, 
#                         allow_dangerous_deserialization=True
#                     )
#                     self.vector_stores[store_name.replace('_index', '')] = store
#                     logger.info(f"Loaded vector store: {store_name}")
#                 except Exception as e:
#                     logger.error(f"Failed to load vector store {store_name}: {e}")
        
#         logger.info("RAG API integration ready")
    
#     def generate_response(self, prompt: str, fallback: str, endpoint: str) -> str:
#         """Generate response using the appropriate model provider"""
#         return self.model_providers[endpoint].generate_response(prompt, fallback)
    
#     def search_documents(self, query: str, store_type: str = "unified") -> list:
#         """Search relevant documents from vector store"""
#         if store_type in self.vector_stores:
#             try:
#                 retriever = self.vector_stores[store_type].as_retriever(search_kwargs={"k": 3})
#                 docs = retriever.invoke(query)
#                 return [{"text": doc.page_content[:500], "source": doc.metadata.get("source", "unknown")} for doc in docs]
#             except Exception as e:
#                 logger.error(f"Vector search error: {e}")
#         return []

# # Global engine instance
# engine = SimpleOrchestrationEngine()

# # Pydantic models
# class QueryRequest(BaseModel):
#     query: str
#     user_id: Optional[str] = "anonymous"

# class SimpleResponse(BaseModel):
#     query_id: str
#     query: str
#     response: str
#     sources: list
#     timestamp: str
#     endpoint: str

# # Lifespan handler
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     logger.info("Starting Simple Orchestration API...")
#     engine.initialize_vector_stores()
#     logger.info("Simple Orchestration API ready!")
    
#     yield
    
#     # Shutdown
#     logger.info("Shutting down Simple Orchestration API...")

# # Initialize FastAPI app
# app = FastAPI(
#     title="Simple Orchestration API",
#     description="Three simple endpoints: ask-vedas, edumentor, wellness with GET and POST methods",
#     version="1.0.0",
#     lifespan=lifespan
# )

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ==================== ASK-VEDAS ENDPOINTS ====================

# @app.get("/ask-vedas")
# async def ask_vedas_get(
#     query: str = Query(..., description="Your spiritual question"),
#     user_id: str = Query("anonymous", description="User ID")
# ):
#     """GET method for Vedas spiritual wisdom"""
#     return await process_vedas_query(query, user_id)

# @app.post("/ask-vedas")
# async def ask_vedas_post(request: QueryRequest):
#     """POST method for Vedas spiritual wisdom"""
#     return await process_vedas_query(request.query, request.user_id)

# async def process_vedas_query(query: str, user_id: str):
#     """Process Vedas query and return spiritual wisdom"""
#     try:
#         # Search relevant documents
#         sources = engine.search_documents(query, "vedas")
#         context = "\n".join([doc["text"] for doc in sources[:2]])
        
#         # Generate response
#         prompt = f"""You are a wise spiritual teacher. Based on ancient Vedic wisdom, provide profound guidance for this question: "{query}"

# Context from sacred texts:
# {context}

# Provide spiritual wisdom that is authentic, practical, and inspiring. Keep it concise but meaningful."""

#         fallback = f"The ancient Vedic texts teach us to seek truth through self-reflection and righteous action. Regarding '{query}', remember that true wisdom comes from understanding the interconnectedness of all existence. Practice mindfulness, act with compassion, and seek the divine within yourself."
        
#         response_text = engine.generate_response(prompt, fallback, "vedas")
        
#         return SimpleResponse(
#             query_id=str(uuid.uuid4()),
#             query=query,
#             response=response_text,
#             sources=sources,
#             timestamp=datetime.now().isoformat(),
#             endpoint="ask-vedas"
#         )
        
#     except Exception as e:
#         logger.error(f"Error in ask-vedas: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# # ==================== EDUMENTOR ENDPOINTS ====================

# @app.get("/edumentor")
# async def edumentor_get(
#     query: str = Query(..., description="Your learning question"),
#     user_id: str = Query("anonymous", description="User ID")
# ):
#     """GET method for educational content"""
#     return await process_edumentor_query(query, user_id)

# @app.post("/edumentor")
# async def edumentor_post(request: QueryRequest):
#     """POST method for educational content"""
#     return await process_edumentor_query(request.query, request.user_id)

# async def process_edumentor_query(query: str, user_id: str):
#     """Process educational query and return learning content"""
#     try:
#         # Search relevant documents
#         sources = engine.search_documents(query, "educational")
#         context = "\n".join([doc["text"] for doc in sources[:2]])
        
#         # Generate response
#         prompt = f"""You are an expert educator. Explain this topic clearly and engagingly: "{query}"

# Educational context:
# {context}

# Provide a clear, comprehensive explanation that:
# - Uses simple, understandable language
# - Includes practical examples
# - Makes the topic interesting and memorable
# - Is suitable for students"""

#         fallback = f"Great question about '{query}'! This is an important topic to understand. Let me break it down for you in simple terms with practical examples that will help you learn and remember the key concepts. The main idea is to understand the fundamental principles and how they apply in real-world situations."
        
#         response_text = engine.generate_response(prompt, fallback, "edumentor")
        
#         return SimpleResponse(
#             query_id=str(uuid.uuid4()),
#             query=query,
#             response=response_text,
#             sources=sources,
#             timestamp=datetime.now().isoformat(),
#             endpoint="edumentor"
#         )
        
#     except Exception as e:
#         logger.error(f"Error in edumentor: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# # ==================== WELLNESS ENDPOINTS ====================

# @app.get("/wellness")
# async def wellness_get(
#     query: str = Query(..., description="Your wellness concern"),
#     user_id: str = Query("anonymous", description="User ID")
# ):
#     """GET method for wellness advice"""
#     return await process_wellness_query(query, user_id)

# @app.post("/wellness")
# async def wellness_post(request: QueryRequest):
#     """POST method for wellness advice"""
#     return await process_wellness_query(request.query, request.user_id)

# async def process_wellness_query(query: str, user_id: str):
#     """Process wellness query and return health advice"""
#     try:
#         # Search relevant documents
#         sources = engine.search_documents(query, "wellness")
#         context = "\n".join([doc["text"] for doc in sources[:2]])
        
#         # Generate response
#         prompt = f"""You are a compassionate wellness counselor. Provide caring, helpful advice for: "{query}"

# Wellness context:
# {context}

# Provide supportive guidance that:
# - Shows empathy and understanding
# - Offers practical, actionable advice
# - Promotes overall wellbeing
# - Is encouraging and positive"""

#         fallback = f"Thank you for reaching out about '{query}'. It's important to take care of your wellbeing. Here are some gentle suggestions: Take time for self-care, practice deep breathing, stay connected with supportive people, and remember that small steps can lead to big improvements. If you're experiencing serious concerns, please consider speaking with a healthcare professional."
        
#         response_text = engine.generate_response(prompt, fallback, "wellness")
        
#         return SimpleResponse(
#             query_id=str(uuid.uuid4()),
#             query=query,
#             response=response_text,
#             sources=sources,
#             timestamp=datetime.now().isoformat(),
#             endpoint="wellness"
#         )
        
#     except Exception as e:
#         logger.error(f"Error in wellness: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# # ==================== ROOT ENDPOINT ====================

# @app.get("/")
# async def root():
#     """Root endpoint with API information"""
#     return {
#         "message": "Simple Orchestration API",
#         "version": "1.0.0",
#         "endpoints": {
#             "ask-vedas": {
#                 "GET": "/ask-vedas?query=your_question&user_id=optional",
#                 "POST": "/ask-vedas with JSON body"
#             },
#             "edumentor": {
#                 "GET": "/edumentor?query=your_question&user_id=optional", 
#                 "POST": "/edumentor with JSON body"
#             },
#             "wellness": {
#                 "GET": "/wellness?query=your_question&user_id=optional",
#                 "POST": "/wellness with JSON body"
#             }
#         },
#         "documentation": "/docs"
#     }

# if __name__ == "__main__":
#     import uvicorn
#     import argparse

#     # Parse command line arguments
#     parser = argparse.ArgumentParser(description="Simple Orchestration API")
#     parser.add_argument("--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
#     parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on (default: 0.0.0.0)")
#     args = parser.parse_args()

#     print("\n" + "="*60)
#     print("  SIMPLE ORCHESTRATION API")
#     print("="*60)
#     print(f" Server URL: http://{args.host}:{args.port}")
#     print(f" API Documentation: http://{args.host}:{args.port}/docs")
#     print("\n Endpoints:")
#     print("   GET/POST /ask-vedas - Spiritual wisdom")
#     print("   GET/POST /edumentor - Educational content")
#     print("   GET/POST /wellness - Health advice")
#     print("="*60)

#     uvicorn.run(app, host=args.host, port=args.port)




# """
# Simple FastAPI with 3 endpoints: ask-vedas, edumentor, wellness
# Each endpoint has both GET and POST methods for frontend integration
# """

# import os
# import uuid
# import logging
# from datetime import datetime
# from typing import Optional, Dict, Any
# from pathlib import Path

# # FastAPI imports
# from fastapi import FastAPI, HTTPException, Query
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from contextlib import asynccontextmanager

# # Environment and AI imports
# from dotenv import load_dotenv
# import google.generativeai as genai

# # LangChain imports
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_community.vectorstores import FAISS

# # Load environment variables
# load_dotenv()

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# class SimpleOrchestrationEngine:
#     """Simple orchestration engine for the three main endpoints"""
    
#     def __init__(self):
#         self.vector_stores = {}
#         self.embedding_model = None
#         self.gemini_model = None
#         self.initialize_gemini()
        
#     def initialize_gemini(self):
#         """Initialize Gemini API with failover"""
#         primary_key = os.getenv("GEMINI_API_KEY")
#         backup_key = os.getenv("GEMINI_API_KEY_BACKUP")
        
#         # Try primary key
#         if primary_key:
#             try:
#                 genai.configure(api_key=primary_key)
#                 self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
#                 test_response = self.gemini_model.generate_content("Hello")
#                 if test_response and test_response.text:
#                     logger.info("Gemini API initialized with primary key")
#                     return
#             except Exception as e:
#                 logger.warning(f"Primary Gemini API key failed: {e}")
        
#         # Try backup key
#         if backup_key:
#             try:
#                 genai.configure(api_key=backup_key)
#                 self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
#                 test_response = self.gemini_model.generate_content("Hello")
#                 if test_response and test_response.text:
#                     logger.info("Gemini API initialized with backup key")
#                     return
#             except Exception as e:
#                 logger.warning(f"Backup Gemini API key failed: {e}")
        
#         logger.error("Both Gemini API keys failed. Using fallback responses.")
#         self.gemini_model = None
    
#     def initialize_vector_stores(self):
#         """Initialize vector stores and embedding model"""
#         logger.info("Initializing embedding model...")
#         self.embedding_model = HuggingFaceEmbeddings(
#             model_name="sentence-transformers/all-MiniLM-L6-v2"
#         )
        
#         # Load existing vector stores
#         vector_store_dir = Path("vector_stores")
#         store_names = ['vedas_index', 'wellness_index', 'educational_index', 'unified_index']
        
#         for store_name in store_names:
#             store_path = vector_store_dir / store_name
#             if store_path.exists():
#                 try:
#                     store = FAISS.load_local(
#                         str(store_path), 
#                         self.embedding_model, 
#                         allow_dangerous_deserialization=True
#                     )
#                     self.vector_stores[store_name.replace('_index', '')] = store
#                     logger.info(f"Loaded vector store: {store_name}")
#                 except Exception as e:
#                     logger.error(f"Failed to load vector store {store_name}: {e}")
        
#         logger.info(f"Initialized with {len(self.vector_stores)} vector stores")
    
#     def generate_response(self, prompt: str, fallback: str) -> str:
#         """Generate response using Gemini API with fallback"""
#         if self.gemini_model:
#             try:
#                 response = self.gemini_model.generate_content(prompt)
#                 if response and response.text:
#                     return response.text.strip()
#             except Exception as e:
#                 logger.warning(f"Gemini API error: {e}")
        
#         return fallback
    
#     def search_documents(self, query: str, store_type: str = "unified") -> list:
#         """Search relevant documents from vector store"""
#         if store_type in self.vector_stores:
#             try:
#                 retriever = self.vector_stores[store_type].as_retriever(search_kwargs={"k": 3})
#                 docs = retriever.invoke(query)
#                 return [{"text": doc.page_content[:500], "source": doc.metadata.get("source", "unknown")} for doc in docs]
#             except Exception as e:
#                 logger.error(f"Vector search error: {e}")
#         return []

# # Global engine instance
# engine = SimpleOrchestrationEngine()

# # Pydantic models
# class QueryRequest(BaseModel):
#     query: str
#     user_id: Optional[str] = "anonymous"

# class SimpleResponse(BaseModel):
#     query_id: str
#     query: str
#     response: str
#     sources: list
#     timestamp: str
#     endpoint: str

# # Lifespan handler
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     logger.info("Starting Simple Orchestration API...")
#     engine.initialize_vector_stores()
#     logger.info("Simple Orchestration API ready!")
    
#     yield
    
#     # Shutdown
#     logger.info("Shutting down Simple Orchestration API...")

# # Initialize FastAPI app
# app = FastAPI(
#     title="Simple Orchestration API",
#     description="Three simple endpoints: ask-vedas, edumentor, wellness with GET and POST methods",
#     version="1.0.0",
#     lifespan=lifespan
# )

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ==================== ASK-VEDAS ENDPOINTS ====================

# @app.get("/ask-vedas")
# async def ask_vedas_get(
#     query: str = Query(..., description="Your spiritual question"),
#     user_id: str = Query("anonymous", description="User ID")
# ):
#     """GET method for Vedas spiritual wisdom"""
#     return await process_vedas_query(query, user_id)

# @app.post("/ask-vedas")
# async def ask_vedas_post(request: QueryRequest):
#     """POST method for Vedas spiritual wisdom"""
#     return await process_vedas_query(request.query, request.user_id)

# async def process_vedas_query(query: str, user_id: str):
#     """Process Vedas query and return spiritual wisdom"""
#     try:
#         # Search relevant documents
#         sources = engine.search_documents(query, "vedas")
#         context = "\n".join([doc["text"] for doc in sources[:2]])
        
#         # Generate response
#         prompt = f"""You are a wise spiritual teacher. Based on ancient Vedic wisdom, provide profound guidance for this question: "{query}"

# Context from sacred texts:
# {context}

# Provide spiritual wisdom that is authentic, practical, and inspiring. Keep it concise but meaningful."""

#         fallback = f"The ancient Vedic texts teach us to seek truth through self-reflection and righteous action. Regarding '{query}', remember that true wisdom comes from understanding the interconnectedness of all existence. Practice mindfulness, act with compassion, and seek the divine within yourself."
        
#         response_text = engine.generate_response(prompt, fallback)
        
#         return SimpleResponse(
#             query_id=str(uuid.uuid4()),
#             query=query,
#             response=response_text,
#             sources=sources,
#             timestamp=datetime.now().isoformat(),
#             endpoint="ask-vedas"
#         )
        
#     except Exception as e:
#         logger.error(f"Error in ask-vedas: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# # ==================== EDUMENTOR ENDPOINTS ====================

# @app.get("/edumentor")
# async def edumentor_get(
#     query: str = Query(..., description="Your learning question"),
#     user_id: str = Query("anonymous", description="User ID")
# ):
#     """GET method for educational content"""
#     return await process_edumentor_query(query, user_id)

# @app.post("/edumentor")
# async def edumentor_post(request: QueryRequest):
#     """POST method for educational content"""
#     return await process_edumentor_query(request.query, request.user_id)

# async def process_edumentor_query(query: str, user_id: str):
#     """Process educational query and return learning content"""
#     try:
#         # Search relevant documents
#         sources = engine.search_documents(query, "educational")
#         context = "\n".join([doc["text"] for doc in sources[:2]])
        
#         # Generate response
#         prompt = f"""You are an expert educator. Explain this topic clearly and engagingly: "{query}"

# Educational context:
# {context}

# Provide a clear, comprehensive explanation that:
# - Uses simple, understandable language
# - Includes practical examples
# - Makes the topic interesting and memorable
# - Is suitable for students"""

#         fallback = f"Great question about '{query}'! This is an important topic to understand. Let me break it down for you in simple terms with practical examples that will help you learn and remember the key concepts. The main idea is to understand the fundamental principles and how they apply in real-world situations."
        
#         response_text = engine.generate_response(prompt, fallback)
        
#         return SimpleResponse(
#             query_id=str(uuid.uuid4()),
#             query=query,
#             response=response_text,
#             sources=sources,
#             timestamp=datetime.now().isoformat(),
#             endpoint="edumentor"
#         )
        
#     except Exception as e:
#         logger.error(f"Error in edumentor: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# # ==================== WELLNESS ENDPOINTS ====================

# @app.get("/wellness")
# async def wellness_get(
#     query: str = Query(..., description="Your wellness concern"),
#     user_id: str = Query("anonymous", description="User ID")
# ):
#     """GET method for wellness advice"""
#     return await process_wellness_query(query, user_id)

# @app.post("/wellness")
# async def wellness_post(request: QueryRequest):
#     """POST method for wellness advice"""
#     return await process_wellness_query(request.query, request.user_id)

# async def process_wellness_query(query: str, user_id: str):
#     """Process wellness query and return health advice"""
#     try:
#         # Search relevant documents
#         sources = engine.search_documents(query, "wellness")
#         context = "\n".join([doc["text"] for doc in sources[:2]])
        
#         # Generate response
#         prompt = f"""You are a compassionate wellness counselor. Provide caring, helpful advice for: "{query}"

# Wellness context:
# {context}

# Provide supportive guidance that:
# - Shows empathy and understanding
# - Offers practical, actionable advice
# - Promotes overall wellbeing
# - Is encouraging and positive"""

#         fallback = f"Thank you for reaching out about '{query}'. It's important to take care of your wellbeing. Here are some gentle suggestions: Take time for self-care, practice deep breathing, stay connected with supportive people, and remember that small steps can lead to big improvements. If you're experiencing serious concerns, please consider speaking with a healthcare professional."
        
#         response_text = engine.generate_response(prompt, fallback)
        
#         return SimpleResponse(
#             query_id=str(uuid.uuid4()),
#             query=query,
#             response=response_text,
#             sources=sources,
#             timestamp=datetime.now().isoformat(),
#             endpoint="wellness"
#         )
        
#     except Exception as e:
#         logger.error(f"Error in wellness: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# # ==================== ROOT ENDPOINT ====================

# @app.get("/")
# async def root():
#     """Root endpoint with API information"""
#     return {
#         "message": "Simple Orchestration API",
#         "version": "1.0.0",
#         "endpoints": {
#             "ask-vedas": {
#                 "GET": "/ask-vedas?query=your_question&user_id=optional",
#                 "POST": "/ask-vedas with JSON body"
#             },
#             "edumentor": {
#                 "GET": "/edumentor?query=your_question&user_id=optional", 
#                 "POST": "/edumentor with JSON body"
#             },
#             "wellness": {
#                 "GET": "/wellness?query=your_question&user_id=optional",
#                 "POST": "/wellness with JSON body"
#             }
#         },
#         "documentation": "/docs"
#     }

# if __name__ == "__main__":
#     import uvicorn
#     import argparse

#     # Parse command line arguments
#     parser = argparse.ArgumentParser(description="Simple Orchestration API")
#     parser.add_argument("--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
#     parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on (default: 0.0.0.0)")
#     args = parser.parse_args()

#     print("\n" + "="*60)
#     print("  SIMPLE ORCHESTRATION API")
#     print("="*60)
#     print(f" Server URL: http://{args.host}:{args.port}")
#     print(f" API Documentation: http://{args.host}:{args.port}/docs")
#     print("\n Endpoints:")
#     print("   GET/POST /ask-vedas - Spiritual wisdom")
#     print("   GET/POST /edumentor - Educational content")
#     print("   GET/POST /wellness - Health advice")
#     print("="*60)

#     uvicorn.run(app, host=args.host, port=args.port)
