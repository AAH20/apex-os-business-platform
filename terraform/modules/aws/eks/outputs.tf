output "cluster_name" { value = aws_eks_cluster.main.name }
output "cluster_endpoint" { value = aws_eks_cluster.main.endpoint }
output "cluster_ca_cert" { value = aws_eks_cluster.main.certificate_authority[0].data sensitive = true }
output "cluster_security_group_id" { value = aws_security_group.cluster.id }
output "node_group_name" { value = aws_eks_node_group.main.node_group_name }
output "oidc_provider_arn" { value = aws_eks_cluster.main.identity[0].oidc[0].issuer }
