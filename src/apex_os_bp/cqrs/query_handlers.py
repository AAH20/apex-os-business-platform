"""Query handlers for the CQRS system."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from apex_os_bp.cqrs.base import QueryHandler
from apex_os_bp.cqrs.exceptions import QueryValidationError
from apex_os_bp.cqrs.queries import (
    GetCustomerQuery,
    GetOrderQuery,
    GetProductQuery,
    ListCustomersQuery,
    ListOrdersQuery,
    ListProductsQuery,
)


class GetOrderHandler(QueryHandler[GetOrderQuery, Optional[Dict[str, Any]]]):
    """Handler for GetOrderQuery."""

    def __init__(self, read_model: Dict[UUID, Dict[str, Any]]):
        self._read_model = read_model

    async def handle(self, query: GetOrderQuery) -> Optional[Dict[str, Any]]:
        if query.order_id == UUID(int=0):
            raise QueryValidationError("order_id is required")
        return self._read_model.get(query.order_id)


class ListOrdersHandler(QueryHandler[ListOrdersQuery, List[Dict[str, Any]]]):
    """Handler for ListOrdersQuery."""

    def __init__(self, read_model: Dict[UUID, Dict[str, Any]]):
        self._read_model = read_model

    async def handle(self, query: ListOrdersQuery) -> List[Dict[str, Any]]:
        results = list(self._read_model.values())

        if query.customer_id:
            results = [
                o for o in results
                if o.get("customer_id") == str(query.customer_id)
            ]
        if query.status:
            results = [o for o in results if o.get("status") == query.status]

        return results[query.offset : query.offset + query.limit]


class GetCustomerHandler(QueryHandler[GetCustomerQuery, Optional[Dict[str, Any]]]):
    """Handler for GetCustomerQuery."""

    def __init__(self, read_model: Dict[UUID, Dict[str, Any]]):
        self._read_model = read_model

    async def handle(self, query: GetCustomerQuery) -> Optional[Dict[str, Any]]:
        if query.customer_id == UUID(int=0):
            raise QueryValidationError("customer_id is required")
        return self._read_model.get(query.customer_id)


class ListCustomersHandler(QueryHandler[ListCustomersQuery, List[Dict[str, Any]]]):
    """Handler for ListCustomersQuery."""

    def __init__(self, read_model: Dict[UUID, Dict[str, Any]]):
        self._read_model = read_model

    async def handle(self, query: ListCustomersQuery) -> List[Dict[str, Any]]:
        results = list(self._read_model.values())

        if query.search:
            search_lower = query.search.lower()
            results = [
                c for c in results
                if search_lower in c.get("name", "").lower()
                or search_lower in c.get("email", "").lower()
            ]

        return results[query.offset : query.offset + query.limit]


class GetProductHandler(QueryHandler[GetProductQuery, Optional[Dict[str, Any]]]):
    """Handler for GetProductQuery."""

    def __init__(self, read_model: Dict[UUID, Dict[str, Any]]):
        self._read_model = read_model

    async def handle(self, query: GetProductQuery) -> Optional[Dict[str, Any]]:
        if query.product_id == UUID(int=0):
            raise QueryValidationError("product_id is required")
        return self._read_model.get(query.product_id)


class ListProductsHandler(QueryHandler[ListProductsQuery, List[Dict[str, Any]]]):
    """Handler for ListProductsQuery."""

    def __init__(self, read_model: Dict[UUID, Dict[str, Any]]):
        self._read_model = read_model

    async def handle(self, query: ListProductsQuery) -> List[Dict[str, Any]]:
        results = list(self._read_model.values())

        if query.category:
            results = [p for p in results if p.get("category") == query.category]
        if query.search:
            search_lower = query.search.lower()
            results = [
                p for p in results
                if search_lower in p.get("name", "").lower()
                or search_lower in p.get("description", "").lower()
            ]

        return results[query.offset : query.offset + query.limit]
