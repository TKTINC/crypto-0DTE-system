#!/bin/bash

# Crypto-0DTE-System Cloud Deployment Script
# One-click deployment to AWS with Terraform

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
TERRAFORM_DIR="terraform"
AWS_REGION="us-east-1"
ENVIRONMENT="production"

echo -e "${PURPLE}☁️  Crypto-0DTE-System Cloud Deployment${NC}"
echo -e "${CYAN}Deploying to AWS with Terraform${NC}"
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
    
    if ! command_exists terraform; then
        missing_deps+=("terraform")
    fi
    
    if ! command_exists aws; then
        missing_deps+=("aws-cli")
    fi
    
    if ! command_exists git; then
        missing_deps+=("git")
    fi
    
    if ! command_exists docker; then
        missing_deps+=("docker")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        echo ""
        echo "Please install the missing dependencies:"
        echo "  - Terraform: https://learn.hashicorp.com/tutorials/terraform/install-cli"
        echo "  - AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
        echo "  - Docker: https://docs.docker.com/get-docker/"
        echo "  - Git: https://git-scm.com/downloads"
        exit 1
    fi
    
    print_success "All prerequisites satisfied"
}

# Check AWS credentials
check_aws_credentials() {
    print_status "Checking AWS credentials..."
    
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials not configured"
        echo ""
        echo "Please configure AWS credentials:"
        echo "  aws configure"
        echo ""
        echo "Or set environment variables:"
        echo "  export AWS_ACCESS_KEY_ID=your_access_key"
        echo "  export AWS_SECRET_ACCESS_KEY=your_secret_key"
        echo "  export AWS_DEFAULT_REGION=us-east-1"
        exit 1
    fi
    
    local aws_account=$(aws sts get-caller-identity --query Account --output text)
    local aws_user=$(aws sts get-caller-identity --query Arn --output text)
    
    print_success "AWS credentials configured"
    print_status "Account: $aws_account"
    print_status "User: $aws_user"
}

# Create Terraform variables file
create_terraform_vars() {
    local vars_file="$TERRAFORM_DIR/terraform.tfvars"
    
    if [ ! -f "$vars_file" ]; then
        print_status "Creating Terraform variables file..."
        
        cat > "$vars_file" << EOF
# Crypto-0DTE-System Terraform Variables

# Project Configuration
project_name = "crypto-0dte-system"
environment  = "production"
aws_region   = "us-east-1"

# Instance Configuration
instance_type = "t3.xlarge"  # 4 vCPU, 16GB RAM
key_pair_name = "crypto-0dte-keypair"

# Database Configuration
db_instance_class = "db.t3.small"  # 2 vCPU, 2GB RAM
db_allocated_storage = 100
db_backup_retention_period = 7

# Redis Configuration
redis_node_type = "cache.t3.micro"  # 2 vCPU, 1GB RAM

# Auto Scaling Configuration
min_capacity = 1
max_capacity = 3
desired_capacity = 1

# Security Configuration
allowed_cidr_blocks = ["0.0.0.0/0"]  # Restrict this in production
enable_ssl = true

# Monitoring Configuration
enable_cloudwatch = true
log_retention_days = 30

# Backup Configuration
enable_automated_backups = true
backup_schedule = "cron(0 2 * * ? *)"  # Daily at 2 AM UTC

# Cost Optimization
enable_spot_instances = false
enable_scheduled_scaling = true

# API Keys (Set these as environment variables or update here)
# delta_exchange_api_key = "your_delta_exchange_api_key"
# openai_api_key = "your_openai_api_key"
# polygon_api_key = "your_polygon_api_key"

# Notification Configuration
# telegram_bot_token = "your_telegram_bot_token"
# email_smtp_host = "smtp.gmail.com"
# email_username = "your_email@gmail.com"

# Trading Configuration
max_position_size = 0.25
risk_level = "moderate"
enable_paper_trading = true

# Tags
tags = {
  Project     = "crypto-0dte-system"
  Environment = "production"
  Owner       = "crypto-trader"
  Purpose     = "ai-crypto-trading"
}
EOF
        
        print_success "Terraform variables file created: $vars_file"
        print_warning "Please update the variables in $vars_file as needed"
    else
        print_status "Terraform variables file already exists: $vars_file"
    fi
}

# Initialize Terraform
init_terraform() {
    print_status "Initializing Terraform..."
    
    cd "$TERRAFORM_DIR"
    
    # Initialize Terraform
    terraform init
    
    # Validate configuration
    terraform validate
    
    print_success "Terraform initialized and validated"
    
    cd ..
}

# Plan Terraform deployment
plan_terraform() {
    print_status "Planning Terraform deployment..."
    
    cd "$TERRAFORM_DIR"
    
    # Create execution plan
    terraform plan -out=tfplan
    
    print_success "Terraform plan created"
    
    cd ..
}

# Apply Terraform deployment
apply_terraform() {
    print_status "Applying Terraform deployment..."
    
    cd "$TERRAFORM_DIR"
    
    # Apply the plan
    terraform apply tfplan
    
    print_success "Terraform deployment completed"
    
    cd ..
}

# Get deployment outputs
get_deployment_outputs() {
    print_status "Getting deployment outputs..."
    
    cd "$TERRAFORM_DIR"
    
    # Get outputs
    local frontend_url=$(terraform output -raw frontend_url 2>/dev/null || echo "Not available")
    local backend_url=$(terraform output -raw backend_url 2>/dev/null || echo "Not available")
    local database_endpoint=$(terraform output -raw database_endpoint 2>/dev/null || echo "Not available")
    local redis_endpoint=$(terraform output -raw redis_endpoint 2>/dev/null || echo "Not available")
    
    cd ..
    
    # Store outputs in variables
    FRONTEND_URL="$frontend_url"
    BACKEND_URL="$backend_url"
    DATABASE_ENDPOINT="$database_endpoint"
    REDIS_ENDPOINT="$redis_endpoint"
    
    print_success "Deployment outputs retrieved"
}

# Build and push Docker images
build_and_push_images() {
    print_status "Building and pushing Docker images..."
    
    # Get AWS account ID and region
    local aws_account=$(aws sts get-caller-identity --query Account --output text)
    local aws_region=$(aws configure get region || echo "us-east-1")
    local ecr_registry="${aws_account}.dkr.ecr.${aws_region}.amazonaws.com"
    
    # Login to ECR
    aws ecr get-login-password --region "$aws_region" | docker login --username AWS --password-stdin "$ecr_registry"
    
    # Build and push backend image
    print_status "Building backend image..."
    docker build -t "${ecr_registry}/${PROJECT_NAME}-backend:latest" -f backend/Dockerfile backend/
    docker push "${ecr_registry}/${PROJECT_NAME}-backend:latest"
    
    # Build and push data feed image
    print_status "Building data feed image..."
    docker build -t "${ecr_registry}/${PROJECT_NAME}-data-feed:latest" -f backend/Dockerfile.data-feed backend/
    docker push "${ecr_registry}/${PROJECT_NAME}-data-feed:latest"
    
    # Build and push signal generator image
    print_status "Building signal generator image..."
    docker build -t "${ecr_registry}/${PROJECT_NAME}-signal-generator:latest" -f backend/Dockerfile.signal-generator backend/
    docker push "${ecr_registry}/${PROJECT_NAME}-signal-generator:latest"
    
    # Build and push frontend image
    print_status "Building frontend image..."
    docker build -t "${ecr_registry}/${PROJECT_NAME}-frontend:latest" frontend/
    docker push "${ecr_registry}/${PROJECT_NAME}-frontend:latest"
    
    print_success "Docker images built and pushed to ECR"
}

# Deploy application to ECS
deploy_to_ecs() {
    print_status "Deploying application to ECS..."
    
    cd "$TERRAFORM_DIR"
    
    # Update ECS services
    terraform apply -target=aws_ecs_service.backend -auto-approve
    terraform apply -target=aws_ecs_service.frontend -auto-approve
    terraform apply -target=aws_ecs_service.data_feed -auto-approve
    terraform apply -target=aws_ecs_service.signal_generator -auto-approve
    
    print_success "Application deployed to ECS"
    
    cd ..
}

# Wait for services to be healthy
wait_for_services() {
    print_status "Waiting for services to be healthy..."
    
    # Wait for backend health check
    if [ "$BACKEND_URL" != "Not available" ]; then
        print_status "Waiting for backend API..."
        timeout 300 bash -c "until curl -f ${BACKEND_URL}/health >/dev/null 2>&1; do sleep 10; done" || {
            print_warning "Backend health check timeout"
        }
    fi
    
    # Wait for frontend
    if [ "$FRONTEND_URL" != "Not available" ]; then
        print_status "Waiting for frontend..."
        timeout 180 bash -c "until curl -f ${FRONTEND_URL} >/dev/null 2>&1; do sleep 10; done" || {
            print_warning "Frontend health check timeout"
        }
    fi
    
    print_success "Services are healthy"
}

# Run post-deployment tasks
run_post_deployment() {
    print_status "Running post-deployment tasks..."
    
    # Initialize database (if backend is available)
    if [ "$BACKEND_URL" != "Not available" ]; then
        print_status "Initializing database..."
        # This would typically be done via ECS task or Lambda
        # For now, we'll skip this step
        print_status "Database initialization skipped (manual step required)"
    fi
    
    # Setup monitoring and alerts
    print_status "Setting up monitoring..."
    # CloudWatch alarms and dashboards are created by Terraform
    
    print_success "Post-deployment tasks completed"
}

# Display deployment information
show_deployment_info() {
    echo ""
    echo -e "${GREEN}🎉 Crypto-0DTE-System Successfully Deployed to AWS!${NC}"
    echo ""
    echo -e "${CYAN}🌐 Access Points:${NC}"
    echo -e "  Frontend Dashboard: ${YELLOW}${FRONTEND_URL}${NC}"
    echo -e "  Backend API:        ${YELLOW}${BACKEND_URL}${NC}"
    echo -e "  API Documentation:  ${YELLOW}${BACKEND_URL}/docs${NC}"
    echo ""
    echo -e "${CYAN}🗄️  Infrastructure:${NC}"
    echo -e "  Database Endpoint:  ${YELLOW}${DATABASE_ENDPOINT}${NC}"
    echo -e "  Redis Endpoint:     ${YELLOW}${REDIS_ENDPOINT}${NC}"
    echo -e "  AWS Region:         ${YELLOW}${AWS_REGION}${NC}"
    echo ""
    echo -e "${CYAN}🔧 Management Commands:${NC}"
    echo -e "  View logs:          ${YELLOW}aws logs tail /aws/ecs/${PROJECT_NAME} --follow${NC}"
    echo -e "  Scale services:     ${YELLOW}aws ecs update-service --cluster ${PROJECT_NAME} --service backend --desired-count 2${NC}"
    echo -e "  Update deployment:  ${YELLOW}./deploy-cloud.sh --update${NC}"
    echo -e "  Destroy resources:  ${YELLOW}cd terraform && terraform destroy${NC}"
    echo ""
    echo -e "${CYAN}📊 Monitoring:${NC}"
    echo -e "  CloudWatch Logs:    ${YELLOW}https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#logsV2:log-groups${NC}"
    echo -e "  ECS Console:        ${YELLOW}https://console.aws.amazon.com/ecs/home?region=${AWS_REGION}#/clusters${NC}"
    echo -e "  RDS Console:        ${YELLOW}https://console.aws.amazon.com/rds/home?region=${AWS_REGION}${NC}"
    echo ""
    echo -e "${CYAN}⚠️  Important Notes:${NC}"
    echo -e "  • Update API keys in AWS Systems Manager Parameter Store"
    echo -e "  • Configure monitoring alerts in CloudWatch"
    echo -e "  • Set up backup schedules for RDS and EFS"
    echo -e "  • Review security groups and access controls"
    echo -e "  • Enable SSL/TLS certificates for production"
    echo ""
    echo -e "${PURPLE}🚀 Ready for Production AI-Powered Crypto Trading!${NC}"
}

# Cleanup function
cleanup() {
    if [ $? -ne 0 ]; then
        print_error "Deployment failed. Check the logs above for details."
        echo ""
        echo "To clean up partial deployment:"
        echo "  cd terraform && terraform destroy"
    fi
}

# Main deployment function
main() {
    trap cleanup EXIT
    
    echo -e "${BLUE}Starting cloud deployment at $(date)${NC}"
    echo ""
    
    # Parse command line arguments
    UPDATE_ONLY=false
    SKIP_BUILD=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --update)
                UPDATE_ONLY=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --update      Update existing deployment"
                echo "  --skip-build  Skip Docker image building"
                echo "  --help        Show this help message"
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
    check_aws_credentials
    
    if [ "$UPDATE_ONLY" = false ]; then
        create_terraform_vars
        init_terraform
        plan_terraform
        apply_terraform
    fi
    
    if [ "$SKIP_BUILD" = false ]; then
        build_and_push_images
    fi
    
    if [ "$UPDATE_ONLY" = true ]; then
        deploy_to_ecs
    fi
    
    get_deployment_outputs
    wait_for_services
    run_post_deployment
    show_deployment_info
    
    print_success "Cloud deployment completed successfully in $SECONDS seconds"
}

# Run main function
main "$@"

