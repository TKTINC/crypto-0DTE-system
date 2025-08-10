#!/bin/bash
# Crypto-0DTE System - Environment Variable Setup
# Creates permanent environment variable configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔑 Crypto-0DTE System - Environment Setup${NC}"
echo "=============================================="
echo "This script will set up permanent environment variables"
echo "for your crypto trading system."
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
        # Use a temporary file for safe editing
        local temp_file=$(mktemp)
        grep -v "^export $var_name=" "$profile_file" > "$temp_file"
        mv "$temp_file" "$profile_file"
        print_info "Updated existing $var_name in $profile_file"
    else
        print_info "Adding new $var_name to $profile_file"
    fi
    
    # Add the new variable
    echo "export $var_name=\"$var_value\"" >> "$profile_file"
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

# Main setup function
setup_environment_variables() {
    local profile_file
    profile_file=$(detect_shell_profile)
    
    print_info "Detected shell: $(basename "$SHELL")"
    print_info "Profile file: $profile_file"
    echo ""
    
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
    
    local delta_testnet_secret
    delta_testnet_secret=$(prompt_for_variable "DELTA_TESTNET_API_SECRET" "Delta Exchange testnet API secret for paper trading" "true")
    add_var_to_profile "DELTA_TESTNET_API_SECRET" "$delta_testnet_secret" "$profile_file"
    
    echo ""
    echo -e "${YELLOW}📋 Optional Variables:${NC}"
    
    # Delta Exchange Live API Keys (Optional - for future live trading)
    echo ""
    read -p "Do you want to set up live trading API keys? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        local delta_live_key
        delta_live_key=$(prompt_for_variable "DELTA_API_KEY" "Delta Exchange live API key for real trading" "true")
        add_var_to_profile "DELTA_API_KEY" "$delta_live_key" "$profile_file"
        
        local delta_live_secret
        delta_live_secret=$(prompt_for_variable "DELTA_API_SECRET" "Delta Exchange live API secret for real trading" "true")
        add_var_to_profile "DELTA_API_SECRET" "$delta_live_secret" "$profile_file"
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
        else
            add_var_to_profile "OPENAI_API_BASE" "https://api.openai.com/v1" "$profile_file"
        fi
    else
        print_info "Skipping OpenAI API keys (can be added later)"
    fi
    
    # Add crypto trading system section header
    echo "" >> "$profile_file"
    echo "# Crypto-0DTE Trading System Environment Variables" >> "$profile_file"
    echo "# Added by setup-env.sh on $(date)" >> "$profile_file"
    
    print_status "Environment variables added to $profile_file"
}

# Validate setup
validate_setup() {
    local profile_file
    profile_file=$(detect_shell_profile)
    
    echo ""
    echo -e "${BLUE}🔍 Validating setup...${NC}"
    
    # Source the profile to test
    if source "$profile_file" 2>/dev/null; then
        print_status "Profile file loads successfully"
    else
        print_error "Profile file has syntax errors"
        return 1
    fi
    
    # Check required variables
    if [[ -n "${DELTA_TESTNET_API_KEY:-}" && -n "${DELTA_TESTNET_API_SECRET:-}" ]]; then
        print_status "Required Delta Exchange testnet keys are set"
    else
        print_error "Required Delta Exchange testnet keys are missing"
        return 1
    fi
    
    # Check optional variables
    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
        print_status "OpenAI API key is set"
    else
        print_info "OpenAI API key not set (optional)"
    fi
    
    if [[ -n "${DELTA_API_KEY:-}" ]]; then
        print_status "Delta Exchange live API key is set"
    else
        print_info "Delta Exchange live API key not set (optional)"
    fi
    
    return 0
}

# Show next steps
show_next_steps() {
    local profile_file
    profile_file=$(detect_shell_profile)
    
    echo ""
    echo "=============================================="
    print_status "🎉 Environment Setup Complete!"
    echo "=============================================="
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
    print_info "To verify environment variables:"
    echo "  echo \$DELTA_TESTNET_API_KEY"
    echo "  echo \$OPENAI_API_KEY"
    echo ""
    print_info "Environment variables are now permanent and will be"
    print_info "available in all new terminal sessions."
}

# Main execution
main() {
    echo "This script will set up permanent environment variables for:"
    echo "  • Delta Exchange API keys (testnet and optionally live)"
    echo "  • OpenAI API keys (optional)"
    echo ""
    echo "These will be added to your shell profile and persist across sessions."
    echo ""
    
    read -p "Continue with environment setup? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "Environment setup cancelled"
        exit 0
    fi
    
    setup_environment_variables
    
    if validate_setup; then
        show_next_steps
    else
        print_error "Setup validation failed. Please check your configuration."
        exit 1
    fi
}

# Run main function
main "$@"

