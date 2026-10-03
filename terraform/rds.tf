# RDS PostgreSQL Database
# This file defines the primary database infrastructure

resource "aws_db_subnet_group" "main" {
  name       = "${var.cluster_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(var.common_tags, {
    Name = "${var.cluster_name}-db-subnet-group"
  })
}

resource "aws_db_parameter_group" "main" {
  family = "postgres${split(".", var.rds_engine_version)[0]}"
  name   = "${var.cluster_name}-pg${split(".", var.rds_engine_version)[0]}"

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_duration"
    value = "1"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = var.common_tags

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.cluster_name}-rds-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for RDS PostgreSQL"

  ingress {
    from_port       = 5432
    to_port         = 5432
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
    Name = "${var.cluster_name}-rds-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = var.common_tags
}

resource "aws_db_instance" "main" {
  identifier = "apex-os-${var.environment}"

  engine         = "postgres"
  engine_version = var.rds_engine_version
  instance_class = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_allocated_storage * 2
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.rds.arn

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name

  multi_az               = var.environment == "prod" ? true : false
  publicly_accessible    = false
  deletion_protection    = var.environment == "prod" ? true : false
  skip_final_snapshot    = var.environment == "prod" ? false : true
  final_snapshot_identifier = var.environment == "prod" ? "apex-os-${var.environment}-final" : null

  backup_retention_period = var.backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  performance_insights_enabled          = var.enable_monitoring
  performance_insights_retention_period = 7

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  auto_minor_version_upgrade = true
  copy_tags_to_snapshot     = true

  tags = merge(var.common_tags, {
    Name = "apex-os-${var.environment}-postgres"
  })

  lifecycle {
    prevent_destroy = false
  }
}

resource "aws_db_instance" "replica" {
  count = var.environment == "prod" ? 1 : 0

  identifier          = "apex-os-${var.environment}-replica"
  replicate_source_db = aws_db_instance.main.arn
  instance_class      = var.rds_instance_class

  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn

  publicly_accessible = false

  performance_insights_enabled          = var.enable_monitoring
  performance_insights_retention_period = 7

  auto_minor_version_upgrade = true
  copy_tags_to_snapshot     = true

  tags = merge(var.common_tags, {
    Name = "apex-os-${var.environment}-postgres-replica"
  })
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${var.cluster_name}/${var.environment}/rds-credentials"
  description             = "RDS credentials for APEX-OS ${var.environment}"
  recovery_window_in_days = var.environment == "prod" ? 30 : 7

  tags = var.common_tags
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    dbname   = var.db_name
    jdbc_url = "postgresql://${aws_db_instance.main.address}:${aws_db_instance.main.port}/${var.db_name}"
  })
}
