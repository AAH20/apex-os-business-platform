output "cluster_autoscaler_policy_arn" { value = aws_iam_policy.cluster_autoscaler.arn }
output "aws_load_balancer_controller_policy_arn" { value = aws_iam_policy.aws_load_balancer_controller.arn }
output "external_dns_policy_arn" { value = aws_iam_policy.external_dns.arn }
output "cert_manager_policy_arn" { value = aws_iam_policy.cert_manager.arn }
