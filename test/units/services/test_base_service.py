"""Unit tests for BaseMongoDBService."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mongodb_mcp.services.mongodb.base import BaseMongoDBService, ResolveResult


pytestmark = pytest.mark.asyncio


class TestEnsureConnected:
    """Tests for _ensure_connected."""

    async def test_returns_client_when_already_connected(self, patch_connection_manager, mock_mongodb_client):
        """Should return client without calling connect() if already connected."""
        service = BaseMongoDBService()
        client = await service._ensure_connected()

        assert client == mock_mongodb_client
        patch_connection_manager.connect.assert_not_called()

    async def test_auto_connects_when_disconnected(self, mock_mongodb_client):
        """Should call connect() when state is not CONNECTED."""
        from mongodb_mcp.services.connection_manager import ConnectionState
        with patch("mongodb_mcp.services.mongodb.base.connection_manager") as mock_cm:
            mock_cm.state = ConnectionState.DISCONNECTED
            mock_cm.connect = AsyncMock()
            mock_cm.get_client.return_value = mock_mongodb_client

            service = BaseMongoDBService()
            client = await service._ensure_connected()

            mock_cm.connect.assert_awaited_once()
            assert client == mock_mongodb_client

    async def test_propagates_connection_error(self):
        """Should propagate ConnectionError if connect() fails."""
        from mongodb_mcp.services.connection_manager import ConnectionState
        with patch("mongodb_mcp.services.mongodb.base.connection_manager") as mock_cm:
            mock_cm.state = ConnectionState.DISCONNECTED
            mock_cm.connect = AsyncMock(side_effect=ConnectionError("timeout"))

            service = BaseMongoDBService()
            with pytest.raises(ConnectionError, match="timeout"):
                await service._ensure_connected()


class TestCheckWriteAllowed:
    """Tests for _check_write_allowed."""

    def test_raises_when_read_only(self, patch_configs):
        """Should raise PermissionError when read_only=True."""
        patch_configs.read_only = True
        service = BaseMongoDBService()
        with pytest.raises(PermissionError, match="read-only"):
            service._check_write_allowed()

    def test_passes_when_write_allowed(self, patch_configs):
        """Should not raise when read_only=False."""
        patch_configs.read_only = False
        service = BaseMongoDBService()
        service._check_write_allowed()  # no exception


class TestCheckDestructiveAllowed:
    """Tests for _check_destructive_allowed."""

    def test_raises_when_read_only(self, patch_configs):
        """Should raise PermissionError when read_only=True (checked first)."""
        patch_configs.read_only = True
        patch_configs.allow_destructive = True
        service = BaseMongoDBService()
        with pytest.raises(PermissionError, match="read-only"):
            service._check_destructive_allowed()

    def test_raises_when_destructive_disabled(self, patch_configs):
        """Should raise PermissionError when allow_destructive=False."""
        patch_configs.read_only = False
        patch_configs.allow_destructive = False
        service = BaseMongoDBService()
        with pytest.raises(PermissionError, match="ALLOW_DESTRUCTIVE"):
            service._check_destructive_allowed()

    def test_passes_when_destructive_enabled(self, patch_configs):
        """Should not raise when read_only=False and allow_destructive=True."""
        patch_configs.read_only = False
        patch_configs.allow_destructive = True
        service = BaseMongoDBService()
        service._check_destructive_allowed()  # no exception


class TestValidateName:
    """Tests for _validate_name."""

    @pytest.mark.parametrize("value", ["", "   ", None])
    def test_raises_on_empty_or_whitespace(self, value):
        """Should raise ValueError for empty/whitespace values."""
        service = BaseMongoDBService()
        with pytest.raises(ValueError, match="required"):
            service._validate_name(value, "Database name")

    def test_passes_on_valid_name(self):
        """Should not raise for valid non-empty name."""
        service = BaseMongoDBService()
        service._validate_name("production", "Database name")  # no exception

    def test_error_message_includes_label(self):
        """Error message should include the provided label."""
        service = BaseMongoDBService()
        with pytest.raises(ValueError, match="Collection name"):
            service._validate_name("", "Collection name")


class TestCheckWriteTarget:
    """Tests for _check_write_target."""

    def test_allows_all_when_not_configured(self, patch_configs):
        """No allowlist configured → allow all."""
        patch_configs.write_allowlist = None
        service = BaseMongoDBService()
        service._check_write_target("mydb", "users")  # no exception

    def test_allows_all_when_empty_string(self, patch_configs):
        """Empty string → allow all."""
        patch_configs.write_allowlist = ""
        service = BaseMongoDBService()
        service._check_write_target("mydb", "users")  # no exception

    def test_allows_all_with_star(self, patch_configs):
        """'*' → allow all."""
        patch_configs.write_allowlist = "*"
        service = BaseMongoDBService()
        service._check_write_target("mydb", "users")  # no exception

    def test_allows_exact_match(self, patch_configs):
        """Exact db.collection match → allow."""
        patch_configs.write_allowlist = "mydb.users,mydb.orders"
        service = BaseMongoDBService()
        service._check_write_target("mydb", "users")  # no exception

    def test_allows_db_wildcard(self, patch_configs):
        """'db.*' matches any collection in that db."""
        patch_configs.write_allowlist = "mydb.*,prod.logs"
        service = BaseMongoDBService()
        service._check_write_target("mydb", "anything")  # no exception

    def test_blocks_unlisted_target(self, patch_configs):
        """Target not in allowlist → raise PermissionError."""
        patch_configs.write_allowlist = "mydb.users,mydb.orders"
        service = BaseMongoDBService()
        with pytest.raises(PermissionError, match="not allowed"):
            service._check_write_target("mydb", "admin_logs")

    def test_blocks_wrong_db(self, patch_configs):
        """Different database not in allowlist → raise."""
        patch_configs.write_allowlist = "mydb.*"
        service = BaseMongoDBService()
        with pytest.raises(PermissionError, match="not allowed"):
            service._check_write_target("other_db", "users")

    def test_error_message_shows_allowed(self, patch_configs):
        """Error message lists allowed targets."""
        patch_configs.write_allowlist = "prod.users,prod.orders"
        service = BaseMongoDBService()
        with pytest.raises(PermissionError, match="prod.users"):
            service._check_write_target("dev", "users")

    def test_collection_none_uses_db_wildcard(self, patch_configs):
        """When collection is None, target is 'db.*' — matches db.* pattern."""
        patch_configs.write_allowlist = "mydb.*"
        service = BaseMongoDBService()
        service._check_write_target("mydb", None)  # no exception

    def test_whitespace_in_patterns_trimmed(self, patch_configs):
        """Spaces around patterns are trimmed."""
        patch_configs.write_allowlist = " mydb.users , mydb.orders "
        service = BaseMongoDBService()
        service._check_write_target("mydb", "users")  # no exception


class TestResolveName:
    """Tests for _resolve_name."""

    async def test_exact_match_returns_found(self):
        """Should return found=True if name exists in available list."""
        service = BaseMongoDBService()
        fetch = AsyncMock(return_value=["users", "orders", "products"])

        result = await service._resolve_name("users", fetch)

        assert result.found is True
        assert result.name == "users"
        assert result.suggestions == []

    async def test_typo_returns_difflib_suggestions(self):
        """Should use difflib to suggest close matches for typos."""
        service = BaseMongoDBService()
        fetch = AsyncMock(return_value=["users", "orders", "products"])

        result = await service._resolve_name("uesrs", fetch)

        assert result.found is False
        assert result.name == "uesrs"
        assert "users" in result.suggestions

    async def test_word_match_returns_substring_suggestions(self):
        """Should use word matching when difflib finds nothing."""
        service = BaseMongoDBService()
        fetch = AsyncMock(return_value=["user_sessions", "user_logs", "orders", "products"])

        # "user log" → split to ["user", "log"] → matches "user_sessions", "user_logs"
        result = await service._resolve_name("user-log", fetch)

        assert result.found is False
        assert "user_logs" in result.suggestions

    async def test_word_match_splits_underscores_and_hyphens(self):
        """Should split on - and _ before word matching."""
        service = BaseMongoDBService()
        fetch = AsyncMock(return_value=["product_catalog", "order_items", "user_profiles"])

        result = await service._resolve_name("product-cat", fetch)

        assert result.found is False
        assert "product_catalog" in result.suggestions

    async def test_fallback_shows_available_when_no_match(self):
        """Should show first N available names when nothing matches."""
        service = BaseMongoDBService()
        available = ["alpha", "beta", "gamma", "delta", "epsilon"]
        fetch = AsyncMock(return_value=available)

        result = await service._resolve_name("xyz123", fetch)

        assert result.found is False
        assert result.suggestions == available[:5]

    async def test_empty_available_returns_empty_suggestions(self):
        """Should handle empty available list gracefully."""
        service = BaseMongoDBService()
        fetch = AsyncMock(return_value=[])

        result = await service._resolve_name("anything", fetch)

        assert result.found is False
        assert result.suggestions == []

    async def test_max_suggestions_limits_results(self):
        """Should respect max_suggestions parameter."""
        service = BaseMongoDBService()
        fetch = AsyncMock(return_value=[f"item_{i}" for i in range(20)])

        result = await service._resolve_name("xyz", fetch, max_suggestions=3)

        assert len(result.suggestions) <= 3

    async def test_cutoff_affects_difflib_sensitivity(self):
        """Higher cutoff means fewer difflib matches."""
        service = BaseMongoDBService()
        fetch = AsyncMock(return_value=["users", "orders", "products"])

        # High cutoff — "usrs" might not match "users"
        result = await service._resolve_name("usrs", fetch, cutoff=0.9)

        # Should still find something via word match or fallback
        assert result.found is False
        assert len(result.suggestions) > 0
