"""EmbeddingCache unit tests.

Tests cover:
- LRU in-memory cache (L1)
- Redis cache (L2) with mocking
- Two-level cache interaction (L1 + L2)
- Cache key generation and normalization
- Metrics tracking
- Edge cases (Redis unavailable, empty queries)
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.common.cache.embedding_cache import (
    EmbeddingCache,
    LRUCache,
    reset_embedding_redis,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_cache():
    """Reset cache state before each test."""
    EmbeddingCache._lru.clear()
    EmbeddingCache.reset_metrics()
    reset_embedding_redis()
    yield
    EmbeddingCache._lru.clear()
    EmbeddingCache.reset_metrics()
    reset_embedding_redis()


SAMPLE_EMBEDDING = [0.1] * 1536
SAMPLE_QUERY = "소비자 분쟁 해결 기준"


# ---------------------------------------------------------------------------
# LRUCache (L1) tests
# ---------------------------------------------------------------------------


class TestLRUCache:
    """Thread-safe in-memory LRU cache tests."""

    def test_get_miss(self):
        lru = LRUCache(maxsize=10)
        assert lru.get("nonexistent") is None

    def test_set_and_get(self):
        lru = LRUCache(maxsize=10)
        lru.set("k1", [1.0, 2.0])
        assert lru.get("k1") == [1.0, 2.0]

    def test_eviction(self):
        lru = LRUCache(maxsize=3)
        lru.set("a", [1.0])
        lru.set("b", [2.0])
        lru.set("c", [3.0])
        lru.set("d", [4.0])  # evicts "a"
        assert lru.get("a") is None
        assert lru.get("d") == [4.0]

    def test_access_refreshes_order(self):
        lru = LRUCache(maxsize=3)
        lru.set("a", [1.0])
        lru.set("b", [2.0])
        lru.set("c", [3.0])
        lru.get("a")  # refresh "a"
        lru.set("d", [4.0])  # evicts "b" (oldest untouched)
        assert lru.get("a") == [1.0]
        assert lru.get("b") is None

    def test_clear(self):
        lru = LRUCache(maxsize=10)
        lru.set("k", [1.0])
        lru.clear()
        assert lru.get("k") is None

    def test_overwrite_existing(self):
        lru = LRUCache(maxsize=10)
        lru.set("k", [1.0])
        lru.set("k", [2.0])
        assert lru.get("k") == [2.0]


# ---------------------------------------------------------------------------
# Cache key tests
# ---------------------------------------------------------------------------


class TestCacheKey:
    """Cache key generation tests."""

    def test_same_query_same_key(self):
        k1 = EmbeddingCache._build_key("hello", "model-a", 1536)
        k2 = EmbeddingCache._build_key("hello", "model-a", 1536)
        assert k1 == k2

    def test_different_query_different_key(self):
        k1 = EmbeddingCache._build_key("hello", "model-a", 1536)
        k2 = EmbeddingCache._build_key("world", "model-a", 1536)
        assert k1 != k2

    def test_different_model_different_key(self):
        k1 = EmbeddingCache._build_key("hello", "model-a", 1536)
        k2 = EmbeddingCache._build_key("hello", "model-b", 1536)
        assert k1 != k2

    def test_different_dimension_different_key(self):
        k1 = EmbeddingCache._build_key("hello", "model-a", 1536)
        k2 = EmbeddingCache._build_key("hello", "model-a", 768)
        assert k1 != k2

    def test_normalization_applied(self):
        """Trailing punctuation, extra spaces, casing should normalize."""
        k1 = EmbeddingCache._build_key("Hello  World?", "m", 1536)
        k2 = EmbeddingCache._build_key("hello world", "m", 1536)
        assert k1 == k2

    def test_key_has_prefix(self):
        key = EmbeddingCache._build_key("test", "m", 1536)
        assert key.startswith("emb:")


# ---------------------------------------------------------------------------
# EmbeddingCache with Redis mocked
# ---------------------------------------------------------------------------


class TestEmbeddingCacheWithRedis:
    """Two-level cache tests with Redis mocked."""

    @patch("app.common.cache.embedding_cache._get_embedding_redis")
    def test_set_and_get_via_redis(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(SAMPLE_EMBEDDING)
        mock_get_redis.return_value = mock_redis

        # Set
        result = EmbeddingCache.set_embedding(SAMPLE_QUERY, SAMPLE_EMBEDDING)
        assert result is True
        mock_redis.setex.assert_called_once()

        # Clear L1 so we go through Redis
        EmbeddingCache._lru.clear()

        # Get from Redis (L2)
        cached = EmbeddingCache.get_embedding(SAMPLE_QUERY)
        assert cached == SAMPLE_EMBEDDING
        assert EmbeddingCache._hit_count == 1

    @patch("app.common.cache.embedding_cache._get_embedding_redis")
    def test_l1_hit_skips_redis(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Store in both levels
        EmbeddingCache.set_embedding(SAMPLE_QUERY, SAMPLE_EMBEDDING)

        # Get should hit L1, not Redis
        mock_redis.get.reset_mock()
        cached = EmbeddingCache.get_embedding(SAMPLE_QUERY)
        assert cached == SAMPLE_EMBEDDING
        mock_redis.get.assert_not_called()
        assert EmbeddingCache._l1_hit_count == 1

    @patch("app.common.cache.embedding_cache._get_embedding_redis")
    def test_miss_returns_none(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        result = EmbeddingCache.get_embedding("not cached query")
        assert result is None
        assert EmbeddingCache._miss_count == 1

    @patch("app.common.cache.embedding_cache._get_embedding_redis")
    def test_redis_error_returns_none(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("connection lost")
        mock_get_redis.return_value = mock_redis

        result = EmbeddingCache.get_embedding(SAMPLE_QUERY)
        assert result is None
        assert EmbeddingCache._error_count == 1

    @patch("app.common.cache.embedding_cache._get_embedding_redis")
    def test_set_redis_error_still_sets_l1(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.setex.side_effect = Exception("write failed")
        mock_get_redis.return_value = mock_redis

        result = EmbeddingCache.set_embedding(SAMPLE_QUERY, SAMPLE_EMBEDDING)
        assert result is False  # Redis failed

        # But L1 should still have it
        cached = EmbeddingCache.get_embedding(SAMPLE_QUERY)
        assert cached == SAMPLE_EMBEDDING

    @patch("app.common.cache.embedding_cache._get_embedding_redis")
    def test_l2_hit_promotes_to_l1(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(SAMPLE_EMBEDDING)
        mock_get_redis.return_value = mock_redis

        # First call goes to Redis
        EmbeddingCache.get_embedding(SAMPLE_QUERY)

        # Second call should hit L1
        mock_redis.get.reset_mock()
        EmbeddingCache.get_embedding(SAMPLE_QUERY)
        mock_redis.get.assert_not_called()
        assert EmbeddingCache._l1_hit_count == 1


# ---------------------------------------------------------------------------
# EmbeddingCache without Redis
# ---------------------------------------------------------------------------


class TestEmbeddingCacheNoRedis:
    """Tests when Redis is unavailable (L1 only mode)."""

    @patch("app.common.cache.embedding_cache._get_embedding_redis", return_value=None)
    def test_set_without_redis(self, _):
        result = EmbeddingCache.set_embedding(SAMPLE_QUERY, SAMPLE_EMBEDDING)
        assert result is False  # Redis store fails

        # But L1 still works
        cached = EmbeddingCache.get_embedding(SAMPLE_QUERY)
        assert cached == SAMPLE_EMBEDDING

    @patch("app.common.cache.embedding_cache._get_embedding_redis", return_value=None)
    def test_miss_without_redis(self, _):
        result = EmbeddingCache.get_embedding("uncached")
        assert result is None
        assert EmbeddingCache._miss_count == 1


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    """Cache metrics tracking."""

    @patch("app.common.cache.embedding_cache._get_embedding_redis", return_value=None)
    def test_metrics_tracking(self, _):
        EmbeddingCache.set_embedding("q1", SAMPLE_EMBEDDING)
        EmbeddingCache.get_embedding("q1")  # L1 hit
        EmbeddingCache.get_embedding("q2")  # miss

        metrics = EmbeddingCache.get_metrics()
        assert metrics["hit_count"] == 1
        assert metrics["l1_hit_count"] == 1
        assert metrics["miss_count"] == 1
        assert metrics["hit_rate"] == 0.5

    def test_reset_metrics(self):
        EmbeddingCache._hit_count = 10
        EmbeddingCache._miss_count = 5
        EmbeddingCache.reset_metrics()
        metrics = EmbeddingCache.get_metrics()
        assert metrics["hit_count"] == 0
        assert metrics["miss_count"] == 0
        assert metrics["hit_rate"] == 0.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case handling."""

    @patch("app.common.cache.embedding_cache._get_embedding_redis", return_value=None)
    def test_empty_query(self, _):
        EmbeddingCache.set_embedding("", [0.0])
        cached = EmbeddingCache.get_embedding("")
        assert cached == [0.0]

    @patch("app.common.cache.embedding_cache._get_embedding_redis", return_value=None)
    def test_korean_query(self, _):
        q = "전자상거래 환불 규정이 어떻게 되나요?"
        EmbeddingCache.set_embedding(q, SAMPLE_EMBEDDING)
        cached = EmbeddingCache.get_embedding(q)
        assert cached == SAMPLE_EMBEDDING

    @patch("app.common.cache.embedding_cache._get_embedding_redis", return_value=None)
    def test_custom_model_and_dimension(self, _):
        EmbeddingCache.set_embedding("q", [1.0], model="custom-model", dimension=768)
        # Default params should miss
        assert EmbeddingCache.get_embedding("q") is None
        # Matching params should hit
        cached = EmbeddingCache.get_embedding("q", model="custom-model", dimension=768)
        assert cached == [1.0]
