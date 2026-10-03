# ElastiCache Redis
# This file defines the Redis caching layer

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.cluster_name}-cache-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = var.common_tags
}

resource "aws_elasticache_parameter_group" "main" {
  family = "redis${split(".", var.elasticache_engine_version)[0]}"
  name   = "${var.cluster_name}-redis${split(".", var.elasticache_engine_version)[0]}"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "activedefrag"
    value = "yes"
  }

  tags = var.common_tags
}

resource "aws_security_group" "elasticache" {
  name_prefix = "${var.cluster_name}-elasticache-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for ElastiCache Redis"

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    cidr_blocks     = var.allowed_cidr_blocks
    security_groups = [aws_security_group.eks_cluster.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "${var.cluster_name}-elasticache-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_kms_key" "elasticache" {
  description             = "KMS key for ElastiCache encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = var.common_tags
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "apex-os-${var.environment}"
  description          = "Redis cluster for APEX-OS ${var.environment}"

  engine         = "redis"
  engine_version = var.elasticache_engine_version
  node_type      = var.elasticache_node_type

  num_cache_clusters         = var.elasticache_num_nodes
  automatic_failover_enabled = var.elasticache_num_nodes > 1
  multi_az_enabled           = var.environment == "prod" ? true : false

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = aws_kms_key.elasticache.arn

  auth_token = var.environment == "prod" ? var.db_password : null

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.elasticache.id]

  parameter_group_name = aws_elasticache_parameter_group.main.name

  snapshot_limit       = var.environment == "prod" ? 7 : 1
  snapshot_window      = "05:00-06:00"
  maintenance_window   = "sun:06:00-sun:07:00"

  auto_minor_version_upgrade = true
  apply_immediately          = false

  tags = merge(var.common_tags, {
    Name = "apex-os-${var.environment}-redis"
  })

  lifecycle {
    ignore_changes = [auth_token]
  }
}

resource "aws_elasticache_cluster" "standalone" {
  count = var.environment == "dev" ? 1 : 0

  cluster_id           = "apex-os-${var.environment}-standalone"
  engine               = "redis"
  engine_version       = var.elasticache_engine_version
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = aws_elasticache_parameter_group.main.name
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.elasticache.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = aws_kms_key.elasticache.arn

  snapshot_window    = "05:00-06:00"
  maintenance_window = "sun:06:00-sun:07:00"

  tags = var.common_tags
}

resource "aws_secretsmanager_secret" "redis_credentials" {
  name                    = "${var.cluster_name}/${var.environment}/redis-credentials"
  description             = "Redis credentials for APEX-OS ${var.environment}"
  recovery_window_in_days = var.environment == "prod" ? 30 : 7

  tags = var.common_tags
}

resource "aws_secretsmanager_secret_version" "redis_credentials" {
  secret_id = aws_secretsmanager_secret.redis_credentials.id
  secret_string = jsonencode({
    host     = var.environment == "dev" ? aws_elasticache_cluster.standalone[0].cache_nodes[0].address : aws_elasticache_replication_group.main.primary_endpoint_address
    port     = 6379
    auth_token = var.environment == "prod" ? var.db_password : null
    ssl      = true
  })
}
