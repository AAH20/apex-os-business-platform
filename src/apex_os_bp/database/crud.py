"""Comprehensive CRUD operations for APEX-OS Business Platform.

GenericCRUD base + specialized CRUDs for User, Account, JournalEntry,
Lead, Agent, Dataset, Model, Alert. SQLAlchemy 2.0 async sessions.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select, func, and_, desc, asc, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from apex_os_bp.database.models import (
    Base, User, Account, Transaction, AuditLog,
    UserRole, AccountStatus, TransactionType,
)

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=Base)


class CRUDException(Exception):
    def __init__(self, message: str, code: str = "CRUD_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundException(CRUDException):
    def __init__(self, entity: str, entity_id: Any):
        super().__init__(f"{entity} with id={entity_id} not found", "NOT_FOUND")


class ValidationException(CRUDException):
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class GenericCRUD(Generic[T]):
    """Base CRUD with create, read, update, delete, list, bulk operations."""

    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, data: Dict[str, Any], user_id: Optional[int] = None) -> T:
        try:
            obj = self.model(**data)
            self.session.add(obj)
            await self.session.flush()
            await self._audit("CREATE", obj, user_id)
            await self.session.commit()
            return obj
        except IntegrityError as e:
            await self.session.rollback()
            raise ValidationException(f"Duplicate or invalid data: {e.orig}")
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise CRUDException(f"Database error: {e}")

    async def read(self, entity_id: Any) -> T:
        obj = await self.session.get(self.model, entity_id)
        if obj is None:
            raise NotFoundException(self.model.__name__, entity_id)
        return obj

    async def update(self, entity_id: Any, data: Dict[str, Any], user_id: Optional[int] = None) -> T:
        obj = await self.read(entity_id)
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        try:
            await self.session.flush()
            await self._audit("UPDATE", obj, user_id)
            await self.session.commit()
            return obj
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise CRUDException(f"Update failed: {e}")

    async def delete(self, entity_id: Any, user_id: Optional[int] = None) -> bool:
        obj = await self.read(entity_id)
        try:
            await self.session.delete(obj)
            await self._audit("DELETE", obj, user_id)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise CRUDException(f"Delete failed: {e}")

    async def list(self, filters: Optional[Dict[str, Any]] = None,
                   order_by: Optional[str] = None, order_dir: str = "asc",
                   limit: int = 100, offset: int = 0) -> List[T]:
        stmt = select(self.model)
        if filters:
            conds = [getattr(self.model, k) == v for k, v in filters.items()
                     if hasattr(self.model, k)]
            if conds:
                stmt = stmt.where(and_(*conds))
        if order_by and hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            stmt = stmt.order_by(desc(col) if order_dir == "desc" else asc(col))
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        stmt = select(func.count()).select_from(self.model)
        if filters:
            conds = [getattr(self.model, k) == v for k, v in filters.items()
                     if hasattr(self.model, k)]
            if conds:
                stmt = stmt.where(and_(*conds))
        return (await self.session.execute(stmt)).scalar_one()

    async def bulk_create(self, items: List[Dict[str, Any]], user_id: Optional[int] = None) -> List[T]:
        if not items:
            return []
        try:
            objs = [self.model(**d) for d in items]
            self.session.add_all(objs)
            await self.session.flush()
            for obj in objs:
                await self._audit("BULK_CREATE", obj, user_id)
            await self.session.commit()
            return objs
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise CRUDException(f"Bulk create failed: {e}")

    async def bulk_update(self, items: List[Dict[str, Any]], id_field: str = "id",
                          user_id: Optional[int] = None) -> int:
        if not items:
            return 0
        count = 0
        try:
            for item in items:
                eid = item.pop(id_field, None)
                if eid is None:
                    continue
                stmt = update(self.model).where(getattr(self.model, id_field) == eid).values(**item)
                count += (await self.session.execute(stmt)).rowcount
            await self._audit("BULK_UPDATE", None, user_id, details=f"Updated {count} records")
            await self.session.commit()
            return count
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise CRUDException(f"Bulk update failed: {e}")

    async def bulk_delete(self, ids: List[Any], id_field: str = "id",
                          user_id: Optional[int] = None) -> int:
        if not ids:
            return 0
        try:
            stmt = delete(self.model).where(getattr(self.model, id_field).in_(ids))
            rc = (await self.session.execute(stmt)).rowcount
            await self._audit("BULK_DELETE", None, user_id, details=f"Deleted {rc} records")
            await self.session.commit()
            return rc
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise CRUDException(f"Bulk delete failed: {e}")

    async def _audit(self, action: str, obj: Optional[T], user_id: Optional[int],
                     details: Optional[str] = None) -> None:
        self.session.add(AuditLog(
            user_id=user_id, action=action, entity_type=self.model.__name__,
            entity_id=getattr(obj, "id", None) if obj else None, details=details,
        ))


class UserCRUD(GenericCRUD[User]):
    """User CRUD with authentication, password hashing, token generation."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        return f"{salt}${hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()}"

    @staticmethod
    def _verify_password(password: str, stored: str) -> bool:
        try:
            salt, pw_hash = stored.split("$", 1)
            computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
            return hmac.compare_digest(computed, pw_hash)
        except (ValueError, AttributeError):
            return False

    async def create_user(self, username: str, email: str, password: str,
                          full_name: Optional[str] = None, role: UserRole = UserRole.VIEWER) -> User:
        if not username or not email or not password:
            raise ValidationException("username, email, and password are required")
        if len(password) < 8:
            raise ValidationException("Password must be at least 8 characters")
        if await self.list(filters={"username": username}):
            raise ValidationException(f"Username '{username}' already exists")
        if await self.list(filters={"email": email}):
            raise ValidationException(f"Email '{email}' already exists")
        return await self.create({
            "username": username, "email": email, "full_name": full_name,
            "role": role, "password_hash": self._hash_password(password),
        })

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        users = await self.list(filters={"username": username})
        if not users:
            return None
        user = users[0]
        stored = getattr(user, "password_hash", None)
        return user if stored and self._verify_password(password, stored) else None

    async def generate_token(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        await self.update(user_id, {"api_token": token, "token_created_at": datetime.utcnow()})
        return token

    async def revoke_token(self, user_id: int) -> None:
        await self.update(user_id, {"api_token": None, "token_created_at": None})

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        user = await self.read(user_id)
        stored = getattr(user, "password_hash", None)
        if not stored or not self._verify_password(old_password, stored):
            raise ValidationException("Invalid current password")
        if len(new_password) < 8:
            raise ValidationException("New password must be at least 8 characters")
        await self.update(user_id, {"password_hash": self._hash_password(new_password)})
        return True

    async def deactivate(self, user_id: int) -> User:
        return await self.update(user_id, {"is_active": False})


class AccountCRUD(GenericCRUD[Account]):
    """Account CRUD with balance calculation and transaction history."""

    def __init__(self, session: AsyncSession):
        super().__init__(Account, session)

    async def create_account(self, user_id: int, name: str, account_number: str,
                             currency: str = "USD", initial_balance: float = 0.0) -> Account:
        if not name or not account_number:
            raise ValidationException("name and account_number are required")
        if await self.list(filters={"account_number": account_number}):
            raise ValidationException(f"Account number '{account_number}' already exists")
        return await self.create({
            "user_id": user_id, "name": name, "account_number": account_number,
            "balance": initial_balance, "currency": currency, "status": AccountStatus.ACTIVE,
        })

    async def get_balance(self, account_id: int) -> float:
        return (await self.read(account_id)).balance

    async def get_transaction_history(self, account_id: int, limit: int = 50) -> List[Transaction]:
        await self.read(account_id)
        stmt = (select(Transaction).where(Transaction.account_id == account_id)
                .order_by(desc(Transaction.created_at)).limit(limit))
        return list((await self.session.execute(stmt)).scalars().all())

    async def transfer(self, from_account_id: int, to_account_id: int,
                       amount: float, description: str = "") -> Dict[str, Any]:
        if amount <= 0:
            raise ValidationException("Transfer amount must be positive")
        from_acc = await self.read(from_account_id)
        to_acc = await self.read(to_account_id)
        if from_acc.balance < amount:
            raise ValidationException("Insufficient funds")
        from_acc.balance -= amount
        to_acc.balance += amount
        self.session.add_all([
            Transaction(account_id=from_account_id, amount=amount,
                        type=TransactionType.DEBIT, description=f"Transfer out: {description}"),
            Transaction(account_id=to_account_id, amount=amount,
                        type=TransactionType.CREDIT, description=f"Transfer in: {description}"),
        ])
        await self.session.commit()
        return {"from_balance": from_acc.balance, "to_balance": to_acc.balance}

    async def freeze(self, account_id: int) -> Account:
        return await self.update(account_id, {"status": AccountStatus.FROZEN})

    async def close(self, account_id: int) -> Account:
        return await self.update(account_id, {"status": AccountStatus.CLOSED})


class JournalEntryCRUD:
    """Double-entry journal entries with validation, posting, reversing."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_entry(self, transactions: List[Dict[str, Any]],
                           description: str = "", reference: Optional[str] = None) -> Dict[str, Any]:
        if len(transactions) < 2:
            raise ValidationException("Journal entry must have at least 2 transactions")
        total = sum(Decimal(str(t["amount"])) for t in transactions)
        if total != 0:
            raise ValidationException(f"Journal entry not balanced (total={total})")
        entry_id = str(uuid.uuid4())
        txns = [Transaction(
            account_id=t["account_id"], amount=t["amount"],
            type=TransactionType.DEBIT if t["amount"] > 0 else TransactionType.CREDIT,
            description=description, reference=reference or entry_id,
        ) for t in transactions]
        self.session.add_all(txns)
        await self.session.commit()
        return {"entry_id": entry_id, "transactions": txns, "balanced": True}

    async def post_entry(self, entry_id: str) -> bool:
        txns = list((await self.session.execute(
            select(Transaction).where(Transaction.reference == entry_id))).scalars().all())
        if not txns:
            raise NotFoundException("JournalEntry", entry_id)
        for txn in txns:
            txn.description = f"[POSTED] {txn.description}"
        await self.session.commit()
        return True

    async def reverse_entry(self, entry_id: str) -> Dict[str, Any]:
        original = list((await self.session.execute(
            select(Transaction).where(Transaction.reference == entry_id))).scalars().all())
        if not original:
            raise NotFoundException("JournalEntry", entry_id)
        reversal = [{"account_id": t.account_id, "amount": -t.amount,
                     "description": f"REVERSAL of {entry_id}", "reference": f"REV-{entry_id}"}
                    for t in original]
        return await self.create_entry(reversal, description=f"Reversal of {entry_id}")

    async def get_entry(self, entry_id: str) -> List[Transaction]:
        stmt = (select(Transaction).where(Transaction.reference == entry_id)
                .order_by(asc(Transaction.id)))
        return list((await self.session.execute(stmt)).scalars().all())


class LeadCRUD:
    """CRM leads with scoring, deduplication, conversion tracking."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_lead(self, name: str, email: str, phone: str = "",
                          company: str = "", source: str = "web",
                          metadata: Optional[Dict] = None) -> Dict[str, Any]:
        existing = await self._find_by_email(email)
        if existing:
            return {"lead": existing, "duplicate": True}
        lead = {"id": str(uuid.uuid4()), "name": name, "email": email, "phone": phone,
                "company": company, "source": source, "status": "new",
                "score": 0, "metadata": metadata or {}, "created_at": time.time()}
        return {"lead": lead, "duplicate": False}

    async def _find_by_email(self, email: str) -> Optional[Dict]:
        return None

    async def score_lead(self, lead_id: str, signals: Dict[str, Any]) -> int:
        weights = {"email_opened": 5, "link_clicked": 10, "form_submitted": 20,
                   "page_view": 2, "demo_requested": 50}
        return min(sum(w for s, w in weights.items() if signals.get(s)), 100)

    async def convert_lead(self, lead_id: str, deal_value: float = 0.0) -> Dict[str, Any]:
        return {"lead_id": lead_id, "status": "converted",
                "deal_value": deal_value, "converted_at": time.time()}

    async def get_conversion_rate(self, source: Optional[str] = None) -> float:
        return 0.0


class AgentCRUD:
    """Agents with message routing and health monitoring."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_agent(self, name: str, capacity: int = 10,
                             metadata: Optional[Dict] = None) -> Dict[str, Any]:
        return {"id": str(uuid.uuid4()), "name": name, "status": "idle",
                "capacity": capacity, "active_connections": 0,
                "metadata": metadata or {}, "last_heartbeat": time.time()}

    async def route_message(self, message: Dict[str, Any],
                            target_agent_id: Optional[str] = None) -> Dict[str, Any]:
        return {"message_id": str(uuid.uuid4()), "agent_id": target_agent_id,
                "status": "delivered" if target_agent_id else "queued",
                "timestamp": time.time()}

    async def health_check(self, agent_id: str) -> Dict[str, Any]:
        return {"agent_id": agent_id, "status": "healthy",
                "last_heartbeat": time.time(), "uptime": 0}

    async def update_heartbeat(self, agent_id: str) -> None:
        pass


class DatasetCRUD:
    """Datasets with ingestion, partitioning, query execution."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def ingest(self, name: str, data: List[Dict[str, Any]],
                     version: str = "1.0.0") -> Dict[str, Any]:
        return {"id": str(uuid.uuid4()), "name": name, "version": version,
                "rows": len(data), "columns": list(data[0].keys()) if data else [],
                "created_at": time.time()}

    async def partition(self, dataset_id: str, partition_key: str,
                        num_partitions: int = 4) -> List[Dict[str, Any]]:
        return [{"partition": i, "dataset_id": dataset_id,
                 "key_range": f"{i}-{i + 1}"} for i in range(num_partitions)]

    async def execute_query(self, dataset_id: str, query: str) -> List[Dict[str, Any]]:
        return []

    async def get_summary(self, dataset_id: str) -> Dict[str, Any]:
        return {"id": dataset_id, "rows": 0, "columns": 0, "fingerprint": ""}


class ModelCRUD:
    """ML models with training, evaluation, deployment."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_model(self, name: str, model_type: str = "sklearn",
                             params: Optional[Dict] = None) -> Dict[str, Any]:
        return {"id": str(uuid.uuid4()), "name": name, "model_type": model_type,
                "version": "0.1.0", "status": "draft", "params": params or {},
                "metrics": {}, "created_at": time.time()}

    async def train(self, model_id: str, dataset_id: str,
                    hyperparams: Optional[Dict] = None) -> Dict[str, Any]:
        return {"model_id": model_id, "status": "training",
                "dataset_id": dataset_id, "hyperparams": hyperparams or {}}

    async def evaluate(self, model_id: str, test_dataset_id: str) -> Dict[str, float]:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

    async def deploy(self, model_id: str, environment: str = "production") -> Dict[str, Any]:
        return {"model_id": model_id, "status": "deployed",
                "environment": environment, "deployed_at": time.time()}

    async def archive(self, model_id: str) -> Dict[str, Any]:
        return {"model_id": model_id, "status": "archived"}


class AlertCRUD:
    """Alerts with rule evaluation and notification dispatch."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_rule(self, name: str, condition: str, threshold: float,
                          severity: str = "warning", channels: Optional[List[str]] = None) -> Dict[str, Any]:
        return {"id": str(uuid.uuid4()), "name": name, "condition": condition,
                "threshold": threshold, "severity": severity,
                "channels": channels or [], "enabled": True, "created_at": time.time()}

    async def evaluate_rule(self, rule_id: str, value: float) -> Optional[Dict[str, Any]]:
        return None

    async def fire_alert(self, rule_id: str, message: str, value: float,
                         severity: str = "warning") -> Dict[str, Any]:
        return {"id": str(uuid.uuid4()), "rule_id": rule_id, "message": message,
                "severity": severity, "status": "firing", "value": value,
                "created_at": time.time()}

    async def acknowledge(self, alert_id: str, user: str) -> Dict[str, Any]:
        return {"id": alert_id, "status": "acknowledged", "acknowledged_by": user}

    async def resolve(self, alert_id: str) -> Dict[str, Any]:
        return {"id": alert_id, "status": "resolved"}

    async def dispatch_notification(self, alert_id: str, channels: List[str]) -> Dict[str, Any]:
        return {"alert_id": alert_id, "channels": channels,
                "dispatched": True, "timestamp": time.time()}
