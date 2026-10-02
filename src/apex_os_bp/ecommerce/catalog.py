"""Product catalog management."""

from __future__ import annotations

from typing import Optional

from .models import Product


class Catalog:
    """In-memory product catalog with search and filtering."""

    def __init__(self) -> None:
        self._products: dict[str, Product] = {}

    def add_product(self, product: Product) -> Product:
        if not product.validate():
            raise ValueError("Invalid product data")
        self._products[product.id] = product
        return product

    def get_product(self, product_id: str) -> Optional[Product]:
        return self._products.get(product_id)

    def get_product_by_sku(self, sku: str) -> Optional[Product]:
        for product in self._products.values():
            if product.sku == sku:
                return product
        return None

    def update_product(self, product_id: str, **kwargs) -> Product:
        product = self._products.get(product_id)
        if product is None:
            raise ValueError(f"Product {product_id} not found")
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        if not product.validate():
            raise ValueError("Updated product data is invalid")
        return product

    def remove_product(self, product_id: str) -> bool:
        if product_id in self._products:
            del self._products[product_id]
            return True
        return False

    def list_products(
        self,
        category: Optional[str] = None,
        active_only: bool = True,
    ) -> list[Product]:
        products = list(self._products.values())
        if active_only:
            products = [p for p in products if p.is_active]
        if category:
            products = [p for p in products if p.category == category]
        return products

    def search(self, query: str) -> list[Product]:
        query_lower = query.lower()
        return [
            p
            for p in self._products.values()
            if p.is_active
            and (
                query_lower in p.name.lower()
                or query_lower in p.description.lower()
                or query_lower in p.sku.lower()
            )
        ]

    def get_categories(self) -> list[str]:
        return sorted({p.category for p in self._products.values() if p.category})

    def count(self) -> int:
        return len(self._products)

    def clear(self) -> None:
        self._products.clear()
