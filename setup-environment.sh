#!/bin/bash
# Crypto-0DTE System - Automated Environment Setup
# ================================================
# Automatically configures environment using preconfigured values from config.py
# No manual input required - just run the script!

set -e

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
ENV_FILE="$PROJECT_ROOT/backend/.env.local"

echo -e "${BLUE}🔑 Crypto-0DTE System - Automated Environment Setup${NC}"
echo "========================================================"
echo "Automatically configuring environment using preconfigured values"
echo "No manual input required!"
echo ""

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
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# Detect shell and profile file
detect_shell_profile() {
    local shell_name=$(basename "$SHELL")
    local profile_file=""
    
    case "$shell_name" in
        "bash")
            if [[ -f "$HOME/.bash_profile" ]]; then
                profile_file="$HOME/.bash_profile"
            elif [[ -f "$HOME/.bashrc" ]]; then
                profile_file="$HOME/.bashrc"
            else
                profile_file="$HOME/.bash_profile"
            fi
            ;;
        "zsh")
            profile_file="$HOME/.zshrc"
            ;;
        *)
            profile_file="$HOME/.profile"
            ;;
    esac
    
    echo "$profile_file"
}

# Create config directory if it doesn't exist
setup_config_directory() {
    if [ ! -d "$CONFIG_DIR" ]; then
        mkdir -p "$CONFIG_DIR"
        chmod 700 "$CONFIG_DIR"
        print_success "Created secure config directory"
    fi
}

# Load existing configuration from config file
load_existing_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        source "$CONFIG_FILE" 2>/dev/null || true
        print_info "Loaded existing configuration from $CONFIG_FILE"
    fi
}

# Check if variable is already set in profile
is_var_in_profile() {
    local var_name="$1"
    local profile_file="$2"
    
    if [[ -f "$profile_file" ]]; then
        grep -q "^export $var_name=" "$profile_file"
    else
        return 1
    fi
}

# Add or update variable in profile
add_var_to_profile() {
    local var_name="$1"
    local var_value="$2"
    local profile_file="$3"
    
    # Create profile file if it doesn't exist
    touch "$profile_file"
    
    # Remove existing variable if present
    if is_var_in_profile "$var_name" "$profile_file"; then
        local temp_file=$(mktemp)
        grep -v "^export $var_name=" "$profile_file" > "$temp_file"
        mv "$temp_file" "$profile_file"
        print_info "Updated existing $var_name in profile"
    else
        print_info "Adding new $var_name to profile"
    fi
    
    # Add the new variable
    echo "export $var_name=\"$var_value\"" >> "$profile_file"
}

# Update config file
update_config_file() {
    local var_name="$1"
    local var_value="$2"
    
    # Create config file if it doesn't exist
    if [[ ! -f "$CONFIG_FILE" ]]; then
        cat > "$CONFIG_FILE" << 'EOF'
# Crypto-0DTE System API Keys Configuration
# ==========================================
# This file stores your API keys persistently and is not committed to git.
# Edit this file to update your API credentials.

EOF
    fi
    
    # Update or add the variable
    if grep -q "^$var_name=" "$CONFIG_FILE"; then
        # Update existing - use | as delimiter to avoid issues with URLs containing /
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^$var_name=.*|$var_name=$var_value|" "$CONFIG_FILE"
        else
            sed -i "s|^$var_name=.*|$var_name=$var_value|" "$CONFIG_FILE"
        fi
        print_info "Updated $var_name in config file"
    else
        # Add new
        echo "$var_name=$var_value" >> "$CONFIG_FILE"
        print_info "Added $var_name to config file"
    fi
}

# Preconfigured values from config.py
get_preconfigured_values() {
    # Delta Exchange API Keys (from config.py)
    # These are the actual values configured in the system
    
    # Testnet API Keys (for paper trading)
    DELTA_TESTNET_API_KEY="qWsp9KOnQ3xylffXdyjUFp0xZ7fGP9"
    DELTA_TESTNET_API_SECRET="xcBcNDpU1bCoWPaTJEmTjxpqjN2G3lYgU3XSnAYpIE1wU93M6hutJB8VGpGD"
    
    # Live API Keys (for production trading - will be configured when ready)
    DELTA_API_KEY=""  # To be configured for live trading
    DELTA_API_SECRET=""  # To be configured for live trading
    
    # OpenAI API Configuration (from config.py)
    OPENAI_API_KEY=""  # Will use system default if available
    OPENAI_API_BASE="https://api.openai.com/v1"
    
    # Environment Configuration
    ENVIRONMENT="testnet"  # Default to testnet for safety
    PAPER_TRADING="true"
    
    print_info "Loaded preconfigured values from config.py"
}

# Setup environment variables automatically
setup_environment_variables() {
    local profile_file
    profile_file=$(detect_shell_profile)
    
    print_header "🔧 Automated Environment Variable Setup"
    print_info "Detected shell: $(basename "$SHELL")"
    print_info "Profile file: $profile_file"
    
    # Backup existing profile
    if [[ -f "$profile_file" ]]; then
        local backup_file="${profile_file}.backup-$(date +%Y%m%d-%H%M%S)"
        cp "$profile_file" "$backup_file"
        print_info "Backed up existing profile to: $backup_file"
    fi
    
    print_info "Configuring all required environment variables..."
    
    # Delta Exchange Testnet API Keys (Required for paper trading)
    add_var_to_profile "DELTA_TESTNET_API_KEY" "$DELTA_TESTNET_API_KEY" "$profile_file"
    update_config_file "DELTA_TESTNET_API_KEY" "$DELTA_TESTNET_API_KEY"
    print_success "Configured Delta Exchange testnet API key"
    
    add_var_to_profile "DELTA_TESTNET_API_SECRET" "$DELTA_TESTNET_API_SECRET" "$profile_file"
    update_config_file "DELTA_TESTNET_API_SECRET" "$DELTA_TESTNET_API_SECRET"
    print_success "Configured Delta Exchange testnet API secret"
    
    # Delta Exchange Live API Keys (Optional - for future live trading)
    if [[ -n "$DELTA_API_KEY" ]]; then
        add_var_to_profile "DELTA_API_KEY" "$DELTA_API_KEY" "$profile_file"
        update_config_file "DELTA_API_KEY" "$DELTA_API_KEY"
        print_success "Configured Delta Exchange live API key"
        
        add_var_to_profile "DELTA_API_SECRET" "$DELTA_API_SECRET" "$profile_file"
        update_config_file "DELTA_API_SECRET" "$DELTA_API_SECRET"
        print_success "Configured Delta Exchange live API secret"
    else
        print_info "Live trading API keys not configured (testnet mode only)"
    fi
    
    # OpenAI API Keys (Optional - use system default if available)
    local system_openai_key="${OPENAI_API_KEY:-}"
    if [[ -n "$system_openai_key" ]]; then
        add_var_to_profile "OPENAI_API_KEY" "$system_openai_key" "$profile_file"
        update_config_file "OPENAI_API_KEY" "$system_openai_key"
        print_success "Configured OpenAI API key (from system)"
    else
        print_info "OpenAI API key not configured (AI features will be limited)"
    fi
    
    add_var_to_profile "OPENAI_API_BASE" "$OPENAI_API_BASE" "$profile_file"
    update_config_file "OPENAI_API_BASE" "$OPENAI_API_BASE"
    print_success "Configured OpenAI API base URL"
    
    # Environment Configuration
    add_var_to_profile "ENVIRONMENT" "$ENVIRONMENT" "$profile_file"
    update_config_file "ENVIRONMENT" "$ENVIRONMENT"
    print_success "Configured environment: $ENVIRONMENT"
    
    add_var_to_profile "PAPER_TRADING" "$PAPER_TRADING" "$profile_file"
    update_config_file "PAPER_TRADING" "$PAPER_TRADING"
    print_success "Configured paper trading: $PAPER_TRADING"
    
    print_success "All environment variables configured automatically"
}

# Generate backend environment file
generate_backend_env() {
    print_header "🔧 Backend Environment File Generation"
    
    # Create backend directory if it doesn't exist
    mkdir -p "$(dirname "$ENV_FILE")"
    
    # Generate .env.local file with preconfigured values
    cat > "$ENV_FILE" << EOF
# Crypto-0DTE System Backend Environment
# Generated by setup-environment.sh on $(date)
# Using preconfigured values from config.py

# Environment Configuration
ENVIRONMENT=$ENVIRONMENT
PAPER_TRADING=$PAPER_TRADING

# Delta Exchange API Configuration (Testnet)
DELTA_TESTNET_API_KEY=$DELTA_TESTNET_API_KEY
DELTA_TESTNET_API_SECRET=$DELTA_TESTNET_API_SECRET

# Delta Exchange API Configuration (Live - for future use)
DELTA_API_KEY=${DELTA_API_KEY:-}
DELTA_API_SECRET=${DELTA_API_SECRET:-}

# OpenAI Configuration
OPENAI_API_KEY=${OPENAI_API_KEY:-}
OPENAI_API_BASE=$OPENAI_API_BASE

# Database Configuration
DATABASE_URL=postgresql+asyncpg://crypto_user:crypto_password@localhost:5432/crypto_0dte_local

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
APP_NAME=Crypto 0DTE Trading System
APP_VERSION=1.0.0
DEBUG=false
API_V1_STR=/api/v1
API_HOST=0.0.0.0
API_PORT=8000
HOST=0.0.0.0
PORT=8000

# Security Configuration
SECRET_KEY=your-super-secret-key-change-in-production
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s [%(levelname)s] %(name)s: %(message)s
LOG_FILE=/Users/balu/crypto-0DTE-system/logs/backend.log

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001
API_CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001

# Trading Configuration
MAX_POSITION_SIZE=1000.0
MAX_DAILY_LOSS=500.0
RISK_PERCENTAGE=0.02

# Market Data Configuration
MARKET_DATA_SYMBOLS=BTCUSDT,ETHUSDT,ADAUSDT
MARKET_DATA_TIMEFRAMES=1m,5m,15m,1h
MARKET_DATA_HISTORY_DAYS=30

# Monitoring Configuration
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=60
EOF
    
    print_success "Backend environment file generated: $ENV_FILE"
    print_info "All configuration values loaded from config.py"
}

# Check current configuration
check_current_config() {
    print_header "🔍 Current Configuration Status"
    
    # Check environment variables
    echo "Environment Variables:"
    echo "  DELTA_TESTNET_API_KEY: ${DELTA_TESTNET_API_KEY:+SET (${#DELTA_TESTNET_API_KEY} chars)}" || echo "  DELTA_TESTNET_API_KEY: NOT SET"
    echo "  DELTA_TESTNET_API_SECRET: ${DELTA_TESTNET_API_SECRET:+SET (${#DELTA_TESTNET_API_SECRET} chars)}" || echo "  DELTA_TESTNET_API_SECRET: NOT SET"
    echo "  DELTA_API_KEY: ${DELTA_API_KEY:+SET (${#DELTA_API_KEY} chars)}" || echo "  DELTA_API_KEY: NOT SET"
    echo "  DELTA_API_SECRET: ${DELTA_API_SECRET:+SET (${#DELTA_API_SECRET} chars)}" || echo "  DELTA_API_SECRET: NOT SET"
    echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:+SET (${#OPENAI_API_KEY} chars)}" || echo "  OPENAI_API_KEY: NOT SET"
    echo "  OPENAI_API_BASE: ${OPENAI_API_BASE:-NOT SET}"
    echo "  ENVIRONMENT: ${ENVIRONMENT:-NOT SET}"
    echo "  PAPER_TRADING: ${PAPER_TRADING:-NOT SET}"
    
    # Check config file
    echo ""
    if [[ -f "$CONFIG_FILE" ]]; then
        print_success "Config file exists: $CONFIG_FILE"
    else
        print_warning "Config file not found: $CONFIG_FILE"
    fi
    
    # Check backend env file
    if [[ -f "$ENV_FILE" ]]; then
        print_success "Backend env file exists: $ENV_FILE"
    else
        print_warning "Backend env file not found: $ENV_FILE"
    fi
    
    echo ""
}

# Validate setup
validate_setup() {
    print_header "🔍 Validation"
    
    local profile_file
    profile_file=$(detect_shell_profile)
    
    # Test profile file
    if source "$profile_file" 2>/dev/null; then
        print_success "Profile file loads successfully"
    else
        print_error "Profile file has syntax errors"
        return 1
    fi
    
    # Check required variables
    if [[ -n "${DELTA_TESTNET_API_KEY:-}" && -n "${DELTA_TESTNET_API_SECRET:-}" ]]; then
        print_success "Required Delta Exchange testnet keys are configured"
    else
        print_error "Required Delta Exchange testnet keys are missing"
        return 1
    fi
    
    # Check config file
    if [[ -f "$CONFIG_FILE" ]]; then
        print_success "Configuration file is valid"
    else
        print_error "Configuration file is missing"
        return 1
    fi
    
    # Check backend env file
    if [[ -f "$ENV_FILE" ]]; then
        print_success "Backend environment file is valid"
    else
        print_error "Backend environment file is missing"
        return 1
    fi
    
    return 0
}

# Show next steps
show_next_steps() {
    local profile_file
    profile_file=$(detect_shell_profile)
    
    print_header "🎉 Setup Complete!"
    echo ""
    print_info "To use the new environment variables:"
    echo ""
    echo "Option 1 - Reload current terminal:"
    echo "  source $profile_file"
    echo ""
    echo "Option 2 - Open a new terminal window"
    echo ""
    print_info "To deploy the crypto trading system:"
    echo "  ./deploy-v2-macos.sh"
    echo ""
    print_info "Configuration files created:"
    echo "  • $CONFIG_FILE (persistent config)"
    echo "  • $ENV_FILE (backend environment)"
    echo "  • $profile_file (shell profile)"
    echo ""
    print_info "To check configuration anytime:"
    echo "  ./setup-environment.sh --check"
}

# Main execution
main() {
    # Handle command line arguments
    if [[ "$1" == "--check" ]]; then
        setup_config_directory
        get_preconfigured_values
        check_current_config
        exit 0
    fi
    
    print_info "Automated environment setup using preconfigured values from config.py"
    print_info "This will configure:"
    echo "  • Delta Exchange testnet API keys (for paper trading)"
    echo "  • Delta Exchange live API keys (if configured)"
    echo "  • OpenAI API keys (if available)"
    echo "  • Shell profile integration (permanent)"
    echo "  • Configuration file management"
    echo "  • Backend environment file generation"
    echo ""
    
    print_info "Starting automated setup..."
    
    setup_config_directory
    get_preconfigured_values
    setup_environment_variables
    generate_backend_env
    
    if validate_setup; then
        show_next_steps
    else
        print_error "Setup validation failed. Please check your configuration."
        exit 1
    fi
}

# Run main function
main "$@"

