# Azure Storage Module - Storage accounts for APEX-OS

variable "name_prefix" {
  description = "Name prefix for storage accounts"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Storage Account for general data
resource "azurerm_storage_account" "data" {
  name                     = "${var.name_prefix}data"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  account_kind             = "StorageV2"
  min_tls_version          = "TLS1_2"
  enable_https_traffic_only = true

  blob_properties {
    versioning_enabled            = true
    change_feed_enabled           = true
    change_feed_retention_in_days = 30
    last_access_time_enabled      = true
    delete_retention_policy {
      days = 30
    }
    container_delete_retention_policy {
      days = 30
    }
  }

  network_rules {
    default_action             = "Deny"
    bypass                     = ["AzureServices"]
    virtual_network_subnet_ids = []
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Storage Account for backups
resource "azurerm_storage_account" "backups" {
  name                     = "${var.name_prefix}backups"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  account_kind             = "StorageV2"
  min_tls_version          = "TLS1_2"
  enable_https_traffic_only = true

  blob_properties {
    versioning_enabled            = true
    change_feed_enabled           = true
    change_feed_retention_in_days = 30
    last_access_time_enabled      = true
    delete_retention_policy {
      days = 90
    }
    container_delete_retention_policy {
      days = 90
    }
  }

  network_rules {
    default_action             = "Deny"
    bypass                     = ["AzureServices"]
    virtual_network_subnet_ids = []
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Blob Containers
resource "azurerm_storage_container" "data" {
  name                  = "apex-os-data"
  storage_account_name  = azurerm_storage_account.data.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "backups" {
  name                  = "apex-os-backups"
  storage_account_name  = azurerm_storage_account.backups.name
  container_access_type = "private"
}

# Outputs
output "data_storage_account_name" {
  value = azurerm_storage_account.data.name
}

output "data_storage_account_id" {
  value = azurerm_storage_account.data.id
}

output "backups_storage_account_name" {
  value = azurerm_storage_account.backups.name
}

output "backups_storage_account_id" {
  value = azurerm_storage_account.backups.id
}
