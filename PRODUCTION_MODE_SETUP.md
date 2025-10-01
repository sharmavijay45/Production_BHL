# 🚀 Production Mode Setup Guide

## ✅ Current Status
- ✅ `.env` file has `PRODUCTION_MODE=true`
- ✅ Vaani URL is correct: `https://vaani-sentinel-gs6x.onrender.com`
- ✅ `requirements.txt` updated with all dependencies

## 🔧 Step-by-Step Setup

### 1. Install All Dependencies
```bash
pip install -r requirements.txt
```

### 2. Verify Environment Variables
```bash
# Check if production mode is set
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('PRODUCTION_MODE:', os.getenv('PRODUCTION_MODE'))"
```

### 3. Test Production Mode Detection
```bash
python test_production_mode.py
```

### 4. Start Services with Production Mode

#### Option A: Simple API (Port 8001)
```bash
# Kill any existing processes on port 8001
netstat -ano | findstr :8001
# If found, kill the process: taskkill /PID <PID> /F

# Start with production mode
python simple_api.py --port 8001
```

#### Option B: MCP Bridge (Port 8002)
```bash
# Kill any existing processes on port 8002
netstat -ano | findstr :8002
# If found, kill the process: taskkill /PID <PID> /F

# Start with production mode
uvicorn mcp_bridge:app --host 0.0.0.0 --port 8002
```

#### Option C: CLI Runner
```bash
python cli_runner.py explain "What is dharma" vedas_agent --input-type text
```

## 🎯 Expected Production Mode Output

### ✅ Success Indicators
When production mode is working, you should see:

```
✅ Production mode enabled with full observability
🔍 Starting trace: trace_1727766123456 for operation: agent_query
📊 Metrics collection initialized
🛡️ Threat detection active
🚨 Alerting system ready
```

### ❌ Failure Indicators
If you see this, dependencies are missing:
```
⚠️ Production mode requested but dependencies missing: No module named 'opentelemetry.instrumentation.psycopg2'
🔄 Falling back to development mode
```

## 🔍 How to See Production Features in Action

### 1. Enhanced API Responses
Production mode adds these fields to responses:
```json
{
  "response": "Your agent response...",
  "security": {
    "authenticated": true,
    "threat_score": 0.1,
    "trace_id": "trace_1727766123456"
  },
  "performance": {
    "response_time": 0.234,
    "agent_processing_time": 0.156
  },
  "observability": {
    "metrics_collected": true,
    "traced": true
  }
}
```

### 2. Metrics Endpoint
Visit: `http://localhost:8001/metrics`
```
# HELP bhiv_agent_queries_total Total number of agent queries
# TYPE bhiv_agent_queries_total counter
bhiv_agent_queries_total{agent="vedas",status="success"} 42.0

# HELP bhiv_threats_detected_total Total threats detected
# TYPE bhiv_threats_detected_total counter
bhiv_threats_detected_total{threat_type="sql_injection",severity="high"} 3.0
```

### 3. Enhanced Logging
```
INFO - observability.metrics - 🔍 Starting trace: trace_1727766123456 for operation: vedas_query
INFO - security.threat_detection - 🛡️ Threat analysis: query="What is dharma" threat_score=0.1
INFO - observability.metrics - ✅ Completed trace: trace_1727766123456 - success in 0.234s
```

### 4. Threat Detection Test
```bash
# This should be blocked in production mode
curl "http://localhost:8001/ask-vedas?query='; DROP TABLE users; --"

# Expected response:
# {"error": "Request blocked due to security policy", "threat_type": "sql_injection"}
```

## 🚨 Troubleshooting

### Issue 1: "Falling back to development mode"
**Solution:** Install missing dependencies
```bash
pip install opentelemetry-instrumentation-psycopg2 psycopg2-binary
```

### Issue 2: Wrong Vaani URL
**Solution:** Restart all processes after updating .env
```bash
# Kill all Python processes
taskkill /F /IM python.exe
taskkill /F /IM uvicorn.exe

# Restart services
python simple_api.py --port 8001
```

### Issue 3: Environment variable not detected
**Solution:** Reload environment
```bash
# PowerShell
$env:PRODUCTION_MODE="true"

# Or restart your terminal/IDE
```

## 🎉 Success Verification

Run this command to verify everything is working:
```bash
# Test production mode
python test_production_mode.py

# Test API with production features
curl "http://localhost:8001/ask-vedas?query=What is dharma?"

# Check metrics
curl "http://localhost:8001/metrics"
```

You should see:
- ✅ Production mode detected
- ✅ All imports successful
- ✅ Enhanced response with security/performance data
- ✅ Metrics available at /metrics endpoint
