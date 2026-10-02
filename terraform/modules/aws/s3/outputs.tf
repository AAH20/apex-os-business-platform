output "bucket_names" { value = [for b in aws_s3_bucket.main : b.bucket] }
output "bucket_arns" { value = [for b in aws_s3_bucket.main : b.arn] }
