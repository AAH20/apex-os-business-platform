output "security_group_ids" { value = var.aws_vpc_id != "" ? [aws_security_group.alb[0].id, aws_security_group.app[0].id, aws_security_group.database[0].id, aws_security_group.redis[0].id] : [] }
output "waf_web_acl_id" { value = var.enable_waf ? aws_wafv2_web_acl.main[0].id : "" }
output "guardduty_detector_id" { value = var.enable_guardduty ? aws_guardduty_detector.main[0].id : "" }
output "securityhub_account_id" { value = var.enable_securityhub ? aws_securityhub_account.main[0].id : "" }
output "kms_key_id" { value = var.enable_encryption_at_rest ? aws_kms_key.main[0].id : "" }
