"""Deepened caching: multi-level, invalidation, warming, analytics, Redis Cluster."""
from __future__ import annotations
import asyncio, json, time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional
import aioredis


class CacheLevel(Enum):
    L1, L2, L3 = "l1", "l2", "l3"


@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    tags: set[str] = field(default_factory=set)


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_sets: int = 0
    total_invalidations: int = 0

    @property
    def hit_ratio(self) -> float:
        t = self.hits + self.misses
        return self.hits / t if t else 0.0

    @property
    def miss_ratio(self) -> float:
        return 1.0 - self.hit_ratio


class L1Cache:
    def __init__(self, max_size: int = 1024, default_ttl: float = 60.0):
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size, self._default_ttl = max_size, default_ttl
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        e = self._store.get(key)
        if e is None:
            self._stats.misses += 1; return None
        if time.monotonic() > e.expires_at:
            self._store.pop(key, None); self._stats.misses += 1; self._stats.evictions += 1; return None
        self._store.move_to_end(key); self._stats.hits += 1; return e.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None, tags: Optional[set[str]] = None) -> None:
        self._store[key] = CacheEntry(value, time.monotonic() + (ttl or self._default_ttl), tags or set())
        self._store.move_to_end(key); self._stats.total_sets += 1
        if len(self._store) > self._max_size:
            self._store.popitem(last=False); self._stats.evictions += 1

    def invalidate(self, key: str) -> bool:
        ok = self._store.pop(key, None) is not None
        if ok: self._stats.total_invalidations += 1
        return ok

    def invalidate_by_tag(self, tag: str) -> int:
        keys = [k for k, v in self._store.items() if tag in v.tags]
        for k in keys: self._store.pop(k, None)
        self._stats.total_invalidations += len(keys); return len(keys)

    def clear(self) -> None: self._store.clear()
    @property
    def stats(self) -> CacheStats: return self._stats


class L2Cache:
    def __init__(self, redis_url: str = "redis://localhost:6379/0", default_ttl: float = 300.0):
        self._redis_url, self._default_ttl = redis_url, default_ttl
        self._redis: Optional[aioredis.Redis] = None
        self._stats = CacheStats()

    async def connect(self) -> None:
        self._redis = await aioredis.from_url(self._redis_url, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        if not self._redis: return None
        raw = await self._redis.get(f"l2:{key}")
        if raw is None: self._stats.misses += 1; return None
        self._stats.hits += 1; return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: Optional[float] = None, tags: Optional[set[str]] = None) -> None:
        if not self._redis: return
        await self._redis.setex(f"l2:{key}", int(ttl or self._default_ttl), json.dumps({"v": value, "t": list(tags or [])}))
        self._stats.total_sets += 1

    async def invalidate(self, key: str) -> bool:
        if not self._redis: return False
        r = await self._redis.delete(f"l2:{key}"); self._stats.total_invalidations += int(r); return bool(r)

    async def invalidate_by_tag(self, tag: str) -> int:
        if not self._redis: return 0
        count = 0
        async for k in self._redis.scan_iter(match="l2:*"):
            raw = await self._redis.get(k)
            if raw and tag in json.loads(raw).get("t", []): await self._redis.delete(k); count += 1
        self._stats.total_invalidations += count; return count

    @property
    def stats(self) -> CacheStats: return self._stats


class L3Cache:
    def __init__(self, startup_nodes: list[dict[str, Any]], default_ttl: float = 3600.0):
        self._startup_nodes, self._default_ttl = startup_nodes, default_ttl
        self._redis: Optional[aioredis.RedisCluster] = None
        self._stats = CacheStats()

    async def connect(self) -> None:
        self._redis = aioredis.RedisCluster(startup_nodes=self._startup_nodes, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        if not self._redis: return None
        raw = await self._redis.get(f"l3:{key}")
        if raw is None: self._stats.misses += 1; return None
        self._stats.hits += 1; return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: Optional[float] = None, tags: Optional[set[str]] = None) -> None:
        if not self._redis: return
        await self._redis.setex(f"l3:{key}", int(ttl or self._default_ttl), json.dumps({"v": value, "t": list(tags or [])}))
        self._stats.total_sets += 1

    async def invalidate(self, key: str) -> bool:
        if not self._redis: return False
        r = await self._redis.delete(f"l3:{key}"); self._stats.total_invalidations += int(r); return bool(r)

    @property
    def stats(self) -> CacheStats: return self._stats


class CacheInvalidator:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._listeners: list[Callable] = []

    async def connect(self) -> None:
        self._redis = await aioredis.from_url(self._redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe("cache:invalidate")
        asyncio.create_task(self._listen())

    async def _listen(self) -> None:
        if not self._pubsub: return
        async for msg in self._pubsub.listen():
            if msg["type"] == "message":
                p = json.loads(msg["data"])
                for cb in self._listeners:
                    if asyncio.iscoroutinefunction(cb): asyncio.create_task(cb(p.get("key"), p.get("tag")))
                    else: cb(p.get("key"), p.get("tag"))

    async def publish_invalidation(self, key: Optional[str] = None, tag: Optional[str] = None) -> None:
        if self._redis: await self._redis.publish("cache:invalidate", json.dumps({"key": key, "tag": tag}))

    def on_invalidate(self, cb: Callable) -> None: self._listeners.append(cb)
    async def close(self) -> None:
        if self._pubsub: await self._pubsub.unsubscribe("cache:invalidate")


class CacheWarmer:
    def __init__(self, mc: "MultiLevelCache"):
        self._mc = mc
        self._counts: dict[str, int] = defaultdict(int)
        self._times: dict[str, list[float]] = defaultdict(list)
        self._cbs: dict[str, Callable[[], Coroutine[Any, Any, Any]]] = {}
        self._running = False

    def register_warmer(self, key: str, cb: Callable[[], Coroutine[Any, Any, Any]]) -> None: self._cbs[key] = cb

    def record_access(self, key: str) -> None:
        now = time.monotonic(); self._counts[key] += 1; self._times[key].append(now)
        if len(self._times[key]) > 100: self._times[key] = self._times[key][-100:]

    def predict_hot_keys(self, threshold: int = 5, window: float = 300.0) -> list[str]:
        now = time.monotonic()
        return sorted([k for k, ts in self._times.items() if len([t for t in ts if now - t < window]) >= threshold],
                      key=lambda k: self._counts[k], reverse=True)

    async def warm(self, keys: Optional[list[str]] = None) -> int:
        n = 0
        for key in (keys or self.predict_hot_keys()):
            cb = self._cbs.get(key)
            if cb:
                try: await self._mc.set(key, await cb(), level=CacheLevel.L2); n += 1
                except Exception: continue
        return n

    async def start_periodic_warm(self, interval: float = 60.0) -> None:
        self._running = True
        while self._running: await self.warm(); await asyncio.sleep(interval)

    def stop(self) -> None: self._running = False


class CacheAnalytics:
    def __init__(self, l1: L1Cache, l2: L2Cache, l3: L3Cache):
        self._levels = {CacheLevel.L1: l1, CacheLevel.L2: l2, CacheLevel.L3: l3}

    def snapshot(self) -> dict[str, Any]:
        r = {}
        for lvl, c in self._levels.items():
            s = c.stats
            r[lvl.value] = {"hits": s.hits, "misses": s.misses, "hit_ratio": round(s.hit_ratio, 4),
                            "miss_ratio": round(s.miss_ratio, 4), "evictions": s.evictions,
                            "total_sets": s.total_sets, "total_invalidations": s.total_invalidations}
        th = sum(c.stats.hits for c in self._levels.values())
        tm = sum(c.stats.misses for c in self._levels.values())
        r["aggregate"] = {"total_hits": th, "total_misses": tm,
                          "overall_hit_ratio": round(th / (th + tm), 4) if (th + tm) else 0.0}
        return r


class MultiLevelCache:
    def __init__(self, l1_size: int = 1024, l1_ttl: float = 60.0,
                 l2_url: str = "redis://localhost:6379/0", l2_ttl: float = 300.0,
                 l3_nodes: Optional[list[dict[str, Any]]] = None, l3_ttl: float = 3600.0):
        self.l1 = L1Cache(l1_size, l1_ttl)
        self.l2 = L2Cache(l2_url, l2_ttl)
        self.l3 = L3Cache(l3_nodes or [{"host": "localhost", "port": 7000}], l3_ttl)
        self.analytics = CacheAnalytics(self.l1, self.l2, self.l3)
        self.warmer = CacheWarmer(self)
        self.invalidator = CacheInvalidator(l2_url)

    async def connect(self) -> None:
        await self.l2.connect(); await self.l3.connect(); await self.invalidator.connect()

    async def get(self, key: str) -> Optional[Any]:
        v = self.l1.get(key)
        if v is not None: return v
        v = await self.l2.get(key)
        if v is not None: self.l1.set(key, v); return v
        v = await self.l3.get(key)
        if v is not None: self.l1.set(key, v); await self.l2.set(key, v); return v
        return None

    async def set(self, key: str, value: Any, level: CacheLevel = CacheLevel.L1,
                  ttl: Optional[float] = None, tags: Optional[set[str]] = None) -> None:
        if level == CacheLevel.L1: self.l1.set(key, value, ttl, tags)
        elif level == CacheLevel.L2: await self.l2.set(key, value, ttl, tags)
        else: await self.l3.set(key, value, ttl, tags)

    async def invalidate(self, key: Optional[str] = None, tag: Optional[str] = None) -> None:
        if key: self.l1.invalidate(key); await self.l2.invalidate(key); await self.l3.invalidate(key)
        if tag: self.l1.invalidate_by_tag(tag); await self.l2.invalidate_by_tag(tag)
        await self.invalidator.publish_invalidation(key, tag)

    async def close(self) -> None: await self.invalidator.close()
