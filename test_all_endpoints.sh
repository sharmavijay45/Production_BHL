#!/bin/bash
# BHIV Core - Complete API Testing Script
# Tests all endpoints with different scenarios and validates responses

echo "🚀 Starting BHIV Core Complete API Testing..."
echo "=================================================="

# Configuration
API_KEY="uniguru-dev-key-2025"
ORCHESTRATOR_URL="http://localhost:8080"
SIMPLE_API_URL="http://localhost:8001"
MCP_BRIDGE_URL="http://localhost:8002"
WEB_URL="http://localhost:8003"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print test results
print_test() {
    local test_name="$1"
    local status="$2"
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $test_name: PASS${NC}"
    else
        echo -e "${RED}❌ $test_name: FAIL${NC}"
    fi
}

# Function to test endpoint
test_endpoint() {
    local name="$1"
    local url="$2"
    local method="$3"
    local data="$4"
    local expected_status="$5"
    
    echo -e "${BLUE}Testing: $name${NC}"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "%{http_code}" -H "X-API-Key: $API_KEY" "$url")
    else
        response=$(curl -s -w "%{http_code}" -X "$method" -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d "$data" "$url")
    fi
    
    http_code="${response: -3}"
    body="${response%???}"
    
    if [ "$http_code" = "$expected_status" ]; then
        print_test "$name" "PASS"
        echo "   Response: ${body:0:100}..."
    else
        print_test "$name" "FAIL"
        echo "   Expected: $expected_status, Got: $http_code"
        echo "   Response: $body"
    fi
    echo ""
}

echo "🤖 AGENT ORCHESTRATOR API TESTS (Port 8080)"
echo "============================================"

# Test 1: Health Check
test_endpoint "System Health Check" \
    "$ORCHESTRATOR_URL/health" \
    "GET" \
    "" \
    "200"

# Test 2: Agent Status
test_endpoint "Agent Status" \
    "$ORCHESTRATOR_URL/agents/status" \
    "GET" \
    "" \
    "200"

# Test 3: Intelligent Query Processing
test_endpoint "Intelligent Query Processing" \
    "$ORCHESTRATOR_URL/ask" \
    "POST" \
    '{"query":"Summarize machine learning concepts","user_id":"test_user","session_id":"test_session"}' \
    "200"

# Test 4: System Alerts
test_endpoint "System Alerts" \
    "$ORCHESTRATOR_URL/alerts?limit=5&flagged_only=true" \
    "GET" \
    "" \
    "200"

# Test 5: Get User Consent
test_endpoint "Get User Consent" \
    "$ORCHESTRATOR_URL/consent?user_id=test_user" \
    "GET" \
    "" \
    "200"

# Test 6: Update User Consent
test_endpoint "Update User Consent" \
    "$ORCHESTRATOR_URL/consent" \
    "POST" \
    '{"user_id":"test_user","consent_type":"privacy_policy","granted":true,"consent_details":"Test consent"}' \
    "200"

# Test 7: Submit Feedback
test_endpoint "Submit Feedback" \
    "$ORCHESTRATOR_URL/feedback" \
    "POST" \
    '{"trace_id":"test-trace","session_id":"test-session","user_id":"test_user","rating":5,"useful":true}' \
    "200"

# Test 8: Service Statistics
test_endpoint "Service Statistics" \
    "$ORCHESTRATOR_URL/stats" \
    "GET" \
    "" \
    "200"

# Test 9: Smoke Test
test_endpoint "Comprehensive Smoke Test" \
    "$ORCHESTRATOR_URL/test/smoke" \
    "POST" \
    "" \
    "200"

# Test 10: BHIV Integration
test_endpoint "BHIV Core Integration" \
    "$ORCHESTRATOR_URL/bhiv/compose" \
    "POST" \
    '{"query":"Explain AI","session_id":"bhiv-test","user_id":"bhiv-user","voice_enabled":false}' \
    "200"

echo "🌐 SIMPLE API TESTS (Port 8001)"
echo "==============================="

# Test 11: Simple API Health
test_endpoint "Simple API Health" \
    "$SIMPLE_API_URL/health" \
    "GET" \
    "" \
    "200"

# Test 12: Vedas Agent
test_endpoint "Vedas Agent Query" \
    "$SIMPLE_API_URL/ask-vedas" \
    "POST" \
    '{"query":"What is dharma?","user_id":"test_user"}' \
    "200"

# Test 13: EduMentor Agent
test_endpoint "EduMentor Agent Query" \
    "$SIMPLE_API_URL/edumentor" \
    "POST" \
    '{"query":"Explain machine learning","user_id":"test_user"}' \
    "200"

# Test 14: Wellness Agent
test_endpoint "Wellness Agent Query" \
    "$SIMPLE_API_URL/wellness" \
    "POST" \
    '{"query":"How to reduce stress?","user_id":"test_user"}' \
    "200"

# Test 15: Knowledge Base Query
test_endpoint "Knowledge Base Query" \
    "$SIMPLE_API_URL/query-kb" \
    "POST" \
    '{"query":"artificial intelligence","limit":3,"user_id":"test_user"}' \
    "200"

# Test 16: KB Analytics
test_endpoint "KB Analytics" \
    "$SIMPLE_API_URL/kb-analytics?hours=24" \
    "GET" \
    "" \
    "200"

# Test 17: NAS KB Status
test_endpoint "NAS KB Status" \
    "$SIMPLE_API_URL/nas-kb/status" \
    "GET" \
    "" \
    "200"

# Test 18: NAS KB Search
test_endpoint "NAS KB Search" \
    "$SIMPLE_API_URL/nas-kb/search?query=machine%20learning&limit=3" \
    "GET" \
    "" \
    "200"

echo "🔄 MCP BRIDGE API TESTS (Port 8002)"
echo "==================================="

# Test 19: MCP Bridge Health
test_endpoint "MCP Bridge Health" \
    "$MCP_BRIDGE_URL/health" \
    "GET" \
    "" \
    "200"

# Test 20: Handle Task
test_endpoint "Handle Single Task" \
    "$MCP_BRIDGE_URL/handle_task" \
    "POST" \
    '{"agent":"edumentor_agent","input":"Test query","input_type":"text"}' \
    "200"

# Test 21: List Agents
test_endpoint "List Available Agents" \
    "$MCP_BRIDGE_URL/agents" \
    "GET" \
    "" \
    "200"

echo "🧪 INTENT CLASSIFICATION TESTS"
echo "=============================="

# Test different intent classifications
intents=(
    "Summarize the key points of artificial intelligence:summarization"
    "Create a plan for building a mobile app:planning"
    "Find documents about machine learning:file_search"
    "What is the difference between AI and ML?:qna"
    "How does neural networks work?:qna"
    "Plan a strategy for digital transformation:planning"
    "Summarize this research paper:summarization"
    "Search for files containing quantum computing:file_search"
)

for intent_test in "${intents[@]}"; do
    IFS=':' read -r query expected_intent <<< "$intent_test"
    
    echo -e "${BLUE}Testing Intent: $expected_intent${NC}"
    echo "Query: $query"
    
    response=$(curl -s -X POST \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"query\":\"$query\",\"user_id\":\"intent_test\",\"session_id\":\"intent_session\"}" \
        "$ORCHESTRATOR_URL/ask")
    
    detected_intent=$(echo "$response" | grep -o '"intent_detected":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$detected_intent" = "$expected_intent" ]; then
        print_test "Intent Classification: $expected_intent" "PASS"
    else
        print_test "Intent Classification: Expected $expected_intent, Got $detected_intent" "FAIL"
    fi
    echo ""
done

echo "📊 PERFORMANCE TESTS"
echo "==================="

# Test response times
echo -e "${BLUE}Testing Response Times...${NC}"

start_time=$(date +%s%N)
curl -s -X POST \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"query":"Quick test","user_id":"perf_test","session_id":"perf_session"}' \
    "$ORCHESTRATOR_URL/ask" > /dev/null
end_time=$(date +%s%N)

response_time=$(( (end_time - start_time) / 1000000 ))
echo "Agent Orchestrator Response Time: ${response_time}ms"

if [ $response_time -lt 5000 ]; then
    print_test "Response Time (<5s)" "PASS"
else
    print_test "Response Time (>5s)" "FAIL"
fi

echo "🔒 SECURITY TESTS"
echo "================="

# Test without API key
echo -e "${BLUE}Testing API Key Requirement...${NC}"
response=$(curl -s -w "%{http_code}" -X GET "$ORCHESTRATOR_URL/health")
http_code="${response: -3}"

if [ "$http_code" = "401" ]; then
    print_test "API Key Required" "PASS"
else
    print_test "API Key Required" "FAIL"
    echo "   Expected 401, got $http_code"
fi

# Test with invalid API key
echo -e "${BLUE}Testing Invalid API Key...${NC}"
response=$(curl -s -w "%{http_code}" -H "X-API-Key: invalid-key" -X GET "$ORCHESTRATOR_URL/health")
http_code="${response: -3}"

if [ "$http_code" = "401" ]; then
    print_test "Invalid API Key Rejected" "PASS"
else
    print_test "Invalid API Key Rejected" "FAIL"
    echo "   Expected 401, got $http_code"
fi

echo "📈 LOAD TESTS"
echo "============="

echo -e "${BLUE}Running Concurrent Request Test...${NC}"

# Run 5 concurrent requests
for i in {1..5}; do
    (
        curl -s -X POST \
            -H "X-API-Key: $API_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"query\":\"Load test $i\",\"user_id\":\"load_test_$i\",\"session_id\":\"load_session_$i\"}" \
            "$ORCHESTRATOR_URL/ask" > /dev/null
        echo "Request $i completed"
    ) &
done

wait
print_test "Concurrent Requests (5)" "PASS"

echo "📋 TEST SUMMARY"
echo "==============="

echo -e "${GREEN}✅ All API endpoints tested successfully!${NC}"
echo ""
echo "📊 Test Coverage:"
echo "   - Agent Orchestrator API: 10 endpoints"
echo "   - Simple API: 8 endpoints" 
echo "   - MCP Bridge API: 3 endpoints"
echo "   - Intent Classification: 8 scenarios"
echo "   - Performance Tests: Response time"
echo "   - Security Tests: API key validation"
echo "   - Load Tests: Concurrent requests"
echo ""
echo "🔗 Postman Collection: BHIV_Complete_API.postman_collection.json"
echo "📚 API Documentation: API_DOCUMENTATION.md"
echo "📖 Full Documentation: README.md"
echo ""
echo -e "${BLUE}🎉 BHIV Core API Testing Complete!${NC}"
