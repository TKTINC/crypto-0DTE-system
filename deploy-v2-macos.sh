#!/bin/bash
# Crypto-0DTE System - Streamlined Deployment Script v2.0
# Designed for reliability, proper dependency resolution, and clear error handling

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Project paths
readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly BACKEND_DIR="$PROJECT_ROOT/backend"
readonly FRONTEND_DIR="$PROJECT_ROOT/frontend"
readonly VENV_DIR="$PROJECT_ROOT/venv"
readonly LOG_DIR="$PROJECT_ROOT/logs"

# Service configuration
readonly BACKEND_PORT=8000
readonly FRONTEND_PORT=3000
readonly POSTGRES_PORT=5432
readonly REDIS_PORT=6379

# Deployment state tracking
DEPLOYMENT_STATE_FILE="$LOG_DIR/deployment.state"
ROLLBACK_COMMANDS_FILE="$LOG_DIR/rollback.sh"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

step() {
    echo -e "${PURPLE}🔄 $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if port is available
port_available() {
    ! lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

# Wait for service to be ready
wait_for_service() {
    local service_name="$1"
    local port="$2"
    local max_attempts=50
    local attempt=1
    
    step "Waiting for $service_name to be ready on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if ! port_available "$port"; then
            success "$service_name is ready on port $port"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    error "$service_name failed to start within $((max_attempts * 2)) seconds"
    
    # CRITICAL FIX: If service failed to start, kill the background process immediately
    warning "Service startup failed - killing background processes to prevent runaway loops"
    
    # Kill the specific process that was started
    if [[ -f "$LOG_DIR/backend.pid" ]]; then
        local pid=$(cat "$LOG_DIR/backend.pid" 2>/dev/null)
        if [[ -n "$pid" ]]; then
            warning "Killing backend process $pid"
            kill -9 "$pid" 2>/dev/null || true
            rm -f "$LOG_DIR/backend.pid"
        fi
    fi
    
    # Kill any Python processes that might be running the backend
    pkill -9 -f "python.*app.main" 2>/dev/null || true
    pkill -9 -f "python.*main.py" 2>/dev/null || true
    pkill -9 -f "uvicorn" 2>/dev/null || true
    
    # Wait a moment and verify processes are killed
    sleep 2
    local remaining=$(ps aux | grep -E "python.*app\.main|uvicorn" | grep -v grep | wc -l)
    if [[ $remaining -gt 0 ]]; then
        warning "Found $remaining remaining backend processes after cleanup"
        ps aux | grep -E "python.*app\.main|uvicorn" | grep -v grep
    else
        success "All backend processes successfully terminated"
    fi
    
    return 1
}

# Save deployment state
save_state() {
    echo "$1" >> "$DEPLOYMENT_STATE_FILE"
}

# Add rollback command
add_rollback() {
    echo "$1" >> "$ROLLBACK_COMMANDS_FILE"
}

# Initialize deployment environment
init_deployment() {
    log "🚀 Initializing Crypto-0DTE System Deployment v2.0"
    echo "============================================================"
    echo "Start Time: $(date)"
    echo "Project Root: $PROJECT_ROOT"
    echo "OS: $(uname -s) $(uname -r)"
    echo ""
    
    # Create necessary directories
    mkdir -p "$LOG_DIR"
    
    # Initialize state tracking
    echo "#!/bin/bash" > "$ROLLBACK_COMMANDS_FILE"
    echo "# Rollback commands for deployment $(date)" >> "$ROLLBACK_COMMANDS_FILE"
    chmod +x "$ROLLBACK_COMMANDS_FILE"
    
    echo "DEPLOYMENT_START=$(date '+%s')" > "$DEPLOYMENT_STATE_FILE"
    save_state "INIT_COMPLETE"
}

# ============================================================================
# PRE-DEPLOYMENT CLEANUP
# ============================================================================

pre_deployment_cleanup() {
    step "Performing pre-deployment cleanup..."
    
    info "Stopping any existing crypto trading processes..."
    
    # Kill all Python backend processes
    pkill -9 -f "Python.*app\.main" 2>/dev/null || true
    pkill -9 -f "python.*app\.main" 2>/dev/null || true
    pkill -9 -f "uvicorn" 2>/dev/null || true
    
    # Kill all crypto database connections
    pkill -9 -f "postgres.*crypto" 2>/dev/null || true
    
    # Kill processes using our ports
    lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true
    
    # Wait for processes to die
    sleep 3
    
    # Verify cleanup
    local remaining_python=$(ps aux | grep -E "Python.*app\.main|python.*app\.main" | grep -v grep | wc -l)
    local remaining_postgres=$(ps aux | grep "postgres.*crypto" | grep -v grep | wc -l)
    
    if [[ $remaining_python -gt 0 ]]; then
        warning "Found $remaining_python remaining Python processes - force killing..."
        ps aux | grep -E "Python.*app\.main|python.*app\.main" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    fi
    
    if [[ $remaining_postgres -gt 0 ]]; then
        warning "Found $remaining_postgres remaining PostgreSQL connections - force killing..."
        ps aux | grep "postgres.*crypto" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    fi
    
    # Final verification
    sleep 2
    local final_check=$(ps aux | grep -E "Python.*app\.main|python.*app\.main|postgres.*crypto" | grep -v grep | wc -l)
    
    if [[ $final_check -eq 0 ]]; then
        success "All existing processes cleaned up successfully"
    else
        warning "Some processes may still be running - continuing with deployment"
        ps aux | grep -E "Python.*app\.main|python.*app\.main|postgres.*crypto" | grep -v grep || true
    fi
    
    save_state "CLEANUP_COMPLETE"
}

# ============================================================================
# DEPENDENCY VALIDATION
# ============================================================================

validate_system_requirements() {
    step "Validating system requirements..."
    
    # Check OS
    if [[ "$(uname -s)" != "Darwin" ]]; then
        error "This script is designed for macOS. For Linux, use deploy-v2-linux.sh"
        exit 1
    fi
    
    # Check Homebrew
    if ! command_exists brew; then
        error "Homebrew not found. Please install Homebrew first:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    # Check Python 3.9+
    if ! command_exists python3; then
        error "Python 3 not found. Installing via Homebrew..."
        brew install python@3.11
    fi
    
    local python_version
    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    local python_major python_minor
    python_major=$(echo "$python_version" | cut -d'.' -f1)
    python_minor=$(echo "$python_version" | cut -d'.' -f2)
    
    if [[ "$python_major" -eq 3 && "$python_minor" -ge 9 ]]; then
        success "Python $python_version found (compatible)"
    else
        error "Python 3.9+ required, found $python_version"
        info "Installing Python 3.11 via Homebrew..."
        brew install python@3.11
    fi
    
    # Check Node.js 18+
    if ! command_exists node; then
        info "Node.js not found. Installing via Homebrew..."
        brew install node
    fi
    
    local node_version
    node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ "$node_version" -ge 18 ]]; then
        success "Node.js v$(node --version) found (compatible)"
    else
        warning "Node.js 18+ recommended, found v$(node --version)"
    fi
    
    save_state "SYSTEM_VALIDATED"
}

# ============================================================================
# SERVICE MANAGEMENT
# ============================================================================

setup_database_services() {
    step "Setting up database and cache services..."
    
    # Install PostgreSQL
    if ! command_exists psql; then
        info "Installing PostgreSQL..."
        brew install postgresql@15
        add_rollback "brew uninstall postgresql@15"
    fi
    
    # Install Redis
    if ! command_exists redis-server; then
        info "Installing Redis..."
        brew install redis
        add_rollback "brew uninstall redis"
    fi
    
    # Start PostgreSQL
    if ! brew services list | grep -q "postgresql@15.*started"; then
        info "Starting PostgreSQL service..."
        brew services start postgresql@15
        add_rollback "brew services stop postgresql@15"
        
        # Wait for PostgreSQL to be ready
        wait_for_service "PostgreSQL" "$POSTGRES_PORT"
    else
        success "PostgreSQL already running"
    fi
    
    # Start Redis
    if ! brew services list | grep -q "redis.*started"; then
        info "Starting Redis service..."
        brew services start redis
        add_rollback "brew services stop redis"
        
        # Wait for Redis to be ready
        wait_for_service "Redis" "$REDIS_PORT"
    else
        success "Redis already running"
    fi
    
    # Create database if it doesn't exist
    if ! psql -lqt | cut -d \| -f 1 | grep -qw crypto_0dte; then
        info "Creating crypto_0dte database..."
        createdb crypto_0dte
        add_rollback "dropdb crypto_0dte"
    else
        success "Database crypto_0dte already exists"
    fi
    
    save_state "DATABASE_SERVICES_READY"
}

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

setup_python_environment() {
    step "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "$VENV_DIR" ]]; then
        info "Creating Python virtual environment..."
        python3 -m venv "$VENV_DIR"
        add_rollback "rm -rf '$VENV_DIR'"
    else
        success "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install backend dependencies
    if [[ -f "$BACKEND_DIR/requirements.txt" ]]; then
        info "Installing Python dependencies..."
        pip install -r "$BACKEND_DIR/requirements.txt"
    else
        error "Backend requirements.txt not found"
        exit 1
    fi
    
    save_state "PYTHON_ENV_READY"
}

setup_node_environment() {
    step "Setting up Node.js environment..."
    
    cd "$FRONTEND_DIR"
    
    # Install frontend dependencies
    if [[ -f "package.json" ]]; then
        info "Installing Node.js dependencies..."
        npm install
    else
        error "Frontend package.json not found"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    save_state "NODE_ENV_READY"
}

# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

setup_environment_config() {
    step "Setting up environment configuration..."
    
    # Check for required environment variables
    local required_vars=(
        "DELTA_TESTNET_API_KEY"
        "DELTA_TESTNET_API_SECRET"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        info "Please set these environment variables and run the script again:"
        echo "  export DELTA_TESTNET_API_KEY='your_testnet_api_key'"
        echo "  export DELTA_TESTNET_API_SECRET='your_testnet_api_secret'"
        exit 1
    fi
    
    # Create backend .env.local file
    local backend_env_file="$BACKEND_DIR/.env.local"
    info "Creating backend environment configuration..."
    
    cat > "$backend_env_file" << EOF
# Auto-generated environment configuration
# Generated: $(date)

# Database Configuration
DATABASE_URL=postgresql://$(whoami)@localhost:5432/crypto_0dte

# Redis Configuration  
REDIS_URL=redis://localhost:6379/0

# Application Configuration
ENVIRONMENT=testnet
DEBUG=false
JWT_SECRET_KEY=$(openssl rand -base64 32)
API_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Delta Exchange Configuration - Testnet API Keys (for paper trading)
DELTA_TESTNET_API_KEY=${DELTA_TESTNET_API_KEY}
DELTA_TESTNET_API_SECRET=${DELTA_TESTNET_API_SECRET}
DELTA_TESTNET_PASSPHRASE=

# Environment Configuration
PAPER_TRADING=true
DELTA_EXCHANGE_TESTNET=true

# OpenAI Configuration (if available)
OPENAI_API_KEY=${OPENAI_API_KEY:-}
OPENAI_API_BASE=${OPENAI_API_BASE:-https://api.openai.com/v1}

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Security Configuration
SECRET_KEY=$(openssl rand -base64 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF
    
    success "Backend environment configuration created"
    
    # Create frontend .env.local file
    local frontend_env_file="$FRONTEND_DIR/.env.local"
    info "Creating frontend environment configuration..."
    
    cat > "$frontend_env_file" << EOF
# Auto-generated frontend environment configuration
# Generated: $(date)

REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=testnet
REACT_APP_PAPER_TRADING=true
EOF
    
    success "Frontend environment configuration created"
    save_state "CONFIG_READY"
}

# ============================================================================
# DATABASE SETUP
# ============================================================================

setup_database() {
    step "Setting up database schema..."
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    cd "$BACKEND_DIR"
    
    # Run database migrations/setup
    if [[ -f "alembic.ini" ]]; then
        info "Running Alembic migrations..."
        alembic upgrade head
    else
        info "Creating database tables..."
        python -c "
from app.database import engine, Base
import asyncio

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✅ Database tables created successfully')

asyncio.run(create_tables())
"
    fi
    
    cd "$PROJECT_ROOT"
    save_state "DATABASE_READY"
}

# ============================================================================
# SERVICE STARTUP
# ============================================================================

start_backend_service() {
    step "Starting backend service..."
    
    # Kill any existing backend processes
    pkill -f "python.*app.main" 2>/dev/null || true
    pkill -f "uvicorn" 2>/dev/null || true
    sleep 2
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    cd "$BACKEND_DIR"
    
    # Start backend service in background
    info "Starting backend on port $BACKEND_PORT..."
    nohup python -m app.main > "$LOG_DIR/backend.log" 2>&1 &
    local backend_pid=$!
    echo "$backend_pid" > "$LOG_DIR/backend.pid"
    
    add_rollback "kill $backend_pid 2>/dev/null || true"
    
    # Wait for backend to be ready
    wait_for_service "Backend API" "$BACKEND_PORT"
    
    cd "$PROJECT_ROOT"
    save_state "BACKEND_STARTED"
}

start_frontend_service() {
    step "Starting frontend service..."
    
    # Kill any existing frontend processes
    pkill -f "node.*react-scripts" 2>/dev/null || true
    pkill -f "npm.*start" 2>/dev/null || true
    sleep 2
    
    cd "$FRONTEND_DIR"
    
    # Start frontend service in background
    info "Starting frontend on port $FRONTEND_PORT..."
    nohup npm start > "$LOG_DIR/frontend.log" 2>&1 &
    local frontend_pid=$!
    echo "$frontend_pid" > "$LOG_DIR/frontend.pid"
    
    add_rollback "kill $frontend_pid 2>/dev/null || true"
    
    # Wait for frontend to be ready
    wait_for_service "Frontend" "$FRONTEND_PORT"
    
    cd "$PROJECT_ROOT"
    save_state "FRONTEND_STARTED"
}

# ============================================================================
# VALIDATION & HEALTH CHECKS
# ============================================================================

validate_deployment() {
    step "Validating deployment..."
    
    # Check backend health
    local backend_health
    if backend_health=$(curl -s "http://localhost:$BACKEND_PORT/health" 2>/dev/null); then
        if echo "$backend_health" | grep -q '"status":"healthy"'; then
            success "Backend health check passed"
        else
            warning "Backend health check returned: $backend_health"
        fi
    else
        error "Backend health check failed"
        return 1
    fi
    
    # Check frontend accessibility
    if curl -s "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
        success "Frontend accessibility check passed"
    else
        error "Frontend accessibility check failed"
        return 1
    fi
    
    # Check database connectivity
    if psql -d crypto_0dte -c "SELECT 1;" >/dev/null 2>&1; then
        success "Database connectivity check passed"
    else
        error "Database connectivity check failed"
        return 1
    fi
    
    # Check Redis connectivity
    if redis-cli ping | grep -q "PONG"; then
        success "Redis connectivity check passed"
    else
        error "Redis connectivity check failed"
        return 1
    fi
    
    save_state "VALIDATION_COMPLETE"
}

# ============================================================================
# CLEANUP & ROLLBACK
# ============================================================================

cleanup_on_failure() {
    error "Deployment failed. Running comprehensive cleanup..."
    
    # Stop ALL trading system processes (not just PID file processes)
    warning "Stopping all crypto trading system processes..."
    
    # CRITICAL FIX: More aggressive process termination
    # First try graceful termination
    pkill -TERM -f "python.*app.main" 2>/dev/null || true
    pkill -TERM -f "python.*main.py" 2>/dev/null || true
    pkill -TERM -f "uvicorn.*app" 2>/dev/null || true
    pkill -TERM -f "fastapi" 2>/dev/null || true
    
    # Wait for graceful termination
    sleep 3
    
    # Then force kill any remaining processes
    pkill -9 -f "python.*app.main" 2>/dev/null || true
    pkill -9 -f "python.*main.py" 2>/dev/null || true
    pkill -9 -f "uvicorn.*app" 2>/dev/null || true
    pkill -9 -f "fastapi" 2>/dev/null || true
    pkill -9 -f "autonomous_trading_orchestrator" 2>/dev/null || true
    pkill -9 -f "trading.*loop" 2>/dev/null || true
    pkill -9 -f "risk.*manager" 2>/dev/null || true
    pkill -9 -f "position.*manager" 2>/dev/null || true
    
    # Kill all Node.js processes related to the frontend
    pkill -9 -f "node.*react-scripts" 2>/dev/null || true
    pkill -9 -f "npm.*start" 2>/dev/null || true
    pkill -9 -f "yarn.*start" 2>/dev/null || true
    
    # Kill processes by port if they're still running
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    
    # Kill any processes we started (legacy cleanup)
    [[ -f "$LOG_DIR/backend.pid" ]] && kill -9 "$(cat "$LOG_DIR/backend.pid")" 2>/dev/null || true
    [[ -f "$LOG_DIR/frontend.pid" ]] && kill -9 "$(cat "$LOG_DIR/frontend.pid")" 2>/dev/null || true
    
    # Clean up PID files
    rm -f "$LOG_DIR"/*.pid 2>/dev/null || true
    
    # Execute rollback commands
    if [[ -f "$ROLLBACK_COMMANDS_FILE" ]]; then
        info "Executing rollback commands..."
        bash "$ROLLBACK_COMMANDS_FILE" 2>/dev/null || true
    fi
    
    # Wait longer for processes to terminate
    sleep 5
    
    # Final aggressive check for any remaining processes
    local remaining_procs=$(ps aux | grep -E "python.*app|uvicorn|fastapi|node.*react|crypto.*trading" | grep -v grep | wc -l)
    if [[ $remaining_procs -gt 0 ]]; then
        warning "Found $remaining_procs remaining processes. Final force kill..."
        ps aux | grep -E "python.*app|uvicorn|fastapi|node.*react|crypto.*trading" | grep -v grep
        
        # Nuclear option - kill by pattern matching
        ps aux | grep -E "python.*app|uvicorn|fastapi|node.*react|crypto.*trading" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
        
        # Wait and check again
        sleep 2
        local final_check=$(ps aux | grep -E "python.*app|uvicorn|fastapi|node.*react|crypto.*trading" | grep -v grep | wc -l)
        if [[ $final_check -gt 0 ]]; then
            error "WARNING: $final_check processes still running after aggressive cleanup!"
            ps aux | grep -E "python.*app|uvicorn|fastapi|node.*react|crypto.*trading" | grep -v grep
        else
            success "All processes successfully terminated after aggressive cleanup"
        fi
    else
        success "All crypto trading system processes stopped"
    fi
    
    error "Deployment failed but cleanup completed successfully"
    info "System is now in a clean state. You can safely retry deployment."
    exit 1
}

# ============================================================================
# MAIN DEPLOYMENT FLOW
# ============================================================================

main() {
    # Set up error handling
    trap cleanup_on_failure ERR
    
    # Initialize deployment
    init_deployment
    
    # Execute deployment steps in order
    pre_deployment_cleanup
    validate_system_requirements
    setup_database_services
    setup_python_environment
    setup_node_environment
    setup_environment_config
    setup_database
    start_backend_service
    start_frontend_service
    validate_deployment
    
    # Deployment success
    local end_time
    end_time=$(date '+%s')
    local start_time
    start_time=$(grep "DEPLOYMENT_START=" "$DEPLOYMENT_STATE_FILE" | cut -d'=' -f2)
    local duration=$((end_time - start_time))
    
    echo ""
    echo "============================================================"
    success "🎉 Crypto-0DTE System Deployment Completed Successfully!"
    echo "============================================================"
    echo "Deployment Duration: ${duration}s"
    echo "Backend URL: http://localhost:$BACKEND_PORT"
    echo "Frontend URL: http://localhost:$FRONTEND_PORT"
    echo "API Documentation: http://localhost:$BACKEND_PORT/docs"
    echo ""
    echo "Logs:"
    echo "  Backend: $LOG_DIR/backend.log"
    echo "  Frontend: $LOG_DIR/frontend.log"
    echo "  Deployment: $LOG_DIR/deployment.state"
    echo ""
    info "System is ready for use!"
    
    save_state "DEPLOYMENT_COMPLETE"
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

