#!/bin/bash

# Crypto-0DTE-System Local Deployment Script
# One-click deployment for development and testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="crypto-0dte-system"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

echo -e "${PURPLE}🚀 Crypto-0DTE-System Local Deployment${NC}"
echo -e "${CYAN}AI-Powered BTC/ETH Trading on Delta Exchange${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_deps=()
    
    if ! command_exists docker; then
        missing_deps+=("docker")
    fi
    
    if ! command_exists docker-compose; then
        missing_deps+=("docker-compose")
    fi
    
    if ! command_exists git; then
        missing_deps+=("git")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        echo ""
        echo "Please install the missing dependencies:"
        echo "  - Docker: https://docs.docker.com/get-docker/"
        echo "  - Docker Compose: https://docs.docker.com/compose/install/"
        echo "  - Git: https://git-scm.com/downloads"
        exit 1
    fi
    
    print_success "All prerequisites satisfied"
}

# Create environment file if it doesn't exist
create_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_status "Creating environment file..."
        
        cat > "$ENV_FILE" << EOF
# Crypto-0DTE-System Environment Configuration

# Application Settings
APP_NAME=crypto-0dte-system
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# API Keys (Replace with your actual keys)
DELTA_EXCHANGE_API_KEY=your_delta_exchange_api_key_here
DELTA_EXCHANGE_API_SECRET=your_delta_exchange_api_secret_here
DELTA_EXCHANGE_PASSPHRASE=your_delta_exchange_passphrase_here
DELTA_EXCHANGE_SANDBOX=true

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1

# External Data APIs
POLYGON_API_KEY=your_polygon_api_key_here
COINGECKO_API_KEY=your_coingecko_api_key_here
FEAR_GREED_API_URL=https://api.alternative.me/fng/

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=crypto_0dte
POSTGRES_USER=crypto_trader
POSTGRES_PASSWORD=secure_crypto_password_2024

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=secure_redis_password_2024

# InfluxDB Configuration
INFLUXDB_HOST=influxdb
INFLUXDB_PORT=8086
INFLUXDB_ORG=crypto-0dte-org
INFLUXDB_BUCKET=market_data
INFLUXDB_TOKEN=secure_influxdb_token_2024

# Trading Configuration
MAX_POSITION_SIZE=0.25
MIN_POSITION_SIZE=0.01
DEFAULT_LEVERAGE=1
RISK_LEVEL=moderate

# Strategy Configuration
STRATEGY_BTC_LIGHTNING_SCALP_ENABLED=true
STRATEGY_ETH_DEFI_CORRELATION_ENABLED=true
STRATEGY_CROSS_ASSET_ARBITRAGE_ENABLED=true
STRATEGY_FUNDING_RATE_ARBITRAGE_ENABLED=false
STRATEGY_FEAR_GREED_CONTRARIAN_ENABLED=true

# Notification Settings
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_email_password_here

# Security Settings
JWT_SECRET_KEY=your_super_secure_jwt_secret_key_here
ENCRYPTION_KEY=your_32_character_encryption_key_here

# Performance Settings
WORKER_PROCESSES=2
MAX_CONNECTIONS=1000
CACHE_TTL=300
MODEL_UPDATE_FREQUENCY=3600

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/app/logs/crypto-0dte.log

# Indian Compliance
ENABLE_TDS_CALCULATION=true
TDS_RATE=0.01
ENABLE_CRYPTO_TAX_REPORTING=true
FINANCIAL_YEAR_START=04-01
EOF
        
        print_success "Environment file created: $ENV_FILE"
        print_warning "Please update the API keys in $ENV_FILE before starting the system"
    else
        print_status "Environment file already exists: $ENV_FILE"
    fi
}

# Start services
start_services() {
    print_status "Starting Crypto-0DTE-System services..."
    
    # Pull latest images
    print_status "Pulling Docker images..."
    docker-compose pull
    
    # Build custom images
    print_status "Building application images..."
    docker-compose build
    
    # Start services
    print_status "Starting all services..."
    docker-compose up -d
    
    print_success "All services started successfully"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for PostgreSQL
    print_status "Waiting for PostgreSQL..."
    timeout 60 bash -c 'until docker-compose exec -T postgres pg_isready -U crypto_trader -d crypto_0dte; do sleep 2; done'
    
    # Wait for Redis
    print_status "Waiting for Redis..."
    timeout 30 bash -c 'until docker-compose exec -T redis redis-cli ping | grep -q PONG; do sleep 2; done'
    
    # Wait for InfluxDB
    print_status "Waiting for InfluxDB..."
    timeout 60 bash -c 'until docker-compose exec -T influxdb influx ping; do sleep 2; done'
    
    # Wait for backend API
    print_status "Waiting for Backend API..."
    timeout 120 bash -c 'until curl -f http://localhost:8000/health >/dev/null 2>&1; do sleep 5; done'
    
    # Wait for frontend
    print_status "Waiting for Frontend..."
    timeout 60 bash -c 'until curl -f http://localhost:3000 >/dev/null 2>&1; do sleep 3; done'
    
    print_success "All services are ready"
}

# Initialize database
initialize_database() {
    print_status "Initializing database..."
    
    # Run database migrations
    docker-compose exec backend python -m app.scripts.init_db
    
    # Create sample data (optional)
    if [ "$1" = "--with-sample-data" ]; then
        print_status "Creating sample data..."
        docker-compose exec backend python -m app.scripts.generate_sample_data
    fi
    
    print_success "Database initialized"
}

# Run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    local failed_checks=()
    
    # Check backend health
    if ! curl -f http://localhost:8000/health >/dev/null 2>&1; then
        failed_checks+=("Backend API")
    fi
    
    # Check frontend
    if ! curl -f http://localhost:3000 >/dev/null 2>&1; then
        failed_checks+=("Frontend")
    fi
    
    # Check database connection
    if ! docker-compose exec -T backend python -c "from app.database import test_connection; test_connection()" >/dev/null 2>&1; then
        failed_checks+=("Database Connection")
    fi
    
    # Check Redis connection
    if ! docker-compose exec -T backend python -c "from app.database import test_redis; test_redis()" >/dev/null 2>&1; then
        failed_checks+=("Redis Connection")
    fi
    
    if [ ${#failed_checks[@]} -ne 0 ]; then
        print_error "Health check failures: ${failed_checks[*]}"
        return 1
    fi
    
    print_success "All health checks passed"
    return 0
}

# Display system information
show_system_info() {
    echo ""
    echo -e "${GREEN}🎉 Crypto-0DTE-System Successfully Deployed!${NC}"
    echo ""
    echo -e "${CYAN}📊 Access Points:${NC}"
    echo -e "  Frontend Dashboard: ${YELLOW}http://localhost:3000${NC}"
    echo -e "  Backend API:        ${YELLOW}http://localhost:8000${NC}"
    echo -e "  API Documentation:  ${YELLOW}http://localhost:8000/docs${NC}"
    echo -e "  InfluxDB UI:        ${YELLOW}http://localhost:8086${NC}"
    echo ""
    echo -e "${CYAN}🔧 Management Commands:${NC}"
    echo -e "  View logs:          ${YELLOW}docker-compose logs -f${NC}"
    echo -e "  Stop system:        ${YELLOW}docker-compose down${NC}"
    echo -e "  Restart system:     ${YELLOW}docker-compose restart${NC}"
    echo -e "  Update system:      ${YELLOW}git pull && docker-compose up -d --build${NC}"
    echo ""
    echo -e "${CYAN}📈 Trading Strategies:${NC}"
    echo -e "  • BTC Lightning Scalp (5-30 min trades)"
    echo -e "  • ETH DeFi Correlation (ecosystem-based)"
    echo -e "  • Cross-Asset Arbitrage (BTC/ETH correlation)"
    echo -e "  • Funding Rate Arbitrage (perpetual contracts)"
    echo -e "  • Fear & Greed Contrarian (sentiment-based)"
    echo ""
    echo -e "${CYAN}⚠️  Important Notes:${NC}"
    echo -e "  • Update API keys in ${YELLOW}.env${NC} file"
    echo -e "  • Enable strategies in the Settings tab"
    echo -e "  • Start with paper trading to test the system"
    echo -e "  • Monitor the AI Signals tab for trading activity"
    echo ""
    echo -e "${PURPLE}🚀 Ready for AI-Powered Crypto Trading!${NC}"
}

# Cleanup function
cleanup() {
    if [ $? -ne 0 ]; then
        print_error "Deployment failed. Cleaning up..."
        docker-compose down >/dev/null 2>&1 || true
    fi
}

# Main deployment function
main() {
    trap cleanup EXIT
    
    echo -e "${BLUE}Starting deployment at $(date)${NC}"
    echo ""
    
    # Parse command line arguments
    SAMPLE_DATA=false
    SKIP_HEALTH_CHECK=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --with-sample-data)
                SAMPLE_DATA=true
                shift
                ;;
            --skip-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --with-sample-data    Create sample trading data"
                echo "  --skip-health-check   Skip health checks after deployment"
                echo "  --help               Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Run deployment steps
    check_prerequisites
    create_env_file
    start_services
    wait_for_services
    
    if [ "$SAMPLE_DATA" = true ]; then
        initialize_database --with-sample-data
    else
        initialize_database
    fi
    
    if [ "$SKIP_HEALTH_CHECK" = false ]; then
        if ! run_health_checks; then
            print_error "Health checks failed. Please check the logs:"
            echo "  docker-compose logs"
            exit 1
        fi
    fi
    
    show_system_info
    
    print_success "Deployment completed successfully in $SECONDS seconds"
}

# Run main function
main "$@"

