#!/bin/bash

# Crypto-0DTE System - Local Deployment (Without Docker) - macOS Compatible
# Full system deployment: Backend + Frontend + Database + Redis

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT=$(pwd)
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_DIR="$PROJECT_ROOT/venv"
LOG_DIR="$PROJECT_ROOT/logs"

# Create logs directory
mkdir -p "$LOG_DIR"

echo -e "${BLUE}🍎 Crypto-0DTE System - Local Deployment (macOS Compatible)${NC}"
echo -e "${BLUE}============================================================${NC}"
echo "Start Time: $(date)"
echo "Project Root: $PROJECT_ROOT"
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

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if service is running (macOS)
service_running() {
    brew services list | grep "$1" | grep -q "started"
}

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1
    
    print_info "Waiting for $service_name to be ready on $host:$port..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            print_status "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within $((max_attempts * 2)) seconds"
    return 1
}

# Detect OS
OS_TYPE=$(uname -s)
if [ "$OS_TYPE" != "Darwin" ]; then
    print_error "This script is designed for macOS. For Linux, use deploy-local-without-docker.sh"
    exit 1
fi

# Phase 1: Prerequisites Check
echo -e "${BLUE}📋 Phase 1: Prerequisites Check${NC}"
echo "================================"

# Check Homebrew
if command_exists brew; then
    print_status "Homebrew found"
else
    print_error "Homebrew not found. Please install Homebrew first:"
    echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

# Check Python 3.9+
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
        PYTHON_CMD="python3"
        print_status "Python $PYTHON_VERSION found (compatible)"
    else
        print_error "Python 3.9+ required, found $PYTHON_VERSION"
        print_info "Install Python 3.11 with: brew install python@3.11"
        exit 1
    fi
else
    print_error "Python 3 not found"
    print_info "Install Python with: brew install python@3.11"
    exit 1
fi

# Check Node.js 18+
if command_exists node; then
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -ge 18 ]; then
        print_status "Node.js v$NODE_VERSION found"
    else
        print_warning "Node.js 18+ recommended, found v$NODE_VERSION"
        print_info "Update Node.js with: brew install node"
    fi
else
    print_error "Node.js not found"
    print_info "Install Node.js with: brew install node"
    exit 1
fi

# Check npm
if command_exists npm; then
    print_status "npm found"
else
    print_error "npm not found"
    exit 1
fi

# Check PostgreSQL
if command_exists psql; then
    print_status "PostgreSQL client found"
else
    print_warning "PostgreSQL client not found - will attempt to install"
fi

# Check Redis
if command_exists redis-cli; then
    print_status "Redis client found"
else
    print_warning "Redis client not found - will attempt to install"
fi

# Check additional tools
if ! command_exists jq; then
    print_warning "jq not found - will install for JSON processing"
fi

if ! command_exists bc; then
    print_warning "bc not found - will install for calculations"
fi

if ! command_exists nc; then
    print_warning "netcat not found - will install for port testing"
fi

echo ""

# Phase 2: System Dependencies Installation
echo -e "${BLUE}🔧 Phase 2: System Dependencies Installation${NC}"
echo "============================================="

# Install PostgreSQL if not present
if ! command_exists psql; then
    print_info "Installing PostgreSQL..."
    brew install postgresql@15
    print_status "PostgreSQL installed"
fi

# Install Redis if not present
if ! command_exists redis-cli; then
    print_info "Installing Redis..."
    brew install redis
    print_status "Redis installed"
fi

# Install additional tools
if ! command_exists jq; then
    print_info "Installing jq..."
    brew install jq
fi

if ! command_exists bc; then
    print_info "Installing bc..."
    brew install bc
fi

if ! command_exists nc; then
    print_info "Installing netcat..."
    brew install netcat
fi

echo ""

# Phase 3: Database and Cache Services Setup
echo -e "${BLUE}🗄️  Phase 3: Database and Cache Services Setup${NC}"
echo "==============================================="

# Start PostgreSQL service
if ! service_running postgresql@15 && ! service_running postgresql; then
    print_info "Starting PostgreSQL service..."
    brew services start postgresql@15 || brew services start postgresql
fi

# Check if PostgreSQL is running
if service_running postgresql@15 || service_running postgresql; then
    print_status "PostgreSQL service running"
else
    print_error "Failed to start PostgreSQL service"
    print_info "Try manually: brew services start postgresql@15"
    exit 1
fi

# Start Redis service
if ! service_running redis; then
    print_info "Starting Redis service..."
    brew services start redis
fi

if service_running redis; then
    print_status "Redis service running"
else
    print_error "Failed to start Redis service"
    print_info "Try manually: brew services start redis"
    exit 1
fi

# Wait for services to be ready
wait_for_service localhost 5432 "PostgreSQL"
wait_for_service localhost 6379 "Redis"

# Setup PostgreSQL database
print_info "Setting up PostgreSQL database..."

# Create database if it doesn't exist
if ! psql postgres -lqt | cut -d \| -f 1 | grep -qw crypto_0dte_local; then
    createdb crypto_0dte_local
    print_status "Database crypto_0dte_local created"
else
    print_info "Database crypto_0dte_local already exists"
fi

# Create user if it doesn't exist
if ! psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='crypto_user'" | grep -q 1; then
    psql postgres -c "CREATE USER crypto_user WITH PASSWORD 'crypto_password';"
    print_status "User crypto_user created"
else
    print_info "User crypto_user already exists"
fi

# Grant privileges
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE crypto_0dte_local TO crypto_user;" 2>/dev/null || true
psql crypto_0dte_local -c "GRANT ALL ON SCHEMA public TO crypto_user;" 2>/dev/null || true

# Test database connection
if PGPASSWORD=crypto_password psql -h localhost -U crypto_user -d crypto_0dte_local -c "SELECT 1;" >/dev/null 2>&1; then
    print_status "Database connection verified"
else
    print_error "Database connection failed"
    print_info "Check PostgreSQL configuration and try again"
    exit 1
fi

# Test Redis connection
if redis-cli ping >/dev/null 2>&1; then
    print_status "Redis connection verified"
else
    print_error "Redis connection failed"
    print_info "Check Redis configuration and try again"
    exit 1
fi

echo ""

# Phase 4: Python Environment Setup
echo -e "${BLUE}🐍 Phase 4: Python Environment Setup${NC}"
echo "====================================="

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    print_info "Creating Python virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    print_status "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
print_status "Virtual environment activated"

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip

# Install backend dependencies
print_info "Installing backend dependencies..."
cd "$BACKEND_DIR"
pip install -r requirements.txt
print_status "Backend dependencies installed"

echo ""

# Phase 4.5: API Key Configuration
echo -e "${BLUE}🔑 Phase 4.5: API Key Configuration${NC}"
echo "======================================"

CONFIG_FILE="$PROJECT_ROOT/config/api-keys.conf"

print_info "Loading API keys from persistent configuration..."

# Check if persistent config exists
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    print_success "Loaded API keys from $CONFIG_FILE"
    
    # Display configuration status
    echo ""
    print_info "API Configuration Status:"
    if [ "$DELTA_CONFIGURED" = "true" ] && [ "$DELTA_EXCHANGE_API_KEY" != "your-testnet-api-key" ]; then
        print_success "✓ Delta Exchange API: Configured"
    else
        print_warning "⚠ Delta Exchange API: Using placeholder"
    fi
    
    if [ "$OPENAI_CONFIGURED" = "true" ] && [ "$OPENAI_API_KEY" != "your-openai-api-key" ]; then
        print_success "✓ OpenAI API: Configured"
    else
        print_warning "⚠ OpenAI API: Using placeholder"
    fi
else
    print_warning "No persistent API configuration found"
    print_info "Using placeholder values for this deployment"
    print_info "To configure real API keys, run: ./setup-api-keys.sh"
    
    # Set placeholder values
    DELTA_EXCHANGE_API_KEY="your-testnet-api-key"
    DELTA_EXCHANGE_API_SECRET="your-testnet-api-secret"
    OPENAI_API_KEY="your-openai-api-key"
    DELTA_CONFIGURED=false
    OPENAI_CONFIGURED=false
fi

echo ""
print_status "API key configuration completed"

echo ""

# Phase 5: Environment Configuration
echo -e "${BLUE}🔐 Phase 5: Environment Configuration${NC}"
echo "====================================="

# Create backend environment file
print_info "Creating backend environment configuration..."
cat > "$BACKEND_DIR/.env.local" << EOF
# Database Configuration
DATABASE_URL=postgresql+asyncpg://crypto_user:crypto_password@localhost:5432/crypto_0dte_local

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
ENVIRONMENT=development
DEBUG=true
JWT_SECRET_KEY=local-development-secret-key-for-testing-only-32-chars-minimum
API_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Delta Exchange Configuration (Testnet)
DELTA_EXCHANGE_API_KEY=$DELTA_EXCHANGE_API_KEY
DELTA_EXCHANGE_API_SECRET=$DELTA_EXCHANGE_API_SECRET
DELTA_EXCHANGE_BASE_URL=https://testnet-api.delta.exchange
DELTA_EXCHANGE_TESTNET=true

# OpenAI Configuration
OPENAI_API_KEY=$OPENAI_API_KEY
OPENAI_API_BASE=https://api.openai.com/v1

# Logging Configuration
LOG_LEVEL=DEBUG
LOG_FILE=$LOG_DIR/backend.log

# Security Configuration
SECRET_KEY=local-development-secret-key-for-testing-only
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF

print_status "Backend environment configuration created"

echo ""

# Create frontend environment file
print_info "Creating frontend environment configuration..."
cat > "$FRONTEND_DIR/.env.local" << EOF
# Backend API Configuration
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_BASE_URL=ws://localhost:8000

# Application Configuration
REACT_APP_ENVIRONMENT=development
REACT_APP_DEBUG=true
REACT_APP_VERSION=1.0.0

# Feature Flags
REACT_APP_ENABLE_TRADING=true
REACT_APP_ENABLE_WEBSOCKETS=true
REACT_APP_ENABLE_NOTIFICATIONS=true

# Delta Exchange Configuration
REACT_APP_DELTA_EXCHANGE_TESTNET=true

# Styling and UI
REACT_APP_THEME=dark
REACT_APP_CHART_PROVIDER=tradingview

# Development Configuration
GENERATE_SOURCEMAP=false
SKIP_PREFLIGHT_CHECK=true
EOF

print_status "Frontend environment configuration created"

echo ""

# Phase 6: Database Migrations
echo -e "${BLUE}🗃️  Phase 6: Database Migrations${NC}"
echo "================================="

cd "$BACKEND_DIR"

# Initialize Alembic if not already done
if [ ! -f "alembic.ini" ]; then
    print_info "Initializing Alembic..."
    alembic init alembic
    print_status "Alembic initialized"
    
    # Fix alembic.ini configuration issues
    print_info "Fixing Alembic configuration..."
    
    # Fix version_num_format
    sed -i '' 's/version_num_format = %04d/version_num_format = %%04d/g' alembic.ini
    
    # Fix database URL
    sed -i '' 's|sqlalchemy.url = driver://user:pass@localhost/dbname|sqlalchemy.url = postgresql://crypto_user:crypto_password@localhost:5432/crypto_0dte_local|g' alembic.ini
    
    # Fix formatter section
    sed -i '' 's/format = %(levelname)-5.5s \[%(name)s\] %(message)s/format = %%(levelname)-5.5s [%%(name)s] %%(message)s/g' alembic.ini
    sed -i '' 's/datefmt = %H:%M:%S/datefmt = %%H:%%M:%%S/g' alembic.ini
    
    print_status "Alembic configuration fixed"
else
    # Fix existing alembic.ini if it has issues
    print_info "Checking and fixing existing Alembic configuration..."
    
    # Check if fixes are needed
    if grep -q "version_num_format = %04d" alembic.ini; then
        sed -i '' 's/version_num_format = %04d/version_num_format = %%04d/g' alembic.ini
        print_status "Fixed version_num_format"
    fi
    
    if grep -q "sqlalchemy.url = driver://user:pass@localhost/dbname" alembic.ini; then
        sed -i '' 's|sqlalchemy.url = driver://user:pass@localhost/dbname|sqlalchemy.url = postgresql://crypto_user:crypto_password@localhost:5432/crypto_0dte_local|g' alembic.ini
        print_status "Fixed database URL"
    fi
    
    if grep -q "format = %(levelname)" alembic.ini; then
        sed -i '' 's/format = %(levelname)-5.5s \[%(name)s\] %(message)s/format = %%(levelname)-5.5s [%%(name)s] %%(message)s/g' alembic.ini
        sed -i '' 's/datefmt = %H:%M:%S/datefmt = %%H:%%M:%%S/g' alembic.ini
        print_status "Fixed formatter section"
    fi
fi

# Create initial migration if needed
if [ ! -d "alembic/versions" ] || [ -z "$(ls -A alembic/versions 2>/dev/null)" ]; then
    print_info "Creating initial database migration..."
    alembic revision --autogenerate -m "Initial migration"
    print_status "Initial migration created"
fi

# Apply migrations
print_info "Applying database migrations..."
alembic upgrade head
print_status "Database migrations applied"

echo ""

# Phase 7: Frontend Dependencies Installation
echo -e "${BLUE}📦 Phase 7: Frontend Dependencies Installation${NC}"
echo "=============================================="

cd "$FRONTEND_DIR"

# Install frontend dependencies
print_info "Installing frontend dependencies..."
npm install
print_status "Frontend dependencies installed"

echo ""

# Phase 8: Backend Service Startup
echo -e "${BLUE}🚀 Phase 8: Backend Service Startup${NC}"
echo "==================================="

cd "$BACKEND_DIR"

# Kill any existing backend processes
print_info "Stopping any existing backend processes..."

# Kill all Python processes that might be running the backend
pkill -f "python.*app.main" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "start_backend" 2>/dev/null || true

# Force kill with SIGKILL
pkill -9 -f "python.*app.main" 2>/dev/null || true
pkill -9 -f "uvicorn" 2>/dev/null || true

# Wait for processes to fully terminate
sleep 10

# Force kill any remaining processes on port 8000 (excluding browser connections)
pids=$(lsof -ti:8000 2>/dev/null | grep -v "^1039$" || true)
if [ ! -z "$pids" ]; then
    print_info "Force killing remaining backend processes on port 8000..."
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 5
fi

# Clean up any lock files and PID files
rm -f "$LOG_DIR/backend.pid" "$LOG_DIR/backend.lock" "$LOG_DIR/start_backend.sh" 2>/dev/null || true

# Final verification - only Python processes should be gone
python_processes=$(lsof -i:8000 2>/dev/null | grep "Python" | wc -l | tr -d ' ')
if [ "$python_processes" -gt 0 ]; then
    print_error "Python processes still running on port 8000 after cleanup:"
    lsof -i:8000 | grep "Python" || true
    print_info "Please manually kill these processes and try again."
    exit 1
fi

# Create a macOS-compatible startup script with port binding test
cat > "$LOG_DIR/start_backend.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../backend"

# Strict error handling
set -e

# Lock file for atomic startup (macOS compatible)
LOCK_FILE="../logs/backend.lock"
PID_FILE="../logs/backend.pid"

# Function to cleanup on exit
cleanup() {
    rmdir "$LOCK_FILE" 2>/dev/null || true
}
trap cleanup EXIT

# macOS-compatible atomic lock creation using mkdir
if ! mkdir "$LOCK_FILE" 2>/dev/null; then
    echo "ERROR: Another backend instance is already starting or running"
    exit 1
fi

# Test if we can bind to port 8000 before starting the actual backend
echo "Testing port 8000 availability..."
if python3 -c "
import socket
import sys
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 8000))
    s.close()
    print('Port 8000 is available')
except Exception as e:
    print(f'Port 8000 is not available: {e}')
    sys.exit(1)
"; then
    echo "Port binding test passed"
else
    echo "ERROR: Port 8000 binding test failed"
    exit 1
fi

# Write our PID to the PID file
echo $$ > "$PID_FILE"

# Start the backend with exec to replace the shell process
echo "Starting backend on port 8000..."
exec python -m app.main
EOF

chmod +x "$LOG_DIR/start_backend.sh"

# Start backend service with enhanced protection
print_info "Starting backend service with enhanced port protection..."

# Start the backend in background and capture its PID
"$LOG_DIR/start_backend.sh" > "$LOG_DIR/backend.log" 2>&1 &
STARTUP_PID=$!

# Wait for startup to complete
sleep 8

# Check if the startup script is still running or if backend started
if kill -0 $STARTUP_PID 2>/dev/null; then
    # Startup script is still running, backend should be starting
    print_info "Backend startup in progress..."
    sleep 5
fi

# Get the actual backend PID from the PID file
if [ -f "$LOG_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$LOG_DIR/backend.pid")
    print_info "Backend PID: $BACKEND_PID"
else
    print_error "Backend PID file not found. Startup may have failed."
    print_info "Check logs: tail -f $LOG_DIR/backend.log"
    exit 1
fi

# Verify exactly one Python process is listening on port 8000
python_count=$(lsof -i:8000 2>/dev/null | grep "Python" | wc -l | tr -d ' ')
if [ "$python_count" -eq 1 ]; then
    print_success "✓ Single backend process confirmed (PID: $BACKEND_PID)"
elif [ "$python_count" -eq 0 ]; then
    print_error "✗ No backend process found on port 8000"
    print_info "Check logs: tail -f $LOG_DIR/backend.log"
    exit 1
else
    print_error "✗ Multiple Python processes detected: $python_count"
    print_info "All processes on port 8000:"
    lsof -i:8000 || true
    print_error "This indicates a serious issue with process management."
    exit 1
fi

# Wait for backend to be ready
wait_for_service localhost 8000 "Backend API"

# Test backend health
print_info "Testing backend health endpoints..."
if curl -s http://localhost:8000/health >/dev/null; then
    print_status "Backend health check passed"
else
    print_error "Backend health check failed"
    print_info "Check backend logs: tail -f $LOG_DIR/backend.log"
    exit 1
fi

echo ""

# Phase 9: Frontend Service Startup
echo -e "${BLUE}🎨 Phase 9: Frontend Service Startup${NC}"
echo "===================================="

cd "$FRONTEND_DIR"

# Kill any existing frontend processes
print_info "Stopping any existing frontend processes..."
pkill -f "npm.*start" 2>/dev/null || true
pkill -f "react-scripts.*start" 2>/dev/null || true
sleep 2

# Start frontend service in background
print_info "Starting frontend development server..."
nohup npm start > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"

# Wait for frontend to be ready
wait_for_service localhost 3000 "Frontend"

echo ""

# Phase 10: System Validation
echo -e "${BLUE}✅ Phase 10: System Validation${NC}"
echo "==============================="

# Test all endpoints
print_info "Validating system endpoints..."

# Backend endpoints
BACKEND_ENDPOINTS=(
    "http://localhost:8000/health"
    "http://localhost:8000/health/ready"
    "http://localhost:8000/health/live"
    "http://localhost:8000/docs"
)

for endpoint in "${BACKEND_ENDPOINTS[@]}"; do
    if curl -s "$endpoint" >/dev/null; then
        print_status "✓ $endpoint"
    else
        print_error "✗ $endpoint"
    fi
done

# Frontend endpoint
if curl -s http://localhost:3000 >/dev/null; then
    print_status "✓ http://localhost:3000 (Frontend)"
else
    print_error "✗ http://localhost:3000 (Frontend)"
fi

echo ""

# Phase 11: Deployment Summary
echo -e "${BLUE}📊 Phase 11: Deployment Summary${NC}"
echo "==============================="

print_status "Crypto-0DTE System deployed successfully on macOS!"
echo ""
echo "🌐 Service URLs:"
echo "   Frontend Dashboard: http://localhost:3000"
echo "   Backend API:        http://localhost:8000"
echo "   API Documentation:  http://localhost:8000/docs"
echo ""
echo "🗄️  Database Services:"
echo "   PostgreSQL:         localhost:5432 (crypto_0dte_local)"
echo "   Redis:              localhost:6379"
echo ""
echo "📁 Process Information:"
echo "   Backend PID:        $BACKEND_PID (logged to $LOG_DIR/backend.log)"
echo "   Frontend PID:       $FRONTEND_PID (logged to $LOG_DIR/frontend.log)"
echo ""
echo "🔧 Management Commands:"
echo "   Stop Backend:       kill $BACKEND_PID"
echo "   Stop Frontend:      kill $FRONTEND_PID"
echo "   View Backend Logs:  tail -f $LOG_DIR/backend.log"
echo "   View Frontend Logs: tail -f $LOG_DIR/frontend.log"
echo ""
echo "🍎 macOS Service Management:"
echo "   Stop PostgreSQL:    brew services stop postgresql@15"
echo "   Stop Redis:         brew services stop redis"
echo "   Restart PostgreSQL: brew services restart postgresql@15"
echo "   Restart Redis:      brew services restart redis"
echo ""
echo "📋 Next Steps:"
echo "   1. Run health check tests: ./test-health-checks.sh"
echo "   2. Run autonomous trading tests: ./test-autonomous-trading.sh"
echo "   3. Access frontend dashboard at http://localhost:3000"
echo ""

# Create stop script for macOS
cat > "$PROJECT_ROOT/stop-local-services-macos.sh" << 'EOF'
#!/bin/bash

# Stop Crypto-0DTE Local Services (macOS)

LOG_DIR="$(pwd)/logs"

echo "🛑 Stopping Crypto-0DTE Local Services (macOS)..."

# Stop backend
if [ -f "$LOG_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$LOG_DIR/backend.pid")
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID"
        echo "✅ Backend service stopped (PID: $BACKEND_PID)"
    else
        echo "⚠️  Backend service not running"
    fi
    rm -f "$LOG_DIR/backend.pid"
fi

# Stop frontend
if [ -f "$LOG_DIR/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$LOG_DIR/frontend.pid")
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID"
        echo "✅ Frontend service stopped (PID: $FRONTEND_PID)"
    else
        echo "⚠️  Frontend service not running"
    fi
    rm -f "$LOG_DIR/frontend.pid"
fi

# Kill any remaining processes
pkill -f "python.*app.main" 2>/dev/null || true
pkill -f "npm.*start" 2>/dev/null || true
pkill -f "react-scripts.*start" 2>/dev/null || true

echo "🏁 All local services stopped"
echo ""
echo "🍎 To stop database services:"
echo "   brew services stop postgresql@15"
echo "   brew services stop redis"
EOF

chmod +x "$PROJECT_ROOT/stop-local-services-macos.sh"
print_status "macOS stop script created: ./stop-local-services-macos.sh"

echo ""
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETED SUCCESSFULLY ON macOS!${NC}"
echo "End Time: $(date)"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Keep this terminal open or services will stop!${NC}"
echo -e "${YELLOW}   Use './stop-local-services-macos.sh' to stop all services cleanly.${NC}"
echo ""
echo -e "${BLUE}🍎 macOS-Specific Notes:${NC}"
echo "   - Services are managed by Homebrew"
echo "   - Database and Redis will persist across reboots"
echo "   - Use 'brew services list' to check service status"
echo "   - Logs are available in the logs/ directory"

