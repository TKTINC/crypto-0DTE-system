#!/bin/bash

# =============================================================================
# CRYPTO-0DTE-SYSTEM: ENHANCED OPTION A DEPLOYMENT SCRIPT
# =============================================================================
# 
# Enhanced version with improved environment state handling and robustness
# - Validates infrastructure exists before proceeding
# - Handles services in various states (missing, draining, etc.)
# - Includes rollback capability for failed deployments
# - More sophisticated waiting and error handling
#
# Prerequisites:
# - AWS CLI configured with proper permissions
# - Docker installed and running
# - All model files committed to repository
#
# Expected runtime: 25-35 minutes
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

# Enhanced error handling with rollback
handle_error() {
    log_error "Script failed at line $1"
    log_error "Check the output above for details"
    
    if [ -f "/tmp/rollback_state.sh" ]; then
        log_warning "Rollback state available. Run rollback_deployment() if needed."
    fi
    
    exit 1
}

trap 'handle_error $LINENO' ERR

# =============================================================================
# ENHANCED UTILITY FUNCTIONS
# =============================================================================

# Check if service exists
check_service_exists() {
    local service_name=$1
    local service_arn=$(aws ecs describe-services --cluster crypto-0dte-system --services $service_name --query 'services[0].serviceArn' --output text 2>/dev/null)
    
    if [ "$service_arn" == "None" ] || [ -z "$service_arn" ]; then
        return 1
    else
        return 0
    fi
}

# Wait for service to reach stable state
wait_for_service_stable() {
    local service_name=$1
    local max_wait=300  # 5 minutes
    local wait_time=0
    
    log_info "Waiting for $service_name to reach stable state..."
    
    while [ $wait_time -lt $max_wait ]; do
        local running_count=$(aws ecs describe-services --cluster crypto-0dte-system --services $service_name --query 'services[0].runningCount' --output text 2>/dev/null)
        local desired_count=$(aws ecs describe-services --cluster crypto-0dte-system --services $service_name --query 'services[0].desiredCount' --output text 2>/dev/null)
        local deployment_status=$(aws ecs describe-services --cluster crypto-0dte-system --services $service_name --query 'services[0].deployments[0].status' --output text 2>/dev/null)
        
        if [ "$running_count" == "$desired_count" ] && [ "$deployment_status" == "PRIMARY" ]; then
            log_success "$service_name is stable ($running_count/$desired_count running)"
            return 0
        fi
        
        log_info "$service_name status: $running_count/$desired_count running, deployment: $deployment_status"
        sleep 30
        wait_time=$((wait_time + 30))
    done
    
    log_error "$service_name did not reach stable state within $max_wait seconds"
    return 1
}

# Store current state for rollback
store_current_state() {
    log_info "Storing current state for potential rollback..."
    
    # Create rollback state file
    cat > /tmp/rollback_state.sh << EOF
#!/bin/bash
# Rollback state captured at $(date)

# Current task definition revisions
BACKEND_PREV_REVISION=\$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-backend --query 'services[0].taskDefinition' --output text 2>/dev/null | cut -d':' -f6 || echo "1")
DATA_FEED_PREV_REVISION=\$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-data-feed --query 'services[0].taskDefinition' --output text 2>/dev/null | cut -d':' -f6 || echo "1")
SIGNAL_GEN_PREV_REVISION=\$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-signal-generator --query 'services[0].taskDefinition' --output text 2>/dev/null | cut -d':' -f6 || echo "1")

# Current desired counts
BACKEND_PREV_DESIRED=\$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-backend --query 'services[0].desiredCount' --output text 2>/dev/null || echo "0")
DATA_FEED_PREV_DESIRED=\$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-data-feed --query 'services[0].desiredCount' --output text 2>/dev/null || echo "0")
SIGNAL_GEN_PREV_DESIRED=\$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-signal-generator --query 'services[0].desiredCount' --output text 2>/dev/null || echo "0")

rollback_deployment() {
    echo "🔄 Rolling back to previous state..."
    
    if [ "\$BACKEND_PREV_REVISION" != "None" ] && [ -n "\$BACKEND_PREV_REVISION" ]; then
        aws ecs update-service --cluster crypto-0dte-system --service crypto-0dte-system-backend --task-definition crypto-0dte-system-backend:\$BACKEND_PREV_REVISION --desired-count \$BACKEND_PREV_DESIRED
    fi
    
    if [ "\$DATA_FEED_PREV_REVISION" != "None" ] && [ -n "\$DATA_FEED_PREV_REVISION" ]; then
        aws ecs update-service --cluster crypto-0dte-system --service crypto-0dte-system-data-feed --task-definition crypto-0dte-system-data-feed:\$DATA_FEED_PREV_REVISION --desired-count \$DATA_FEED_PREV_DESIRED
    fi
    
    if [ "\$SIGNAL_GEN_PREV_REVISION" != "None" ] && [ -n "\$SIGNAL_GEN_PREV_REVISION" ]; then
        aws ecs update-service --cluster crypto-0dte-system --service crypto-0dte-system-signal-generator --task-definition crypto-0dte-system-signal-generator:\$SIGNAL_GEN_PREV_REVISION --desired-count \$SIGNAL_GEN_PREV_DESIRED
    fi
    
    echo "✅ Rollback completed"
}
EOF
    
    chmod +x /tmp/rollback_state.sh
    log_success "Current state stored in /tmp/rollback_state.sh"
}

# Validate infrastructure exists
validate_infrastructure() {
    log_info "Validating infrastructure components..."
    
    # Check cluster exists
    local cluster_status=$(aws ecs describe-clusters --clusters crypto-0dte-system --query 'clusters[0].status' --output text 2>/dev/null)
    if [ "$cluster_status" != "ACTIVE" ]; then
        log_error "ECS cluster crypto-0dte-system is not active or doesn't exist"
        log_error "Please run the full deployment script first to create infrastructure"
        return 1
    fi
    log_success "ECS cluster crypto-0dte-system is active"
    
    # Check ECR repositories exist
    local repos=("backend" "data-feed" "signal-generator" "frontend")
    for repo in "${repos[@]}"; do
        local repo_uri=$(aws ecr describe-repositories --repository-names crypto-0dte-system-$repo --query 'repositories[0].repositoryUri' --output text 2>/dev/null)
        if [ "$repo_uri" == "None" ] || [ -z "$repo_uri" ]; then
            log_error "ECR repository crypto-0dte-system-$repo doesn't exist"
            log_error "Please run the full deployment script first to create ECR repositories"
            return 1
        fi
        log_success "ECR repository crypto-0dte-system-$repo exists"
    done
    
    # Check load balancer exists (warning only)
    local lb_arn=$(aws elbv2 describe-load-balancers --names crypto-0dte-system-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null)
    if [ "$lb_arn" == "None" ] || [ -z "$lb_arn" ]; then
        log_warning "Load balancer crypto-0dte-system-alb doesn't exist - endpoints may not work"
    else
        log_success "Load balancer crypto-0dte-system-alb exists"
    fi
    
    log_success "Infrastructure validation completed"
}

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

# Validate infrastructure exists
validate_infrastructure

log_success "All prerequisites validated"

# =============================================================================
# STEP 1: VERIFY MODEL FILES AND STORE CURRENT STATE
# =============================================================================

log_step "STEP 1: VERIFY MODEL FILES AND STORE CURRENT STATE"

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

# Store current state for rollback
store_current_state

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

# Function to build and push image
build_and_push_image() {
    local service_name=$1
    local directory=$2
    
    log_info "Building $service_name image..."
    cd $directory
    
    # Build with no cache to ensure new model files are included
    docker build --no-cache -t crypto-0dte-system-$service_name .
    
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

# Build all three images
build_and_push_image "backend" "backend"
build_and_push_image "data-feed" "data-feed"
build_and_push_image "signal-generator" "signal-generator"

log_success "All Docker images rebuilt and pushed with model fixes"

# =============================================================================
# STEP 4: ENHANCED SERVICE STATE MANAGEMENT
# =============================================================================

log_step "STEP 4: ENHANCED SERVICE STATE MANAGEMENT"

SERVICES=("crypto-0dte-system-backend" "crypto-0dte-system-data-feed" "crypto-0dte-system-signal-generator")

# Check which services exist and their current state
for service in "${SERVICES[@]}"; do
    if check_service_exists $service; then
        local current_desired=$(aws ecs describe-services --cluster crypto-0dte-system --services $service --query 'services[0].desiredCount' --output text)
        local current_running=$(aws ecs describe-services --cluster crypto-0dte-system --services $service --query 'services[0].runningCount' --output text)
        log_info "$service exists: $current_running/$current_desired running"
        
        if [ "$current_desired" != "0" ]; then
            log_info "Stopping $service..."
            aws ecs update-service --cluster crypto-0dte-system --service $service --desired-count 0 > /dev/null
        else
            log_info "$service is already stopped"
        fi
    else
        log_warning "$service does not exist - will need to create it"
        # Note: This script assumes services exist. For creating services, use the full deployment script.
    fi
done

# Wait for all services to stop
log_info "Waiting for all services to stop..."
for service in "${SERVICES[@]}"; do
    if check_service_exists $service; then
        wait_for_service_stable $service
    fi
done

log_success "All existing services are stopped"

# =============================================================================
# STEP 5: GET LATEST TASK DEFINITION REVISIONS
# =============================================================================

log_step "STEP 5: GET LATEST TASK DEFINITION REVISIONS"

log_info "Getting latest task definition revisions..."

BACKEND_REVISION=$(aws ecs describe-task-definition --task-definition crypto-0dte-system-backend --query 'taskDefinition.revision' --output text 2>/dev/null || echo "1")
DATA_FEED_REVISION=$(aws ecs describe-task-definition --task-definition crypto-0dte-system-data-feed --query 'taskDefinition.revision' --output text 2>/dev/null || echo "1")
SIGNAL_GEN_REVISION=$(aws ecs describe-task-definition --task-definition crypto-0dte-system-signal-generator --query 'taskDefinition.revision' --output text 2>/dev/null || echo "1")

log_info "Task definition revisions:"
log_info "  Backend: $BACKEND_REVISION"
log_info "  Data-feed: $DATA_FEED_REVISION"
log_info "  Signal-generator: $SIGNAL_GEN_REVISION"

# Verify we have valid revisions
if [ "$BACKEND_REVISION" == "None" ] || [ -z "$BACKEND_REVISION" ]; then
    log_error "Failed to get backend task definition revision"
    log_error "Please run the full deployment script first to create task definitions"
    exit 1
fi

log_success "Retrieved all task definition revisions"

# =============================================================================
# STEP 6: VERIFY TASK DEFINITIONS HAVE CLEAN DATABASE URLS
# =============================================================================

log_step "STEP 6: VERIFY TASK DEFINITIONS HAVE CLEAN DATABASE URLS"

log_info "Verifying backend task definition has clean database URL..."
BACKEND_DB_URL=$(aws ecs describe-task-definition --task-definition crypto-0dte-system-backend:$BACKEND_REVISION --query 'taskDefinition.containerDefinitions[0].environment[?name==`DATABASE_URL`].value' --output text 2>/dev/null)

log_info "Backend database URL: $BACKEND_DB_URL"

# Check for common issues
if [[ "$BACKEND_DB_URL" == *":5432:5432"* ]]; then
    log_error "Backend task definition still has malformed port (5432:5432)!"
    log_error "Please fix the task definition first"
    exit 1
elif [[ "$BACKEND_DB_URL" == *"Warning"* ]] || [[ "$BACKEND_DB_URL" == *"╷"* ]]; then
    log_error "Backend task definition still has Terraform warnings!"
    log_error "Please fix the task definition first"
    exit 1
elif [ "$BACKEND_DB_URL" == "None" ] || [ -z "$BACKEND_DB_URL" ]; then
    log_warning "Backend task definition has no database URL - may be using SSM parameters"
else
    log_success "Backend task definition has clean database URL"
fi

# =============================================================================
# STEP 7: RESTART SERVICES WITH NEW IMAGES
# =============================================================================

log_step "STEP 7: RESTART SERVICES WITH NEW IMAGES"

# Restart services that exist
for service in "${SERVICES[@]}"; do
    if check_service_exists $service; then
        local service_short=$(echo $service | sed 's/crypto-0dte-system-//')
        local revision_var="${service_short^^}_REVISION"
        local revision=${!revision_var}
        
        log_info "Restarting $service with new image (revision $revision)..."
        aws ecs update-service \
            --cluster crypto-0dte-system \
            --service $service \
            --task-definition crypto-0dte-system-$service_short:$revision \
            --desired-count 1 \
            --force-new-deployment > /dev/null
        
        log_success "$service restart initiated"
    else
        log_warning "$service does not exist - skipping restart"
    fi
done

log_success "All existing services restarted with new images"

# =============================================================================
# STEP 8: ENHANCED WAITING FOR CONTAINERS TO START
# =============================================================================

log_step "STEP 8: ENHANCED WAITING FOR CONTAINERS TO START"

log_info "Waiting for containers to start and reach stable state..."

# Wait for each service individually with better monitoring
for service in "${SERVICES[@]}"; do
    if check_service_exists $service; then
        log_info "Monitoring $service startup..."
        wait_for_service_stable $service
    fi
done

log_success "All services have reached stable state"

# =============================================================================
# STEP 9: COMPREHENSIVE SERVICE STATUS CHECK
# =============================================================================

log_step "STEP 9: COMPREHENSIVE SERVICE STATUS CHECK"

log_info "Checking comprehensive service status..."
aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-backend crypto-0dte-system-frontend crypto-0dte-system-data-feed crypto-0dte-system-signal-generator --query 'services[*].[serviceName,runningCount,desiredCount,lastStatus]' --output table

# Get individual service status for validation
BACKEND_RUNNING=$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-backend --query 'services[0].runningCount' --output text 2>/dev/null || echo "0")
FRONTEND_RUNNING=$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-frontend --query 'services[0].runningCount' --output text 2>/dev/null || echo "0")
DATA_FEED_RUNNING=$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-data-feed --query 'services[0].runningCount' --output text 2>/dev/null || echo "0")
SIGNAL_GEN_RUNNING=$(aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-signal-generator --query 'services[0].runningCount' --output text 2>/dev/null || echo "0")

log_info "Service running counts:"
log_info "  Backend: $BACKEND_RUNNING/1"
log_info "  Frontend: $FRONTEND_RUNNING/1"
log_info "  Data-feed: $DATA_FEED_RUNNING/1"
log_info "  Signal-generator: $SIGNAL_GEN_RUNNING/1"

# =============================================================================
# STEP 10: ENHANCED APPLICATION LOG CHECKING
# =============================================================================

log_step "STEP 10: ENHANCED APPLICATION LOG CHECKING"

log_info "Checking recent application logs for clean startup..."

# Check logs for each service
for service_short in "backend" "data-feed" "signal-generator"; do
    log_info "Checking $service_short logs..."
    
    RECENT_LOGS=$(aws logs filter-log-events --log-group-name "/ecs/crypto-0dte-system/$service_short" --start-time $(date -d '5 minutes ago' +%s)000 --query 'events[-3:].message' --output text 2>/dev/null | tail -3 || echo "No recent logs yet")
    
    if [ "$RECENT_LOGS" == "No recent logs yet" ]; then
        log_warning "No recent $service_short logs found - container may still be starting"
    else
        log_info "Recent $service_short logs:"
        echo "$RECENT_LOGS" | head -3
        
        # Check for specific errors
        if echo "$RECENT_LOGS" | grep -q "ModuleNotFoundError"; then
            log_warning "Still seeing import errors in $service_short logs"
        elif echo "$RECENT_LOGS" | grep -q "5432:5432"; then
            log_warning "Still seeing database port errors in $service_short logs"
        else
            log_success "$service_short logs look clean"
        fi
    fi
    echo ""
done

# =============================================================================
# STEP 11: ENHANCED ENDPOINT TESTING
# =============================================================================

log_step "STEP 11: ENHANCED ENDPOINT TESTING"

log_info "Getting load balancer DNS and testing endpoints..."
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
    log_info "🧪 Testing endpoints (with retries)..."
    
    # Test with retries
    test_endpoint_with_retry() {
        local url=$1
        local name=$2
        local max_retries=3
        local retry=0
        
        while [ $retry -lt $max_retries ]; do
            local status=$(curl -s -o /dev/null -w "%{http_code}" $url 2>/dev/null || echo "ERROR")
            if [ "$status" == "200" ]; then
                echo "$name: $status ✅"
                return 0
            fi
            retry=$((retry + 1))
            if [ $retry -lt $max_retries ]; then
                sleep 10
            fi
        done
        echo "$name: $status ⚠️"
        return 1
    }
    
    test_endpoint_with_retry "http://$LB_DNS" "Frontend"
    test_endpoint_with_retry "http://$LB_DNS/api/health" "Backend Health"
    test_endpoint_with_retry "http://$LB_DNS/docs" "API Docs"
fi

# =============================================================================
# STEP 12: ENHANCED FINAL STATUS SUMMARY
# =============================================================================

log_step "STEP 12: ENHANCED FINAL STATUS SUMMARY"

echo ""
log_info "📊 ENHANCED DEPLOYMENT SUMMARY:"
echo "============================================================"

# Service status summary with enhanced logic
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

# Check data-feed (important but not critical)
if [ "$DATA_FEED_RUNNING" != "1" ]; then
    log_warning "Data-feed service: $DATA_FEED_RUNNING/1 (not fully running)"
    ALL_SERVICES_RUNNING=false
else
    log_success "Data-feed service: $DATA_FEED_RUNNING/1 (running)"
fi

# Check signal-generator (important but not critical)
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
    log_info "This may be normal - containers can take 5-10 minutes to fully start"
    
    echo ""
    log_info "🔄 To check progress:"
    echo "  aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-backend crypto-0dte-system-frontend --query 'services[*].[serviceName,runningCount,desiredCount]' --output table"
    
    echo ""
    log_info "📋 If issues persist:"
    echo "  1. Check CloudWatch logs: aws logs filter-log-events --log-group-name '/ecs/crypto-0dte-system/backend' --start-time \$(date -d '10 minutes ago' +%s)000"
    echo "  2. Check service events: aws ecs describe-services --cluster crypto-0dte-system --services crypto-0dte-system-backend --query 'services[0].events[0:3]'"
    echo "  3. Run rollback if needed: source /tmp/rollback_state.sh && rollback_deployment"
fi

echo ""
log_info "💰 Expected cost reduction:"
log_info "  - No more ECS retry loops"
log_info "  - NAT Gateway usage should drop significantly"
log_info "  - Daily costs should be under $10/day"
log_info "  - Monthly savings: $3,000+ per month"

echo ""
log_info "🛠️  Rollback available:"
log_info "  If you need to rollback: source /tmp/rollback_state.sh && rollback_deployment"

echo ""
log_success "🎯 ENHANCED OPTION A DEPLOYMENT COMPLETED!"
log_info "Total runtime: $(date)"
log_info "Rollback state saved in: /tmp/rollback_state.sh"

exit 0

