#!/bin/bash

# Crypto-0DTE System - Autonomous Trading Validation Tests
# Tests the complete autonomous trading workflow including data ingestion, signal generation, and trade execution

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT=$(pwd)
LOG_DIR="$PROJECT_ROOT/logs"
RESULTS_FILE="$LOG_DIR/autonomous-trading-results.json"
REPORT_FILE="$LOG_DIR/autonomous-trading-report.txt"
TEST_DURATION=300  # 5 minutes of autonomous testing
POLLING_INTERVAL=30  # 30 seconds between checks

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNING_TESTS=0

# Trading metrics
SIGNALS_GENERATED=0
TRADES_EXECUTED=0
DATA_POINTS_RECEIVED=0
ERRORS_ENCOUNTERED=0

# Create logs directory
mkdir -p "$LOG_DIR"

echo -e "${BLUE}🤖 Crypto-0DTE System - Autonomous Trading Validation Tests${NC}"
echo -e "${BLUE}============================================================${NC}"
echo "Start Time: $(date)"
echo "Project Root: $PROJECT_ROOT"
echo "Test Duration: $TEST_DURATION seconds ($(($TEST_DURATION / 60)) minutes)"
echo "Polling Interval: $POLLING_INTERVAL seconds"
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
    echo "$(printf '%.0s-' {1..60})"
}

print_metric() {
    echo -e "${MAGENTA}📊 $1${NC}"
}

# Function to record test result
record_test() {
    local test_name="$1"
    local status="$2"
    local details="$3"
    local metrics="${4:-{}}"
    
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
    echo "{\"test\": \"$test_name\", \"status\": \"$status\", \"details\": \"$details\", \"metrics\": $metrics, \"timestamp\": \"$(date -Iseconds)\"}" >> "$RESULTS_FILE"
}

# Function to get API response
get_api_response() {
    local url="$1"
    local timeout="${2:-10}"
    
    curl -s --max-time "$timeout" "$url" 2>/dev/null || echo "{\"error\": \"API call failed\"}"
}

# Function to test JSON field
test_json_field() {
    local json="$1"
    local field="$2"
    
    if command -v jq >/dev/null 2>&1; then
        echo "$json" | jq -r ".$field" 2>/dev/null || echo "null"
    else
        echo "null"
    fi
}

# Function to count array elements
count_json_array() {
    local json="$1"
    local field="$2"
    
    if command -v jq >/dev/null 2>&1; then
        echo "$json" | jq -r ".$field | length" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# Initialize results file
echo "" > "$RESULTS_FILE"

# Prerequisites check
print_test_header "Prerequisites Check"

# Check if system is healthy first
print_info "Checking system health before autonomous testing..."

# Basic health check
local health_response=$(get_api_response "http://localhost:8000/health")
local health_status=$(test_json_field "$health_response" "status")

if [ "$health_status" = "healthy" ]; then
    record_test "System Health Prerequisites" "PASS" "System is healthy"
else
    record_test "System Health Prerequisites" "FAIL" "System is not healthy: $health_status"
    echo -e "${RED}❌ System health check failed. Run ./test-health-checks.sh first${NC}"
    exit 1
fi

# Check required tools
if ! command -v jq >/dev/null 2>&1; then
    print_warning "jq not found - installing for JSON processing..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y jq
    elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y jq
    fi
fi

echo ""

# Test Suite 1: Market Data Ingestion Testing
print_test_header "Test Suite 1: Market Data Ingestion Testing"

print_info "Testing real-time market data ingestion from Delta Exchange..."

# Test market data symbols endpoint
local symbols_response=$(get_api_response "http://localhost:8000/api/v1/market-data/symbols")
local symbols_count=$(count_json_array "$symbols_response" "symbols")

if [ "$symbols_count" -gt 0 ]; then
    record_test "Market Data Symbols Retrieval" "PASS" "Retrieved $symbols_count symbols" "{\"symbols_count\": $symbols_count}"
    DATA_POINTS_RECEIVED=$((DATA_POINTS_RECEIVED + symbols_count))
else
    record_test "Market Data Symbols Retrieval" "FAIL" "No symbols retrieved"
fi

# Test specific ticker data
local ticker_symbols=("BTCUSDT" "ETHUSDT" "ADAUSDT")
for symbol in "${ticker_symbols[@]}"; do
    local ticker_response=$(get_api_response "http://localhost:8000/api/v1/market-data/ticker/$symbol")
    local ticker_price=$(test_json_field "$ticker_response" "price")
    local ticker_volume=$(test_json_field "$ticker_response" "volume")
    
    if [ "$ticker_price" != "null" ] && [ "$ticker_price" != "" ]; then
        record_test "Market Data Ticker: $symbol" "PASS" "Price: $ticker_price, Volume: $ticker_volume" "{\"price\": \"$ticker_price\", \"volume\": \"$ticker_volume\"}"
        DATA_POINTS_RECEIVED=$((DATA_POINTS_RECEIVED + 1))
    else
        record_test "Market Data Ticker: $symbol" "FAIL" "No price data received"
    fi
done

# Test historical data retrieval
local historical_response=$(get_api_response "http://localhost:8000/api/v1/market-data/historical/BTCUSDT?interval=1h&limit=24")
local historical_count=$(count_json_array "$historical_response" "data")

if [ "$historical_count" -gt 0 ]; then
    record_test "Historical Data Retrieval" "PASS" "Retrieved $historical_count historical data points" "{\"data_points\": $historical_count}"
    DATA_POINTS_RECEIVED=$((DATA_POINTS_RECEIVED + historical_count))
else
    record_test "Historical Data Retrieval" "WARN" "Limited or no historical data"
fi

echo ""

# Test Suite 2: Technical Analysis and Signal Generation
print_test_header "Test Suite 2: Technical Analysis and Signal Generation"

print_info "Testing AI-powered signal generation with technical analysis..."

# Test signal generation endpoint
local signals_response=$(get_api_response "http://localhost:8000/api/v1/signals")
local signals_count=$(count_json_array "$signals_response" "signals")

if [ "$signals_count" -gt 0 ]; then
    record_test "Signal Generation Endpoint" "PASS" "Generated $signals_count signals" "{\"signals_count\": $signals_count}"
    SIGNALS_GENERATED=$((SIGNALS_GENERATED + signals_count))
else
    record_test "Signal Generation Endpoint" "WARN" "No signals generated yet"
fi

# Test latest signals
local latest_signals_response=$(get_api_response "http://localhost:8000/api/v1/signals/latest")
local latest_signals_count=$(count_json_array "$latest_signals_response" "signals")

if [ "$latest_signals_count" -gt 0 ]; then
    record_test "Latest Signals Retrieval" "PASS" "Retrieved $latest_signals_count latest signals" "{\"latest_signals\": $latest_signals_count}"
    
    # Analyze signal quality
    local first_signal=$(echo "$latest_signals_response" | jq -r '.signals[0]' 2>/dev/null || echo "{}")
    local signal_confidence=$(test_json_field "$first_signal" "confidence")
    local signal_strategy=$(test_json_field "$first_signal" "strategy")
    local signal_symbol=$(test_json_field "$first_signal" "symbol")
    
    if [ "$signal_confidence" != "null" ] && [ "$signal_strategy" != "null" ]; then
        record_test "Signal Quality Analysis" "PASS" "Signal: $signal_symbol, Strategy: $signal_strategy, Confidence: $signal_confidence" "{\"confidence\": \"$signal_confidence\", \"strategy\": \"$signal_strategy\"}"
    else
        record_test "Signal Quality Analysis" "WARN" "Signal structure incomplete"
    fi
else
    record_test "Latest Signals Retrieval" "WARN" "No latest signals available"
fi

# Test technical indicators
local indicators_response=$(get_api_response "http://localhost:8000/api/v1/signals/indicators/BTCUSDT")
local rsi_value=$(test_json_field "$indicators_response" "rsi")
local macd_value=$(test_json_field "$indicators_response" "macd")
local bb_upper=$(test_json_field "$indicators_response" "bollinger_bands.upper")

if [ "$rsi_value" != "null" ] && [ "$macd_value" != "null" ]; then
    record_test "Technical Indicators Calculation" "PASS" "RSI: $rsi_value, MACD: $macd_value" "{\"rsi\": \"$rsi_value\", \"macd\": \"$macd_value\"}"
else
    record_test "Technical Indicators Calculation" "WARN" "Some indicators not calculated"
fi

echo ""

# Test Suite 3: Autonomous Trading Cycle Testing
print_test_header "Test Suite 3: Autonomous Trading Cycle Testing"

print_info "Starting $TEST_DURATION second autonomous trading cycle test..."
print_info "This will monitor the system's ability to continuously:"
print_info "  1. Fetch market data"
print_info "  2. Generate trading signals"
print_info "  3. Execute trades (testnet)"
print_info "  4. Monitor performance"

# Initialize cycle metrics
local cycle_start_time=$(date +%s)
local cycle_end_time=$((cycle_start_time + TEST_DURATION))
local cycle_count=0
local successful_cycles=0
local failed_cycles=0

echo ""
print_info "Autonomous cycle monitoring started..."
echo "Progress: [$(printf '%.0s-' {1..50})]"

while [ $(date +%s) -lt $cycle_end_time ]; do
    cycle_count=$((cycle_count + 1))
    local current_time=$(date +%s)
    local elapsed_time=$((current_time - cycle_start_time))
    local remaining_time=$((cycle_end_time - current_time))
    
    # Progress indicator
    local progress=$((elapsed_time * 50 / TEST_DURATION))
    local progress_bar=$(printf '%.0s=' $(seq 1 $progress))$(printf '%.0s-' $(seq $((progress + 1)) 50))
    echo -ne "\rProgress: [$progress_bar] ${elapsed_time}s/${TEST_DURATION}s"
    
    # Test current cycle
    local cycle_success=true
    
    # Check market data freshness
    local current_ticker=$(get_api_response "http://localhost:8000/api/v1/market-data/ticker/BTCUSDT" 5)
    local current_price=$(test_json_field "$current_ticker" "price")
    local current_timestamp=$(test_json_field "$current_ticker" "timestamp")
    
    if [ "$current_price" = "null" ] || [ "$current_price" = "" ]; then
        cycle_success=false
        ERRORS_ENCOUNTERED=$((ERRORS_ENCOUNTERED + 1))
    else
        DATA_POINTS_RECEIVED=$((DATA_POINTS_RECEIVED + 1))
    fi
    
    # Check signal generation
    local current_signals=$(get_api_response "http://localhost:8000/api/v1/signals/latest" 5)
    local current_signals_count=$(count_json_array "$current_signals" "signals")
    
    if [ "$current_signals_count" -gt 0 ]; then
        SIGNALS_GENERATED=$((SIGNALS_GENERATED + current_signals_count))
        
        # Check if any signals are actionable
        local actionable_signals=$(echo "$current_signals" | jq -r '.signals[] | select(.confidence > 0.7) | .symbol' 2>/dev/null | wc -l)
        if [ "$actionable_signals" -gt 0 ]; then
            # Simulate trade execution check (testnet)
            local trade_response=$(get_api_response "http://localhost:8000/api/v1/trading/simulate" 5)
            local trade_status=$(test_json_field "$trade_response" "status")
            
            if [ "$trade_status" = "success" ] || [ "$trade_status" = "simulated" ]; then
                TRADES_EXECUTED=$((TRADES_EXECUTED + 1))
            fi
        fi
    fi
    
    # Record cycle result
    if [ "$cycle_success" = true ]; then
        successful_cycles=$((successful_cycles + 1))
    else
        failed_cycles=$((failed_cycles + 1))
    fi
    
    # Wait for next cycle
    sleep $POLLING_INTERVAL
done

echo ""  # New line after progress bar
echo ""

# Analyze autonomous cycle results
local cycle_success_rate=$(echo "scale=1; $successful_cycles * 100 / $cycle_count" | bc -l)

if [ "$successful_cycles" -gt $((cycle_count * 80 / 100)) ]; then
    record_test "Autonomous Cycle Success Rate" "PASS" "Success rate: ${cycle_success_rate}% ($successful_cycles/$cycle_count)" "{\"success_rate\": $cycle_success_rate, \"successful_cycles\": $successful_cycles, \"total_cycles\": $cycle_count}"
elif [ "$successful_cycles" -gt $((cycle_count * 60 / 100)) ]; then
    record_test "Autonomous Cycle Success Rate" "WARN" "Success rate: ${cycle_success_rate}% ($successful_cycles/$cycle_count)" "{\"success_rate\": $cycle_success_rate, \"successful_cycles\": $successful_cycles, \"total_cycles\": $cycle_count}"
else
    record_test "Autonomous Cycle Success Rate" "FAIL" "Success rate: ${cycle_success_rate}% ($successful_cycles/$cycle_count)" "{\"success_rate\": $cycle_success_rate, \"successful_cycles\": $successful_cycles, \"total_cycles\": $cycle_count}"
fi

echo ""

# Test Suite 4: Performance and Reliability Testing
print_test_header "Test Suite 4: Performance and Reliability Testing"

# Test system performance metrics
local performance_response=$(get_api_response "http://localhost:8000/health/detailed")
local cpu_usage=$(test_json_field "$performance_response" "system.cpu_percent")
local memory_usage=$(test_json_field "$performance_response" "system.memory_percent")
local response_time=$(test_json_field "$performance_response" "response_time_ms")

if [ "$cpu_usage" != "null" ] && [ "$memory_usage" != "null" ]; then
    local cpu_num=$(echo "$cpu_usage" | sed 's/[^0-9.]//g')
    local memory_num=$(echo "$memory_usage" | sed 's/[^0-9.]//g')
    
    if [ "$(echo "$cpu_num < 80" | bc -l)" -eq 1 ] && [ "$(echo "$memory_num < 80" | bc -l)" -eq 1 ]; then
        record_test "System Performance Metrics" "PASS" "CPU: ${cpu_usage}, Memory: ${memory_usage}" "{\"cpu_usage\": \"$cpu_usage\", \"memory_usage\": \"$memory_usage\"}"
    else
        record_test "System Performance Metrics" "WARN" "High resource usage - CPU: ${cpu_usage}, Memory: ${memory_usage}" "{\"cpu_usage\": \"$cpu_usage\", \"memory_usage\": \"$memory_usage\"}"
    fi
else
    record_test "System Performance Metrics" "WARN" "Performance metrics not available"
fi

# Test error rate
local error_rate=$(echo "scale=1; $ERRORS_ENCOUNTERED * 100 / $cycle_count" | bc -l)

if [ "$(echo "$error_rate < 5" | bc -l)" -eq 1 ]; then
    record_test "System Error Rate" "PASS" "Error rate: ${error_rate}% ($ERRORS_ENCOUNTERED/$cycle_count)" "{\"error_rate\": $error_rate, \"errors\": $ERRORS_ENCOUNTERED}"
elif [ "$(echo "$error_rate < 10" | bc -l)" -eq 1 ]; then
    record_test "System Error Rate" "WARN" "Error rate: ${error_rate}% ($ERRORS_ENCOUNTERED/$cycle_count)" "{\"error_rate\": $error_rate, \"errors\": $ERRORS_ENCOUNTERED}"
else
    record_test "System Error Rate" "FAIL" "Error rate: ${error_rate}% ($ERRORS_ENCOUNTERED/$cycle_count)" "{\"error_rate\": $error_rate, \"errors\": $ERRORS_ENCOUNTERED}"
fi

# Test data throughput
local data_throughput=$(echo "scale=1; $DATA_POINTS_RECEIVED / ($TEST_DURATION / 60)" | bc -l)

if [ "$(echo "$data_throughput > 10" | bc -l)" -eq 1 ]; then
    record_test "Data Throughput" "PASS" "Throughput: ${data_throughput} data points/minute" "{\"throughput\": $data_throughput, \"total_data_points\": $DATA_POINTS_RECEIVED}"
elif [ "$(echo "$data_throughput > 5" | bc -l)" -eq 1 ]; then
    record_test "Data Throughput" "WARN" "Throughput: ${data_throughput} data points/minute" "{\"throughput\": $data_throughput, \"total_data_points\": $DATA_POINTS_RECEIVED}"
else
    record_test "Data Throughput" "FAIL" "Throughput: ${data_throughput} data points/minute" "{\"throughput\": $data_throughput, \"total_data_points\": $DATA_POINTS_RECEIVED}"
fi

echo ""

# Test Suite 5: Trading Logic Validation
print_test_header "Test Suite 5: Trading Logic Validation"

# Test risk management
local risk_response=$(get_api_response "http://localhost:8000/api/v1/trading/risk-check")
local max_position_size=$(test_json_field "$risk_response" "max_position_size")
local risk_limit=$(test_json_field "$risk_response" "risk_limit")

if [ "$max_position_size" != "null" ] && [ "$risk_limit" != "null" ]; then
    record_test "Risk Management Configuration" "PASS" "Max position: $max_position_size, Risk limit: $risk_limit" "{\"max_position_size\": \"$max_position_size\", \"risk_limit\": \"$risk_limit\"}"
else
    record_test "Risk Management Configuration" "WARN" "Risk management parameters not fully configured"
fi

# Test signal quality over time
local signal_quality_score=0
if [ "$SIGNALS_GENERATED" -gt 0 ]; then
    # Calculate average confidence of generated signals
    local signals_analysis=$(get_api_response "http://localhost:8000/api/v1/signals/analysis")
    local avg_confidence=$(test_json_field "$signals_analysis" "average_confidence")
    local signal_diversity=$(test_json_field "$signals_analysis" "strategy_diversity")
    
    if [ "$avg_confidence" != "null" ]; then
        local confidence_num=$(echo "$avg_confidence" | sed 's/[^0-9.]//g')
        if [ "$(echo "$confidence_num > 0.6" | bc -l)" -eq 1 ]; then
            record_test "Signal Quality Score" "PASS" "Average confidence: $avg_confidence, Diversity: $signal_diversity" "{\"avg_confidence\": \"$avg_confidence\", \"diversity\": \"$signal_diversity\"}"
        else
            record_test "Signal Quality Score" "WARN" "Low average confidence: $avg_confidence" "{\"avg_confidence\": \"$avg_confidence\"}"
        fi
    else
        record_test "Signal Quality Score" "WARN" "Signal quality analysis not available"
    fi
else
    record_test "Signal Quality Score" "FAIL" "No signals generated during test period"
fi

# Test trade execution logic
if [ "$TRADES_EXECUTED" -gt 0 ]; then
    local execution_rate=$(echo "scale=1; $TRADES_EXECUTED * 100 / $SIGNALS_GENERATED" | bc -l)
    
    if [ "$(echo "$execution_rate > 10" | bc -l)" -eq 1 ] && [ "$(echo "$execution_rate < 50" | bc -l)" -eq 1 ]; then
        record_test "Trade Execution Rate" "PASS" "Execution rate: ${execution_rate}% ($TRADES_EXECUTED/$SIGNALS_GENERATED)" "{\"execution_rate\": $execution_rate, \"trades_executed\": $TRADES_EXECUTED}"
    elif [ "$(echo "$execution_rate > 5" | bc -l)" -eq 1 ]; then
        record_test "Trade Execution Rate" "WARN" "Execution rate: ${execution_rate}% (may be conservative)" "{\"execution_rate\": $execution_rate, \"trades_executed\": $TRADES_EXECUTED}"
    else
        record_test "Trade Execution Rate" "WARN" "Low execution rate: ${execution_rate}%" "{\"execution_rate\": $execution_rate, \"trades_executed\": $TRADES_EXECUTED}"
    fi
else
    record_test "Trade Execution Rate" "WARN" "No trades executed during test period"
fi

echo ""

# Generate Autonomous Trading Report
print_test_header "Autonomous Trading Report Generation"

# Create detailed report
cat > "$REPORT_FILE" << EOF
Crypto-0DTE System - Autonomous Trading Validation Report
=========================================================
Generated: $(date)
Test Duration: $TEST_DURATION seconds ($(($TEST_DURATION / 60)) minutes)
Polling Interval: $POLLING_INTERVAL seconds

SUMMARY
-------
Total Tests: $TOTAL_TESTS
Passed: $PASSED_TESTS
Failed: $FAILED_TESTS
Warnings: $WARNING_TESTS

Success Rate: $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)%

AUTONOMOUS TRADING METRICS
--------------------------
Autonomous Cycles: $cycle_count
Successful Cycles: $successful_cycles
Failed Cycles: $failed_cycles
Cycle Success Rate: ${cycle_success_rate}%

Data Points Received: $DATA_POINTS_RECEIVED
Signals Generated: $SIGNALS_GENERATED
Trades Executed: $TRADES_EXECUTED
Errors Encountered: $ERRORS_ENCOUNTERED

Data Throughput: ${data_throughput} points/minute
Error Rate: ${error_rate}%

SYSTEM STATUS
-------------
EOF

# Add system status based on results
if [ "$FAILED_TESTS" -eq 0 ] && [ "$successful_cycles" -gt $((cycle_count * 80 / 100)) ]; then
    if [ "$WARNING_TESTS" -eq 0 ]; then
        echo "🟢 EXCELLENT - Autonomous trading system fully operational" >> "$REPORT_FILE"
        OVERALL_STATUS="EXCELLENT"
    else
        echo "🟡 GOOD - Autonomous trading system operational with minor issues" >> "$REPORT_FILE"
        OVERALL_STATUS="GOOD"
    fi
elif [ "$FAILED_TESTS" -lt 3 ] && [ "$successful_cycles" -gt $((cycle_count * 60 / 100)) ]; then
    echo "🟠 FAIR - Autonomous trading system partially operational" >> "$REPORT_FILE"
    OVERALL_STATUS="FAIR"
else
    echo "🔴 POOR - Autonomous trading system has significant issues" >> "$REPORT_FILE"
    OVERALL_STATUS="POOR"
fi

# Add detailed analysis
cat >> "$REPORT_FILE" << EOF

DETAILED ANALYSIS
-----------------
Market Data Ingestion: $([ "$DATA_POINTS_RECEIVED" -gt 50 ] && echo "✅ Excellent" || echo "⚠️ Needs improvement")
Signal Generation: $([ "$SIGNALS_GENERATED" -gt 10 ] && echo "✅ Active" || echo "⚠️ Limited")
Trade Execution: $([ "$TRADES_EXECUTED" -gt 0 ] && echo "✅ Functional" || echo "⚠️ Not executing")
System Stability: $([ "$ERRORS_ENCOUNTERED" -lt 5 ] && echo "✅ Stable" || echo "⚠️ Some issues")

RECOMMENDATIONS
---------------
EOF

if [ "$FAILED_TESTS" -gt 0 ]; then
    echo "- Fix failed tests before production deployment" >> "$REPORT_FILE"
fi

if [ "$SIGNALS_GENERATED" -eq 0 ]; then
    echo "- Check signal generation algorithms and market data connectivity" >> "$REPORT_FILE"
fi

if [ "$TRADES_EXECUTED" -eq 0 ]; then
    echo "- Verify trade execution logic and testnet connectivity" >> "$REPORT_FILE"
fi

if [ "$ERRORS_ENCOUNTERED" -gt 5 ]; then
    echo "- Investigate and fix sources of errors in the system" >> "$REPORT_FILE"
fi

echo "- Monitor system performance in production environment" >> "$REPORT_FILE"
echo "- Set up alerting for autonomous trading failures" >> "$REPORT_FILE"
echo "- Regularly review and optimize trading strategies" >> "$REPORT_FILE"

# Display final results
echo ""
echo -e "${BLUE}📊 Final Autonomous Trading Test Results${NC}"
echo "=========================================="
echo ""

# Test results summary
echo -e "Test Results:"
echo -e "  Total Tests: ${BLUE}$TOTAL_TESTS${NC}"
echo -e "  Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "  Failed: ${RED}$FAILED_TESTS${NC}"
echo -e "  Warnings: ${YELLOW}$WARNING_TESTS${NC}"
echo -e "  Success Rate: ${CYAN}$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)%${NC}"
echo ""

# Trading metrics summary
echo -e "Trading Metrics:"
print_metric "Autonomous Cycles: $cycle_count (${cycle_success_rate}% success rate)"
print_metric "Data Points Received: $DATA_POINTS_RECEIVED (${data_throughput}/min)"
print_metric "Signals Generated: $SIGNALS_GENERATED"
print_metric "Trades Executed: $TRADES_EXECUTED"
print_metric "Errors Encountered: $ERRORS_ENCOUNTERED (${error_rate}% error rate)"
echo ""

# Overall status
case "$OVERALL_STATUS" in
    "EXCELLENT")
        echo -e "Overall Status: ${GREEN}🟢 EXCELLENT${NC}"
        echo -e "${GREEN}🎉 Autonomous trading system is fully operational and ready for production!${NC}"
        echo -e "${GREEN}✅ All systems functioning optimally${NC}"
        ;;
    "GOOD")
        echo -e "Overall Status: ${YELLOW}🟡 GOOD${NC}"
        echo -e "${YELLOW}✅ Autonomous trading system is operational with minor optimizations needed${NC}"
        echo -e "${YELLOW}⚠️  Address warnings for optimal performance${NC}"
        ;;
    "FAIR")
        echo -e "Overall Status: ${YELLOW}🟠 FAIR${NC}"
        echo -e "${YELLOW}⚠️  Autonomous trading system needs improvements before production${NC}"
        echo -e "${YELLOW}🔧 Address failed tests and optimize performance${NC}"
        ;;
    "POOR")
        echo -e "Overall Status: ${RED}🔴 POOR${NC}"
        echo -e "${RED}❌ Autonomous trading system has critical issues${NC}"
        echo -e "${RED}🚨 Significant fixes required before production deployment${NC}"
        ;;
esac

echo ""
echo -e "📁 Detailed Results: ${CYAN}$RESULTS_FILE${NC}"
echo -e "📋 Full Report: ${CYAN}$REPORT_FILE${NC}"
echo ""

# Production readiness assessment
if [ "$OVERALL_STATUS" = "EXCELLENT" ] || [ "$OVERALL_STATUS" = "GOOD" ]; then
    echo -e "${GREEN}🚀 PRODUCTION READINESS: APPROVED${NC}"
    echo -e "${GREEN}   Your autonomous crypto trading system is ready for Railway deployment!${NC}"
    echo ""
    echo -e "${CYAN}Next Steps:${NC}"
    echo -e "   1. Deploy to Railway: Follow Railway deployment guide"
    echo -e "   2. Configure production environment variables"
    echo -e "   3. Set up monitoring and alerting"
    echo -e "   4. Start with small position sizes"
    echo -e "   5. Monitor performance closely for first 24 hours"
else
    echo -e "${RED}🚨 PRODUCTION READINESS: NOT APPROVED${NC}"
    echo -e "${RED}   Fix identified issues before production deployment${NC}"
    echo ""
    echo -e "${CYAN}Required Actions:${NC}"
    echo -e "   1. Fix all failed tests"
    echo -e "   2. Address performance issues"
    echo -e "   3. Improve signal generation if needed"
    echo -e "   4. Re-run this test until EXCELLENT or GOOD status achieved"
fi

echo ""
echo "End Time: $(date)"

# Exit with appropriate code
if [ "$OVERALL_STATUS" = "EXCELLENT" ] || [ "$OVERALL_STATUS" = "GOOD" ]; then
    exit 0
else
    exit 1
fi

