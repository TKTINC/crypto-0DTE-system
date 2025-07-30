# Crypto-0DTE-System Terraform Outputs

output "frontend_url" {
  description = "URL of the frontend application"
  value       = "http://${aws_lb.main.dns_name}"
}

output "backend_url" {
  description = "URL of the backend API"
  value       = "http://${aws_lb.main.dns_name}/api"
}

output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "database_endpoint" {
  description = "RDS database endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "database_port" {
  description = "RDS database port"
  value       = aws_db_instance.main.port
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = aws_elasticache_replication_group.main.port
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "security_group_alb_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "security_group_ecs_id" {
  description = "ID of the ECS security group"
  value       = aws_security_group.ecs.id
}

output "ecr_repository_urls" {
  description = "URLs of the ECR repositories"
  value = {
    backend          = aws_ecr_repository.backend.repository_url
    frontend         = aws_ecr_repository.frontend.repository_url
    data_feed        = aws_ecr_repository.data_feed.repository_url
    signal_generator = aws_ecr_repository.signal_generator.repository_url
  }
}

output "cloudwatch_log_groups" {
  description = "Names of the CloudWatch log groups"
  value = {
    backend          = aws_cloudwatch_log_group.backend.name
    frontend         = aws_cloudwatch_log_group.frontend.name
    data_feed        = aws_cloudwatch_log_group.data_feed.name
    signal_generator = aws_cloudwatch_log_group.signal_generator.name
  }
}

output "ssm_parameter_names" {
  description = "Names of the SSM parameters for API keys"
  value = {
    delta_exchange_api_key = aws_ssm_parameter.delta_exchange_api_key.name
    openai_api_key         = aws_ssm_parameter.openai_api_key.name
  }
}

output "database_password_command" {
  description = "Command to retrieve database password"
  value       = "terraform output -raw database_password"
}

output "redis_password_command" {
  description = "Command to retrieve Redis password"
  value       = "terraform output -raw redis_password"
}

output "database_password" {
  description = "Database password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "redis_password" {
  description = "Redis password"
  value       = random_password.redis_password.result
  sensitive   = true
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "project_name" {
  description = "Project name"
  value       = var.project_name
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

