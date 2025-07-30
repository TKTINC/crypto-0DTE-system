# Crypto-0DTE-System Terraform Variables

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "crypto-0dte-system"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type for ECS tasks"
  type        = string
  default     = "t3.xlarge"
}

variable "key_pair_name" {
  description = "Name of the AWS key pair"
  type        = string
  default     = "crypto-0dte-keypair"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.small"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "db_backup_retention_period" {
  description = "RDS backup retention period in days"
  type        = number
  default     = 7
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "min_capacity" {
  description = "Minimum number of ECS tasks"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 3
}

variable "desired_capacity" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_ssl" {
  description = "Enable SSL/TLS"
  type        = bool
  default     = true
}

variable "enable_cloudwatch" {
  description = "Enable CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "enable_automated_backups" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_schedule" {
  description = "Backup schedule in cron format"
  type        = string
  default     = "cron(0 2 * * ? *)"
}

variable "enable_spot_instances" {
  description = "Enable spot instances for cost optimization"
  type        = bool
  default     = false
}

variable "enable_scheduled_scaling" {
  description = "Enable scheduled scaling"
  type        = bool
  default     = true
}

variable "max_position_size" {
  description = "Maximum position size as percentage of portfolio"
  type        = number
  default     = 0.25
}

variable "risk_level" {
  description = "Risk level (conservative, moderate, aggressive)"
  type        = string
  default     = "moderate"
  
  validation {
    condition     = contains(["conservative", "moderate", "aggressive"], var.risk_level)
    error_message = "Risk level must be one of: conservative, moderate, aggressive."
  }
}

variable "enable_paper_trading" {
  description = "Enable paper trading mode"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "crypto-0dte-system"
    Environment = "production"
    Owner       = "crypto-trader"
    Purpose     = "ai-crypto-trading"
  }
}

