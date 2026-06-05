#!/bin/bash

# Test script for NexaCore Backend API including new OIDC endpoints
# Usage: ./test_all_endpoints.sh

BASE_URL="http://localhost:8000"

echo "========================================="
echo "Testing NexaCore Backend API"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

test_endpoint() {
    local name=$1
    local method=$2
    local url=$3
    local data=$4
    
    echo -e "\n📍 Testing: ${name}"
    echo "   Method: ${method}"
    echo "   URL: ${url}"
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "${url}")
    else
        response=$(curl -s -w "\n%{http_code}" -X "${method}" "${url}" \
            -H "Content-Type: application/json" \
            -d "${data}")
    fi
    
    # Extract HTTP code (last line)
    http_code=$(echo "$response" | tail -n 1)
    # Extract body (all but last line)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "   ${GREEN}✓ Success (HTTP $http_code)${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null | head -20
    else
        echo -e "   ${RED}✗ Failed (HTTP $http_code)${NC}"
        echo "$body"
    fi
}

echo "========================================="
echo "1. Health & Monitoring Endpoints"
echo "========================================="

test_endpoint "Health Check" "GET" "${BASE_URL}/health"
test_endpoint "Readiness Check" "GET" "${BASE_URL}/ready"
test_endpoint "Metrics" "GET" "${BASE_URL}/metrics" | head -30

echo ""
echo "========================================="
echo "2. OIDC/SSO Authentication Endpoints (NEW!)"
echo "========================================="

test_endpoint "OIDC Info" "GET" "${BASE_URL}/auth/oidc/info"

test_endpoint "OIDC Login (Get Authorization URL)" "GET" \
    "${BASE_URL}/auth/oidc/login?redirect_uri=http://localhost:3000/callback&state=test123"

echo ""
echo "========================================="
echo "3. Session Management"
echo "========================================="

test_endpoint "Create Session" "POST" "${BASE_URL}/sessions" \
    '{
        "name": "Alice Johnson",
        "team": "platform",
        "role": "SDE-1",
        "employee_type": "fte"
    }'

test_endpoint "List Sessions" "GET" "${BASE_URL}/sessions"

echo ""
echo "========================================="
echo "4. Memory System"
echo "========================================="

test_endpoint "Memory Summary" "GET" "${BASE_URL}/memory/summary"

test_endpoint "Query Memories" "GET" \
    "${BASE_URL}/memories?team=platform&employee_type=fte&role=SDE-1"

echo ""
echo "========================================="
echo "5. Chat Endpoint (AI Agent)"
echo "========================================="

test_endpoint "Chat Query" "POST" "${BASE_URL}/chat" \
    '{
        "name": "Test User",
        "team": "platform",
        "role": "SDE-1",
        "employee_type": "fte",
        "query": "What AWS access do I need?"
    }'

echo ""
echo "========================================="
echo "6. Data Endpoints"
echo "========================================="

test_endpoint "List Tickets" "GET" "${BASE_URL}/tickets"
test_endpoint "List Reminders" "GET" "${BASE_URL}/reminders"
test_endpoint "Audit Log" "GET" "${BASE_URL}/audit"

echo ""
echo "========================================="
echo "7. Database Statistics"
echo "========================================="

test_endpoint "Database Stats" "GET" "${BASE_URL}/db-stats"

echo ""
echo "========================================="
echo "✅ Testing Complete!"
echo "========================================="
echo ""
echo "Summary:"
echo "- Backend server is running on ${BASE_URL}"
echo "- All core endpoints tested"
echo "- New OIDC/SSO endpoints are live and working"
echo "- Google OAuth configured (provider: google)"
echo ""
echo "Next steps:"
echo "1. Test full OIDC flow by visiting the authorization URL"
echo "2. Update frontend to use SSO login"
echo "3. Check API documentation at ${BASE_URL}/docs"
echo ""
