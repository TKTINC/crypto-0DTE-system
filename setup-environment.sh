#!/bin/bash
# Crypto-0DTE System - Unified Environment Setup
# ==============================================
# Consolidates functionality from setup-api-keys.sh, setup-env.sh, and configure-api-keys.sh
# One script to handle all environment configuration needs

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

echo -e "${BLUE}🔑 Crypto-0DTE System - Environment Setup${NC}"
echo "=============================================="
echo "Unified setup for all environment configuration"
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
        # Update existing
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/^$var_name=.*/$var_name=$var_value/" "$CONFIG_FILE"
        else
            sed -i "s/^$var_name=.*/$var_name=$var_value/" "$CONFIG_FILE"
        fi
        print_info "Updated $var_name in config file"
    else
        # Add new
        echo "$var_name=$var_value" >> "$CONFIG_FILE"
        print_info "Added $var_name to config file"
    fi
}

# Prompt for variable value
prompt_for_variable() {
    local var_name="$1"
    local var_description="$2"
    local current_value="${!var_name:-}"
    local is_secret="$3"
    
    echo ""
    echo -e "${BLUE}Setting up: $var_name${NC}"
    echo "Description: $var_description"
    
    if [[ -n "$current_value" ]]; then
        if [[ "$is_secret" == "true" ]]; then
            echo "Current value: ****** (${#current_value} characters)"
        else
            echo "Current value: $current_value"
        fi
        echo ""
        read -p "Keep current value? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            current_value=""
        else
            echo "$current_value"
            return 0
        fi
    fi
    
    while [[ -z "$current_value" ]]; do
        if [[ "$is_secret" == "true" ]]; then
            read -s -p "Enter $var_name: " current_value
            echo
        else
            read -p "Enter $var_name: " current_value
        fi
        
        if [[ -z "$current_value" ]]; then
            print_warning "Value cannot be empty. Please try again."
        fi
    done
    
    echo "$current_value"
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

# Setup environment variables
setup_environment_variables() {
    local profile_file
    profile_file=$(detect_shell_profile)
    
    print_header "🔧 Environment Variable Setup"
    print_info "Detected shell: $(basename "$SHELL")"
    print_info "Profile file: $profile_file"
    
    # Backup existing profile
    if [[ -f "$profile_file" ]]; then
        local backup_file="${profile_file}.backup-$(date +%Y%m%d-%H%M%S)"
        cp "$profile_file" "$backup_file"
        print_info "Backed up existing profile to: $backup_file"
    fi
    
    echo ""
    echo -e "${YELLOW}📋 Required Variables:${NC}"
    
    # Delta Exchange Testnet API Keys (Required)
    local delta_testnet_key
    delta_testnet_key=$(prompt_for_variable "DELTA_TESTNET_API_KEY" "Delta Exchange testnet API key for paper trading" "true")
    add_var_to_profile "DELTA_TESTNET_API_KEY" "$delta_testnet_key" "$profile_file"
    update_config_file "DELTA_TESTNET_API_KEY" "$delta_testnet_key"
    
    local delta_testnet_secret
    delta_testnet_secret=$(prompt_for_variable "DELTA_TESTNET_API_SECRET" "Delta Exchange testnet API secret for paper trading" "true")
    add_var_to_profile "DELTA_TESTNET_API_SECRET" "$delta_testnet_secret" "$profile_file"
    update_config_file "DELTA_TESTNET_API_SECRET" "$delta_testnet_secret"
    
    echo ""
    echo -e "${YELLOW}📋 Optional Variables:${NC}"
    
    # Delta Exchange Live API Keys (Optional)
    echo ""
    read -p "Do you want to set up live trading API keys? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        local delta_live_key
        delta_live_key=$(prompt_for_variable "DELTA_API_KEY" "Delta Exchange live API key for real trading" "true")
        add_var_to_profile "DELTA_API_KEY" "$delta_live_key" "$profile_file"
        update_config_file "DELTA_API_KEY" "$delta_live_key"
        
        local delta_live_secret
        delta_live_secret=$(prompt_for_variable "DELTA_API_SECRET" "Delta Exchange live API secret for real trading" "true")
        add_var_to_profile "DELTA_API_SECRET" "$delta_live_secret" "$profile_file"
        update_config_file "DELTA_API_SECRET" "$delta_live_secret"
    else
        print_info "Skipping live trading API keys (can be added later)"
    fi
    
    # OpenAI API Keys (Optional)
    echo ""
    read -p "Do you want to set up OpenAI API keys for AI features? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        local openai_key
        openai_key=$(prompt_for_variable "OPENAI_API_KEY" "OpenAI API key for AI-powered trading features" "true")
        add_var_to_profile "OPENAI_API_KEY" "$openai_key" "$profile_file"
        update_config_file "OPENAI_API_KEY" "$openai_key"
        
        # Check if user wants custom OpenAI base URL
        local current_openai_base="${OPENAI_API_BASE:-https://api.openai.com/v1}"
        echo ""
        echo "OpenAI API Base URL (current: $current_openai_base)"
        read -p "Use custom OpenAI API base URL? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            local openai_base
            openai_base=$(prompt_for_variable "OPENAI_API_BASE" "OpenAI API base URL" "false")
            add_var_to_profile "OPENAI_API_BASE" "$openai_base" "$profile_file"
            update_config_file "OPENAI_API_BASE" "$openai_base"
        else
            add_var_to_profile "OPENAI_API_BASE" "https://api.openai.com/v1" "$profile_file"
            update_config_file "OPENAI_API_BASE" "https://api.openai.com/v1"
        fi
    else
        print_info "Skipping OpenAI API keys (can be added later)"
    fi
    
    print_success "Environment variables configured successfully"
}

# Generate backend environment file
generate_backend_env() {
    print_header "🔧 Backend Environment File Generation"
    
    # Load current config
    load_existing_config
    
    # Create backend directory if it doesn't exist
    mkdir -p "$(dirname "$ENV_FILE")"
    
    # Generate .env.local file
    cat > "$ENV_FILE" << EOF
# Crypto-0DTE System Backend Environment
# Generated by setup-environment.sh on $(date)

# Environment Configuration
ENVIRONMENT=testnet

# Delta Exchange API Configuration
DELTA_TESTNET_API_KEY=${DELTA_TESTNET_API_KEY:-}
DELTA_TESTNET_API_SECRET=${DELTA_TESTNET_API_SECRET:-}
DELTA_API_KEY=${DELTA_API_KEY:-}
DELTA_API_SECRET=${DELTA_API_SECRET:-}

# OpenAI Configuration
OPENAI_API_KEY=${OPENAI_API_KEY:-}
OPENAI_API_BASE=${OPENAI_API_BASE:-https://api.openai.com/v1}

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/crypto_trading

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Logging Configuration
LOG_LEVEL=INFO
EOF
    
    print_success "Backend environment file generated: $ENV_FILE"
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
    load_existing_config
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
        load_existing_config
        check_current_config
        exit 0
    fi
    
    echo "This script will set up your complete environment for the crypto trading system:"
    echo "  • Delta Exchange API keys (testnet and optionally live)"
    echo "  • OpenAI API keys (optional)"
    echo "  • Shell profile integration (permanent)"
    echo "  • Configuration file management"
    echo "  • Backend environment file generation"
    echo ""
    
    read -p "Continue with environment setup? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "Environment setup cancelled"
        exit 0
    fi
    
    setup_config_directory
    load_existing_config
    check_current_config
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

