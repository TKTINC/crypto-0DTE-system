#!/bin/bash

# Crypto-0DTE Autonomous Trading System Validation
# ================================================
# This script validates that the autonomous trading system is working correctly

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "$(printf '=%.0s' {1..50})"
}

print_success() {
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

# Test API connectivity
test_api_connectivity() {
    print_header "🌐 API Connectivity Tests"
    
    # Test backend health
    print_info "Testing backend health..."
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        print_success "Backend API is responding"
        
        # Get health details
        health_response=$(curl -s http://localhost:8000/health)
        echo "   Response: $health_response"
    else
        print_error "Backend API is not responding"
        return 1
    fi
    
    # Test Delta Exchange connectivity
    print_info "Testing Delta Exchange API connectivity..."
    delta_test=$(curl -s http://localhost:8000/api/v1/market-data/test-delta-connection 2>/dev/null)
    if [ $? -eq 0 ]; then
        print_success "Delta Exchange API connection test passed"
        echo "   Response: $delta_test"
    else
        print_warning "Delta Exchange API connection test failed or endpoint not available"
    fi
    
    # Test OpenAI connectivity
    print_info "Testing OpenAI API connectivity..."
    openai_test=$(curl -s http://localhost:8000/api/v1/signals/test-openai-connection 2>/dev/null)
    if [ $? -eq 0 ]; then
        print_success "OpenAI API connection test passed"
        echo "   Response: $openai_test"
    else
        print_warning "OpenAI API connection test failed or endpoint not available"
    fi
    
    echo ""
}

# Test autonomous signal generation
test_signal_generation() {
    print_header "🤖 Autonomous Signal Generation Tests"
    
    # Check if signals are being generated
    print_info "Checking recent signal generation..."
    signals_response=$(curl -s http://localhost:8000/api/v1/signals/recent?limit=5 2>/dev/null)
    
    if [ $? -eq 0 ] && [ "$signals_response" != "[]" ] && [ "$signals_response" != "null" ]; then
        print_success "Recent signals found"
        echo "   Signals: $signals_response"
        
        # Count signals
        signal_count=$(echo "$signals_response" | jq length 2>/dev/null || echo "0")
        print_info "Found $signal_count recent signals"
    else
        print_warning "No recent signals found or signals endpoint not available"
        print_info "This could mean:"
        print_info "  - System just started and hasn't generated signals yet"
        print_info "  - API keys not configured"
        print_info "  - Signal generation service not running"
    fi
    
    # Test manual signal generation
    print_info "Testing manual signal generation..."
    manual_signal=$(curl -s -X POST http://localhost:8000/api/v1/signals/generate \
        -H "Content-Type: application/json" \
        -d '{"symbol": "BTC-USDT", "timeframe": "1h"}' 2>/dev/null)
    
    if [ $? -eq 0 ] && [ "$manual_signal" != "null" ]; then
        print_success "Manual signal generation successful"
        echo "   Signal: $manual_signal"
    else
        print_warning "Manual signal generation failed or endpoint not available"
    fi
    
    echo ""
}

# Test market data ingestion
test_market_data() {
    print_header "📊 Market Data Ingestion Tests"
    
    # Check if market data is being received
    print_info "Checking recent market data..."
    market_data=$(curl -s http://localhost:8000/api/v1/market-data/recent?symbol=BTC-USDT&limit=5 2>/dev/null)
    
    if [ $? -eq 0 ] && [ "$market_data" != "[]" ] && [ "$market_data" != "null" ]; then
        print_success "Recent market data found"
        echo "   Data points: $(echo "$market_data" | jq length 2>/dev/null || echo "N/A")"
        
        # Show latest data point
        latest_data=$(echo "$market_data" | jq '.[0]' 2>/dev/null)
        if [ "$latest_data" != "null" ]; then
            print_info "Latest data point: $latest_data"
        fi
    else
        print_warning "No recent market data found or endpoint not available"
        print_info "This could mean:"
        print_info "  - Market data ingestion not started"
        print_info "  - Delta Exchange API not configured"
        print_info "  - Database connection issues"
    fi
    
    # Test live market data feed
    print_info "Testing live market data feed..."
    live_data=$(curl -s http://localhost:8000/api/v1/market-data/live/BTC-USDT 2>/dev/null)
    
    if [ $? -eq 0 ] && [ "$live_data" != "null" ]; then
        print_success "Live market data feed is working"
        echo "   Live data: $live_data"
    else
        print_warning "Live market data feed not available"
    fi
    
    echo ""
}

# Test autonomous trading activity
test_trading_activity() {
    print_header "💰 Autonomous Trading Activity Tests"
    
    # Check recent trades
    print_info "Checking recent trading activity..."
    trades_response=$(curl -s http://localhost:8000/api/v1/trading/recent?limit=10 2>/dev/null)
    
    if [ $? -eq 0 ] && [ "$trades_response" != "[]" ] && [ "$trades_response" != "null" ]; then
        print_success "Recent trading activity found"
        trade_count=$(echo "$trades_response" | jq length 2>/dev/null || echo "0")
        print_info "Found $trade_count recent trades"
        
        # Show trade summary
        echo "   Recent trades: $trades_response"
    else
        print_warning "No recent trading activity found"
        print_info "This could mean:"
        print_info "  - System is in paper trading mode"
        print_info "  - No trading signals generated yet"
        print_info "  - Trading engine not started"
        print_info "  - Insufficient balance or risk limits"
    fi
    
    # Check portfolio status
    print_info "Checking portfolio status..."
    portfolio_response=$(curl -s http://localhost:8000/api/v1/portfolio/status 2>/dev/null)
    
    if [ $? -eq 0 ] && [ "$portfolio_response" != "null" ]; then
        print_success "Portfolio status available"
        echo "   Portfolio: $portfolio_response"
    else
        print_warning "Portfolio status not available"
    fi
    
    echo ""
}

# Test system monitoring
test_system_monitoring() {
    print_header "📈 System Monitoring Tests"
    
    # Check system metrics
    print_info "Checking system performance metrics..."
    metrics_response=$(curl -s http://localhost:8000/api/v1/monitoring/metrics 2>/dev/null)
    
    if [ $? -eq 0 ] && [ "$metrics_response" != "null" ]; then
        print_success "System metrics available"
        echo "   Metrics: $metrics_response"
    else
        print_warning "System metrics not available"
    fi
    
    # Check logs for autonomous activity
    print_info "Checking recent logs for autonomous activity..."
    if [ -f "backend/logs/app.log" ]; then
        recent_logs=$(tail -20 backend/logs/app.log | grep -i "signal\|trade\|autonomous\|delta\|openai" || echo "No relevant logs found")
        if [ "$recent_logs" != "No relevant logs found" ]; then
            print_success "Found autonomous activity in logs"
            echo "   Recent activity:"
            echo "$recent_logs" | sed 's/^/     /'
        else
            print_warning "No autonomous activity found in recent logs"
        fi
    else
        print_warning "Log file not found at backend/logs/app.log"
    fi
    
    echo ""
}

# Test configuration
test_configuration() {
    print_header "⚙️  Configuration Tests"
    
    # Check if API keys are configured
    print_info "Checking API key configuration..."
    
    if [ -f "backend/.env.local" ]; then
        print_success "Environment file found"
        
        # Check for placeholder values
        if grep -q "your-testnet-api-key" backend/.env.local; then
            print_warning "Delta Exchange API key appears to be placeholder"
            print_info "Update DELTA_EXCHANGE_API_KEY in backend/.env.local"
        else
            print_success "Delta Exchange API key appears to be configured"
        fi
        
        if grep -q "your-openai-api-key" backend/.env.local; then
            print_warning "OpenAI API key appears to be placeholder"
            print_info "Update OPENAI_API_KEY in backend/.env.local"
        else
            print_success "OpenAI API key appears to be configured"
        fi
    else
        print_error "Environment file not found at backend/.env.local"
        print_info "Run the deployment script to create configuration"
    fi
    
    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}"
    echo "🚀 Crypto-0DTE Autonomous Trading System Validation"
    echo "=================================================="
    echo -e "${NC}"
    echo "This script validates that your autonomous trading system is working correctly."
    echo "The system should be:"
    echo "  • Connecting to Delta Exchange for market data"
    echo "  • Using OpenAI for signal generation"
    echo "  • Automatically generating trading signals"
    echo "  • Executing trades autonomously"
    echo ""
    
    # Run all tests
    test_configuration
    test_api_connectivity
    test_market_data
    test_signal_generation
    test_trading_activity
    test_system_monitoring
    
    # Summary
    print_header "📋 Validation Summary"
    print_info "Validation completed. Review the results above."
    print_info ""
    print_info "🔧 If you see warnings or errors:"
    print_info "  1. Ensure API keys are properly configured in backend/.env.local"
    print_info "  2. Check that both backend and frontend are running"
    print_info "  3. Verify database and Redis are accessible"
    print_info "  4. Allow time for the system to start autonomous operations"
    print_info ""
    print_info "🎯 For a fully autonomous system, you should see:"
    print_info "  • Market data being ingested regularly"
    print_info "  • Signals being generated automatically"
    print_info "  • Trading activity (if enabled and funded)"
    print_info "  • System metrics and monitoring data"
    echo ""
}

# Run the validation
main "$@"

