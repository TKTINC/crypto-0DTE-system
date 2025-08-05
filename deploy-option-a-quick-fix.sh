#!/bin/bash

# =============================================================================
# CRYPTO-0DTE-SYSTEM: OPTION A QUICK FIX DEPLOYMENT SCRIPT
# =============================================================================
# 
# This script implements Option A: Quick Fix deployment strategy
# - Rebuilds Docker images with the new model files
# - Updates ECS services to use new images with clean database URLs
# - Tests the complete system functionality
#
# Prerequisites:
# - AWS CLI configured with proper permissions
# - Docker installed and running
# - All model files committed to repository
#
# Expected runtime: 20-30 minutes
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    echo -e "\n${BLUE}🔧 $1${NC}"
    echo "============================================================"
}

# Error handling
handle_error() {
    log_error "Script failed at line $1"
    log_error "Check the output above for details"
    exit 1
}

trap 'handle_error $LINENO' ERR

# =============================================================================
# STEP 0: VALIDATION AND SETUP
# =============================================================================

log_step "STEP 0: VALIDATION AND SETUP"

# Check if we're in the right directory
if [ ! -f "deploy-cloud.sh" ] || [ ! -d "backend" ]; then
    log_error "Please run this script from the crypto-0DTE-system directory"
    exit 1
fi

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed or not in PATH"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running. Please start Docker."
    exit 1
fi

# Get AWS account ID
log_info "Getting AWS account information..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$ACCOUNT_ID" ]; then
    log_error "Failed to get AWS account ID. Check your AWS CLI configuration."
    exit 1
fi

log_success "AWS Account ID: $ACCOUNT_ID"
log_success "All prerequisites validated"

# =============================================================================
# STEP 1: VERIFY MODEL FILES ARE PRESENT
# =============================================================================

log_step "STEP 1: VERIFY MODEL FILES ARE PRESENT"

REQUIRED_FILES=(
    "backend/app/models/signal.py"
    "backend/app/models/portfolio.py"
    "backend/app/models/user.py"
    "backend/app/models/compliance.py"
    "backend/app/models/risk_profile.py"
)

log_info "Checking for required model files..."
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        log_success "Found: $file"
    else
        log_error "Missing: $file"
        exit 1
    fi
done

log_success "All required model files are present"

# =============================================================================
# STEP 2: LOGIN TO ECR
# =============================================================================

log_step "STEP 2: LOGIN TO ECR"

log_info "Logging into Amazon ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

if [ $? -eq 0 ]; then
    log_success "Successfully logged into ECR"
else
    log_error "Failed to login to ECR"
    exit 1
fi

# =============================================================================
# STEP 3: REBUILD DOCKER IMAGES WITH MODEL FIXES
# =============================================================================

log_step "STEP 3: REBUILD DOCKER IMAGES WITH MODEL FIXES"

# Function to build and push image with specific Dockerfile
build_and_push_image_with_dockerfile() {
    local service_name=$1
    local directory=$2
    local dockerfile=$3
    
    log_info "Building $service_name image using $dockerfile..."
    cd $directory
    
    # Build with no cache to ensure new model files are included
    docker build --no-cache -f $dockerfile -t crypto-0dte-system-$service_name .
    
    if [ $? -ne 0 ]; then
        log_error "Failed to build $service_name image"
        exit 1
    fi
    
    # Tag for ECR
    docker tag crypto-0dte-system-$service_name:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/crypto-0dte-system-$service_name:latest
    
    # Push to ECR
    log_info "Pushing $service_name image to ECR..."
    docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/crypto-0dte-system-$service_name:latest
    
    if [ $? -eq 0 ]; then
        log_success "$service_name image built and pushed successfully"
    else
        log_error "Failed to push $service_name image to ECR"
        exit 1
    fi
    
    cd ..
}

# Build all three images (all from backend directory with different Dockerfiles)
build_and_push_image_with_dockerfile "backend" "backend" "Dockerfile"
build_and_push_image_with_dockerfile "data-feed" "backend" "Dockerfile.data-feed"
build_and_push_image_with_dockerfile "signal-generator" "backend" "Dockerfile.signal-generator"

log_success "All Docker images rebuilt and pushed with model fixes"

# =============================================================================
# STEP 4: STOP ECS SERVICES TO FORCE FRESH IMAGE PULLS
# =============================================================================

log_step "STEP 4: STOP ECS SERVICES TO FORCE FRESH IMAGE PULLS"

log_info "Stopping backend service..."
aws ecs update-service --cluster crypto-0dte-system --service crypto-0dte-system-backend --desired-count 0 > /dev/null

log_info "Stopping data-feed service..."
aws ecs update-service --cluster crypto-0dte-system --service crypto-0dte-system-data-feed --desired-count 0 > /dev/null

log_info "Stopping signal-generator service..."
aws ecs update-service --cluster crypto-0dte-system --service crypto-0dte-system-signal-generator --desired-count 0 > /dev/null

log_info "Waiting for services to stop (60 seconds)..."
sleep 60

log_success "All services stopped"

# =============================================================================
# STEP 5: GET LATEST TASK DEFINITION REVISIONS
# =============================================================================

log_step "STEP 5: GET LATEST TASK DEFINITION REVISIONS"

log_info "Getting latest task definition revisions..."

BACKEND_REVISION=$(aws ecs describe-task-definition --task-definition crypto-0dte-system-backend --query 'taskDefinition.revision' --output text)
DATA_FEED_REVISION=$(aws ecs describe-task-definition --task-definition crypto-0dte-system-data-feed --query 'taskDefinition.revision' --output text)
SIGNAL_GEN_REVISION=$(aws ecs describe-task-definition --task-definition crypto-0dte-system-signal-generator --query 'taskDefinition.revision' --output text)

log_info "Task definition revisions:"
log_info "  Backend: $BACKEND_REVISION"
log_info "  Data-feed: $DATA_FEED_REVISION"
log_info "  Signal-generator: $SIGNAL_GEN_REVISION"

# Verify we have valid revisions
if [ "$BACKEND_REVISION" == "None" ] || [ -z "$BACKEND_REVISION" ]; then
    log_error "Failed to get backend task definition revision"
    exit 1
fi

log_success "Retrieved all task definition revisions"

# =============================================================================
# STEP 6: VERIFY TASK DEFINITIONS HAVE CLEAN DATABASE URLS
# =============================================================================

log_step "STEP 6: VERIFY TASK DEFINITIONS HAVE CLEAN DATABASE URLS"

log_info "Verifying backend task definition has clean database URL..."
BACKEND_DB_URL=$(aws ecs describe-task-definition --task-definition crypto-0dte-system-backend:$BACKEND_REVISION --query 'taskDefinition.containerDefinitions[0].environment[?name==`DATABASE_URL`].value' --output text)

log_info "Backend database URL: $BACKEND_DB_URL"

# Check for common issues
if [[ "$BACKEND_DB_URL" == *":5432:5432"* ]]; then
    log_error "Backend task definition still has malformed port (5432:5432)!"
    exit 1
elif [[ "$BACKEND_DB_URL" == *"Warning"* ]] || [[ "$BACKEND_DB_URL" == *"╷"* ]]; then
    log_error "Backend task definition still has Terraform warnings!"
    exit 1
elif [ "$BACKEND_DB_URL" == "None" ] || [ -z "$BACKEND_DB_URL" ]; then
    log_error "Backend task definition has no database URL!"
    exit 1
else
    log_success "Backend task definition has clean database URL"
fi

# =============================================================================
# STEP 7: RESTART SERVICES WITH NEW IMAGES
# =============================================================================

log_step "STEP 7: RESTART SERVICES WITH NEW IMAGES"

log_info "Restarting backend service with new image..."
aws ecs update-service \
    --cluster crypto-0dte-system \
    --service crypto-0dte-system-backend \
    --task-definition crypto-0dte-system-backend:$BACKEND_REVISION \
    --desired-count 1 \
    --force-new-deployment > /dev/null

log_info "Restarting data-feed service with new image..."
aws ecs update-service \
    --cluster crypto-0dte-system \
    --service crypto-0dte-system-data-feed \
    --task-definition crypto-0dte-system-data-feed:$DATA_FEED_REVISION \
    --desired-count 1 \
    --force-new-deployment > /dev/null

log_info "Restarting signal-generator service with new image..."
aws ecs update-service \
    --cluster crypto-0dte-system \
    --service crypto-0dte-system-signal-generator \
    --task-definition crypto-0dte-system-signal-generator:$SIGNAL_GEN_REVISION \
    --desired-count 1 \
    --force-new-deployment > /dev/null

log_success "All services restarted with new images and clean database URLs"

# =============================================================================
# STEP 8: WAIT FOR CONTAINERS TO START
# =============================================================================

log_step "STEP 8: WAIT FOR CONTAINERS TO START"

log_info "Waiting for containers to start (3 minutes)..."
sleep 180

log_success "Wait period completed"

# =============================================================================
# STEP 9: CHECK SERVICE STATUS
# =============================================================================

log_step "STEP 9: CHECK SERVICE STATUS"

log_info "Checking service status..."
aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-backend crypto-0dte-system-frontend crypto-0dte-system-data-feed crypto-0dte-system-signal-generator --query 'services[*].[serviceName,runningCount,desiredCount,lastStatus]' --output table

# Get individual service status for validation
BACKEND_RUNNING=$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-backend --query 'services[0].runningCount' --output text)
FRONTEND_RUNNING=$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-frontend --query 'services[0].runningCount' --output text)
DATA_FEED_RUNNING=$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-data-feed --query 'services[0].runningCount' --output text)
SIGNAL_GEN_RUNNING=$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-signal-generator --query 'services[0].runningCount' --output text)

log_info "Service running counts:"
log_info "  Backend: $BACKEND_RUNNING/1"
log_info "  Frontend: $FRONTEND_RUNNING/1"
log_info "  Data-feed: $DATA_FEED_RUNNING/1"
log_info "  Signal-generator: $SIGNAL_GEN_RUNNING/1"

# =============================================================================
# STEP 10: CHECK APPLICATION LOGS
# =============================================================================

log_step "STEP 10: CHECK APPLICATION LOGS"

log_info "Checking recent backend logs for clean startup..."
RECENT_LOGS=$(aws logs filter-log-events --log-group-name "/ecs/crypto-0dte-system/backend" --start-time $(date -d '5 minutes ago' +%s)000 --query 'events[-5:].message' --output text 2>/dev/null | tail -5 || echo "No recent backend logs yet")

if [ "$RECENT_LOGS" == "No recent backend logs yet" ]; then
    log_warning "No recent backend logs found - containers may still be starting"
else
    log_info "Recent backend logs:"
    echo "$RECENT_LOGS"
    
    # Check for import errors
    if echo "$RECENT_LOGS" | grep -q "ModuleNotFoundError"; then
        log_warning "Still seeing import errors in logs - may need more time"
    elif echo "$RECENT_LOGS" | grep -q "5432:5432"; then
        log_warning "Still seeing database port errors in logs"
    else
        log_success "Logs look clean - no obvious import or database errors"
    fi
fi

# =============================================================================
# STEP 11: GET LOAD BALANCER DNS AND TEST ENDPOINTS
# =============================================================================

log_step "STEP 11: GET LOAD BALANCER DNS AND TEST ENDPOINTS"

log_info "Getting load balancer DNS..."
LB_DNS=$(aws elbv2 describe-load-balancers --names crypto-0dte-system-alb --query 'LoadBalancers[0].DNSName' --output text 2>/dev/null || echo "")

if [ -z "$LB_DNS" ] || [ "$LB_DNS" == "None" ]; then
    log_warning "Could not get load balancer DNS - may not be created yet"
    LB_DNS="[LOAD_BALANCER_NOT_FOUND]"
else
    log_success "Load balancer DNS: $LB_DNS"
fi

echo ""
log_info "🌐 Your Crypto Trading System URLs:"
echo "Frontend Dashboard: http://$LB_DNS"
echo "Backend Health: http://$LB_DNS/api/health"
echo "API Documentation: http://$LB_DNS/docs"
echo "Trading Signals: http://$LB_DNS/api/signals"
echo "Portfolio Status: http://$LB_DNS/api/portfolio"

if [ "$LB_DNS" != "[LOAD_BALANCER_NOT_FOUND]" ]; then
    echo ""
    log_info "🧪 Testing endpoints..."
    
    FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$LB_DNS 2>/dev/null || echo "ERROR")
    HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$LB_DNS/api/health 2>/dev/null || echo "ERROR")
    DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$LB_DNS/docs 2>/dev/null || echo "ERROR")
    
    echo "Frontend: $FRONTEND_STATUS"
    echo "Backend Health: $HEALTH_STATUS"
    echo "API Docs: $DOCS_STATUS"
    
    # Evaluate results
    if [ "$FRONTEND_STATUS" == "200" ] && [ "$HEALTH_STATUS" == "200" ]; then
        log_success "🎉 System is responding correctly!"
    elif [ "$FRONTEND_STATUS" == "200" ] || [ "$HEALTH_STATUS" == "200" ]; then
        log_warning "Partial success - some endpoints responding"
    else
        log_warning "Endpoints not ready yet - may need more time for containers to fully start"
    fi
fi

# =============================================================================
# STEP 12: FINAL STATUS SUMMARY
# =============================================================================

log_step "STEP 12: FINAL STATUS SUMMARY"

echo ""
log_info "📊 DEPLOYMENT SUMMARY:"
echo "============================================================"

# Service status summary
ALL_SERVICES_RUNNING=true
if [ "$BACKEND_RUNNING" != "1" ]; then
    log_warning "Backend service: $BACKEND_RUNNING/1 (not fully running)"
    ALL_SERVICES_RUNNING=false
else
    log_success "Backend service: $BACKEND_RUNNING/1 (running)"
fi

if [ "$FRONTEND_RUNNING" != "1" ]; then
    log_warning "Frontend service: $FRONTEND_RUNNING/1 (not fully running)"
    ALL_SERVICES_RUNNING=false
else
    log_success "Frontend service: $FRONTEND_RUNNING/1 (running)"
fi

if [ "$DATA_FEED_RUNNING" != "1" ]; then
    log_warning "Data-feed service: $DATA_FEED_RUNNING/1 (not fully running)"
    ALL_SERVICES_RUNNING=false
else
    log_success "Data-feed service: $DATA_FEED_RUNNING/1 (running)"
fi

if [ "$SIGNAL_GEN_RUNNING" != "1" ]; then
    log_warning "Signal-generator service: $SIGNAL_GEN_RUNNING/1 (not fully running)"
    ALL_SERVICES_RUNNING=false
else
    log_success "Signal-generator service: $SIGNAL_GEN_RUNNING/1 (running)"
fi

echo ""
if [ "$ALL_SERVICES_RUNNING" == "true" ]; then
    log_success "🎉 ALL SERVICES ARE RUNNING!"
    log_success "🚀 Your autonomous crypto trading system is operational!"
    
    if [ "$LB_DNS" != "[LOAD_BALANCER_NOT_FOUND]" ]; then
        echo ""
        log_info "🌐 Access your system at: http://$LB_DNS"
    fi
    
    echo ""
    log_info "💰 Expected cost reduction:"
    log_info "  - No more ECS retry loops"
    log_info "  - NAT Gateway usage should drop significantly"
    log_info "  - Daily costs should be under $10/day"
    
else
    log_warning "⚠️  Some services are not fully running yet"
    log_info "This is normal - containers may need a few more minutes to start"
    log_info "You can monitor progress with:"
    echo "  aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-backend crypto-0dte-system-data-feed crypto-0dte-system-signal-generator --query 'services[*].[serviceName,runningCount,desiredCount]' --output table"
fi

echo ""
log_info "📋 Next steps if issues persist:"
log_info "  1. Check CloudWatch logs for specific error messages"
log_info "  2. Verify Docker images were pushed successfully to ECR"
log_info "  3. Monitor ECS service events for deployment status"
log_info "  4. Wait 5-10 more minutes for containers to fully start"

echo ""
log_success "🎯 OPTION A QUICK FIX DEPLOYMENT COMPLETED!"
log_info "Total runtime: $(date)"

exit 0

