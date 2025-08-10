#!/bin/bash
# Crypto-0DTE System - Configuration Management
# Handles environment setup, API key validation, and configuration generation

# ============================================================================
# CONFIGURATION TEMPLATES
# ============================================================================

# Generate backend environment configuration
generate_backend_config() {
    local env_file="$BACKEND_DIR/.env.local"
    local temp_file="$env_file.tmp"
    
    step "Generating backend configuration..."
    
    # Validate required variables
    validate_env_vars || return 1
    validate_api_keys || return 1
    
    # Generate JWT secret if not provided
    local jwt_secret
    jwt_secret=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Generate app secret if not provided
    local app_secret
    app_secret=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Create configuration file
    cat > "$temp_file" << EOF
# Crypto-0DTE System Backend Configuration
# Auto-generated: $(date)
# Environment: Testnet (Paper Trading)

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DATABASE_URL=postgresql://$(whoami)@localhost:5432/crypto_0dte

# ============================================================================
# REDIS CONFIGURATION
# ============================================================================
REDIS_URL=redis://localhost:6379/0

# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================
ENVIRONMENT=testnet
DEBUG=false
JWT_SECRET_KEY=$jwt_secret
API_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================
HOST=0.0.0.0
PORT=8000
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# ============================================================================
# DELTA EXCHANGE CONFIGURATION
# ============================================================================

# Production API Keys (for live trading - NOT USED in testnet mode)
DELTA_API_KEY=
DELTA_API_SECRET=
DELTA_API_PASSPHRASE=

# Testnet API Keys (for paper trading - CURRENTLY ACTIVE)
DELTA_TESTNET_API_KEY=$DELTA_TESTNET_API_KEY
DELTA_TESTNET_API_SECRET=$DELTA_TESTNET_API_SECRET
DELTA_TESTNET_PASSPHRASE=${DELTA_TESTNET_PASSPHRASE:-}

# ============================================================================
# ENVIRONMENT SWITCHING
# ============================================================================
PAPER_TRADING=true
DELTA_EXCHANGE_TESTNET=true

# ============================================================================
# OPENAI CONFIGURATION
# ============================================================================
OPENAI_API_KEY=${OPENAI_API_KEY:-}
OPENAI_API_BASE=${OPENAI_API_BASE:-https://api.openai.com/v1}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================
SECRET_KEY=$app_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ============================================================================
# FEATURE FLAGS
# ============================================================================
ENABLE_AUTONOMOUS_TRADING=true
ENABLE_RISK_MANAGEMENT=true
ENABLE_POSITION_MANAGEMENT=true
ENABLE_SIGNAL_GENERATION=true

# ============================================================================
# PERFORMANCE CONFIGURATION
# ============================================================================
MAX_WORKERS=4
WORKER_TIMEOUT=30
KEEP_ALIVE=2

# ============================================================================
# MONITORING CONFIGURATION
# ============================================================================
ENABLE_METRICS=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30
EOF

    # Validate configuration file
    if [[ -s "$temp_file" ]]; then
        mv "$temp_file" "$env_file"
        success "Backend configuration generated: $env_file"
        
        # Show configuration summary
        info "Configuration Summary:"
        echo "  Environment: testnet (paper trading)"
        echo "  Database: crypto_0dte"
        echo "  API Keys: Testnet keys configured"
        echo "  Server: localhost:8000"
        echo "  CORS: localhost:3000 allowed"
        
        return 0
    else
        error "Failed to generate backend configuration"
        rm -f "$temp_file"
        return 1
    fi
}

# Generate frontend environment configuration
generate_frontend_config() {
    local env_file="$FRONTEND_DIR/.env.local"
    local temp_file="$env_file.tmp"
    
    step "Generating frontend configuration..."
    
    cat > "$temp_file" << EOF
# Crypto-0DTE System Frontend Configuration
# Auto-generated: $(date)
# Environment: Testnet (Paper Trading)

# ============================================================================
# API CONFIGURATION
# ============================================================================
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_BASE_URL=ws://localhost:8000

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================
REACT_APP_ENVIRONMENT=testnet
REACT_APP_PAPER_TRADING=true
REACT_APP_DEBUG=false

# ============================================================================
# FEATURE FLAGS
# ============================================================================
REACT_APP_ENABLE_AUTONOMOUS_TRADING=true
REACT_APP_ENABLE_LIVE_TRADING=false
REACT_APP_ENABLE_ADVANCED_CHARTS=true
REACT_APP_ENABLE_NOTIFICATIONS=true

# ============================================================================
# UI CONFIGURATION
# ============================================================================
REACT_APP_THEME=dark
REACT_APP_REFRESH_INTERVAL=5000
REACT_APP_CHART_UPDATE_INTERVAL=1000

# ============================================================================
# DELTA EXCHANGE CONFIGURATION
# ============================================================================
REACT_APP_EXCHANGE_NAME=Delta Exchange
REACT_APP_EXCHANGE_ENV=testnet
REACT_APP_BASE_CURRENCY=USDT

# ============================================================================
# DEVELOPMENT CONFIGURATION
# ============================================================================
GENERATE_SOURCEMAP=false
DISABLE_ESLINT_PLUGIN=true
FAST_REFRESH=true
EOF

    # Validate configuration file
    if [[ -s "$temp_file" ]]; then
        mv "$temp_file" "$env_file"
        success "Frontend configuration generated: $env_file"
        
        # Show configuration summary
        info "Configuration Summary:"
        echo "  API URL: http://localhost:8000"
        echo "  Environment: testnet"
        echo "  Paper Trading: enabled"
        echo "  Theme: dark"
        
        return 0
    else
        error "Failed to generate frontend configuration"
        rm -f "$temp_file"
        return 1
    fi
}

# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

# Validate backend configuration
validate_backend_config() {
    local env_file="$BACKEND_DIR/.env.local"
    
    step "Validating backend configuration..."
    
    if [[ ! -f "$env_file" ]]; then
        error "Backend configuration file not found: $env_file"
        return 1
    fi
    
    # Check required variables in config file
    local required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
        "DELTA_TESTNET_API_KEY"
        "DELTA_TESTNET_API_SECRET"
        "JWT_SECRET_KEY"
        "SECRET_KEY"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" "$env_file" || grep -q "^$var=$" "$env_file"; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing or empty configuration variables:"
        for var in "${missing_vars[@]}"; do
            echo "  ❌ $var"
        done
        return 1
    fi
    
    success "Backend configuration validation passed"
    return 0
}

# Validate frontend configuration
validate_frontend_config() {
    local env_file="$FRONTEND_DIR/.env.local"
    
    step "Validating frontend configuration..."
    
    if [[ ! -f "$env_file" ]]; then
        error "Frontend configuration file not found: $env_file"
        return 1
    fi
    
    # Check required variables in config file
    local required_vars=(
        "REACT_APP_API_BASE_URL"
        "REACT_APP_ENVIRONMENT"
        "REACT_APP_PAPER_TRADING"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" "$env_file" || grep -q "^$var=$" "$env_file"; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing or empty configuration variables:"
        for var in "${missing_vars[@]}"; do
            echo "  ❌ $var"
        done
        return 1
    fi
    
    success "Frontend configuration validation passed"
    return 0
}

# ============================================================================
# CONFIGURATION BACKUP & RESTORE
# ============================================================================

# Backup existing configuration
backup_existing_config() {
    local backup_dir="$LOG_DIR/config-backup-$(date +%Y%m%d-%H%M%S)"
    
    step "Backing up existing configuration..."
    
    mkdir -p "$backup_dir"
    
    # Backup backend config
    if [[ -f "$BACKEND_DIR/.env.local" ]]; then
        cp "$BACKEND_DIR/.env.local" "$backup_dir/backend.env.local"
        info "Backend config backed up"
    fi
    
    # Backup frontend config
    if [[ -f "$FRONTEND_DIR/.env.local" ]]; then
        cp "$FRONTEND_DIR/.env.local" "$backup_dir/frontend.env.local"
        info "Frontend config backed up"
    fi
    
    # Backup database config if exists
    if [[ -f "$BACKEND_DIR/alembic.ini" ]]; then
        cp "$BACKEND_DIR/alembic.ini" "$backup_dir/alembic.ini"
        info "Database config backed up"
    fi
    
    success "Configuration backup saved to: $backup_dir"
    echo "$backup_dir" > "$LOG_DIR/last-config-backup.txt"
}

# Restore configuration from backup
restore_config_from_backup() {
    local backup_dir="$1"
    
    if [[ -z "$backup_dir" && -f "$LOG_DIR/last-config-backup.txt" ]]; then
        backup_dir=$(cat "$LOG_DIR/last-config-backup.txt")
    fi
    
    if [[ ! -d "$backup_dir" ]]; then
        error "Backup directory not found: $backup_dir"
        return 1
    fi
    
    step "Restoring configuration from backup..."
    
    # Restore backend config
    if [[ -f "$backup_dir/backend.env.local" ]]; then
        cp "$backup_dir/backend.env.local" "$BACKEND_DIR/.env.local"
        info "Backend config restored"
    fi
    
    # Restore frontend config
    if [[ -f "$backup_dir/frontend.env.local" ]]; then
        cp "$backup_dir/frontend.env.local" "$FRONTEND_DIR/.env.local"
        info "Frontend config restored"
    fi
    
    # Restore database config
    if [[ -f "$backup_dir/alembic.ini" ]]; then
        cp "$backup_dir/alembic.ini" "$BACKEND_DIR/alembic.ini"
        info "Database config restored"
    fi
    
    success "Configuration restored from: $backup_dir"
}

# ============================================================================
# CONFIGURATION MANAGEMENT MAIN FUNCTION
# ============================================================================

setup_all_configuration() {
    step "Setting up complete system configuration..."
    
    # Backup existing configuration
    backup_existing_config
    
    # Generate new configuration
    generate_backend_config || return 1
    generate_frontend_config || return 1
    
    # Validate generated configuration
    validate_backend_config || return 1
    validate_frontend_config || return 1
    
    success "Complete system configuration setup completed"
    
    # Show configuration files
    info "Configuration files created:"
    echo "  Backend: $BACKEND_DIR/.env.local"
    echo "  Frontend: $FRONTEND_DIR/.env.local"
    echo "  Backup: $(cat "$LOG_DIR/last-config-backup.txt" 2>/dev/null || echo "None")"
    
    return 0
}

# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

export -f generate_backend_config
export -f generate_frontend_config
export -f validate_backend_config
export -f validate_frontend_config
export -f backup_existing_config
export -f restore_config_from_backup
export -f setup_all_configuration

