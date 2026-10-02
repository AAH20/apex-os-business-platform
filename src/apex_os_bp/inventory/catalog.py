"""Product catalog management."""
from __future__ import annotations

from typing import Dict, List, Optional

from apex_os_bp.inventory.models import Product, ProductCategory


class ProductCatalog:
    """Product catalog for managing product definitions."""

    def __init__(self):
        self._products: Dict[str, Product] = {}
        self._sku_index: Dict[str, str] = {}  # sku -> product_id

    def add_product(self, product: Product) -> None:
        """Add a product to the catalog."""
        if product.sku in self._sku_index:
            existing_id = self._sku_index[product.sku]
            if existing_id != product.id:
                raise ValueError(f"SKU already exists: {product.sku}")
        self._products[product.id] = product
        self._sku_index[product.sku] = product.id

    def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        return self._products.get(product_id)

    def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU."""
        product_id = self._sku_index.get(sku)
        if product_id:
            return self._products.get(product_id)
        return None

    def update_product(self, product_id: str, **kwargs) -> Product:
        """Update product attributes."""
        product = self._products.get(product_id)
        if not product:
            raise ValueError(f"Product not found: {product_id}")
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        return product

    def remove_product(self, product_id: str) -> None:
        """Remove a product from the catalog."""
        product = self._products.pop(product_id, None)
        if product:
            self._sku_index.pop(product.sku, None)

    def list_products(
        self,
        category: Optional[ProductCategory] = None,
        active_only: bool = True,
    ) -> List[Product]:
        """List products, optionally filtered."""
        products = list(self._products.values())
        if active_only:
            products = [p for p in products if p.is_active]
        if category:
            products = [p for p in products if p.category == category]
        return products

    def search(self, query: str) -> List[Product]:
        """Search products by name or SKU."""
        query_lower = query.lower()
        return [
            p for p in self._products.values()
            if query_lower in p.name.lower() or query_lower in p.sku.lower()
        ]

    def count(self) -> int:
        """Total number of products."""
        return len(self._products)
