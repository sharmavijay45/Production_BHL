# BHIV Core - Complete API Documentation

## Overview

This document provides comprehensive API documentation for the BHIV Core system, including all endpoints, request/response formats, and testing commands.

## Base URLs

- **Simple API**: `http://localhost:8001` - Agent-specific endpoints
- **MCP Bridge**: `http://localhost:8002` - Task routing and RL
- **Web Interface**: `http://localhost:8003` - Web dashboard
- **Agent Orchestrator**: `http://localhost:8080` - Unified agent system with EMS integration

## Authentication

Most endpoints require API key authentication:
```bash
-H "X-API-Key: uniguru-dev-key-2025"
```

## 🤖 Agent Orchestrator API (Port 8080)

### Core Agent Processing

#### POST /ask - Intelligent Query Processing
```bash
curl -X POST "http://localhost:8080/ask" \
  -H "X-API-Key: uniguru-dev-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize the key concepts of machine learning",
    "user_id": "user123",
    "session_id": "session456",
    "input_type": "text"
  }'
```

**Response Format:**
```json
{
  "response": "Machine learning is a subset of artificial intelligence...",
  "agent_used": "SummarizerAgent",
  "intent_detected": "summarization",
  "confidence_score": 0.95,
  "processing_time_ms": 1250,
  "trace_id": "trace-uuid-123",
  "session_id": "session456",
  "timestamp": "2025-01-01T12:00:00.000000",
  "metadata": {
    "orchestrator_processed": true,
    "low_confidence_fallback": false,
    "original_intent": null,
    "status": "success"
  }
}
```

#### POST /feedback - Collect User Feedback for RL
```bash
curl -X POST "http://localhost:8080/feedback" \
  -H "X-API-Key: uniguru-dev-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "trace-123",
    "session_id": "session-456",
    "user_id": "user123",
    "rating": 5,
    "feedback_text": "Very helpful response",
    "useful": true
  }'
```

**Response:**
```json
{
  "status": "success",
  "feedback_id": "feedback-uuid-456"
}
```

### EMS Integration Endpoints

#### GET /alerts - System Alerts and Flagged Activities
```bash
# Get all alerts
curl -X GET "http://localhost:8080/alerts?limit=10&flagged_only=false" \
  -H "X-API-Key: uniguru-dev-key-2025"

# Get only high-priority flagged alerts
curl -X GET "http://localhost:8080/alerts?limit=5&flagged_only=true" \
  -H "X-API-Key: uniguru-dev-key-2025"
```

**Response Format:**
```json
{
  "alerts": [
    {
      "alert_id": "alert-uuid-123",
      "type": "processing_issue",
      "severity": "medium",
      "message": "Processing issue in trace trace-456",
      "query": "What is artificial intelligence?",
      "confidence": 0.25,
      "timestamp": "2025-01-01T12:00:00.000000",
      "details": {
        "status": "error",
        "grounded": false,
        "processing_time": 5000
      }
    },
    {
      "alert_id": "health-2025-01-01T12:00:00.000000",
      "type": "system_health",
      "severity": "high",
      "message": "System health issues detected",
      "timestamp": "2025-01-01T12:00:00.000000",
      "details": {
        "status": "degraded",
        "components": {
          "rag_api": false,
          "mongodb": true,
          "ollama_llm": false,
          "gemini_llm": true
        }
      }
    }
  ],
  "total_count": 2,
  "flagged_only": true,
  "timestamp": "2025-01-01T12:00:00.000000"
}
```

#### GET /consent - Get User Consent Status
```bash
curl -X GET "http://localhost:8080/consent?user_id=user123" \
  -H "X-API-Key: uniguru-dev-key-2025"
```

**Response:**
```json
{
  "user_id": "user123",
  "consent_status": {
    "privacy_policy": {
      "granted": true,
      "timestamp": "2025-01-01T00:00:00.000000",
      "version": "1.0"
    },
    "data_processing": {
      "granted": true,
      "timestamp": "2025-01-01T00:00:00.000000",
      "purpose": "AI model training and improvement"
    },
    "analytics": {
      "granted": false,
      "timestamp": null,
      "purpose": "Usage analytics and performance monitoring"
    }
  },
  "last_updated": "2025-01-01T12:00:00.000000",
  "compliance_status": "compliant"
}
```

#### POST /consent - Update User Consent
```bash
curl -X POST "http://localhost:8080/consent" \
  -H "X-API-Key: uniguru-dev-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "consent_type": "privacy_policy",
    "granted": true,
    "consent_details": "User agreed to privacy policy v1.0"
  }'
```

**Response:**
```json
{
  "user_id": "user123",
  "consent_type": "privacy_policy",
  "granted": true,
  "timestamp": "2025-01-01T12:00:00.000000",
  "consent_id": "consent-uuid-789"
}
```

### System Monitoring & Health

#### GET /health - System Health Check
```bash
curl -X GET "http://localhost:8080/health" \
  -H "X-API-Key: uniguru-dev-key-2025"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T12:00:00.000000",
  "components": {
    "rag_api": true,
    "mongodb": true,
    "ollama_llm": false,
    "gemini_llm": true
  },
  "config": {
    "service_port": 8080,
    "canary_traffic": 10,
    "rl_enabled": true,
    "uniguru_jugaad": true,
    "ollama_model": "llama3.1"
  },
  "rag_api": {
    "url": " https://61fe43d7354f.ngrok-free.app/rag",
    "status": "healthy",
    "response_time": "150ms"
  }
}
```

#### GET /stats - Service Statistics
```bash
curl -X GET "http://localhost:8080/stats" \
  -H "X-API-Key: uniguru-dev-key-2025"
```

#### GET /agents/status - Agent Health and Status
```bash
curl -X GET "http://localhost:8080/agents/status" \
  -H "X-API-Key: uniguru-dev-key-2025"
```

**Response:**
```json
{
  "orchestrator": {
    "orchestrator": "AgentOrchestrator",
    "available_agents": {
      "summarization": {
        "name": "SummarizerAgent",
        "description": "Text summarization and condensation",
        "status": "available"
      },
      "planning": {
        "name": "PlannerAgent", 
        "description": "Project planning and strategy",
        "status": "available"
      },
      "file_search": {
        "name": "FileSearchAgent",
        "description": "Document and file retrieval",
        "status": "available"
      },
      "qna": {
        "name": "QnAAgent",
        "description": "Question answering and knowledge retrieval",
        "status": "available"
      }
    },
    "supported_intents": ["summarization", "planning", "file_search", "qna"],
    "timestamp": "2025-01-01T12:00:00.000000"
  },
  "agent_health": {
    "summarization": {"status": "healthy"},
    "planning": {"status": "healthy"},
    "file_search": {"status": "healthy"},
    "qna": {"status": "healthy"}
  },
  "overall_status": "healthy",
  "timestamp": "2025-01-01T12:00:00.000000"
}
```

### Advanced Features

#### POST /test/smoke - Comprehensive Smoke Test
```bash
curl -X POST "http://localhost:8080/test/smoke" \
  -H "X-API-Key: uniguru-dev-key-2025"
```

#### POST /bhiv/compose - BHIV Core Integration
```bash
curl -X POST "http://localhost:8080/bhiv/compose" \
  -H "X-API-Key: uniguru-dev-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain quantum computing",
    "session_id": "bhiv-session",
    "user_id": "bhiv-user",
    "voice_enabled": true,
    "language": "en",
    "max_results": 5
  }'
```

## 🌐 Simple API (Port 8001)

### Agent-Specific Endpoints

#### POST /ask-vedas - Spiritual Guidance
```bash
# POST request
curl -X POST "http://localhost:8001/ask-vedas" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is dharma?",
    "user_id": "user123"
  }'

# GET request
curl -X GET "http://localhost:8001/ask-vedas?query=What%20is%20dharma&user_id=user123"
```

#### POST /edumentor - Educational Content
```bash
# POST request
curl -X POST "http://localhost:8001/edumentor" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain machine learning",
    "user_id": "user123"
  }'

# GET request
curl -X GET "http://localhost:8001/edumentor?query=Explain%20machine%20learning&user_id=user123"
```

#### POST /wellness - Wellness Guidance
```bash
# POST request
curl -X POST "http://localhost:8001/wellness" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to manage stress?",
    "user_id": "user123"
  }'

# GET request
curl -X GET "http://localhost:8001/wellness?query=How%20to%20manage%20stress&user_id=user123"
```

### Knowledge Base Endpoints

#### POST /query-kb - Knowledge Base Query
```bash
# POST request
curl -X POST "http://localhost:8001/query-kb" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence",
    "filters": {"domain": "technology"},
    "limit": 5,
    "user_id": "user123"
  }'

# GET request
curl -X GET "http://localhost:8001/query-kb?query=artificial%20intelligence&limit=5&user_id=user123"
```

### NAS Knowledge Base Endpoints

#### GET /nas-kb/status - NAS KB Status
```bash
curl -X GET "http://localhost:8001/nas-kb/status"
```

#### GET /nas-kb/documents - List Documents
```bash
curl -X GET "http://localhost:8001/nas-kb/documents"
```

#### GET /nas-kb/search - Search Documents
```bash
curl -X GET "http://localhost:8001/nas-kb/search?query=machine%20learning&limit=5"
```

#### GET /nas-kb/document/{document_id} - Get Document Content
```bash
curl -X GET "http://localhost:8001/nas-kb/document/doc-123"
```

### System Endpoints

#### GET /health - Health Check
```bash
curl -X GET "http://localhost:8001/health"
```

#### GET /kb-analytics - Knowledge Base Analytics
```bash
curl -X GET "http://localhost:8001/kb-analytics?hours=24"
```

#### POST /kb-feedback - Submit KB Feedback
```bash
curl -X POST "http://localhost:8001/kb-feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": "query-123",
    "feedback": {
      "rating": 5,
      "helpful": true,
      "comment": "Very useful response"
    }
  }'
```

## 🔄 MCP Bridge API (Port 8002)

### Task Processing

#### POST /handle_task - Single Task Processing
```bash
curl -X POST "http://localhost:8002/handle_task" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "edumentor_agent",
    "input": "Explain machine learning",
    "input_type": "text",
    "model": "default",
    "task_id": "task-123"
  }'
```

#### POST /handle_multi_task - Multi-Task Processing
```bash
curl -X POST "http://localhost:8002/handle_multi_task" \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      {
        "path": "document.pdf",
        "type": "pdf",
        "data": "base64_encoded_content"
      }
    ],
    "agent": "knowledge_agent",
    "task_type": "analyze",
    "batch_id": "batch-456"
  }'
```

### Reinforcement Learning

#### POST /feedback - RL Feedback
```bash
curl -X POST "http://localhost:8002/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-123",
    "agent": "edumentor_agent",
    "model": "default",
    "rating": 5,
    "feedback_type": "quality",
    "user_id": "user123"
  }'
```

#### GET /rl-stats - RL Statistics
```bash
curl -X GET "http://localhost:8002/rl-stats"
```

### System Management

#### GET /health - Health Check
```bash
curl -X GET "http://localhost:8002/health"
```

#### GET /agents - List Available Agents
```bash
curl -X GET "http://localhost:8002/agents"
```

#### GET /models - List Available Models
```bash
curl -X GET "http://localhost:8002/models"
```

## 🌐 Web Interface (Port 8003)

### Authentication
The web interface uses Basic Authentication:
- **Admin**: `admin/secret`
- **User**: `user/secret`

### Available Pages
- **Home**: `/` - File upload and processing
- **Dashboard**: `/dashboard` - System overview and analytics
- **Download**: `/download_nlo/{task_id}?format=json` - Download results

## 📊 Response Formats

### Standard Response Format
```json
{
  "query_id": "uuid-123",
  "query": "user query",
  "response": "generated response",
  "sources": [
    {
      "text": "source content preview",
      "source": "document.pdf",
      "score": 0.85
    }
  ],
  "timestamp": "2025-01-01T12:00:00.000000",
  "endpoint": "ask-vedas",
  "status": 200
}
```

### Error Response Format
```json
{
  "error": "Error description",
  "status_code": 500,
  "timestamp": "2025-01-01T12:00:00.000000",
  "request_id": "req-uuid-456"
}
```

## 🧪 Testing Scripts

### Comprehensive Testing Script
```bash
#!/bin/bash
# Complete system test script

echo "🚀 Starting BHIV Core System Tests..."

# Test 1: Agent Orchestrator Health
echo "1. Testing Agent Orchestrator Health..."
curl -s -X GET "http://localhost:8080/health" \
  -H "X-API-Key: uniguru-dev-key-2025" | jq .

# Test 2: Intelligent Query Processing
echo "2. Testing Intelligent Query Processing..."
curl -s -X POST "http://localhost:8080/ask" \
  -H "X-API-Key: uniguru-dev-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize machine learning concepts",
    "user_id": "test-user",
    "session_id": "test-session"
  }' | jq .

# Test 3: System Alerts
echo "3. Testing System Alerts..."
curl -s -X GET "http://localhost:8080/alerts?limit=5" \
  -H "X-API-Key: uniguru-dev-key-2025" | jq .

# Test 4: Consent Management
echo "4. Testing Consent Management..."
curl -s -X GET "http://localhost:8080/consent?user_id=test-user" \
  -H "X-API-Key: uniguru-dev-key-2025" | jq .

# Test 5: Agent Status
echo "5. Testing Agent Status..."
curl -s -X GET "http://localhost:8080/agents/status" \
  -H "X-API-Key: uniguru-dev-key-2025" | jq .

# Test 6: Simple API Health
echo "6. Testing Simple API Health..."
curl -s -X GET "http://localhost:8001/health" | jq .

# Test 7: Knowledge Base Query
echo "7. Testing Knowledge Base Query..."
curl -s -X POST "http://localhost:8001/query-kb" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence",
    "limit": 3,
    "user_id": "test-user"
  }' | jq .

# Test 8: MCP Bridge Health
echo "8. Testing MCP Bridge Health..."
curl -s -X GET "http://localhost:8002/health" | jq .

# Test 9: Feedback Collection
echo "9. Testing Feedback Collection..."
curl -s -X POST "http://localhost:8080/feedback" \
  -H "X-API-Key: uniguru-dev-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "test-trace-123",
    "session_id": "test-session",
    "user_id": "test-user",
    "rating": 5,
    "useful": true
  }' | jq .

# Test 10: Smoke Test
echo "10. Running Comprehensive Smoke Test..."
curl -s -X POST "http://localhost:8080/test/smoke" \
  -H "X-API-Key: uniguru-dev-key-2025" | jq .

echo "✅ All tests completed!"
```

## 🔧 Environment Configuration

### Required Environment Variables
```env
# API Keys
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
UNIGURU_API_KEY=uniguru-dev-key-2025

# Service Configuration
UNIGURU_SERVICE_PORT=8080
UNIGURU_SERVICE_HOST=0.0.0.0

# Database
MONGO_URI=mongodb://localhost:27017/uniguru_lm

# RAG API
RAG_API_URL= https://61fe43d7354f.ngrok-free.app/rag

# Ollama (Optional)
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3.1

# Vaani Integration
VAANI_USERNAME=admin
VAANI_PASSWORD=secret
VAANI_ENDPOINT=https://vaani-sentinel-gs6x.onrender.com

# Feature Flags
USE_RL=true
USE_UNIGURU_JUGAAD=true
CANARY_TRAFFIC_PERCENT=10
```

## 📈 Performance Monitoring

### Key Metrics to Monitor
- **Response Time**: Average processing time per request
- **Success Rate**: Percentage of successful requests
- **Agent Selection**: RL-based agent routing effectiveness
- **System Health**: Component availability and performance
- **User Satisfaction**: Feedback ratings and usage patterns

### Monitoring Endpoints
```bash
# Real-time metrics
curl -X GET "http://localhost:8080/stats" -H "X-API-Key: uniguru-dev-key-2025"

# Health status
curl -X GET "http://localhost:8080/health" -H "X-API-Key: uniguru-dev-key-2025"

# Agent performance
curl -X GET "http://localhost:8080/agents/status" -H "X-API-Key: uniguru-dev-key-2025"

# System alerts
curl -X GET "http://localhost:8080/alerts" -H "X-API-Key: uniguru-dev-key-2025"
```

## 🚀 Deployment

### Docker Deployment
```bash
# Build and run with docker-compose
docker-compose -f docker-compose.dev.yml up --build

# Or run individual services
docker build -t bhiv-core .
docker run -p 8080:8080 -e GROQ_API_KEY=your_key bhiv-core
```

### Production Checklist
- [ ] Environment variables configured
- [ ] API keys secured
- [ ] MongoDB connection established
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] Backup strategy in place
- [ ] Security measures implemented
- [ ] Performance testing completed

---

This documentation covers all available endpoints and provides comprehensive testing examples for the BHIV Core system. For additional support, refer to the main README.md file or contact the development team.
