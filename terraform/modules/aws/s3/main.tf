# AWS S3 Module - Object storage for APEX-OS

variable "bucket_names" {
  description = "List of S3 bucket names"
  type        = list(string)
  default     = []
}

variable "name_prefix" {
  description = "Name prefix for buckets"
  type        = string
}

variable "enable_encryption_at_rest" {
  description = "Enable server-side encryption"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# S3 Buckets
resource "aws_s3_bucket" "main" {
  for_each = toset(var.bucket_names)

  bucket = "${var.name_prefix}-${each.value}"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-${each.value}"
  })
}

# Bucket Versioning
resource "aws_s3_bucket_versioning" "main" {
  for_each = toset(var.bucket_names)

  bucket = aws_s3_bucket.main[each.value].id

  versioning_configuration {
    status = "Enabled"
  }
}

# Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  for_each = var.enable_encryption_at_rest ? toset(var.bucket_names) : toset([])

  bucket = aws_s3_bucket.main[each.value].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3[0].arn
    }
    bucket_key_enabled = true
  }
}

# Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "main" {
  for_each = toset(var.bucket_names)

  bucket = aws_s3_bucket.main[each.value].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket Lifecycle Rules
resource "aws_s3_bucket_lifecycle_configuration" "main" {
  for_each = toset(var.bucket_names)

  bucket = aws_s3_bucket.main[each.value].id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555
    }
  }
}

# KMS Key for S3 Encryption
resource "aws_kms_key" "s3" {
  count = var.enable_encryption_at_rest ? 1 : 0

  description             = "KMS key for S3 encryption - ${var.name_prefix}"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = var.tags
}

resource "aws_kms_alias" "s3" {
  count = var.enable_encryption_at_rest ? 1 : 0

  name          = "alias/${var.name_prefix}-s3"
  target_key_id = aws_kms_key.s3[0].key_id
}

# Outputs
output "bucket_names" {
  value = [for b in aws_s3_bucket.main : b.bucket]
}

output "bucket_arns" {
  value = [for b in aws_s3_bucket.main : b.arn]
}
