# BHIV Core Integration Usage Guide

## 🎯 How Production Features Work with Your Existing APIs

**Great news!** All the production features (security, observability, threat detection) are now seamlessly integrated with your existing interfaces. You can continue using `simple_api.py`, `mcp_bridge.py`, and `cli_runner.py` exactly as before, and the system will automatically provide enhanced capabilities.

## 🔄 How It Works

### Development Mode (Default)
```bash
# Your existing usage works exactly the same
python simple_api.py --port 8001
python mcp_bridge.py
python cli_runner.py explain "What is dharma?" vedas_agent
```

### Production Mode (Enhanced)
```bash
# Enable production mode with environment variable
export PRODUCTION_MODE=true

# Now your same APIs get enhanced with:
# ✅ JWT Authentication & RBAC
# ✅ Threat Detection & Response  
# ✅ Metrics & Distributed Tracing
# ✅ Automated Alerting
# ✅ Audit Logging

python simple_api.py --port 8001  # Same command, enhanced features!
```

## 🚀 Simple API Integration

### Your Existing Endpoints Work the Same
```bash
# Vedas Agent - Works exactly as before
curl "http://localhost:8001/ask-vedas?query=What is dharma?"

# EduMentor Agent - Same interface
curl "http://localhost:8001/edumentor?query=Explain machine learning"

# Wellness Agent - Same interface  
curl "http://localhost:8001/wellness?query=How to reduce stress?"
```

### But Now With Production Features!

**In Development Mode:**
- Uses original agent implementations
- No authentication required
- Basic logging only
- Direct responses

**In Production Mode:**
- Uses enhanced agents with security & observability
- Optional JWT authentication (backwards compatible)
- Comprehensive metrics and tracing
- Threat detection on all requests
- Automated alerting on failures

### Example: Enhanced vs Original Response

**Development Mode Response:**
```json
{
  "query_id": "123e4567-e89b-12d3-a456-426614174000",
  "query": "What is dharma?",
  "response": "Dharma represents righteous living...",
  "sources": [...],
  "timestamp": "2025-09-30T14:48:42",
  "endpoint": "ask-vedas",
  "status": 200
}
```

**Production Mode Response (Same format, enhanced processing):**
```json
{
  "query_id": "123e4567-e89b-12d3-a456-426614174000",
  "query": "What is dharma?",
  "response": "Dharma represents righteous living...",
  "sources": [{"text": "Enhanced agent response", "source": "production_vedas_agent"}],
  "timestamp": "2025-09-30T14:48:42",
  "endpoint": "ask-vedas",
  "status": 200
}
```

## 🤖 CLI Runner Integration

### Your Existing Commands Work
```bash
# All your existing CLI commands work exactly the same
python cli_runner.py explain "What is dharma?" vedas_agent
python cli_runner.py create "meditation guide" wellness_agent
python cli_runner.py analyze "machine learning" edumentor_agent
```

### Enhanced in Production Mode
When `PRODUCTION_MODE=true`:
- **Security**: All agent calls are authenticated and authorized
- **Observability**: Every command is traced and metrics are collected
- **Threat Detection**: Malicious queries are automatically blocked
- **Audit Logging**: Complete audit trail of all operations

## 🌉 MCP Bridge Integration

### Same Interface, Enhanced Backend
```bash
# Start MCP Bridge (same command)
python mcp_bridge.py

# Your existing API calls work the same
curl -X POST http://localhost:8002/handle_task \
  -H "Content-Type: application/json" \
  -d '{"agent":"vedas_agent","input":"What is dharma?","input_type":"text"}'
```

### Production Enhancements
- **Load Balancing**: Requests distributed across agent instances
- **Circuit Breakers**: Automatic failover on agent failures
- **Rate Limiting**: Protection against abuse
- **Health Monitoring**: Real-time agent health tracking

## 🔐 Authentication (Optional in Production)

### Without Authentication (Backwards Compatible)
```bash
# Works exactly as before - no auth required
curl "http://localhost:8001/ask-vedas?query=What is dharma?"
```

### With Authentication (Enhanced Security)
```bash
# Get JWT token
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

# Use token for enhanced features
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/ask-vedas?query=What is dharma?"
```

## 📊 Observability Integration

### Automatic Metrics Collection
Every request to your existing APIs now automatically collects:
- **Response Times**: How fast each agent responds
- **Success Rates**: Which agents are performing well
- **Error Tracking**: Detailed error analysis
- **Usage Patterns**: Which agents are used most

### View Metrics
```bash
# Prometheus metrics endpoint
curl http://localhost:8001/metrics

# Grafana dashboard
open http://localhost:3000  # admin/admin123
```

### Distributed Tracing
Every request is automatically traced across:
- API Gateway → Microservice → Agent → External APIs
- Complete request flow visualization in Jaeger
- Performance bottleneck identification

## 🛡️ Threat Protection

### Automatic Security
All your existing endpoints now have:
- **SQL Injection Detection**: Malicious queries blocked automatically
- **Rate Limiting**: Protection against DDoS attacks
- **IP Blocking**: Automatic blocking of malicious IPs
- **Content Filtering**: Inappropriate content detection

### Example: Threat Detection in Action
```bash
# This malicious request is automatically blocked
curl "http://localhost:8001/ask-vedas?query='; DROP TABLE users; --"

# Response: 403 Forbidden - Request blocked due to security policy
# Alert sent to admins automatically
```

## 🚀 Getting Started

### Step 1: Choose Your Mode

**Development Mode (Default):**
```bash
# No changes needed - everything works as before
python simple_api.py --port 8001
```

**Production Mode (Enhanced):**
```bash
# Set environment variable
export PRODUCTION_MODE=true

# Start with enhanced features
python simple_api.py --port 8001
```

### Step 2: Use Your Existing Code
```bash
# All your existing code works exactly the same!
python cli_runner.py explain "What is dharma?" vedas_agent
curl "http://localhost:8001/ask-vedas?query=What is dharma?"
```

### Step 3: Monitor (Production Mode Only)
```bash
# View real-time metrics
open http://localhost:3000  # Grafana

# View distributed traces  
open http://localhost:16686  # Jaeger

# Check system health
curl http://localhost:8001/health
```

## 🎯 Key Benefits

### For You (The Developer)
- ✅ **Zero Code Changes**: Your existing code works unchanged
- ✅ **Backward Compatibility**: Development mode preserves original behavior
- ✅ **Gradual Migration**: Enable production features when ready
- ✅ **Same Interfaces**: CLI, API, and MCP Bridge work identically

### For Production (When Ready)
- ✅ **Enterprise Security**: JWT, RBAC, threat detection
- ✅ **Scalability**: Auto-scaling, load balancing, circuit breakers
- ✅ **Observability**: Metrics, tracing, alerting, health monitoring
- ✅ **Reliability**: High availability, automated recovery, audit trails

## 🔧 Configuration

### Environment Variables
```env
# Basic Configuration
PRODUCTION_MODE=true  # Enable enhanced features

# Security (Optional)
JWT_SECRET_KEY=your-secret-key
ENABLE_AUTH=true

# Observability (Optional)
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
JAEGER_ENABLED=true

# Alerting (Optional)
SLACK_WEBHOOK_URL=your-slack-webhook
EMAIL_ALERTS_ENABLED=true
```

### Gradual Rollout Strategy
1. **Week 1**: Test in development mode (no changes)
2. **Week 2**: Enable production mode in staging
3. **Week 3**: Enable authentication and monitoring
4. **Week 4**: Full production deployment with all features

## 🎉 Summary

**The integration is completely transparent!** 

- Your existing `simple_api.py`, `mcp_bridge.py`, and `cli_runner.py` work exactly as before
- Set `PRODUCTION_MODE=true` to get enhanced security, observability, and scalability
- No code changes required - just environment configuration
- Backward compatible - you can switch between modes anytime

**You get production-grade features without changing a single line of your existing code!**

🚀 **Your BHIV Core agents now have enterprise-grade capabilities while maintaining the same simple interfaces you're used to.**
