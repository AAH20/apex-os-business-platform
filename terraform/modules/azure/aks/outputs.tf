output "cluster_name" { value = azurerm_kubernetes_cluster.main.name }
output "cluster_endpoint" { value = azurerm_kubernetes_cluster.main.kube_config[0].host }
output "cluster_ca_cert" { value = azurerm_kubernetes_cluster.main.kube_config[0].cluster_ca_certificate sensitive = true }
output "client_certificate" { value = azurerm_kubernetes_cluster.main.kube_config[0].client_certificate sensitive = true }
output "client_key" { value = azurerm_kubernetes_cluster.main.kube_config[0].client_key sensitive = true }
output "cluster_password" { value = azurerm_kubernetes_cluster.main.kube_config[0].password sensitive = true }
output "kube_config_raw" { value = azurerm_kubernetes_cluster.main.kube_config_raw sensitive = true }
output "identity_principal_id" { value = azurerm_user_assigned_identity.aks.principal_id }
