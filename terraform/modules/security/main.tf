# Security Module - Security groups, WAF, GuardDuty, Security Hub for APEX-OS

variable "name_prefix" {
  description = "Name prefix for security resources"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "aws_vpc_id" {
  description = "AWS VPC ID"
  type        = string
  default     = ""
}

variable "allowed_cidr_blocks" {
  description = "Allowed CIDR blocks"
  type        = list(string)
  default     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
}

variable "enable_waf" {
  description = "Enable AWS WAF"
  type        = bool
  default     = true
}

variable "enable_shield" {
  description = "Enable AWS Shield Advanced"
  type        = bool
  default     = false
}

variable "enable_guardduty" {
  description = "Enable AWS GuardDuty"
  type        = bool
  default     = true
}

variable "enable_securityhub" {
  description = "Enable AWS Security Hub"
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "enable_encryption_at_rest" {
  description = "Enable encryption at rest"
  type        = bool
  default     = true
}

variable "enable_encryption_in_transit" {
  description = "Enable TLS/SSL encryption in transit"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# =============================================================================
# AWS WAF Web ACL
# =============================================================================

resource "aws_wafv2_web_acl" "main" {
  count = var.enable_waf ? 1 : 0

  name        = "${var.name_prefix}-waf"
  description = "WAF Web ACL for APEX-OS"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # AWS Managed Rules - Common Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # AWS Managed Rules - Known Bad Inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # AWS Managed Rules - SQL Injection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesSQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Rate Limiting Rule
  rule {
    name     = "RateLimitRule"
    priority = 4

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.name_prefix}-waf"
    sampled_requests_enabled   = true
  }

  tags = var.tags
}

# =============================================================================
# AWS Shield Advanced
# =============================================================================

resource "aws_shield_protection" "main" {
  count = var.enable_shield ? 1 : 0

  name         = "${var.name_prefix}-shield"
  resource_arn = "arn:aws:elasticloadbalancing:*:*:loadbalancer/app/${var.name_prefix}-alb/*"

  tags = var.tags
}

# =============================================================================
# AWS GuardDuty
# =============================================================================

resource "aws_guardduty_detector" "main" {
  count = var.enable_guardduty ? 1 : 0

  enable = true

  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        enable = true
      }
    }
  }

  tags = var.tags
}

# =============================================================================
# AWS Security Hub
# =============================================================================

resource "aws_securityhub_account" "main" {
  count = var.enable_securityhub ? 1 : 0

  enable_default_standards = false
}

resource "aws_securityhub_standards_subscription" "cis" {
  count = var.enable_securityhub ? 1 : 0

  standards_arn = "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0"

  depends_on = [aws_securityhub_account.main]
}

resource "aws_securityhub_standards_subscription" "pci_dss" {
  count = var.enable_securityhub ? 1 : 0

  standards_arn = "arn:aws:securityhub:::ruleset/pci-dss/v/3.2.1"

  depends_on = [aws_securityhub_account.main]
}

# =============================================================================
# AWS Config
# =============================================================================

resource "aws_config_configuration_recorder" "main" {
  count = var.enable_securityhub ? 1 : 0

  name     = "${var.name_prefix}-config-recorder"
  role_arn = aws_iam_role.config[0].arn

  recording_group {
    all_supported                 = true
    record_global_resource_types = true
  }
}

resource "aws_config_configuration_recorder_status" "main" {
  count = var.enable_securityhub ? 1 : 0

  name       = aws_config_configuration_recorder.main[0].name
  is_enabled = true

  depends_on = [aws_config_delivery_channel.main]
}

resource "aws_config_delivery_channel" "main" {
  count = var.enable_securityhub ? 1 : 0

  name           = "${var.name_prefix}-config-delivery"
  s3_bucket_name = "${var.name_prefix}-config-bucket"
  s3_key_prefix  = "config"

  snapshot_delivery_properties {
    delivery_frequency = "One_Hour"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_iam_role" "config" {
  count = var.enable_securityhub ? 1 : 0

  name = "${var.name_prefix}-config-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "config.amazonaws.com" }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "config" {
  count = var.enable_securityhub ? 1 : 0

  role       = aws_iam_role.config[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}

# =============================================================================
# AWS Security Groups
# =============================================================================

# ALB Security Group
resource "aws_security_group" "alb" {
  count = var.aws_vpc_id != "" ? 1 : 0

  name_prefix = "${var.name_prefix}-alb-"
  vpc_id      = var.aws_vpc_id
  description = "Security group for Application Load Balancer"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alb-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Application Security Group
resource "aws_security_group" "app" {
  count = var.aws_vpc_id != "" ? 1 : 0

  name_prefix = "${var.name_prefix}-app-"
  vpc_id      = var.aws_vpc_id
  description = "Security group for application servers"

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb[0].id]
    description     = "Application port from ALB"
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Application port from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-app-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Database Security Group
resource "aws_security_group" "database" {
  count = var.aws_vpc_id != "" ? 1 : 0

  name_prefix = "${var.name_prefix}-db-"
  vpc_id      = var.aws_vpc_id
  description = "Security group for database servers"

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app[0].id]
    description     = "PostgreSQL from app servers"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-db-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Redis Security Group
resource "aws_security_group" "redis" {
  count = var.aws_vpc_id != "" ? 1 : 0

  name_prefix = "${var.name_prefix}-redis-"
  vpc_id      = var.aws_vpc_id
  description = "Security group for Redis cache"

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app[0].id]
    description     = "Redis from app servers"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-redis-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# AWS KMS Key for Encryption
# =============================================================================

resource "aws_kms_key" "main" {
  count = var.enable_encryption_at_rest ? 1 : 0

  description             = "KMS key for APEX-OS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  multi_region            = true

  tags = var.tags
}

resource "aws_kms_alias" "main" {
  count = var.enable_encryption_at_rest ? 1 : 0

  name          = "alias/${var.name_prefix}-main"
  target_key_id = aws_kms_key.main[0].key_id
}

# Outputs
output "security_group_ids" {
  value = var.aws_vpc_id != "" ? [
    aws_security_group.alb[0].id,
    aws_security_group.app[0].id,
    aws_security_group.database[0].id,
    aws_security_group.redis[0].id,
  ] : []
}

output "waf_web_acl_id" {
  value = var.enable_waf ? aws_wafv2_web_acl.main[0].id : ""
}

output "guardduty_detector_id" {
  value = var.enable_guardduty ? aws_guardduty_detector.main[0].id : ""
}

output "securityhub_account_id" {
  value = var.enable_securityhub ? aws_securityhub_account.main[0].id : ""
}

output "kms_key_id" {
  value = var.enable_encryption_at_rest ? aws_kms_key.main[0].id : ""
}
