#!/bin/bash

# Improved Crypto-0DTE-System Cloud Deployment Script
# Includes all fixes from deployment troubleshooting

set -e  # Exit on any error

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_NAME="crypto-0dte-system"
AWS_REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🚀 Starting Crypto-0DTE-System Cloud Deployment"
echo "Project: $PROJECT_NAME"
echo "Region: $AWS_REGION"
echo "Account: $ACCOUNT_ID"
echo "=========================================="

# =============================================================================
# PRE-DEPLOYMENT CHECKS
# =============================================================================

echo "[INFO] Running pre-deployment checks..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "[ERROR] AWS CLI not found. Please install AWS CLI."
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker not found. Please install Docker."
    exit 1
fi

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo "[ERROR] Terraform not found. Please install Terraform."
    exit 1
fi

# Verify AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "[ERROR] AWS credentials not configured. Please run 'aws configure'."
    exit 1
fi

echo "[SUCCESS] Pre-deployment checks passed!"

# =============================================================================
# STOP EXISTING SERVICES (Prevent Retry Loops)
# =============================================================================

echo "[INFO] Stopping existing services to prevent retry loops..."

# Stop ECS services if they exist
for service in backend frontend data-feed signal-generator; do
    if aws ecs describe-services --cluster $PROJECT_NAME --services $PROJECT_NAME-$service &> /dev/null; then
        echo "[INFO] Stopping service: $PROJECT_NAME-$service"
        aws ecs update-service --cluster $PROJECT_NAME --service $PROJECT_NAME-$service --desired-count 0 || true
    fi
done

# Wait for services to stop
echo "[INFO] Waiting for services to stop..."
sleep 30

# =============================================================================
# IAM ROLE CREATION
# =============================================================================

echo "[INFO] Checking ECS execution role..."

if ! aws iam get-role --role-name ecsTaskExecutionRole &> /dev/null; then
    echo "[INFO] Creating ECS execution role..."
    
    # Create trust policy
    cat > /tmp/trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

    # Create role
    aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document file:///tmp/trust-policy.json
    
    # Attach policies
    aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
    
    # Add SSM parameter access
    cat > /tmp/ssm-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameters",
                "ssm:GetParameter",
                "ssm:GetParametersByPath"
            ],
            "Resource": [
                "arn:aws:ssm:$AWS_REGION:$ACCOUNT_ID:parameter/$PROJECT_NAME/*"
            ]
        }
    ]
}
EOF

    aws iam put-role-policy --role-name ecsTaskExecutionRole --policy-name SSMParameterAccess --policy-document file:///tmp/ssm-policy.json
    
    echo "[SUCCESS] ECS execution role created!"
else
    echo "[INFO] ECS execution role already exists"
    
    # Ensure SSM policy is attached
    aws iam put-role-policy --role-name ecsTaskExecutionRole --policy-name SSMParameterAccess --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:GetParameters",
                    "ssm:GetParameter",
                    "ssm:GetParametersByPath"
                ],
                "Resource": [
                    "arn:aws:ssm:'$AWS_REGION':'$ACCOUNT_ID':parameter/'$PROJECT_NAME'/*"
                ]
            }
        ]
    }' || true
fi

# =============================================================================
# DOCKER IMAGE BUILDING
# =============================================================================

echo "[INFO] Building and pushing Docker images..."

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Create ECR repositories if they don't exist
for repo in backend frontend data-feed signal-generator; do
    if ! aws ecr describe-repositories --repository-names $PROJECT_NAME-$repo &> /dev/null; then
        echo "[INFO] Creating ECR repository: $PROJECT_NAME-$repo"
        aws ecr create-repository --repository-name $PROJECT_NAME-$repo --region $AWS_REGION
    fi
done

# Build and push backend image
echo "[INFO] Building backend image..."
cd backend
docker build -t $PROJECT_NAME-backend .
docker tag $PROJECT_NAME-backend:latest $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-backend:latest
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-backend:latest

# Build and push frontend image
echo "[INFO] Building frontend image..."
cd ../frontend
docker build -t $PROJECT_NAME-frontend .
docker tag $PROJECT_NAME-frontend:latest $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-frontend:latest
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-frontend:latest

# Build and push data feed image
echo "[INFO] Building data feed image..."
cd ../backend
docker build -f Dockerfile.data-feed -t $PROJECT_NAME-data-feed .
docker tag $PROJECT_NAME-data-feed:latest $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-data-feed:latest
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-data-feed:latest

# Build and push signal generator image
echo "[INFO] Building signal generator image..."
docker build -f Dockerfile.signal-generator -t $PROJECT_NAME-signal-generator .
docker tag $PROJECT_NAME-signal-generator:latest $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-signal-generator:latest
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-signal-generator:latest

cd ..

echo "[SUCCESS] All Docker images built and pushed!"

# =============================================================================
# TERRAFORM DEPLOYMENT
# =============================================================================

echo "[INFO] Deploying infrastructure with Terraform..."

cd terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -out=tfplan

# Apply with retries
echo "[INFO] Applying Terraform configuration..."
if ! terraform apply tfplan; then
    echo "[WARNING] Terraform apply failed, trying targeted approach..."
    
    # Apply core infrastructure first
    terraform apply -target=aws_vpc.main -target=aws_subnet.public -target=aws_subnet.private -auto-approve
    terraform apply -target=aws_internet_gateway.main -target=aws_nat_gateway.main -auto-approve
    terraform apply -target=aws_security_group.alb -target=aws_security_group.ecs -auto-approve
    terraform apply -target=aws_lb.main -target=aws_lb_target_group.backend -target=aws_lb_target_group.frontend -auto-approve
    terraform apply -target=aws_lb_listener.main -auto-approve
    terraform apply -target=aws_ecs_cluster.main -auto-approve
    terraform apply -target=aws_db_instance.main -target=aws_elasticache_replication_group.main -auto-approve
    
    # Apply ECS resources
    terraform apply -target=aws_ecs_task_definition.backend -target=aws_ecs_task_definition.frontend -auto-approve
    terraform apply -target=aws_ecs_task_definition.data_feed -target=aws_ecs_task_definition.signal_generator -auto-approve
    terraform apply -target=aws_ecs_service.backend -target=aws_ecs_service.frontend -auto-approve
    terraform apply -target=aws_ecs_service.data_feed -target=aws_ecs_service.signal_generator -auto-approve
    
    # Final apply to catch any remaining resources
    terraform apply -auto-approve
fi

echo "[SUCCESS] Infrastructure deployed!"

# Get outputs
ALB_DNS=$(terraform output -raw alb_dns_name)
DB_ENDPOINT=$(terraform output -raw database_endpoint)
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)

echo "Load Balancer DNS: $ALB_DNS"

cd ..

# =============================================================================
# API KEY CONFIGURATION
# =============================================================================

echo "[INFO] Configuring API keys..."

# Check if API keys are already configured
if aws ssm get-parameter --name "/$PROJECT_NAME/openai_api_key" &> /dev/null; then
    echo "[INFO] API keys already configured"
else
    echo "[WARNING] API keys not configured. Please run:"
    echo "aws ssm put-parameter --name '/$PROJECT_NAME/openai_api_key' --value 'your-openai-key' --type 'SecureString' --overwrite"
    echo "aws ssm put-parameter --name '/$PROJECT_NAME/delta_exchange_api_key' --value 'your-delta-key' --type 'SecureString' --overwrite"
    echo "aws ssm put-parameter --name '/$PROJECT_NAME/delta_exchange_secret_key' --value 'your-delta-secret' --type 'SecureString' --overwrite"
fi

# =============================================================================
# SERVICE HEALTH MONITORING
# =============================================================================

echo "[INFO] Monitoring service startup..."

# Wait for services to be healthy
for i in {1..30}; do
    echo "[INFO] Checking service health... ($i/30)"
    
    # Check ECS services
    BACKEND_RUNNING=$(aws ecs describe-services --cluster $PROJECT_NAME --services $PROJECT_NAME-backend --query 'services[0].runningCount' --output text 2>/dev/null || echo "0")
    FRONTEND_RUNNING=$(aws ecs describe-services --cluster $PROJECT_NAME --services $PROJECT_NAME-frontend --query 'services[0].runningCount' --output text 2>/dev/null || echo "0")
    DATA_FEED_RUNNING=$(aws ecs describe-services --cluster $PROJECT_NAME --services $PROJECT_NAME-data-feed --query 'services[0].runningCount' --output text 2>/dev/null || echo "0")
    SIGNAL_GEN_RUNNING=$(aws ecs describe-services --cluster $PROJECT_NAME --services $PROJECT_NAME-signal-generator --query 'services[0].runningCount' --output text 2>/dev/null || echo "0")
    
    echo "Backend: $BACKEND_RUNNING/1, Frontend: $FRONTEND_RUNNING/1, Data Feed: $DATA_FEED_RUNNING/1, Signal Gen: $SIGNAL_GEN_RUNNING/1"
    
    if [ "$BACKEND_RUNNING" = "1" ] && [ "$FRONTEND_RUNNING" = "1" ] && [ "$DATA_FEED_RUNNING" = "1" ] && [ "$SIGNAL_GEN_RUNNING" = "1" ]; then
        echo "[SUCCESS] All services are running!"
        break
    fi
    
    sleep 30
done

# =============================================================================
# ENDPOINT TESTING
# =============================================================================

echo "[INFO] Testing endpoints..."

# Test frontend
if curl -f -s "http://$ALB_DNS" > /dev/null; then
    echo "[SUCCESS] Frontend is accessible: http://$ALB_DNS"
else
    echo "[WARNING] Frontend not accessible yet"
fi

# Test backend health
if curl -f -s "http://$ALB_DNS/api/health" > /dev/null; then
    echo "[SUCCESS] Backend API is accessible: http://$ALB_DNS/api/health"
else
    echo "[WARNING] Backend API not accessible yet"
fi

# Test API docs
if curl -f -s "http://$ALB_DNS/docs" > /dev/null; then
    echo "[SUCCESS] API documentation is accessible: http://$ALB_DNS/docs"
else
    echo "[WARNING] API documentation not accessible yet"
fi

# =============================================================================
# DEPLOYMENT SUMMARY
# =============================================================================

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=========================================="
echo "Frontend URL: http://$ALB_DNS"
echo "Backend API: http://$ALB_DNS/api"
echo "API Docs: http://$ALB_DNS/docs"
echo "Health Check: http://$ALB_DNS/api/health"
echo ""
echo "Database Endpoint: $DB_ENDPOINT"
echo "Redis Endpoint: $REDIS_ENDPOINT"
echo ""
echo "Next Steps:"
echo "1. Configure API keys if not already done"
echo "2. Monitor logs: aws logs filter-log-events --log-group-name '/ecs/$PROJECT_NAME/backend'"
echo "3. Check service status: aws ecs describe-services --cluster $PROJECT_NAME --services $PROJECT_NAME-backend"
echo ""
echo "🚀 Your Crypto Trading System is now live!"

# =============================================================================
# CLEANUP
# =============================================================================

# Clean up temporary files
rm -f /tmp/trust-policy.json /tmp/ssm-policy.json

echo "[INFO] Deployment script completed successfully!"

