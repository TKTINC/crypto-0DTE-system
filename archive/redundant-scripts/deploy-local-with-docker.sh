#!/bin/bash

# Crypto-0DTE System - Local Deployment (With Docker)
# Full system deployment: Backend + Frontend + Database + Redis using Docker Compose

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT=$(pwd)
LOG_DIR="$PROJECT_ROOT/logs"
COMPOSE_FILE="docker-compose.local.yml"

# Create logs directory
mkdir -p "$LOG_DIR"

echo -e "${BLUE}🐳 Crypto-0DTE System - Local Deployment (With Docker)${NC}"
echo -e "${BLUE}=======================================================${NC}"
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

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=60
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

# Check Docker
if command_exists docker; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    print_status "Docker $DOCKER_VERSION found"
else
    print_error "Docker not found - please install Docker first"
    exit 1
fi

# Check Docker Compose
if command_exists docker-compose; then
    COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
    print_status "Docker Compose $COMPOSE_VERSION found"
elif docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
    COMPOSE_VERSION=$(docker compose version --short)
    print_status "Docker Compose $COMPOSE_VERSION found (integrated)"
else
    print_error "Docker Compose not found - please install Docker Compose"
    exit 1
fi

# Set compose command
if [ -z "$COMPOSE_CMD" ]; then
    COMPOSE_CMD="docker-compose"
fi

# Check Docker daemon
if ! docker info >/dev/null 2>&1; then
    print_error "Docker daemon not running - please start Docker"
    exit 1
fi
print_status "Docker daemon running"

# Check netcat for port testing
if ! command_exists nc; then
    print_warning "netcat not found - installing..."
    if command_exists apt-get; then
        sudo apt-get update && sudo apt-get install -y netcat
    elif command_exists yum; then
        sudo yum install -y nc
    fi
fi

echo ""

# Phase 2: Docker Compose Configuration
echo -e "${BLUE}🔧 Phase 2: Docker Compose Configuration${NC}"
echo "========================================="

# Create Docker Compose file
print_info "Creating Docker Compose configuration..."
cat > "$COMPOSE_FILE" << 'EOF'
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: crypto-postgres-local
    environment:
      POSTGRES_DB: crypto_0dte_local
      POSTGRES_USER: crypto_user
      POSTGRES_PASSWORD: crypto_password
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U crypto_user -d crypto_0dte_local"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    restart: unless-stopped
    networks:
      - crypto-network

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: crypto-redis-local
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped
    networks:
      - crypto-network

  # Backend API Service
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile.railway
      args:
        - BUILDKIT_INLINE_CACHE=1
    container_name: crypto-backend-local
    environment:
      DATABASE_URL: postgresql://crypto_user:crypto_password@postgres:5432/crypto_0dte_local
      REDIS_URL: redis://redis:6379/0
      ENVIRONMENT: development
      DEBUG: "true"
      JWT_SECRET_KEY: local-development-secret-key-for-testing-only-32-chars-minimum
      API_CORS_ORIGINS: http://localhost:3000,http://127.0.0.1:3000
      HOST: 0.0.0.0
      PORT: 8000
      DELTA_EXCHANGE_TESTNET: "true"
      DELTA_EXCHANGE_API_KEY: ${DELTA_EXCHANGE_API_KEY:-your-testnet-api-key}
      DELTA_EXCHANGE_API_SECRET: ${DELTA_EXCHANGE_API_SECRET:-your-testnet-api-secret}
      DELTA_EXCHANGE_BASE_URL: https://testnet-api.delta.exchange
      OPENAI_API_KEY: ${OPENAI_API_KEY:-your-openai-api-key}
      OPENAI_API_BASE: https://api.openai.com/v1
      LOG_LEVEL: DEBUG
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    networks:
      - crypto-network
    volumes:
      - ./logs:/app/logs

  # Frontend Dashboard
  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
      args:
        - REACT_APP_API_BASE_URL=http://localhost:8000
        - REACT_APP_WS_BASE_URL=ws://localhost:8000
        - REACT_APP_ENVIRONMENT=development
        - REACT_APP_DEBUG=true
        - REACT_APP_ENABLE_TRADING=true
        - REACT_APP_ENABLE_WEBSOCKETS=true
        - REACT_APP_DELTA_EXCHANGE_TESTNET=true
    container_name: crypto-frontend-local
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    networks:
      - crypto-network

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  crypto-network:
    driver: bridge
EOF

print_status "Docker Compose configuration created"

# Create database initialization script
print_info "Creating database initialization script..."
cat > "init-db.sql" << 'EOF'
-- Initialize Crypto-0DTE Database
-- This script runs automatically when PostgreSQL container starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set timezone
SET timezone = 'UTC';

-- Create initial schema (tables will be created by Alembic migrations)
-- This is just for any initial setup needed

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE crypto_0dte_local TO crypto_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO crypto_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO crypto_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO crypto_user;

-- Log initialization
INSERT INTO pg_stat_statements_info (dealloc) VALUES (0) ON CONFLICT DO NOTHING;
EOF

print_status "Database initialization script created"

echo ""

# Phase 3: Environment Variables Setup
echo -e "${BLUE}🔐 Phase 3: Environment Variables Setup${NC}"
echo "======================================"

# Create .env file for Docker Compose
print_info "Creating environment variables file..."
cat > ".env" << EOF
# External API Keys (replace with your actual keys)
DELTA_EXCHANGE_API_KEY=your-testnet-api-key
DELTA_EXCHANGE_API_SECRET=your-testnet-api-secret
OPENAI_API_KEY=your-openai-api-key

# Docker Build Arguments
BUILDKIT_INLINE_CACHE=1
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1
EOF

print_status "Environment variables configured"

# Load environment variables if they exist
if [ -f ".env.local" ]; then
    print_info "Loading local environment variables..."
    set -a
    source .env.local
    set +a
    print_status "Local environment variables loaded"
fi

echo ""

# Phase 4: Docker Images Build
echo -e "${BLUE}🔨 Phase 4: Docker Images Build${NC}"
echo "==============================="

# Clean up any existing containers
print_info "Cleaning up existing containers..."
$COMPOSE_CMD -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

# Build images
print_info "Building Docker images (this may take several minutes)..."
$COMPOSE_CMD -f "$COMPOSE_FILE" build --no-cache --parallel

print_status "Docker images built successfully"

# List built images
print_info "Built images:"
docker images | grep -E "(crypto|postgres|redis)" | head -10

echo ""

# Phase 5: Infrastructure Services Startup
echo -e "${BLUE}🗄️  Phase 5: Infrastructure Services Startup${NC}"
echo "=============================================="

# Start database and cache services first
print_info "Starting infrastructure services (PostgreSQL, Redis)..."
$COMPOSE_CMD -f "$COMPOSE_FILE" up -d postgres redis

# Wait for infrastructure services
print_info "Waiting for infrastructure services to be healthy..."
$COMPOSE_CMD -f "$COMPOSE_FILE" ps

# Wait for services to be ready
wait_for_service localhost 5432 "PostgreSQL"
wait_for_service localhost 6379 "Redis"

# Verify infrastructure health
print_info "Verifying infrastructure health..."
if $COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres pg_isready -U crypto_user >/dev/null 2>&1; then
    print_status "PostgreSQL health check passed"
else
    print_error "PostgreSQL health check failed"
    $COMPOSE_CMD -f "$COMPOSE_FILE" logs postgres
    exit 1
fi

if $COMPOSE_CMD -f "$COMPOSE_FILE" exec -T redis redis-cli ping >/dev/null 2>&1; then
    print_status "Redis health check passed"
else
    print_error "Redis health check failed"
    $COMPOSE_CMD -f "$COMPOSE_FILE" logs redis
    exit 1
fi

echo ""

# Phase 6: Application Services Startup
echo -e "${BLUE}🚀 Phase 6: Application Services Startup${NC}"
echo "========================================="

# Start backend service
print_info "Starting backend service..."
$COMPOSE_CMD -f "$COMPOSE_FILE" up -d backend

# Wait for backend to be ready
wait_for_service localhost 8000 "Backend API"

# Verify backend health
print_info "Verifying backend health..."
if curl -s http://localhost:8000/health >/dev/null; then
    print_status "Backend health check passed"
else
    print_error "Backend health check failed"
    $COMPOSE_CMD -f "$COMPOSE_FILE" logs backend
    exit 1
fi

# Start frontend service
print_info "Starting frontend service..."
$COMPOSE_CMD -f "$COMPOSE_FILE" up -d frontend

# Wait for frontend to be ready
wait_for_service localhost 3000 "Frontend"

echo ""

# Phase 7: Database Migrations
echo -e "${BLUE}🗃️  Phase 7: Database Migrations${NC}"
echo "================================="

# Run database migrations
print_info "Running database migrations..."
$COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic upgrade head

print_status "Database migrations completed"

echo ""

# Phase 8: System Validation
echo -e "${BLUE}✅ Phase 8: System Validation${NC}"
echo "=============================="

# Check all container status
print_info "Checking container status..."
$COMPOSE_CMD -f "$COMPOSE_FILE" ps

# Test all endpoints
print_info "Validating system endpoints..."

# Backend endpoints
BACKEND_ENDPOINTS=(
    "http://localhost:8000/health"
    "http://localhost:8000/health/detailed"
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

# Check resource usage
print_info "Container resource usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

echo ""

# Phase 9: Deployment Summary
echo -e "${BLUE}📊 Phase 9: Deployment Summary${NC}"
echo "=============================="

print_status "Crypto-0DTE System deployed successfully with Docker!"
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
echo "🐳 Docker Management:"
echo "   View Status:        $COMPOSE_CMD -f $COMPOSE_FILE ps"
echo "   View Logs:          $COMPOSE_CMD -f $COMPOSE_FILE logs [service]"
echo "   Stop Services:      $COMPOSE_CMD -f $COMPOSE_FILE down"
echo "   Restart Service:    $COMPOSE_CMD -f $COMPOSE_FILE restart [service]"
echo ""
echo "📋 Container Information:"
$COMPOSE_CMD -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "📁 Log Files:"
echo "   Backend Logs:       $COMPOSE_CMD -f $COMPOSE_FILE logs backend"
echo "   Frontend Logs:      $COMPOSE_CMD -f $COMPOSE_FILE logs frontend"
echo "   Database Logs:      $COMPOSE_CMD -f $COMPOSE_FILE logs postgres"
echo "   Redis Logs:         $COMPOSE_CMD -f $COMPOSE_FILE logs redis"
echo ""

# Create management scripts
print_info "Creating management scripts..."

# Create stop script
cat > "stop-docker-services.sh" << EOF
#!/bin/bash

# Stop Crypto-0DTE Docker Services

echo "🛑 Stopping Crypto-0DTE Docker Services..."
$COMPOSE_CMD -f $COMPOSE_FILE down

echo "🧹 Cleaning up..."
docker system prune -f --volumes

echo "🏁 All Docker services stopped and cleaned up"
EOF

chmod +x "stop-docker-services.sh"

# Create restart script
cat > "restart-docker-services.sh" << EOF
#!/bin/bash

# Restart Crypto-0DTE Docker Services

echo "🔄 Restarting Crypto-0DTE Docker Services..."
$COMPOSE_CMD -f $COMPOSE_FILE restart

echo "✅ All services restarted"
$COMPOSE_CMD -f $COMPOSE_FILE ps
EOF

chmod +x "restart-docker-services.sh"

# Create logs script
cat > "view-docker-logs.sh" << EOF
#!/bin/bash

# View Crypto-0DTE Docker Logs

SERVICE=\${1:-""}

if [ -z "\$SERVICE" ]; then
    echo "📋 Available services:"
    $COMPOSE_CMD -f $COMPOSE_FILE ps --services
    echo ""
    echo "Usage: ./view-docker-logs.sh [service_name]"
    echo "   or: ./view-docker-logs.sh (to view all logs)"
    echo ""
    echo "📊 Viewing all service logs..."
    $COMPOSE_CMD -f $COMPOSE_FILE logs --tail=50 -f
else
    echo "📊 Viewing logs for \$SERVICE..."
    $COMPOSE_CMD -f $COMPOSE_FILE logs --tail=50 -f "\$SERVICE"
fi
EOF

chmod +x "view-docker-logs.sh"

print_status "Management scripts created:"
print_status "  ./stop-docker-services.sh - Stop all services"
print_status "  ./restart-docker-services.sh - Restart all services"
print_status "  ./view-docker-logs.sh [service] - View service logs"

echo ""
echo "📋 Next Steps:"
echo "   1. Run health check tests: ./test-health-checks.sh"
echo "   2. Run autonomous trading tests: ./test-autonomous-trading.sh"
echo "   3. Access frontend dashboard at http://localhost:3000"
echo "   4. Monitor logs: ./view-docker-logs.sh"
echo ""

echo -e "${GREEN}🎉 DOCKER DEPLOYMENT COMPLETED SUCCESSFULLY!${NC}"
echo "End Time: $(date)"
echo ""
echo -e "${YELLOW}💡 TIP: Use './view-docker-logs.sh' to monitor service logs${NC}"
echo -e "${YELLOW}💡 TIP: Use './stop-docker-services.sh' to stop all services${NC}"

