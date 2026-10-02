output "namespaces" { value = [for ns in kubernetes_namespace.main : ns.metadata[0].name] }
output "core_service_account" { value = kubernetes_service_account.core.metadata[0].name }
output "data_service_account" { value = kubernetes_service_account.data.metadata[0].name }
