"""EmbeddingCache - Redis + in-memory LRU cache for embedding vectors."""

import hashlib
import json
import logging
import os
import threading
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from app.common.cache.base import normalize_query

logger = logging.getLogger(__name__)

# Separate Redis client for embedding cache
_emb_redis_client = None
_emb_redis_init_attempted = False


def _get_embedding_redis():
    """Redis client for embedding cache (checks ENABLE_EMBEDDING_CACHE)."""
    global _emb_redis_client, _emb_redis_init_attempted

    if _emb_redis_client is not None:
        return _emb_redis_client
    if _emb_redis_init_attempted:
        return None
    _emb_redis_init_attempted = True

    if os.getenv("ENABLE_EMBEDDING_CACHE", "false").lower() != "true":
        logger.debug("[EmbeddingCache] Disabled (ENABLE_EMBEDDING_CACHE != true)")
        return None

    try:
        import redis

        _emb_redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        _emb_redis_client.ping()
        logger.info("[EmbeddingCache] Redis connection established")
        return _emb_redis_client
    except Exception as e:
        logger.warning(f"[EmbeddingCache] Redis connection failed: {e}")
        _emb_redis_client = None
        return None


def reset_embedding_redis():
    """Reset for testing."""
    global _emb_redis_client, _emb_redis_init_attempted
    _emb_redis_client = None
    _emb_redis_init_attempted = False


class LRUCache:
    """Thread-safe in-memory LRU cache."""

    def __init__(self, maxsize: int = 500):
        self._cache: OrderedDict = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[List[float]]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def set(self, key: str, value: List[float]) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class EmbeddingCache:
    """Two-level embedding cache: L1 in-memory LRU + L2 Redis."""

    PREFIX = "emb"
    TTL_SECONDS = 604800  # 7 days

    _hit_count = 0
    _miss_count = 0
    _error_count = 0
    _l1_hit_count = 0

    _lru = LRUCache(maxsize=500)

    @classmethod
    def _build_key(cls, query: str, model: str, dimension: int) -> str:
        normalized = normalize_query(query)
        raw = f"{normalized}|{model}|{dimension}"
        h = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"{cls.PREFIX}:{h}"

    @classmethod
    def get_embedding(
        cls, query: str, model: str = "text-embedding-3-large", dimension: int = 1536
    ) -> Optional[List[float]]:
        key = cls._build_key(query, model, dimension)

        # L1: in-memory LRU
        cached = cls._lru.get(key)
        if cached is not None:
            cls._l1_hit_count += 1
            cls._hit_count += 1
            return cached

        # L2: Redis
        redis = _get_embedding_redis()
        if not redis:
            cls._miss_count += 1
            return None

        try:
            data = redis.get(key)
            if data:
                embedding = json.loads(data)
                cls._lru.set(key, embedding)  # promote to L1
                cls._hit_count += 1
                logger.debug(f"[EmbeddingCache] L2 HIT: {key}")
                return embedding

            cls._miss_count += 1
            return None
        except Exception as e:
            cls._error_count += 1
            logger.warning(f"[EmbeddingCache] Get error: {e}")
            return None

    @classmethod
    def set_embedding(
        cls,
        query: str,
        embedding: List[float],
        model: str = "text-embedding-3-large",
        dimension: int = 1536,
    ) -> bool:
        key = cls._build_key(query, model, dimension)

        # Always set L1
        cls._lru.set(key, embedding)

        # Set L2 (Redis)
        redis = _get_embedding_redis()
        if not redis:
            return False

        try:
            serialized = json.dumps(embedding)
            redis.setex(key, cls.TTL_SECONDS, serialized)
            logger.debug(f"[EmbeddingCache] SET: {key}")
            return True
        except Exception as e:
            cls._error_count += 1
            logger.warning(f"[EmbeddingCache] Set error: {e}")
            return False

    @classmethod
    def get_metrics(cls) -> Dict[str, Any]:
        total = cls._hit_count + cls._miss_count
        hit_rate = cls._hit_count / total if total > 0 else 0.0
        return {
            "prefix": cls.PREFIX,
            "ttl_seconds": cls.TTL_SECONDS,
            "hit_count": cls._hit_count,
            "miss_count": cls._miss_count,
            "l1_hit_count": cls._l1_hit_count,
            "error_count": cls._error_count,
            "hit_rate": round(hit_rate, 4),
        }

    @classmethod
    def reset_metrics(cls) -> None:
        cls._hit_count = 0
        cls._miss_count = 0
        cls._error_count = 0
        cls._l1_hit_count = 0

    @classmethod
    def clear(cls) -> None:
        cls._lru.clear()
        redis = _get_embedding_redis()
        if redis:
            try:
                keys = list(redis.scan_iter(match=f"{cls.PREFIX}:*"))
                if keys:
                    redis.delete(*keys)
            except Exception as e:
                logger.warning(f"[EmbeddingCache] Clear error: {e}")
