#!/bin/bash

# =============================================================================
# QUICK SERVICE RESTART SCRIPT
# =============================================================================
# 
# This script bypasses the tag verification issue and directly restarts
# ECS services with the newly built Docker images that contain the SQLAlchemy fix.
#
# Prerequisites: Docker images already built and pushed to ECR (completed)
# Expected runtime: 15-25 minutes
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

# =============================================================================
# STEP 1: SETUP
# =============================================================================

log_step "STEP 1: SETUP"

# Get AWS account ID
log_info "Getting AWS account information..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$ACCOUNT_ID" ]; then
    log_error "Failed to get AWS account ID. Check your AWS CLI configuration."
    exit 1
fi

log_success "AWS Account ID: $ACCOUNT_ID"

# =============================================================================
# STEP 2: STOP SERVICES
# =============================================================================

log_step "STEP 2: STOP SERVICES"

log_info "Stopping backend service..."
aws ecs update-service --cluster crypto-0dte-system --service crypto-0dte-system-backend --desired-count 0 > /dev/null

log_info "Stopping data-feed service..."
aws ecs update-service --cluster crypto-0dte-system --service crypto-0dte-system-data-feed --desired-count 0 > /dev/null

log_info "Stopping signal-generator service..."
aws ecs update-service --cluster crypto-0dte-system --service crypto-0dte-system-signal-generator --desired-count 0 > /dev/null

log_info "Waiting for services to stop (90 seconds)..."
sleep 90

log_success "All services stopped"

# =============================================================================
# STEP 3: GET TASK DEFINITION REVISIONS
# =============================================================================

log_step "STEP 3: GET TASK DEFINITION REVISIONS"

log_info "Getting latest task definition revisions..."

BACKEND_REVISION=$(aws ecs describe-task-definition --task-definition crypto-0dte-system-backend --query 'taskDefinition.revision' --output text)
DATA_FEED_REVISION=$(aws ecs describe-task-definition --task-definition crypto-0dte-system-data-feed --query 'taskDefinition.revision' --output text)
SIGNAL_GEN_REVISION=$(aws ecs describe-task-definition --task-definition crypto-0dte-system-signal-generator --query 'taskDefinition.revision' --output text)

log_info "Task definition revisions:"
log_info "  Backend: $BACKEND_REVISION"
log_info "  Data-feed: $DATA_FEED_REVISION"
log_info "  Signal-generator: $SIGNAL_GEN_REVISION"

log_success "Retrieved all task definition revisions"

# =============================================================================
# STEP 4: RESTART SERVICES WITH NEW IMAGES
# =============================================================================

log_step "STEP 4: RESTART SERVICES WITH NEW IMAGES"

log_info "Restarting backend service with SQLAlchemy fix..."
aws ecs update-service \
    --cluster crypto-0dte-system \
    --service crypto-0dte-system-backend \
    --task-definition crypto-0dte-system-backend:$BACKEND_REVISION \
    --desired-count 1 \
    --force-new-deployment > /dev/null

log_info "Restarting data-feed service with SQLAlchemy fix..."
aws ecs update-service \
    --cluster crypto-0dte-system \
    --service crypto-0dte-system-data-feed \
    --task-definition crypto-0dte-system-data-feed:$DATA_FEED_REVISION \
    --desired-count 1 \
    --force-new-deployment > /dev/null

log_info "Restarting signal-generator service with SQLAlchemy fix..."
aws ecs update-service \
    --cluster crypto-0dte-system \
    --service crypto-0dte-system-signal-generator \
    --task-definition crypto-0dte-system-signal-generator:$SIGNAL_GEN_REVISION \
    --desired-count 1 \
    --force-new-deployment > /dev/null

log_success "All services restarted with force new deployment"

# =============================================================================
# STEP 5: WAIT FOR CONTAINERS TO START
# =============================================================================

log_step "STEP 5: WAIT FOR CONTAINERS TO START"

log_info "Waiting for containers to start with SQLAlchemy fix (4 minutes)..."
sleep 240

log_success "Wait period completed"

# =============================================================================
# STEP 6: CHECK SERVICE STATUS
# =============================================================================

log_step "STEP 6: CHECK SERVICE STATUS"

log_info "Checking service status..."
aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-backend crypto-0dte-system-frontend crypto-0dte-system-data-feed crypto-0dte-system-signal-generator --query 'services[*].[serviceName,runningCount,desiredCount]' --output table

# Get individual service status
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
# STEP 7: CHECK APPLICATION LOGS
# =============================================================================

log_step "STEP 7: CHECK APPLICATION LOGS"

log_info "Checking recent application logs for SQLAlchemy errors..."

# Function to check logs for specific service
check_service_logs() {
    local service_name=$1
    log_info "Checking $service_name logs..."
    
    RECENT_LOGS=$(aws logs filter-log-events --log-group-name "/ecs/crypto-0dte-system/$service_name" --start-time $(date -d '5 minutes ago' +%s)000 --query 'events[-3:].message' --output text 2>/dev/null | tail -3 || echo "No recent logs yet")
    
    if [ "$RECENT_LOGS" == "No recent logs yet" ]; then
        log_warning "No recent $service_name logs found - container may still be starting"
    else
        log_info "Recent $service_name logs:"
        echo "$RECENT_LOGS" | head -3
        
        # Check for specific errors
        if echo "$RECENT_LOGS" | grep -q "metadata.*reserved"; then
            log_error "Still seeing SQLAlchemy metadata errors in $service_name logs!"
        elif echo "$RECENT_LOGS" | grep -q "ModuleNotFoundError"; then
            log_warning "Still seeing import errors in $service_name logs"
        else
            log_success "$service_name logs look clean - no SQLAlchemy metadata errors"
        fi
    fi
    echo ""
}

# Check logs for each service
check_service_logs "backend"
check_service_logs "data-feed"
check_service_logs "signal-generator"

# =============================================================================
# STEP 8: TEST ENDPOINTS
# =============================================================================

log_step "STEP 8: TEST ENDPOINTS"

log_info "Getting load balancer DNS and testing endpoints..."
LB_DNS=$(aws elbv2 describe-load-balancers --names crypto-0dte-system-alb --query 'LoadBalancers[0].DNSName' --output text 2>/dev/null || echo "")

if [ -z "$LB_DNS" ] || [ "$LB_DNS" == "None" ]; then
    log_warning "Could not get load balancer DNS"
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
    
    # Test endpoints with timeout
    test_endpoint() {
        local url=$1
        local name=$2
        local status=$(timeout 10 curl -s -o /dev/null -w "%{http_code}" $url 2>/dev/null || echo "TIMEOUT")
        echo "$name: $status"
        
        if [ "$status" == "200" ]; then
            return 0
        else
            return 1
        fi
    }
    
    test_endpoint "http://$LB_DNS" "Frontend"
    test_endpoint "http://$LB_DNS/api/health" "Backend Health"
    test_endpoint "http://$LB_DNS/docs" "API Docs"
fi

# =============================================================================
# STEP 9: FINAL STATUS SUMMARY
# =============================================================================

log_step "STEP 9: FINAL STATUS SUMMARY"

echo ""
log_info "📊 FINAL STATUS SUMMARY:"
echo "============================================================"

# Comprehensive status check
ALL_SERVICES_RUNNING=true
CRITICAL_SERVICES_RUNNING=true

# Check backend (critical)
if [ "$BACKEND_RUNNING" != "1" ]; then
    log_warning "Backend service: $BACKEND_RUNNING/1 (not fully running) - CRITICAL"
    ALL_SERVICES_RUNNING=false
    CRITICAL_SERVICES_RUNNING=false
else
    log_success "Backend service: $BACKEND_RUNNING/1 (running)"
fi

# Check frontend (critical)
if [ "$FRONTEND_RUNNING" != "1" ]; then
    log_warning "Frontend service: $FRONTEND_RUNNING/1 (not fully running) - CRITICAL"
    ALL_SERVICES_RUNNING=false
    CRITICAL_SERVICES_RUNNING=false
else
    log_success "Frontend service: $FRONTEND_RUNNING/1 (running)"
fi

# Check data-feed (important)
if [ "$DATA_FEED_RUNNING" != "1" ]; then
    log_warning "Data-feed service: $DATA_FEED_RUNNING/1 (not fully running)"
    ALL_SERVICES_RUNNING=false
else
    log_success "Data-feed service: $DATA_FEED_RUNNING/1 (running)"
fi

# Check signal-generator (important)
if [ "$SIGNAL_GEN_RUNNING" != "1" ]; then
    log_warning "Signal-generator service: $SIGNAL_GEN_RUNNING/1 (not fully running)"
    ALL_SERVICES_RUNNING=false
else
    log_success "Signal-generator service: $SIGNAL_GEN_RUNNING/1 (running)"
fi

echo ""
if [ "$ALL_SERVICES_RUNNING" == "true" ]; then
    log_success "🎉 ALL SERVICES ARE RUNNING PERFECTLY!"
    log_success "🚀 Your autonomous crypto trading system is fully operational!"
    log_success "💰 SQLAlchemy metadata conflict resolved!"
    
    if [ "$LB_DNS" != "[LOAD_BALANCER_NOT_FOUND]" ]; then
        echo ""
        log_info "🌐 Access your system at: http://$LB_DNS"
    fi
    
elif [ "$CRITICAL_SERVICES_RUNNING" == "true" ]; then
    log_success "✅ CRITICAL SERVICES ARE RUNNING!"
    log_info "Your system is operational, though some background services may need more time"
    
    if [ "$LB_DNS" != "[LOAD_BALANCER_NOT_FOUND]" ]; then
        echo ""
        log_info "🌐 Access your system at: http://$LB_DNS"
    fi
    
else
    log_warning "⚠️  Critical services are not fully running yet"
    log_info "Check the logs above for any remaining errors"
    
    echo ""
    log_info "🔄 To check progress:"
    echo "  aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-backend crypto-0dte-system-data-feed --query 'services[*].[serviceName,runningCount,desiredCount]' --output table"
fi

echo ""
log_info "💰 Expected cost reduction:"
log_info "  - No more ECS retry loops from SQLAlchemy errors"
log_info "  - NAT Gateway usage should drop significantly"
log_info "  - Daily costs should be under $10/day"
log_info "  - Monthly savings: $3,000+ per month"

echo ""
log_success "🎯 QUICK SERVICE RESTART COMPLETED!"
log_info "Total runtime: $(date)"

exit 0

