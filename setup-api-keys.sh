#!/bin/bash

# Crypto-0DTE System API Keys Setup
# =================================
# One-time setup script for configuring API keys persistently

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$PROJECT_ROOT/config"
CONFIG_FILE="$CONFIG_DIR/api-keys.conf"

# Helper functions
print_header() {
    echo -e "${BLUE}$1${NC}"
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

# Create config directory if it doesn't exist
setup_config_directory() {
    if [ ! -d "$CONFIG_DIR" ]; then
        mkdir -p "$CONFIG_DIR"
        chmod 700 "$CONFIG_DIR"
        print_success "Created secure config directory"
    fi
}

# Load existing configuration
load_existing_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
        return 0
    else
        return 1
    fi
}

# Save configuration to file
save_config() {
    cat > "$CONFIG_FILE" << EOF
# Crypto-0DTE System API Keys Configuration
# ==========================================
# This file stores your API keys persistently and is not committed to git.
# Edit this file to update your API credentials.

# Delta Exchange Configuration (Testnet)
# Get your credentials at: https://testnet.delta.exchange/
DELTA_EXCHANGE_API_KEY=$DELTA_EXCHANGE_API_KEY
DELTA_EXCHANGE_API_SECRET=$DELTA_EXCHANGE_API_SECRET

# OpenAI Configuration
# Get your API key at: https://platform.openai.com/api-keys
OPENAI_API_KEY=$OPENAI_API_KEY

# Configuration Status
# Set to 'true' when you have configured real API keys
DELTA_CONFIGURED=$DELTA_CONFIGURED
OPENAI_CONFIGURED=$OPENAI_CONFIGURED

# Last Updated
LAST_UPDATED=$(date '+%Y-%m-%d %H:%M:%S')
EOF
    chmod 600 "$CONFIG_FILE"
    print_success "Configuration saved to $CONFIG_FILE"
}

# Configure Delta Exchange
configure_delta_exchange() {
    print_header "🏦 Delta Exchange API Configuration"
    echo "-----------------------------------"
    print_info "Delta Exchange provides cryptocurrency trading and market data."
    print_info "For testnet trading, create an account at: https://testnet.delta.exchange/"
    echo ""
    
    if [ "$DELTA_CONFIGURED" = "true" ] && [ "$DELTA_EXCHANGE_API_KEY" != "your-testnet-api-key" ]; then
        print_info "Current Delta Exchange API Key: ${DELTA_EXCHANGE_API_KEY:0:10}..."
        read -p "Do you want to update Delta Exchange credentials? (y/n): " update_delta
        if [ "$update_delta" != "y" ] && [ "$update_delta" != "Y" ]; then
            return 0
        fi
    fi
    
    read -p "Do you have Delta Exchange testnet API credentials? (y/n): " has_delta_keys
    
    if [ "$has_delta_keys" = "y" ] || [ "$has_delta_keys" = "Y" ]; then
        echo ""
        print_info "Please enter your Delta Exchange testnet API credentials:"
        read -p "API Key: " delta_api_key
        read -s -p "API Secret: " delta_api_secret
        echo ""
        
        if [ ! -z "$delta_api_key" ] && [ ! -z "$delta_api_secret" ]; then
            DELTA_EXCHANGE_API_KEY="$delta_api_key"
            DELTA_EXCHANGE_API_SECRET="$delta_api_secret"
            DELTA_CONFIGURED=true
            print_success "Delta Exchange API credentials configured"
        else
            print_warning "Empty credentials provided, keeping existing values"
        fi
    else
        print_info "Keeping placeholder values. Configure later by running this script again."
        DELTA_EXCHANGE_API_KEY="your-testnet-api-key"
        DELTA_EXCHANGE_API_SECRET="your-testnet-api-secret"
        DELTA_CONFIGURED=false
    fi
}

# Configure OpenAI
configure_openai() {
    print_header "🧠 OpenAI API Configuration"
    echo "-----------------------------"
    print_info "OpenAI API is used for AI-powered trading signal generation."
    print_info "Get your API key at: https://platform.openai.com/api-keys"
    echo ""
    
    if [ "$OPENAI_CONFIGURED" = "true" ] && [ "$OPENAI_API_KEY" != "your-openai-api-key" ]; then
        print_info "Current OpenAI API Key: ${OPENAI_API_KEY:0:10}..."
        read -p "Do you want to update OpenAI API key? (y/n): " update_openai
        if [ "$update_openai" != "y" ] && [ "$update_openai" != "Y" ]; then
            return 0
        fi
    fi
    
    read -p "Do you have an OpenAI API key? (y/n): " has_openai_key
    
    if [ "$has_openai_key" = "y" ] || [ "$has_openai_key" = "Y" ]; then
        echo ""
        print_info "Please enter your OpenAI API key:"
        read -s -p "OpenAI API Key (starts with sk-): " openai_api_key
        echo ""
        
        if [ ! -z "$openai_api_key" ]; then
            OPENAI_API_KEY="$openai_api_key"
            OPENAI_CONFIGURED=true
            print_success "OpenAI API key configured"
        else
            print_warning "Empty API key provided, keeping existing value"
        fi
    else
        print_info "Keeping placeholder value. Configure later by running this script again."
        OPENAI_API_KEY="your-openai-api-key"
        OPENAI_CONFIGURED=false
    fi
}

# Display configuration summary
show_summary() {
    print_header "📋 Configuration Summary"
    echo ""
    
    if [ "$DELTA_CONFIGURED" = "true" ]; then
        print_success "✓ Delta Exchange API: Configured"
    else
        print_warning "⚠ Delta Exchange API: Using placeholder"
    fi
    
    if [ "$OPENAI_CONFIGURED" = "true" ]; then
        print_success "✓ OpenAI API: Configured"
    else
        print_warning "⚠ OpenAI API: Using placeholder"
    fi
    
    echo ""
    print_info "Configuration file: $CONFIG_FILE"
    print_info "To update keys later, run: ./setup-api-keys.sh"
    print_info "To deploy system, run: ./deploy-local-without-docker-macos.sh"
}

# Main function
main() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                    🔑 Crypto-0DTE API Keys Setup                            ║"
    echo "║                        One-time Configuration                               ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    
    setup_config_directory
    
    # Load existing configuration or set defaults
    if load_existing_config; then
        print_info "Loaded existing configuration from $CONFIG_FILE"
    else
        print_info "Creating new configuration file"
        # Set defaults
        DELTA_EXCHANGE_API_KEY="your-testnet-api-key"
        DELTA_EXCHANGE_API_SECRET="your-testnet-api-secret"
        OPENAI_API_KEY="your-openai-api-key"
        DELTA_CONFIGURED=false
        OPENAI_CONFIGURED=false
    fi
    
    echo ""
    configure_delta_exchange
    echo ""
    configure_openai
    echo ""
    save_config
    echo ""
    show_summary
    echo ""
}

# Run main function
main "$@"

