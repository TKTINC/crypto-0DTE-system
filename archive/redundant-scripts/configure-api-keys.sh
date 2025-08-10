#!/bin/bash

# Crypto-0DTE API Keys Configuration Helper
# ========================================
# Helps configure API keys for autonomous trading

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

ENV_FILE="backend/.env.local"

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
    echo -e "${CYAN}ℹ️  $1${NC}"
}

check_current_config() {
    print_header "🔍 Current API Configuration"
    
    if [ ! -f "$ENV_FILE" ]; then
        print_error "Environment file not found: $ENV_FILE"
        print_info "Run the deployment script first to create the environment file"
        return 1
    fi
    
    print_success "Environment file found: $ENV_FILE"
    echo ""
    
    # Check Delta Exchange configuration
    print_info "Delta Exchange Configuration:"
    local delta_key=$(grep "DELTA_EXCHANGE_API_KEY=" "$ENV_FILE" | cut -d'=' -f2)
    local delta_secret=$(grep "DELTA_EXCHANGE_API_SECRET=" "$ENV_FILE" | cut -d'=' -f2)
    local delta_url=$(grep "DELTA_EXCHANGE_BASE_URL=" "$ENV_FILE" | cut -d'=' -f2)
    
    if [ "$delta_key" = "your-testnet-api-key" ] || [ "$delta_key" = "" ]; then
        print_warning "Delta Exchange API Key: Not configured (placeholder value)"
    else
        print_success "Delta Exchange API Key: Configured (${delta_key:0:8}...)"
    fi
    
    if [ "$delta_secret" = "your-testnet-api-secret" ] || [ "$delta_secret" = "" ]; then
        print_warning "Delta Exchange API Secret: Not configured (placeholder value)"
    else
        print_success "Delta Exchange API Secret: Configured (${delta_secret:0:8}...)"
    fi
    
    print_info "Delta Exchange URL: $delta_url"
    echo ""
    
    # Check OpenAI configuration
    print_info "OpenAI Configuration:"
    local openai_key=$(grep "OPENAI_API_KEY=" "$ENV_FILE" | cut -d'=' -f2)
    local openai_base=$(grep "OPENAI_API_BASE=" "$ENV_FILE" | cut -d'=' -f2)
    
    if [ "$openai_key" = "your-openai-api-key" ] || [ "$openai_key" = "" ]; then
        print_warning "OpenAI API Key: Not configured (placeholder value)"
    else
        print_success "OpenAI API Key: Configured (${openai_key:0:8}...)"
    fi
    
    print_info "OpenAI Base URL: $openai_base"
    echo ""
}

configure_delta_exchange() {
    print_header "🔧 Configure Delta Exchange API"
    
    print_info "Delta Exchange is used for:"
    print_info "  • Real-time market data"
    print_info "  • Order execution"
    print_info "  • Portfolio management"
    echo ""
    
    print_info "To get Delta Exchange API credentials:"
    print_info "  1. Go to https://testnet.delta.exchange/"
    print_info "  2. Create an account or log in"
    print_info "  3. Navigate to API Management"
    print_info "  4. Create a new API key with trading permissions"
    print_info "  5. Copy the API Key and Secret"
    echo ""
    
    read -p "Do you want to configure Delta Exchange API now? (y/n): " configure_delta
    
    if [ "$configure_delta" = "y" ] || [ "$configure_delta" = "Y" ]; then
        echo ""
        read -p "Enter your Delta Exchange API Key: " delta_api_key
        read -s -p "Enter your Delta Exchange API Secret: " delta_api_secret
        echo ""
        
        if [ "$delta_api_key" != "" ] && [ "$delta_api_secret" != "" ]; then
            # Update the environment file
            sed -i.bak "s/DELTA_EXCHANGE_API_KEY=.*/DELTA_EXCHANGE_API_KEY=$delta_api_key/" "$ENV_FILE"
            sed -i.bak "s/DELTA_EXCHANGE_API_SECRET=.*/DELTA_EXCHANGE_API_SECRET=$delta_api_secret/" "$ENV_FILE"
            
            print_success "Delta Exchange API credentials updated"
        else
            print_warning "API credentials not provided, skipping configuration"
        fi
    fi
    echo ""
}

configure_openai() {
    print_header "🔧 Configure OpenAI API"
    
    print_info "OpenAI is used for:"
    print_info "  • AI-powered signal generation"
    print_info "  • Market sentiment analysis"
    print_info "  • Trading strategy optimization"
    echo ""
    
    print_info "To get OpenAI API credentials:"
    print_info "  1. Go to https://platform.openai.com/api-keys"
    print_info "  2. Create an account or log in"
    print_info "  3. Create a new secret key"
    print_info "  4. Copy the API key (starts with sk-)"
    echo ""
    
    read -p "Do you want to configure OpenAI API now? (y/n): " configure_openai
    
    if [ "$configure_openai" = "y" ] || [ "$configure_openai" = "Y" ]; then
        echo ""
        read -s -p "Enter your OpenAI API Key: " openai_api_key
        echo ""
        
        if [ "$openai_api_key" != "" ]; then
            # Update the environment file
            sed -i.bak "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$openai_api_key/" "$ENV_FILE"
            
            print_success "OpenAI API credentials updated"
        else
            print_warning "API key not provided, skipping configuration"
        fi
    fi
    echo ""
}

test_api_connections() {
    print_header "🧪 Test API Connections"
    
    print_info "Testing API connections with configured credentials..."
    echo ""
    
    # Test if backend is running
    if ! curl -s http://localhost:8000/health >/dev/null 2>&1; then
        print_warning "Backend is not running. Start it to test API connections:"
        print_info "  cd backend && python -m app.main"
        return 1
    fi
    
    # Test Delta Exchange
    print_info "Testing Delta Exchange connection..."
    local delta_test=$(curl -s http://localhost:8000/api/v1/market-data/test-connection 2>/dev/null)
    if [ $? -eq 0 ] && [ "$delta_test" != "null" ]; then
        print_success "Delta Exchange connection successful"
        echo "   Response: $delta_test"
    else
        print_warning "Delta Exchange connection failed or endpoint not available"
    fi
    
    # Test OpenAI
    print_info "Testing OpenAI connection..."
    local openai_test=$(curl -s http://localhost:8000/api/v1/signals/test-ai-connection 2>/dev/null)
    if [ $? -eq 0 ] && [ "$openai_test" != "null" ]; then
        print_success "OpenAI connection successful"
        echo "   Response: $openai_test"
    else
        print_warning "OpenAI connection failed or endpoint not available"
    fi
    
    echo ""
}

restart_backend() {
    print_header "🔄 Restart Backend"
    
    print_info "After updating API keys, you need to restart the backend for changes to take effect."
    echo ""
    
    read -p "Do you want to restart the backend now? (y/n): " restart_backend
    
    if [ "$restart_backend" = "y" ] || [ "$restart_backend" = "Y" ]; then
        print_info "Stopping existing backend processes..."
        
        # Kill all Python backend processes more thoroughly
        pkill -f "python.*app.main" 2>/dev/null || true
        pkill -f "uvicorn" 2>/dev/null || true
        
        # Wait longer for processes to terminate
        sleep 5
        
        # Force kill any remaining processes on port 8000
        local pids=$(lsof -ti:8000 2>/dev/null || true)
        if [ ! -z "$pids" ]; then
            print_info "Force killing remaining processes on port 8000..."
            echo "$pids" | xargs kill -9 2>/dev/null || true
            sleep 2
        fi
        
        # Verify port 8000 is free
        if lsof -i:8000 >/dev/null 2>&1; then
            print_error "Port 8000 is still in use. Please manually kill processes and try again."
            print_info "Check processes: lsof -i:8000"
            return 1
        fi
        
        print_info "Starting backend..."
        cd backend
        nohup python -m app.main > ../logs/backend.log 2>&1 &
        BACKEND_PID=$!
        cd ..
        
        print_success "Backend restarted with PID: $BACKEND_PID"
        print_info "Waiting for backend to be ready..."
        
        # Wait for backend to start
        for i in {1..30}; do
            if curl -s http://localhost:8000/health >/dev/null 2>&1; then
                print_success "Backend is ready!"
                
                # Verify only one process is running
                local process_count=$(lsof -ti:8000 2>/dev/null | wc -l)
                if [ "$process_count" -eq 1 ]; then
                    print_success "Single backend process confirmed"
                else
                    print_warning "Multiple processes detected on port 8000: $process_count"
                fi
                break
            fi
            sleep 1
        done
    fi
    echo ""
}

main() {
    echo -e "${BLUE}"
    echo "🔑 Crypto-0DTE API Keys Configuration"
    echo "===================================="
    echo -e "${NC}"
    echo "This standalone utility allows you to update API keys for an existing deployment."
    echo "For new deployments, use the integrated deployment script instead:"
    echo "  ./deploy-local-without-docker-macos.sh"
    echo ""
    
    # Check if backend directory exists
    if [ ! -d "backend" ]; then
        print_error "Backend directory not found. Please run this script from the project root."
        exit 1
    fi
    
    # Check if .env.local exists
    if [ ! -f "backend/.env.local" ]; then
        print_error "Backend .env.local file not found. Please run the deployment script first:"
        print_info "  ./deploy-local-without-docker-macos.sh"
        exit 1
    fi
    
    # Check current configuration
    check_current_config
    
    # Configure APIs
    configure_delta_exchange
    configure_openai
    
    # Test connections
    test_api_connections
    
    # Final summary
    print_header "📋 Configuration Summary"
    print_success "API keys have been updated in backend/.env.local"
    print_info ""
    print_info "To apply the changes, restart your backend service:"
    print_info "  1. Stop current backend: pkill -f 'python.*app.main'"
    print_info "  2. Start backend: cd backend && python -m app.main"
    print_info "  3. Or redeploy: ./deploy-local-without-docker-macos.sh"
    print_info ""
    print_info "Next steps after restart:"
    print_info "  • Run: ./validate-autonomous-system.sh"
    print_info "  • Run: ./monitor-autonomous-trading.sh"
    print_info "  • Check the frontend at: http://localhost:3000"
    echo ""
}

# Run the configuration
main "$@"

