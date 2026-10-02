output "resource_group_name" { value = azurerm_resource_group.main.name }
output "vnet_id" { value = azurerm_virtual_network.main.id }
output "vnet_name" { value = azurerm_virtual_network.main.name }
output "aks_subnet_id" { value = azurerm_subnet.aks.id }
output "appgw_subnet_id" { value = azurerm_subnet.appgw.id }
output "database_subnet_id" { value = azurerm_subnet.database.id }
