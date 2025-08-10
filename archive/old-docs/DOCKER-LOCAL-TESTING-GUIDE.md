# Docker Local Testing Guide
## Crypto-0DTE System Container-Based Validation

### 🎯 **DOCKER TESTING OBJECTIVES**

Docker testing provides the most accurate representation of your Railway deployment environment. This approach ensures:

1. **Production parity** - Identical environment to Railway deployment
2. **Dependency isolation** - No conflicts with local system packages
3. **Consistent behavior** - Same results across different development machines
4. **Deployment confidence** - If it works in Docker locally, it will work on Railway
5. **Container optimization** - Verify Docker image size and startup time
6. **Multi-service orchestration** - Test complete system integration

### 🐳 **WHY DOCKER FOR LOCAL TESTING?**

#### **Production Parity Benefits:**
Railway uses containerized deployments, so Docker testing provides:
- **Identical runtime environment** to production
- **Same dependency versions** and system libraries
- **Consistent networking** and port configurations
- **Realistic resource constraints** and performance characteristics
- **Container-specific behaviors** and limitations

#### **Development Advantages:**
- **Clean environment** without local system interference
- **Easy reset** to known good state
- **Reproducible builds** across team members
- **Simplified dependency management**
- **Faster debugging** of deployment-specific issues

### 🔧 **DOCKER PREREQUISITES**

#### **System Requirements**
- Docker Engine 20.10+ (latest stable recommended)
- Docker Compose 2.0+ (for multi-service orchestration)
- 8GB+ RAM (for running multiple containers)
- 20GB+ free disk space (for images and volumes)

#### **Install Docker**
```bash
# Ubuntu/Debian installation
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (avoid sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker-compose --version

# Test Docker functionality
docker run hello-world
```

#### **Docker Configuration**
```bash
# Configure Docker daemon for development
sudo tee /etc/docker/daemon.json << 'EOF'
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "storage-driver": "overlay2"
}
EOF

# Restart Docker service
sudo systemctl restart docker
```

### 📁 **DOCKER COMPOSE SETUP**

#### **Create Complete Docker Compose Configuration**
Create `docker-compose.local.yml`:
```yaml
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
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U crypto_user -d crypto_0dte_local"]
      interval: 10s
      timeout: 5s
      retries: 5
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
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - crypto-network

  # Backend API Service
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile.railway
    container_name: crypto-backend-local
    environment:
      # Database Configuration
      DATABASE_URL: postgresql://crypto_user:crypto_password@postgres:5432/crypto_0dte_local
      REDIS_URL: redis://redis:6379/0
      
      # Application Configuration
      ENVIRONMENT: development
      DEBUG: "true"
      JWT_SECRET_KEY: local-development-secret-key-for-testing-only
      API_CORS_ORIGINS: http://localhost:3000,http://127.0.0.1:3000
      
      # Delta Exchange Configuration (Testnet)
      DELTA_EXCHANGE_API_KEY: ${DELTA_EXCHANGE_API_KEY:-your-testnet-api-key}
      DELTA_EXCHANGE_API_SECRET: ${DELTA_EXCHANGE_API_SECRET:-your-testnet-api-secret}
      DELTA_EXCHANGE_BASE_URL: https://testnet-api.delta.exchange
      DELTA_EXCHANGE_TESTNET: "true"
      
      # OpenAI Configuration
      OPENAI_API_KEY: ${OPENAI_API_KEY:-your-openai-api-key}
      OPENAI_API_BASE: https://api.openai.com/v1
      
      # Logging Configuration
      LOG_LEVEL: DEBUG
      
      # Container-specific
      PORT: 8000
    ports:
      - "8000:8000"
    volumes:
      - ./backend/app:/app/app:ro
      - backend_logs:/app/logs
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
      start_period: 40s
    restart: unless-stopped
    networks:
      - crypto-network

  # Data Feed Service
  data-feed:
    build:
      context: .
      dockerfile: backend/Dockerfile.data-feed
    container_name: crypto-data-feed-local
    environment:
      # Database Configuration
      DATABASE_URL: postgresql://crypto_user:crypto_password@postgres:5432/crypto_0dte_local
      REDIS_URL: redis://redis:6379/0
      
      # Application Configuration
      ENVIRONMENT: development
      DEBUG: "true"
      
      # Delta Exchange Configuration
      DELTA_EXCHANGE_API_KEY: ${DELTA_EXCHANGE_API_KEY:-your-testnet-api-key}
      DELTA_EXCHANGE_API_SECRET: ${DELTA_EXCHANGE_API_SECRET:-your-testnet-api-secret}
      DELTA_EXCHANGE_BASE_URL: https://testnet-api.delta.exchange
      DELTA_EXCHANGE_TESTNET: "true"
      
      # Data Feed Configuration
      MARKET_DATA_INTERVAL: 5
      SYMBOLS: BTC-USDT,ETH-USDT
      
      # Logging Configuration
      LOG_LEVEL: DEBUG
    volumes:
      - ./backend/app:/app/app:ro
      - datafeed_logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      backend:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - crypto-network

  # Signal Generator Service
  signal-generator:
    build:
      context: .
      dockerfile: backend/Dockerfile.signal-generator
    container_name: crypto-signal-generator-local
    environment:
      # Database Configuration
      DATABASE_URL: postgresql://crypto_user:crypto_password@postgres:5432/crypto_0dte_local
      REDIS_URL: redis://redis:6379/0
      
      # Application Configuration
      ENVIRONMENT: development
      DEBUG: "true"
      
      # OpenAI Configuration
      OPENAI_API_KEY: ${OPENAI_API_KEY:-your-openai-api-key}
      OPENAI_API_BASE: https://api.openai.com/v1
      
      # Signal Generation Configuration
      SIGNAL_GENERATION_INTERVAL: 60
      STRATEGIES: btc_lightning_scalp,eth_defi_correlation,cross_asset_arbitrage
      
      # Logging Configuration
      LOG_LEVEL: DEBUG
    volumes:
      - ./backend/app:/app/app:ro
      - signals_logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      backend:
        condition: service_healthy
      data-feed:
        condition: service_started
    restart: unless-stopped
    networks:
      - crypto-network

  # Frontend Dashboard
  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    container_name: crypto-frontend-local
    environment:
      REACT_APP_API_BASE_URL: http://localhost:8000
      REACT_APP_WS_BASE_URL: ws://localhost:8000
      REACT_APP_ENVIRONMENT: development
      REACT_APP_DEBUG: "true"
      REACT_APP_ENABLE_TRADING: "true"
      REACT_APP_ENABLE_WEBSOCKETS: "true"
      REACT_APP_DELTA_EXCHANGE_TESTNET: "true"
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src:ro
      - ./frontend/public:/app/public:ro
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - crypto-network

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  backend_logs:
    driver: local
  datafeed_logs:
    driver: local
  signals_logs:
    driver: local

networks:
  crypto-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

#### **Create Environment File for Docker**
Create `.env.docker`:
```bash
# External API Keys (set these with your actual keys)
DELTA_EXCHANGE_API_KEY=your-delta-exchange-testnet-api-key
DELTA_EXCHANGE_API_SECRET=your-delta-exchange-testnet-api-secret
OPENAI_API_KEY=your-openai-api-key

# Docker-specific configuration
COMPOSE_PROJECT_NAME=crypto-0dte-local
COMPOSE_FILE=docker-compose.local.yml
```

### 🚀 **DOCKER TESTING PROCEDURES**

#### **Test 1: Build All Images**
```bash
# Navigate to project root
cd crypto-0DTE-system

# Load environment variables
export $(cat .env.docker | xargs)

# Build all images
docker-compose -f docker-compose.local.yml build

# Verify images were created
docker images | grep crypto

# Expected output:
# crypto-0dte-system_backend          latest    [IMAGE_ID]    [SIZE]
# crypto-0dte-system_data-feed        latest    [IMAGE_ID]    [SIZE]
# crypto-0dte-system_signal-generator latest    [IMAGE_ID]    [SIZE]
# crypto-0dte-system_frontend         latest    [IMAGE_ID]    [SIZE]
```

#### **Test 2: Start Infrastructure Services**
```bash
# Start database and cache services first
docker-compose -f docker-compose.local.yml up -d postgres redis

# Wait for services to be healthy
docker-compose -f docker-compose.local.yml ps

# Check service health
docker-compose -f docker-compose.local.yml exec postgres pg_isready -U crypto_user
docker-compose -f docker-compose.local.yml exec redis redis-cli ping

# Expected output:
# postgres: accepting connections
# redis: PONG
```

#### **Test 3: Database Initialization**
```bash
# Run database migrations
docker-compose -f docker-compose.local.yml exec backend alembic upgrade head

# Verify database tables
docker-compose -f docker-compose.local.yml exec postgres psql -U crypto_user -d crypto_0dte_local -c "\dt"

# Expected output: List of tables (users, portfolios, signals, etc.)
```

#### **Test 4: Start Application Services**
```bash
# Start backend service
docker-compose -f docker-compose.local.yml up -d backend

# Monitor backend startup
docker-compose -f docker-compose.local.yml logs -f backend

# Wait for healthy status
docker-compose -f docker-compose.local.yml ps backend

# Test backend health
curl http://localhost:8000/health
```

#### **Test 5: Start Data Services**
```bash
# Start data feed service
docker-compose -f docker-compose.local.yml up -d data-feed

# Start signal generator service
docker-compose -f docker-compose.local.yml up -d signal-generator

# Monitor service logs
docker-compose -f docker-compose.local.yml logs -f data-feed signal-generator

# Verify services are running
docker-compose -f docker-compose.local.yml ps
```

#### **Test 6: Start Frontend Service**
```bash
# Start frontend service
docker-compose -f docker-compose.local.yml up -d frontend

# Monitor frontend build and startup
docker-compose -f docker-compose.local.yml logs -f frontend

# Test frontend accessibility
curl http://localhost:3000

# Open in browser
open http://localhost:3000
```

### 🔍 **DOCKER SYSTEM VALIDATION**

#### **Test 7: Complete System Health Check**
```bash
# Check all service status
docker-compose -f docker-compose.local.yml ps

# Expected output: All services "Up" and healthy

# Test all health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/live

# Test frontend loading
curl -I http://localhost:3000
```

#### **Test 8: Inter-Service Communication**
```bash
# Test backend to database
docker-compose -f docker-compose.local.yml exec backend python -c "
from app.database import engine
import asyncio
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT 1')
        print('Database connection: OK')
asyncio.run(test())
"

# Test backend to Redis
docker-compose -f docker-compose.local.yml exec backend python -c "
import redis
import os
r = redis.from_url(os.getenv('REDIS_URL'))
r.ping()
print('Redis connection: OK')
"

# Test data feed to backend API
docker-compose -f docker-compose.local.yml exec data-feed curl -f http://backend:8000/health
```

#### **Test 9: Container Resource Usage**
```bash
# Monitor container resource usage
docker stats

# Check container logs for errors
docker-compose -f docker-compose.local.yml logs --tail=50 backend
docker-compose -f docker-compose.local.yml logs --tail=50 data-feed
docker-compose -f docker-compose.local.yml logs --tail=50 signal-generator

# Verify no memory leaks or excessive CPU usage
```

### 📊 **DOCKER PERFORMANCE TESTING**

#### **Test 10: Container Startup Time**
```bash
# Measure startup time for each service
time docker-compose -f docker-compose.local.yml up -d postgres
time docker-compose -f docker-compose.local.yml up -d redis
time docker-compose -f docker-compose.local.yml up -d backend
time docker-compose -f docker-compose.local.yml up -d data-feed
time docker-compose -f docker-compose.local.yml up -d signal-generator
time docker-compose -f docker-compose.local.yml up -d frontend

# Target startup times:
# postgres: < 10 seconds
# redis: < 5 seconds
# backend: < 30 seconds
# data-feed: < 20 seconds
# signal-generator: < 20 seconds
# frontend: < 60 seconds (includes build)
```

#### **Test 11: Image Size Optimization**
```bash
# Check image sizes
docker images | grep crypto

# Target image sizes:
# backend: < 500MB
# data-feed: < 400MB
# signal-generator: < 400MB
# frontend: < 200MB (multi-stage build)

# Analyze image layers
docker history crypto-0dte-system_backend:latest
```

#### **Test 12: Memory and CPU Usage**
```bash
# Monitor resource usage during operation
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Target resource usage:
# postgres: < 100MB RAM, < 5% CPU
# redis: < 50MB RAM, < 2% CPU
# backend: < 200MB RAM, < 10% CPU
# data-feed: < 150MB RAM, < 5% CPU
# signal-generator: < 150MB RAM, < 5% CPU
# frontend: < 100MB RAM, < 2% CPU
```

### 🔄 **DOCKER INTEGRATION TESTING**

#### **Test 13: End-to-End Workflow**
```bash
# Test complete trading workflow through Docker containers

# 1. Verify market data collection
docker-compose -f docker-compose.local.yml exec data-feed python -c "
from app.services.delta_exchange_service import DeltaExchangeService
import asyncio
async def test():
    service = DeltaExchangeService()
    data = await service.get_market_data('BTC-USDT')
    print(f'Market data: {data}')
asyncio.run(test())
"

# 2. Verify signal generation
docker-compose -f docker-compose.local.yml exec signal-generator python -c "
from app.services.signal_generation_service import SignalGenerationService
import asyncio
async def test():
    service = SignalGenerationService()
    signal = await service.generate_signal('BTC-USDT')
    print(f'Generated signal: {signal}')
asyncio.run(test())
"

# 3. Test API endpoints
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"testpass123"}'

curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"testpass123"}'
```

#### **Test 14: WebSocket Functionality**
```bash
# Test WebSocket connections through Docker network
docker-compose -f docker-compose.local.yml exec backend python -c "
import asyncio
import websockets

async def test_websocket():
    uri = 'ws://localhost:8000/ws'
    async with websockets.connect(uri) as websocket:
        await websocket.send('test message')
        response = await websocket.recv()
        print(f'WebSocket response: {response}')

asyncio.run(test_websocket())
"
```

### 🛠️ **DOCKER TROUBLESHOOTING**

#### **Common Docker Issues:**

**Build Failures:**
```bash
# Clear Docker build cache
docker builder prune -a

# Rebuild with no cache
docker-compose -f docker-compose.local.yml build --no-cache

# Check Dockerfile syntax
docker build --dry-run -f backend/Dockerfile.railway .
```

**Service Startup Failures:**
```bash
# Check service logs
docker-compose -f docker-compose.local.yml logs [service-name]

# Inspect container configuration
docker inspect [container-name]

# Check service dependencies
docker-compose -f docker-compose.local.yml config
```

**Network Connectivity Issues:**
```bash
# Test network connectivity between containers
docker-compose -f docker-compose.local.yml exec backend ping postgres
docker-compose -f docker-compose.local.yml exec backend ping redis

# Check network configuration
docker network ls
docker network inspect crypto-0dte-local_crypto-network
```

**Resource Issues:**
```bash
# Check available system resources
docker system df
docker system prune

# Monitor resource usage
docker stats --no-stream
```

### 🧹 **DOCKER CLEANUP PROCEDURES**

#### **Development Cleanup:**
```bash
# Stop all services
docker-compose -f docker-compose.local.yml down

# Remove containers and networks
docker-compose -f docker-compose.local.yml down --remove-orphans

# Remove volumes (WARNING: This deletes all data)
docker-compose -f docker-compose.local.yml down -v

# Clean up unused Docker resources
docker system prune -a
```

#### **Reset to Clean State:**
```bash
# Complete reset (WARNING: Removes all data)
docker-compose -f docker-compose.local.yml down -v --remove-orphans
docker system prune -a -f
docker volume prune -f

# Rebuild everything from scratch
docker-compose -f docker-compose.local.yml build --no-cache
docker-compose -f docker-compose.local.yml up -d
```

### ✅ **DOCKER TESTING CHECKLIST**

Before proceeding to Railway deployment:

**Build and Images:**
- [ ] All Docker images build successfully
- [ ] Image sizes are within acceptable limits
- [ ] No security vulnerabilities in base images
- [ ] Multi-stage builds optimize final image size

**Service Orchestration:**
- [ ] All services start in correct order
- [ ] Health checks pass for all services
- [ ] Inter-service communication works
- [ ] Service dependencies resolve correctly

**Functionality:**
- [ ] Database migrations run successfully
- [ ] API endpoints respond correctly
- [ ] WebSocket connections establish
- [ ] Real-time data flows between services

**Performance:**
- [ ] Startup times meet targets
- [ ] Resource usage within limits
- [ ] No memory leaks detected
- [ ] CPU usage remains reasonable

**Integration:**
- [ ] End-to-end workflows function
- [ ] External API integrations work
- [ ] Frontend connects to backend
- [ ] Authentication flow completes

### 🎯 **DOCKER SUCCESS CRITERIA**

Docker testing is complete when:

1. **All services start** without errors
2. **Health checks pass** consistently
3. **Resource usage** stays within targets
4. **Integration tests** pass completely
5. **Performance metrics** meet requirements
6. **No critical errors** in logs
7. **Complete workflows** function end-to-end

### 🚀 **RAILWAY DEPLOYMENT CONFIDENCE**

Successful Docker testing provides:

- **99% deployment confidence** for Railway
- **Identical runtime environment** validation
- **Performance characteristics** verification
- **Resource requirement** confirmation
- **Integration behavior** validation

**If it works in Docker locally, it WILL work on Railway!**

