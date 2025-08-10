#!/bin/bash

# Crypto-0DTE System - Local Deployment (Without Docker)
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

echo -e "${BLUE}🚀 Crypto-0DTE System - Local Deployment (Without Docker)${NC}"
echo -e "${BLUE}================================================================${NC}"
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if service is running
service_running() {
    systemctl is-active --quiet "$1" 2>/dev/null
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

# Phase 1: Prerequisites Check
echo -e "${BLUE}📋 Phase 1: Prerequisites Check${NC}"
echo "================================"

# Check Python 3.11+
if command_exists python3.11; then
    PYTHON_CMD="python3.11"
    print_status "Python 3.11 found"
elif command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [ "$(echo "$PYTHON_VERSION >= 3.11" | bc -l)" -eq 1 ]; then
        PYTHON_CMD="python3"
        print_status "Python $PYTHON_VERSION found (compatible)"
    else
        print_error "Python 3.11+ required, found $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3.11+ not found"
    exit 1
fi

# Check Node.js 18+
if command_exists node; then
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -ge 18 ]; then
        print_status "Node.js v$NODE_VERSION found"
    else
        print_error "Node.js 18+ required, found v$NODE_VERSION"
        exit 1
    fi
else
    print_error "Node.js not found"
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

echo ""

# Phase 2: System Dependencies Installation
echo -e "${BLUE}🔧 Phase 2: System Dependencies Installation${NC}"
echo "============================================="

# Install PostgreSQL if not present
if ! command_exists psql; then
    print_info "Installing PostgreSQL..."
    if command_exists apt-get; then
        sudo apt-get update
        sudo apt-get install -y postgresql postgresql-contrib
    elif command_exists yum; then
        sudo yum install -y postgresql postgresql-server postgresql-contrib
    else
        print_error "Unable to install PostgreSQL - unsupported package manager"
        exit 1
    fi
    print_status "PostgreSQL installed"
fi

# Install Redis if not present
if ! command_exists redis-cli; then
    print_info "Installing Redis..."
    if command_exists apt-get; then
        sudo apt-get install -y redis-server
    elif command_exists yum; then
        sudo yum install -y redis
    else
        print_error "Unable to install Redis - unsupported package manager"
        exit 1
    fi
    print_status "Redis installed"
fi

echo ""

# Phase 3: Database and Cache Services Setup
echo -e "${BLUE}🗄️  Phase 3: Database and Cache Services Setup${NC}"
echo "==============================================="

# Start PostgreSQL service
if ! service_running postgresql; then
    print_info "Starting PostgreSQL service..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
fi

if service_running postgresql; then
    print_status "PostgreSQL service running"
else
    print_error "Failed to start PostgreSQL service"
    exit 1
fi

# Start Redis service
if ! service_running redis-server && ! service_running redis; then
    print_info "Starting Redis service..."
    if systemctl list-unit-files | grep -q redis-server; then
        sudo systemctl start redis-server
        sudo systemctl enable redis-server
    else
        sudo systemctl start redis
        sudo systemctl enable redis
    fi
fi

if service_running redis-server || service_running redis; then
    print_status "Redis service running"
else
    print_error "Failed to start Redis service"
    exit 1
fi

# Wait for services to be ready
wait_for_service localhost 5432 "PostgreSQL"
wait_for_service localhost 6379 "Redis"

# Setup PostgreSQL database
print_info "Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE crypto_0dte_local;" 2>/dev/null || print_warning "Database may already exist"
sudo -u postgres psql -c "CREATE USER crypto_user WITH PASSWORD 'crypto_password';" 2>/dev/null || print_warning "User may already exist"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE crypto_0dte_local TO crypto_user;" 2>/dev/null || true
print_status "PostgreSQL database configured"

# Test database connection
if PGPASSWORD=crypto_password psql -h localhost -U crypto_user -d crypto_0dte_local -c "SELECT 1;" >/dev/null 2>&1; then
    print_status "Database connection verified"
else
    print_error "Database connection failed"
    exit 1
fi

# Test Redis connection
if redis-cli ping >/dev/null 2>&1; then
    print_status "Redis connection verified"
else
    print_error "Redis connection failed"
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

# Phase 5: Environment Configuration
echo -e "${BLUE}🔐 Phase 5: Environment Configuration${NC}"
echo "====================================="

# Create backend environment file
print_info "Creating backend environment configuration..."
cat > "$BACKEND_DIR/.env.local" << EOF
# Database Configuration
DATABASE_URL=postgresql://crypto_user:crypto_password@localhost:5432/crypto_0dte_local

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
DELTA_EXCHANGE_API_KEY=your-testnet-api-key
DELTA_EXCHANGE_API_SECRET=your-testnet-api-secret
DELTA_EXCHANGE_BASE_URL=https://testnet-api.delta.exchange
DELTA_EXCHANGE_TESTNET=true

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
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

# Start backend service in background
print_info "Starting backend service..."
nohup python -m app.main > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$LOG_DIR/backend.pid"

# Wait for backend to be ready
wait_for_service localhost 8000 "Backend API"

# Test backend health
print_info "Testing backend health endpoints..."
if curl -s http://localhost:8000/health >/dev/null; then
    print_status "Backend health check passed"
else
    print_error "Backend health check failed"
    exit 1
fi

echo ""

# Phase 9: Frontend Service Startup
echo -e "${BLUE}🎨 Phase 9: Frontend Service Startup${NC}"
echo "===================================="

cd "$FRONTEND_DIR"

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

print_status "Crypto-0DTE System deployed successfully!"
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
echo "📋 Next Steps:"
echo "   1. Run health check tests: ./test-health-checks.sh"
echo "   2. Run autonomous trading tests: ./test-autonomous-trading.sh"
echo "   3. Access frontend dashboard at http://localhost:3000"
echo ""

# Create stop script
cat > "$PROJECT_ROOT/stop-local-services.sh" << 'EOF'
#!/bin/bash

# Stop Crypto-0DTE Local Services

LOG_DIR="$(pwd)/logs"

echo "🛑 Stopping Crypto-0DTE Local Services..."

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
pkill -f "python -m app.main" 2>/dev/null || true
pkill -f "npm start" 2>/dev/null || true

echo "🏁 All local services stopped"
EOF

chmod +x "$PROJECT_ROOT/stop-local-services.sh"
print_status "Stop script created: ./stop-local-services.sh"

echo ""
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!${NC}"
echo "End Time: $(date)"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Keep this terminal open or services will stop!${NC}"
echo -e "${YELLOW}   Use './stop-local-services.sh' to stop all services cleanly.${NC}"

