#!/bin/bash

# Crypto-0DTE System - Comprehensive Health Check Tests
# Tests all basic health checks including database, Redis, API endpoints, and system components

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT=$(pwd)
LOG_DIR="$PROJECT_ROOT/logs"
RESULTS_FILE="$LOG_DIR/health-check-results.json"
REPORT_FILE="$LOG_DIR/health-check-report.txt"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNING_TESTS=0

# Create logs directory
mkdir -p "$LOG_DIR"

echo -e "${BLUE}🏥 Crypto-0DTE System - Comprehensive Health Check Tests${NC}"
echo -e "${BLUE}=========================================================${NC}"
echo "Start Time: $(date)"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_test_header() {
    echo -e "${CYAN}🧪 $1${NC}"
    echo "$(printf '%.0s-' {1..50})"
}

# Function to record test result
record_test() {
    local test_name="$1"
    local status="$2"
    local details="$3"
    local response_time="${4:-N/A}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    case "$status" in
        "PASS")
            PASSED_TESTS=$((PASSED_TESTS + 1))
            print_status "$test_name"
            ;;
        "FAIL")
            FAILED_TESTS=$((FAILED_TESTS + 1))
            print_error "$test_name - $details"
            ;;
        "WARN")
            WARNING_TESTS=$((WARNING_TESTS + 1))
            print_warning "$test_name - $details"
            ;;
    esac
    
    # Record to JSON results file
    echo "{\"test\": \"$test_name\", \"status\": \"$status\", \"details\": \"$details\", \"response_time\": \"$response_time\", \"timestamp\": \"$(date -Iseconds)\"}" >> "$RESULTS_FILE"
}

# Function to test HTTP endpoint
test_http_endpoint() {
    local url="$1"
    local expected_status="${2:-200}"
    local test_name="$3"
    local timeout="${4:-10}"
    
    local start_time=$(date +%s.%N)
    local response=$(curl -s -w "HTTPSTATUS:%{http_code};TIME:%{time_total}" --max-time "$timeout" "$url" 2>/dev/null || echo "HTTPSTATUS:000;TIME:0")
    local end_time=$(date +%s.%N)
    
    local http_status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local response_time=$(echo "$response" | grep -o "TIME:[0-9.]*" | cut -d: -f2)
    local body=$(echo "$response" | sed -E 's/HTTPSTATUS:[0-9]*;TIME:[0-9.]*$//')
    
    if [ "$http_status" = "$expected_status" ]; then
        record_test "$test_name" "PASS" "HTTP $http_status (${response_time}s)" "$response_time"
        return 0
    else
        record_test "$test_name" "FAIL" "Expected HTTP $expected_status, got $http_status" "$response_time"
        return 1
    fi
}

# Function to test database connection
test_database_connection() {
    local db_url="$1"
    local test_name="$2"
    
    local start_time=$(date +%s.%N)
    
    if command -v psql >/dev/null 2>&1; then
        if echo "SELECT 1;" | PGPASSWORD=crypto_password psql -h localhost -U crypto_user -d crypto_0dte_local -t >/dev/null 2>&1; then
            local end_time=$(date +%s.%N)
            local response_time=$(echo "$end_time - $start_time" | bc -l)
            record_test "$test_name" "PASS" "Database connection successful" "$response_time"
            return 0
        else
            record_test "$test_name" "FAIL" "Database connection failed" "N/A"
            return 1
        fi
    else
        record_test "$test_name" "WARN" "psql not available for testing" "N/A"
        return 1
    fi
}

# Function to test Redis connection
test_redis_connection() {
    local redis_url="$1"
    local test_name="$2"
    
    local start_time=$(date +%s.%N)
    
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -h localhost -p 6379 ping >/dev/null 2>&1; then
            local end_time=$(date +%s.%N)
            local response_time=$(echo "$end_time - $start_time" | bc -l)
            record_test "$test_name" "PASS" "Redis connection successful" "$response_time"
            return 0
        else
            record_test "$test_name" "FAIL" "Redis connection failed" "N/A"
            return 1
        fi
    else
        record_test "$test_name" "WARN" "redis-cli not available for testing" "N/A"
        return 1
    fi
}

# Function to test JSON response structure
test_json_response() {
    local url="$1"
    local expected_fields="$2"
    local test_name="$3"
    
    local response=$(curl -s "$url" 2>/dev/null || echo "{}")
    
    if command -v jq >/dev/null 2>&1; then
        local is_valid_json=$(echo "$response" | jq empty >/dev/null 2>&1 && echo "true" || echo "false")
        
        if [ "$is_valid_json" = "true" ]; then
            local missing_fields=""
            for field in $expected_fields; do
                if ! echo "$response" | jq -e ".$field" >/dev/null 2>&1; then
                    missing_fields="$missing_fields $field"
                fi
            done
            
            if [ -z "$missing_fields" ]; then
                record_test "$test_name" "PASS" "All expected fields present"
                return 0
            else
                record_test "$test_name" "FAIL" "Missing fields:$missing_fields"
                return 1
            fi
        else
            record_test "$test_name" "FAIL" "Invalid JSON response"
            return 1
        fi
    else
        record_test "$test_name" "WARN" "jq not available for JSON validation"
        return 1
    fi
}

# Initialize results file
echo "[]" > "$RESULTS_FILE"
echo "" > "$RESULTS_FILE"  # Clear file for appending

# Test Suite 1: Infrastructure Health Checks
print_test_header "Test Suite 1: Infrastructure Health Checks"

# Test PostgreSQL connection
test_database_connection "postgresql://crypto_user:crypto_password@localhost:5432/crypto_0dte_local" "PostgreSQL Connection"

# Test Redis connection
test_redis_connection "redis://localhost:6379/0" "Redis Connection"

# Test PostgreSQL database operations
if command -v psql >/dev/null 2>&1; then
    print_info "Testing PostgreSQL database operations..."
    
    # Test table creation
    if echo "CREATE TABLE IF NOT EXISTS health_test (id SERIAL PRIMARY KEY, test_time TIMESTAMP DEFAULT NOW());" | PGPASSWORD=crypto_password psql -h localhost -U crypto_user -d crypto_0dte_local >/dev/null 2>&1; then
        record_test "PostgreSQL Table Creation" "PASS" "Test table created successfully"
        
        # Test data insertion
        if echo "INSERT INTO health_test DEFAULT VALUES;" | PGPASSWORD=crypto_password psql -h localhost -U crypto_user -d crypto_0dte_local >/dev/null 2>&1; then
            record_test "PostgreSQL Data Insertion" "PASS" "Test data inserted successfully"
            
            # Test data retrieval
            if echo "SELECT COUNT(*) FROM health_test;" | PGPASSWORD=crypto_password psql -h localhost -U crypto_user -d crypto_0dte_local -t >/dev/null 2>&1; then
                record_test "PostgreSQL Data Retrieval" "PASS" "Test data retrieved successfully"
            else
                record_test "PostgreSQL Data Retrieval" "FAIL" "Failed to retrieve test data"
            fi
        else
            record_test "PostgreSQL Data Insertion" "FAIL" "Failed to insert test data"
        fi
        
        # Cleanup test table
        echo "DROP TABLE IF EXISTS health_test;" | PGPASSWORD=crypto_password psql -h localhost -U crypto_user -d crypto_0dte_local >/dev/null 2>&1
    else
        record_test "PostgreSQL Table Creation" "FAIL" "Failed to create test table"
    fi
fi

# Test Redis operations
if command -v redis-cli >/dev/null 2>&1; then
    print_info "Testing Redis operations..."
    
    # Test Redis set/get
    if redis-cli -h localhost -p 6379 set health_test "test_value" >/dev/null 2>&1; then
        record_test "Redis SET Operation" "PASS" "Test key set successfully"
        
        if [ "$(redis-cli -h localhost -p 6379 get health_test 2>/dev/null)" = "test_value" ]; then
            record_test "Redis GET Operation" "PASS" "Test key retrieved successfully"
        else
            record_test "Redis GET Operation" "FAIL" "Failed to retrieve test key"
        fi
        
        # Cleanup test key
        redis-cli -h localhost -p 6379 del health_test >/dev/null 2>&1
    else
        record_test "Redis SET Operation" "FAIL" "Failed to set test key"
    fi
fi

echo ""

# Test Suite 2: Backend API Health Checks
print_test_header "Test Suite 2: Backend API Health Checks"

# Basic health endpoint
test_http_endpoint "http://localhost:8000/health" 200 "Backend Basic Health Check"

# Detailed health endpoint
test_http_endpoint "http://localhost:8000/health/detailed" 200 "Backend Detailed Health Check"

# Readiness probe
test_http_endpoint "http://localhost:8000/health/ready" 200 "Backend Readiness Probe"

# Liveness probe
test_http_endpoint "http://localhost:8000/health/live" 200 "Backend Liveness Probe"

# API documentation
test_http_endpoint "http://localhost:8000/docs" 200 "Backend API Documentation"

# OpenAPI schema
test_http_endpoint "http://localhost:8000/openapi.json" 200 "Backend OpenAPI Schema"

# Test JSON response structure for health endpoints
test_json_response "http://localhost:8000/health" "status timestamp" "Backend Health JSON Structure"
test_json_response "http://localhost:8000/health/detailed" "status services database redis" "Backend Detailed Health JSON Structure"

echo ""

# Test Suite 3: Frontend Health Checks
print_test_header "Test Suite 3: Frontend Health Checks"

# Frontend main page
test_http_endpoint "http://localhost:3000" 200 "Frontend Main Page"

# Frontend static assets (if accessible)
test_http_endpoint "http://localhost:3000/static/js" 404 "Frontend Static Assets Directory" 5

# Frontend manifest
test_http_endpoint "http://localhost:3000/manifest.json" 200 "Frontend Manifest" 5

echo ""

# Test Suite 4: API Endpoint Health Checks
print_test_header "Test Suite 4: API Endpoint Health Checks"

# Market data endpoints
test_http_endpoint "http://localhost:8000/api/v1/market-data/symbols" 200 "Market Data Symbols Endpoint"
test_http_endpoint "http://localhost:8000/api/v1/market-data/ticker/BTCUSDT" 200 "Market Data Ticker Endpoint"

# Signals endpoints
test_http_endpoint "http://localhost:8000/api/v1/signals" 200 "Trading Signals Endpoint"
test_http_endpoint "http://localhost:8000/api/v1/signals/latest" 200 "Latest Signals Endpoint"

# Portfolio endpoints
test_http_endpoint "http://localhost:8000/api/v1/portfolio/summary" 401 "Portfolio Summary Endpoint (Auth Required)"
test_http_endpoint "http://localhost:8000/api/v1/portfolio/positions" 401 "Portfolio Positions Endpoint (Auth Required)"

# Trading endpoints
test_http_endpoint "http://localhost:8000/api/v1/trading/orders" 401 "Trading Orders Endpoint (Auth Required)"

# Authentication endpoints
test_http_endpoint "http://localhost:8000/api/v1/auth/register" 422 "Auth Register Endpoint (No Data)"
test_http_endpoint "http://localhost:8000/api/v1/auth/login" 422 "Auth Login Endpoint (No Data)"

echo ""

# Test Suite 5: Database Schema Health Checks
print_test_header "Test Suite 5: Database Schema Health Checks"

if command -v psql >/dev/null 2>&1; then
    print_info "Testing database schema..."
    
    # Check if Alembic version table exists
    if echo "SELECT version_num FROM alembic_version LIMIT 1;" | PGPASSWORD=crypto_password psql -h localhost -U crypto_user -d crypto_0dte_local -t >/dev/null 2>&1; then
        record_test "Database Migration Status" "PASS" "Alembic version table exists"
        
        # Get current migration version
        local current_version=$(echo "SELECT version_num FROM alembic_version LIMIT 1;" | PGPASSWORD=crypto_password psql -h localhost -U crypto_user -d crypto_0dte_local -t 2>/dev/null | tr -d ' ')
        if [ -n "$current_version" ]; then
            record_test "Database Migration Version" "PASS" "Current version: $current_version"
        else
            record_test "Database Migration Version" "WARN" "No migration version found"
        fi
    else
        record_test "Database Migration Status" "FAIL" "Alembic version table not found"
    fi
    
    # Check for expected tables
    local expected_tables=("users" "portfolios" "positions" "transactions" "signals" "compliance_records")
    for table in "${expected_tables[@]}"; do
        if echo "SELECT 1 FROM information_schema.tables WHERE table_name='$table';" | PGPASSWORD=crypto_password psql -h localhost -U crypto_user -d crypto_0dte_local -t | grep -q 1; then
            record_test "Database Table: $table" "PASS" "Table exists"
        else
            record_test "Database Table: $table" "WARN" "Table not found (may not be created yet)"
        fi
    done
fi

echo ""

# Test Suite 6: External Dependencies Health Checks
print_test_header "Test Suite 6: External Dependencies Health Checks"

# Test Delta Exchange API connectivity (testnet)
print_info "Testing external API connectivity..."

# Delta Exchange testnet health
if curl -s --max-time 10 "https://testnet-api.delta.exchange/v2/products" >/dev/null 2>&1; then
    record_test "Delta Exchange Testnet API" "PASS" "API accessible"
else
    record_test "Delta Exchange Testnet API" "WARN" "API not accessible (may be network issue)"
fi

# OpenAI API health (basic connectivity test)
if curl -s --max-time 10 "https://api.openai.com/v1/models" -H "Authorization: Bearer invalid" 2>/dev/null | grep -q "error"; then
    record_test "OpenAI API Connectivity" "PASS" "API accessible (authentication expected to fail)"
else
    record_test "OpenAI API Connectivity" "WARN" "API not accessible (may be network issue)"
fi

echo ""

# Test Suite 7: System Resource Health Checks
print_test_header "Test Suite 7: System Resource Health Checks"

# Check disk space
local disk_usage=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 90 ]; then
    record_test "Disk Space Usage" "PASS" "Usage: ${disk_usage}%"
elif [ "$disk_usage" -lt 95 ]; then
    record_test "Disk Space Usage" "WARN" "Usage: ${disk_usage}% (getting high)"
else
    record_test "Disk Space Usage" "FAIL" "Usage: ${disk_usage}% (critically high)"
fi

# Check memory usage
if command -v free >/dev/null 2>&1; then
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$memory_usage" -lt 80 ]; then
        record_test "Memory Usage" "PASS" "Usage: ${memory_usage}%"
    elif [ "$memory_usage" -lt 90 ]; then
        record_test "Memory Usage" "WARN" "Usage: ${memory_usage}% (getting high)"
    else
        record_test "Memory Usage" "FAIL" "Usage: ${memory_usage}% (critically high)"
    fi
fi

# Check CPU load
if command -v uptime >/dev/null 2>&1; then
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_cores=$(nproc 2>/dev/null || echo "1")
    local load_percentage=$(echo "scale=0; $load_avg * 100 / $cpu_cores" | bc -l 2>/dev/null || echo "0")
    
    if [ "$load_percentage" -lt 70 ]; then
        record_test "CPU Load Average" "PASS" "Load: ${load_avg} (${load_percentage}%)"
    elif [ "$load_percentage" -lt 90 ]; then
        record_test "CPU Load Average" "WARN" "Load: ${load_avg} (${load_percentage}%)"
    else
        record_test "CPU Load Average" "FAIL" "Load: ${load_avg} (${load_percentage}%)"
    fi
fi

echo ""

# Test Suite 8: Security Health Checks
print_test_header "Test Suite 8: Security Health Checks"

# Check for environment variables
print_info "Checking security configuration..."

# Check if JWT secret is properly configured
if curl -s "http://localhost:8000/health/detailed" | grep -q "jwt_configured.*true" 2>/dev/null; then
    record_test "JWT Secret Configuration" "PASS" "JWT secret properly configured"
else
    record_test "JWT Secret Configuration" "WARN" "JWT secret configuration unclear"
fi

# Check CORS configuration
local cors_response=$(curl -s -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: GET" -X OPTIONS "http://localhost:8000/health" 2>/dev/null || echo "")
if echo "$cors_response" | grep -q "Access-Control-Allow-Origin" 2>/dev/null; then
    record_test "CORS Configuration" "PASS" "CORS headers present"
else
    record_test "CORS Configuration" "WARN" "CORS headers not detected"
fi

# Check for debug mode in production
if curl -s "http://localhost:8000/health/detailed" | grep -q "debug.*false" 2>/dev/null; then
    record_test "Debug Mode Configuration" "PASS" "Debug mode disabled"
elif curl -s "http://localhost:8000/health/detailed" | grep -q "debug.*true" 2>/dev/null; then
    record_test "Debug Mode Configuration" "WARN" "Debug mode enabled (OK for development)"
else
    record_test "Debug Mode Configuration" "WARN" "Debug mode status unclear"
fi

echo ""

# Generate Health Check Report
print_test_header "Health Check Report Generation"

# Create detailed report
cat > "$REPORT_FILE" << EOF
Crypto-0DTE System - Health Check Report
========================================
Generated: $(date)
Project Root: $PROJECT_ROOT

SUMMARY
-------
Total Tests: $TOTAL_TESTS
Passed: $PASSED_TESTS
Failed: $FAILED_TESTS
Warnings: $WARNING_TESTS

Success Rate: $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)%

SYSTEM STATUS
-------------
EOF

# Add system status based on results
if [ "$FAILED_TESTS" -eq 0 ]; then
    if [ "$WARNING_TESTS" -eq 0 ]; then
        echo "🟢 EXCELLENT - All tests passed" >> "$REPORT_FILE"
        OVERALL_STATUS="EXCELLENT"
    else
        echo "🟡 GOOD - All critical tests passed, some warnings" >> "$REPORT_FILE"
        OVERALL_STATUS="GOOD"
    fi
elif [ "$FAILED_TESTS" -lt 3 ]; then
    echo "🟠 FAIR - Some non-critical tests failed" >> "$REPORT_FILE"
    OVERALL_STATUS="FAIR"
else
    echo "🔴 POOR - Multiple critical tests failed" >> "$REPORT_FILE"
    OVERALL_STATUS="POOR"
fi

# Add recommendations
cat >> "$REPORT_FILE" << EOF

RECOMMENDATIONS
---------------
EOF

if [ "$FAILED_TESTS" -gt 0 ]; then
    echo "- Review failed tests and fix underlying issues" >> "$REPORT_FILE"
fi

if [ "$WARNING_TESTS" -gt 0 ]; then
    echo "- Address warning conditions for optimal performance" >> "$REPORT_FILE"
fi

echo "- Run autonomous trading tests: ./test-autonomous-trading.sh" >> "$REPORT_FILE"
echo "- Monitor system logs for any errors" >> "$REPORT_FILE"
echo "- Verify external API keys are properly configured" >> "$REPORT_FILE"

# Display final results
echo ""
echo -e "${BLUE}📊 Final Health Check Results${NC}"
echo "=============================="
echo ""
echo -e "Total Tests: ${BLUE}$TOTAL_TESTS${NC}"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo -e "Warnings: ${YELLOW}$WARNING_TESTS${NC}"
echo ""
echo -e "Success Rate: ${CYAN}$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)%${NC}"
echo ""

case "$OVERALL_STATUS" in
    "EXCELLENT")
        echo -e "Overall Status: ${GREEN}🟢 EXCELLENT${NC}"
        echo -e "${GREEN}✅ System is healthy and ready for production!${NC}"
        ;;
    "GOOD")
        echo -e "Overall Status: ${YELLOW}🟡 GOOD${NC}"
        echo -e "${YELLOW}⚠️  System is mostly healthy with minor issues${NC}"
        ;;
    "FAIR")
        echo -e "Overall Status: ${YELLOW}🟠 FAIR${NC}"
        echo -e "${YELLOW}⚠️  System has some issues that should be addressed${NC}"
        ;;
    "POOR")
        echo -e "Overall Status: ${RED}🔴 POOR${NC}"
        echo -e "${RED}❌ System has critical issues that must be fixed${NC}"
        ;;
esac

echo ""
echo -e "📁 Detailed Results: ${CYAN}$RESULTS_FILE${NC}"
echo -e "📋 Full Report: ${CYAN}$REPORT_FILE${NC}"
echo ""

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}🎉 Ready to proceed with autonomous trading tests!${NC}"
    echo -e "${GREEN}   Run: ./test-autonomous-trading.sh${NC}"
else
    echo -e "${RED}🚨 Fix failed tests before proceeding to autonomous trading tests${NC}"
fi

echo ""
echo "End Time: $(date)"

# Exit with appropriate code
if [ "$FAILED_TESTS" -eq 0 ]; then
    exit 0
else
    exit 1
fi

