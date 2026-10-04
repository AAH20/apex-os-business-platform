"""Deepened integration module: webhooks, API keys, marketplace, data mapping, analytics."""
from __future__ import annotations
import hashlib, hmac, json, time, uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

# ── Webhook Management ──────────────────────────────────────────────────────


class WebhookStatus(str, Enum):
    ACTIVE = "active"; DISABLED = "disabled"; FAILED = "failed"


@dataclass
class Webhook:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""; events: list[str] = field(default_factory=list)
    secret: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: WebhookStatus = WebhookStatus.ACTIVE
    max_retries: int = 3; retry_backoff: float = 1.0; timeout: float = 10.0
    created_at: float = field(default_factory=time.time)
    last_triggered: float | None = None; failure_count: int = 0

    def sign_payload(self, payload: bytes) -> str:
        return hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()
    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_retries and self.status != WebhookStatus.DISABLED
    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.max_retries: self.status = WebhookStatus.FAILED
    def record_success(self) -> None:
        self.failure_count = 0; self.last_triggered = time.time()


class WebhookManager:
    def __init__(self) -> None: self._webhooks: dict[str, Webhook] = {}
    def register(self, url: str, events: list[str], **kw: Any) -> Webhook:
        wh = Webhook(url=url, events=events, **kw); self._webhooks[wh.id] = wh; return wh
    def unregister(self, wid: str) -> bool: return self._webhooks.pop(wid, None) is not None
    def get(self, wid: str) -> Webhook | None: return self._webhooks.get(wid)
    def list_for_event(self, event: str) -> list[Webhook]:
        return [w for w in self._webhooks.values() if event in w.events and w.status == WebhookStatus.ACTIVE]
    def dispatch(self, event: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        results, body = [], json.dumps(payload).encode()
        for wh in self.list_for_event(event):
            attempt, delivered = 0, False
            while wh.should_retry(attempt) and not delivered:
                try:
                    self._send(wh, body); wh.record_success(); delivered = True
                except Exception:
                    wh.record_failure(); attempt += 1; time.sleep(wh.retry_backoff * (2 ** attempt))
            results.append({"webhook_id": wh.id, "delivered": delivered, "attempts": attempt + 1})
        return results
    def _send(self, wh: Webhook, body: bytes) -> None:
        import urllib.request
        req = urllib.request.Request(wh.url, data=body,
            headers={"Content-Type": "application/json", "X-Webhook-Signature": wh.sign_payload(body)}, method="POST")
        with urllib.request.urlopen(req, timeout=wh.timeout) as resp:
            if resp.status >= 400: raise RuntimeError(f"HTTP {resp.status}")

# ── API Key Management ──────────────────────────────────────────────────────


class KeyStatus(str, Enum):
    ACTIVE = "active"; ROTATED = "rotated"; REVOKED = "revoked"; EXPIRED = "expired"


@dataclass
class ApiKey:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""; prefix: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    hashed_secret: str = ""; status: KeyStatus = KeyStatus.ACTIVE
    scopes: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None; last_used: float | None = None
    use_count: int = 0; rotated_from: str | None = None

    @staticmethod
    def hash_secret(secret: str) -> str: return hashlib.sha256(secret.encode()).hexdigest()
    def verify(self, secret: str) -> bool:
        if self.status != KeyStatus.ACTIVE: return False
        if self.expires_at and time.time() > self.expires_at:
            self.status = KeyStatus.EXPIRED; return False
        return hmac.compare_digest(self.hashed_secret, self.hash_secret(secret))
    def record_use(self) -> None: self.last_used = time.time(); self.use_count += 1


class ApiKeyManager:
    def __init__(self) -> None: self._keys: dict[str, ApiKey] = {}
    def create(
        self,
        name: str,
        scopes: list[str] | None = None,
        ttl_seconds: float | None = None
    ) -> tuple[ApiKey, str]:
        secret = uuid.uuid4().hex + uuid.uuid4().hex
        key = ApiKey(name=name, scopes=scopes or [], hashed_secret=ApiKey.hash_secret(secret),
                     expires_at=time.time() + ttl_seconds if ttl_seconds else None)
        self._keys[key.id] = key; return key, secret
    def authenticate(self, secret: str) -> ApiKey | None:
        hashed = ApiKey.hash_secret(secret)
        for key in self._keys.values():
            if hmac.compare_digest(key.hashed_secret, hashed):
                if key.verify(secret): key.record_use(); return key
                return None
        return None
    def rotate(self, key_id: str) -> tuple[ApiKey, str] | None:
        old = self._keys.get(key_id)
        if not old: return None
        old.status = KeyStatus.ROTATED
        new_key, secret = self.create(old.name, old.scopes, old.expires_at - old.created_at if old.expires_at else None)
        new_key.rotated_from = old.id; return new_key, secret
    def revoke(self, key_id: str) -> bool:
        key = self._keys.get(key_id)
        if key: key.status = KeyStatus.REVOKED; return True
        return False
    def list_keys(self, status: KeyStatus | None = None) -> list[ApiKey]:
        keys = self._keys.values()
        if status: keys = [k for k in keys if k.status == status]
        return list(keys)

# ── Integration Marketplace ─────────────────────────────────────────────────


class PluginStatus(str, Enum):
    AVAILABLE = "available"; INSTALLED = "installed"; ENABLED = "enabled"; DISABLED = "disabled"


@dataclass
class Plugin:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""; version: str = "1.0.0"; description: str = ""; author: str = ""
    entry_point: str = ""; hooks: list[str] = field(default_factory=list)
    status: PluginStatus = PluginStatus.AVAILABLE
    config: dict[str, Any] = field(default_factory=dict); installed_at: float | None = None


class Marketplace:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}; self._hooks: dict[str, list[Callable]] = defaultdict(list)
    def publish(
        self,
        name: str,
        version: str,
        entry_point: str,
        desc: str = "",
        author: str = "",
        hooks: list[str] | None = None
    ) -> Plugin:
        p = Plugin(name=name, version=version, entry_point=entry_point,
                   description=desc, author=author, hooks=hooks or [])
        self._plugins[p.id] = p; return p
    def install(self, pid: str) -> bool:
        p = self._plugins.get(pid)
        if not p or p.status != PluginStatus.AVAILABLE: return False
        p.status = PluginStatus.INSTALLED; p.installed_at = time.time(); return True
    def enable(self, pid: str) -> bool:
        p = self._plugins.get(pid)
        if not p or p.status not in (PluginStatus.INSTALLED, PluginStatus.DISABLED): return False
        p.status = PluginStatus.ENABLED
        for hook in p.hooks: self._hooks[hook].append(self._load_handler(p))
        return True
    def disable(self, pid: str) -> bool:
        p = self._plugins.get(pid)
        if not p or p.status != PluginStatus.ENABLED: return False
        p.status = PluginStatus.DISABLED
        for hook in p.hooks:
            self._hooks[hook] = [h for h in self._hooks[hook] if getattr(h, "__plugin_id__", None) != p.id]
        return True
    def _load_handler(self, plugin: Plugin) -> Callable:
        def handler(event: str, data: dict[str, Any]) -> Any:
            return {"plugin": plugin.name, "event": event, "data": data}
        handler.__plugin_id__ = plugin.id; return handler
    def execute_hook(self, hook: str, event: str, data: dict[str, Any]) -> list[Any]:
        return [h(event, data) for h in self._hooks.get(hook, [])]
    def search(self, query: str = "") -> list[Plugin]:
        if not query: return list(self._plugins.values())
        q = query.lower()
        return [p for p in self._plugins.values() if q in p.name.lower() or q in p.description.lower()]

# ── Data Mapping & Transformation ───────────────────────────────────────────


class TransformType(str, Enum):
    RENAME = "rename"; CONVERT = "convert"; FILTER = "filter"; COMPUTE = "compute"; NEST = "nest"


@dataclass
class TransformRule:
    source_path: str; target_path: str
    transform: TransformType = TransformType.RENAME
    params: dict[str, Any] = field(default_factory=dict)


class DataMapper:
    def __init__(self) -> None:
        self._rules: list[TransformRule] = []
        self._converters: dict[str, Callable] = {
            "upper": str.upper, "lower": str.lower, "int": int, "float": float, "str": str,
            "bool": lambda v: str(v).lower() in ("true", "1", "yes"),
        }
    def add_rule(self, rule: TransformRule) -> None: self._rules.append(rule)
    def map(self, data: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for rule in self._rules:
            value = self._get_path(data, rule.source_path)
            if value is None: continue
            if rule.transform == TransformType.RENAME: self._set_path(result, rule.target_path, value)
            elif rule.transform == TransformType.CONVERT:
                conv = self._converters.get(rule.params.get("type", ""))
                if conv: self._set_path(result, rule.target_path, conv(value))
            elif rule.transform == TransformType.FILTER:
                if value == rule.params.get("equals"): self._set_path(result, rule.target_path, value)
            elif rule.transform == TransformType.COMPUTE:
                try: self._set_path(
                    result,
                    rule.target_path,
                    eval(rule.params.get("expr", ""), {"__builtins__": {}}, {"value": value})
                )
                except Exception: pass
            elif rule.transform == TransformType.NEST: self._set_path(result, rule.target_path, value)
        return result
    @staticmethod
    def _get_path(data: dict[str, Any], path: str) -> Any:
        current: Any = data
        for part in path.split("."):
            if isinstance(current, dict): current = current.get(part)
            else: return None
        return current
    @staticmethod
    def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
        parts = path.split("."); current = data
        for part in parts[:-1]: current = current.setdefault(part, {})
        current[parts[-1]] = value

# ── Integration Analytics ───────────────────────────────────────────────────


@dataclass
class UsageRecord:
    integration: str; operation: str
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0; success: bool = True
    bytes_transferred: int = 0; metadata: dict[str, Any] = field(default_factory=dict)


class IntegrationAnalytics:
    def __init__(self) -> None: self._records: list[UsageRecord] = []
    def record(self, record: UsageRecord) -> None: self._records.append(record)
    def summary(self, integration: str | None = None) -> dict[str, Any]:
        records = [r for r in self._records if integration is None or r.integration == integration]
        if not records: return {"total": 0, "success_rate": 0.0, "avg_duration_ms": 0.0}
        total = len(records); successes = sum(1 for r in records if r.success)
        by_op: dict[str, int] = defaultdict(int)
        for r in records: by_op[r.operation] += 1
        return {"total": total, "success_rate": successes / total,
                "avg_duration_ms": round(sum(r.duration_ms for r in records) / total, 2),
                "total_bytes": sum(r.bytes_transferred for r in records), "by_operation": dict(by_op)}
    def top_integrations(self, limit: int = 5) -> list[tuple[str, int]]:
        counts: dict[str, int] = defaultdict(int)
        for r in self._records: counts[r.integration] += 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    def error_rate(self, integration: str | None = None) -> float:
        records = [r for r in self._records if integration is None or r.integration == integration]
        if not records: return 0.0
        return sum(1 for r in records if not r.success) / len(records)
