#!/bin/bash
# Crypto-0DTE System - Deployment Utilities
# Enhanced error handling, validation, and monitoring functions

# ============================================================================
# ADVANCED ERROR HANDLING
# ============================================================================

# Enhanced error handler with context
handle_error() {
    local exit_code=$?
    local line_number=$1
    local command="$2"
    local function_name="${FUNCNAME[2]:-main}"
    
    echo ""
    error "💥 DEPLOYMENT FAILED"
    echo "============================================================"
    echo "Exit Code: $exit_code"
    echo "Function: $function_name"
    echo "Line: $line_number"
    echo "Command: $command"
    echo "Time: $(date)"
    echo "============================================================"
    
    # Capture system state for debugging
    capture_debug_info
    
    # Run cleanup
    cleanup_on_failure
}

# Set up enhanced error trapping
setup_error_handling() {
    set -eE  # Exit on error and inherit ERR trap
    trap 'handle_error ${LINENO} "$BASH_COMMAND"' ERR
}

# Capture debug information on failure
capture_debug_info() {
    local debug_file="$LOG_DIR/debug-$(date +%Y%m%d-%H%M%S).log"
    
    {
        echo "=== SYSTEM DEBUG INFO ==="
        echo "Date: $(date)"
        echo "User: $(whoami)"
        echo "PWD: $(pwd)"
        echo "OS: $(uname -a)"
        echo ""
        
        echo "=== PROCESS INFO ==="
        ps aux | grep -E "(python|node|postgres|redis)" | grep -v grep || true
        echo ""
        
        echo "=== PORT STATUS ==="
        lsof -i :8000 || echo "Port 8000: Not in use"
        lsof -i :3000 || echo "Port 3000: Not in use"
        lsof -i :5432 || echo "Port 5432: Not in use"
        lsof -i :6379 || echo "Port 6379: Not in use"
        echo ""
        
        echo "=== DISK SPACE ==="
        df -h
        echo ""
        
        echo "=== MEMORY USAGE ==="
        free -h 2>/dev/null || vm_stat
        echo ""
        
        echo "=== RECENT LOGS ==="
        if [[ -f "$LOG_DIR/backend.log" ]]; then
            echo "--- Backend Log (last 20 lines) ---"
            tail -20 "$LOG_DIR/backend.log"
        fi
        
        if [[ -f "$LOG_DIR/frontend.log" ]]; then
            echo "--- Frontend Log (last 20 lines) ---"
            tail -20 "$LOG_DIR/frontend.log"
        fi
        
    } > "$debug_file"
    
    warning "Debug information saved to: $debug_file"
}

# ============================================================================
# ENHANCED VALIDATION FUNCTIONS
# ============================================================================

# Validate environment variables with detailed feedback
validate_env_vars() {
    step "Validating environment variables..."
    
    local required_vars=(
        "DELTA_TESTNET_API_KEY:Delta Exchange testnet API key"
        "DELTA_TESTNET_API_SECRET:Delta Exchange testnet API secret"
    )
    
    local optional_vars=(
        "OPENAI_API_KEY:OpenAI API key for AI features"
        "OPENAI_API_BASE:OpenAI API base URL"
    )
    
    local missing_required=()
    local missing_optional=()
    
    # Check required variables
    for var_info in "${required_vars[@]}"; do
        local var_name="${var_info%%:*}"
        local var_desc="${var_info##*:}"
        
        if [[ -z "${!var_name:-}" ]]; then
            missing_required+=("$var_name ($var_desc)")
        else
            success "$var_name is set"
        fi
    done
    
    # Check optional variables
    for var_info in "${optional_vars[@]}"; do
        local var_name="${var_info%%:*}"
        local var_desc="${var_info##*:}"
        
        if [[ -z "${!var_name:-}" ]]; then
            missing_optional+=("$var_name ($var_desc)")
        else
            success "$var_name is set"
        fi
    done
    
    # Report missing required variables
    if [[ ${#missing_required[@]} -gt 0 ]]; then
        error "Missing required environment variables:"
        for var in "${missing_required[@]}"; do
            echo "  ❌ $var"
        done
        echo ""
        info "Set these variables and run the script again:"
        echo "  export DELTA_TESTNET_API_KEY='your_testnet_api_key'"
        echo "  export DELTA_TESTNET_API_SECRET='your_testnet_api_secret'"
        return 1
    fi
    
    # Report missing optional variables
    if [[ ${#missing_optional[@]} -gt 0 ]]; then
        warning "Missing optional environment variables:"
        for var in "${missing_optional[@]}"; do
            echo "  ⚠️  $var"
        done
        info "These are optional but recommended for full functionality"
    fi
    
    return 0
}

# Validate API keys format and basic connectivity
validate_api_keys() {
    step "Validating API key format and connectivity..."
    
    # Check API key format (basic validation)
    if [[ ${#DELTA_TESTNET_API_KEY} -lt 10 ]]; then
        error "DELTA_TESTNET_API_KEY appears to be too short (${#DELTA_TESTNET_API_KEY} characters)"
        return 1
    fi
    
    if [[ ${#DELTA_TESTNET_API_SECRET} -lt 20 ]]; then
        error "DELTA_TESTNET_API_SECRET appears to be too short (${#DELTA_TESTNET_API_SECRET} characters)"
        return 1
    fi
    
    success "API key format validation passed"
    
    # Test basic connectivity to Delta Exchange testnet
    info "Testing connectivity to Delta Exchange testnet..."
    if curl -s --max-time 10 "https://cdn-ind.testnet.deltaex.org/time" >/dev/null; then
        success "Delta Exchange testnet is reachable"
    else
        warning "Could not reach Delta Exchange testnet (network issue or service down)"
        info "Deployment will continue, but API calls may fail"
    fi
    
    return 0
}

# Comprehensive system health check
system_health_check() {
    step "Performing comprehensive system health check..."
    
    local health_issues=()
    
    # Check disk space (need at least 1GB free)
    local available_space
    available_space=$(df . | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 1048576 ]]; then  # 1GB in KB
        health_issues+=("Low disk space: $(df -h . | awk 'NR==2 {print $4}') available")
    fi
    
    # Check memory (need at least 2GB total)
    if command_exists free; then
        local total_mem
        total_mem=$(free -m | awk 'NR==2{print $2}')
        if [[ $total_mem -lt 2048 ]]; then
            health_issues+=("Low memory: ${total_mem}MB total")
        fi
    fi
    
    # Check for conflicting processes
    if pgrep -f "python.*app.main" >/dev/null; then
        health_issues+=("Existing backend process detected")
    fi
    
    if pgrep -f "node.*react-scripts" >/dev/null; then
        health_issues+=("Existing frontend process detected")
    fi
    
    # Report health issues
    if [[ ${#health_issues[@]} -gt 0 ]]; then
        warning "System health issues detected:"
        for issue in "${health_issues[@]}"; do
            echo "  ⚠️  $issue"
        done
        
        # Ask user if they want to continue
        echo ""
        read -p "Continue deployment despite health issues? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "Deployment cancelled by user"
            exit 0
        fi
    else
        success "System health check passed"
    fi
    
    return 0
}

# ============================================================================
# ENHANCED SERVICE MONITORING
# ============================================================================

# Monitor service startup with detailed feedback
monitor_service_startup() {
    local service_name="$1"
    local port="$2"
    local log_file="$3"
    local max_attempts=60  # 2 minutes
    local attempt=1
    
    step "Monitoring $service_name startup..."
    
    while [ $attempt -le $max_attempts ]; do
        # Check if port is in use
        if ! port_available "$port"; then
            success "$service_name is ready on port $port"
            return 0
        fi
        
        # Check for errors in log file
        if [[ -f "$log_file" ]]; then
            local recent_errors
            recent_errors=$(tail -10 "$log_file" | grep -i "error\|exception\|failed" | tail -3)
            if [[ -n "$recent_errors" ]]; then
                warning "Recent errors in $service_name log:"
                echo "$recent_errors" | sed 's/^/    /'
            fi
        fi
        
        # Progress indicator
        case $((attempt % 4)) in
            1) echo -n "🔄 " ;;
            2) echo -n "⏳ " ;;
            3) echo -n "🔄 " ;;
            0) echo -n "⏳ " ;;
        esac
        
        sleep 2
        ((attempt++))
    done
    
    error "$service_name failed to start within $((max_attempts * 2)) seconds"
    
    # Show recent log entries for debugging
    if [[ -f "$log_file" ]]; then
        error "Recent log entries from $service_name:"
        tail -20 "$log_file" | sed 's/^/    /'
    fi
    
    return 1
}

# ============================================================================
# DEPLOYMENT STATE MANAGEMENT
# ============================================================================

# Check if deployment step was already completed
step_completed() {
    local step_name="$1"
    [[ -f "$DEPLOYMENT_STATE_FILE" ]] && grep -q "^$step_name$" "$DEPLOYMENT_STATE_FILE"
}

# Skip step if already completed
skip_if_completed() {
    local step_name="$1"
    local step_description="$2"
    
    if step_completed "$step_name"; then
        success "$step_description (already completed)"
        return 0
    else
        return 1
    fi
}

# ============================================================================
# INTERACTIVE FEATURES
# ============================================================================

# Interactive confirmation for destructive operations
confirm_destructive_operation() {
    local operation="$1"
    local details="$2"
    
    warning "Destructive operation: $operation"
    if [[ -n "$details" ]]; then
        echo "Details: $details"
    fi
    echo ""
    
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "Operation cancelled by user"
        return 1
    fi
    
    return 0
}

# Show deployment progress
show_progress() {
    local current_step="$1"
    local total_steps="$2"
    local step_name="$3"
    
    local progress=$((current_step * 100 / total_steps))
    local bar_length=30
    local filled_length=$((progress * bar_length / 100))
    
    printf "\r["
    printf "%*s" $filled_length | tr ' ' '█'
    printf "%*s" $((bar_length - filled_length)) | tr ' ' '░'
    printf "] %d%% - %s" $progress "$step_name"
    
    if [[ $current_step -eq $total_steps ]]; then
        echo ""  # New line when complete
    fi
}

# ============================================================================
# CLEANUP UTILITIES
# ============================================================================

# Graceful service shutdown
graceful_shutdown() {
    local service_name="$1"
    local pid_file="$2"
    local max_wait=10
    
    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        
        if kill -0 "$pid" 2>/dev/null; then
            info "Gracefully shutting down $service_name (PID: $pid)..."
            kill -TERM "$pid"
            
            # Wait for graceful shutdown
            local wait_count=0
            while kill -0 "$pid" 2>/dev/null && [[ $wait_count -lt $max_wait ]]; do
                sleep 1
                ((wait_count++))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                warning "Force killing $service_name (PID: $pid)..."
                kill -KILL "$pid"
            fi
            
            success "$service_name shutdown complete"
        fi
        
        rm -f "$pid_file"
    fi
}

# Complete system cleanup
complete_cleanup() {
    step "Performing complete system cleanup..."
    
    # Shutdown services gracefully
    graceful_shutdown "Backend" "$LOG_DIR/backend.pid"
    graceful_shutdown "Frontend" "$LOG_DIR/frontend.pid"
    
    # Kill any remaining processes
    pkill -f "python.*app.main" 2>/dev/null || true
    pkill -f "node.*react-scripts" 2>/dev/null || true
    pkill -f "uvicorn" 2>/dev/null || true
    
    # Clean up temporary files
    rm -f "$LOG_DIR"/*.pid 2>/dev/null || true
    
    success "System cleanup complete"
}

# ============================================================================
# UTILITY EXPORTS
# ============================================================================

# Export functions for use in main deployment script
export -f handle_error
export -f setup_error_handling
export -f capture_debug_info
export -f validate_env_vars
export -f validate_api_keys
export -f system_health_check
export -f monitor_service_startup
export -f step_completed
export -f skip_if_completed
export -f confirm_destructive_operation
export -f show_progress
export -f graceful_shutdown
export -f complete_cleanup

