#!/bin/bash

# Crypto-0DTE Autonomous Trading System Monitor
# ============================================
# Continuously monitors the autonomous trading system activity

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
MONITOR_INTERVAL=30  # seconds between checks
LOG_FILE="autonomous_monitor.log"

# Helper functions
timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

log_message() {
    echo "$(timestamp) - $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    log_message "SUCCESS: $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    log_message "WARNING: $1"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    log_message "ERROR: $1"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# Monitor functions
check_system_health() {
    local health_response=$(curl -s http://localhost:8000/health 2>/dev/null)
    if [ $? -eq 0 ] && [ "$health_response" != "" ]; then
        local status=$(echo "$health_response" | jq -r '.status' 2>/dev/null || echo "unknown")
        if [ "$status" = "healthy" ]; then
            print_success "System health: $status"
            return 0
        else
            print_warning "System health: $status"
            return 1
        fi
    else
        print_error "System health check failed - backend not responding"
        return 1
    fi
}

check_market_data_flow() {
    local market_data=$(curl -s http://localhost:8000/api/v1/market-data/recent?symbol=BTC-USDT&limit=1 2>/dev/null)
    if [ $? -eq 0 ] && [ "$market_data" != "[]" ] && [ "$market_data" != "null" ]; then
        local timestamp=$(echo "$market_data" | jq -r '.[0].timestamp' 2>/dev/null || echo "unknown")
        print_success "Market data flowing - Latest: $timestamp"
        return 0
    else
        print_warning "No recent market data found"
        return 1
    fi
}

check_signal_generation() {
    local signals=$(curl -s http://localhost:8000/api/v1/signals/recent?limit=1 2>/dev/null)
    if [ $? -eq 0 ] && [ "$signals" != "[]" ] && [ "$signals" != "null" ]; then
        local signal_count=$(echo "$signals" | jq length 2>/dev/null || echo "0")
        local latest_signal=$(echo "$signals" | jq -r '.[0].created_at' 2>/dev/null || echo "unknown")
        print_success "Signal generation active - Latest: $latest_signal"
        return 0
    else
        print_warning "No recent signals generated"
        return 1
    fi
}

check_trading_activity() {
    local trades=$(curl -s http://localhost:8000/api/v1/trading/recent?limit=1 2>/dev/null)
    if [ $? -eq 0 ] && [ "$trades" != "[]" ] && [ "$trades" != "null" ]; then
        local trade_count=$(echo "$trades" | jq length 2>/dev/null || echo "0")
        local latest_trade=$(echo "$trades" | jq -r '.[0].timestamp' 2>/dev/null || echo "unknown")
        print_success "Trading activity detected - Latest: $latest_trade"
        return 0
    else
        print_info "No recent trading activity (normal for paper trading)"
        return 0
    fi
}

check_api_connections() {
    # Check Delta Exchange
    local delta_status=$(curl -s http://localhost:8000/api/v1/market-data/connection-status 2>/dev/null)
    if [ $? -eq 0 ] && [ "$delta_status" != "null" ]; then
        print_success "Delta Exchange connection active"
    else
        print_warning "Delta Exchange connection status unknown"
    fi
    
    # Check OpenAI
    local openai_status=$(curl -s http://localhost:8000/api/v1/signals/ai-status 2>/dev/null)
    if [ $? -eq 0 ] && [ "$openai_status" != "null" ]; then
        print_success "OpenAI connection active"
    else
        print_warning "OpenAI connection status unknown"
    fi
}

display_dashboard() {
    clear
    echo -e "${BLUE}"
    echo "🚀 Crypto-0DTE Autonomous Trading System Monitor"
    echo "==============================================="
    echo -e "${NC}"
    echo "📅 $(timestamp)"
    echo "🔄 Monitoring every $MONITOR_INTERVAL seconds (Press Ctrl+C to stop)"
    echo ""
    
    # System status
    print_header "🏥 System Health"
    check_system_health
    echo ""
    
    # Market data
    print_header "📊 Market Data Flow"
    check_market_data_flow
    echo ""
    
    # Signal generation
    print_header "🤖 AI Signal Generation"
    check_signal_generation
    echo ""
    
    # Trading activity
    print_header "💰 Trading Activity"
    check_trading_activity
    echo ""
    
    # API connections
    print_header "🌐 External API Connections"
    check_api_connections
    echo ""
    
    # Recent logs
    print_header "📝 Recent Activity (Last 5 log entries)"
    if [ -f "backend/logs/app.log" ]; then
        tail -5 backend/logs/app.log | grep -E "(signal|trade|market|delta|openai)" | tail -3 | sed 's/^/   /' || echo "   No recent autonomous activity in logs"
    else
        echo "   Log file not found"
    fi
    echo ""
    
    # Portfolio summary
    print_header "💼 Portfolio Summary"
    local portfolio=$(curl -s http://localhost:8000/api/v1/portfolio/summary 2>/dev/null)
    if [ $? -eq 0 ] && [ "$portfolio" != "null" ]; then
        echo "   $portfolio"
    else
        echo "   Portfolio data not available"
    fi
    echo ""
    
    print_info "Next check in $MONITOR_INTERVAL seconds..."
}

# Signal handlers
cleanup() {
    echo ""
    print_info "Monitoring stopped by user"
    log_message "Monitoring session ended"
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

# Main monitoring loop
main() {
    log_message "Starting autonomous trading system monitoring"
    
    while true; do
        display_dashboard
        sleep $MONITOR_INTERVAL
    done
}

# Check if backend is running before starting
if ! curl -s http://localhost:8000/health >/dev/null 2>&1; then
    print_error "Backend is not running on localhost:8000"
    print_info "Please start the backend first:"
    print_info "  cd backend && python -m app.main"
    exit 1
fi

# Start monitoring
main "$@"

