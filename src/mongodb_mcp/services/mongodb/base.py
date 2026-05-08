from typing import Callable, Awaitable, Any, Dict, List
from difflib import get_close_matches
from dataclasses import dataclass, field
from mongodb_mcp.services.connection_manager import connection_manager, ConnectionState
from mongodb_mcp.clients.mongodb import MongoDBClient
from mongodb_mcp.configs import configs

import logging

logger = logging.getLogger(__name__)

@dataclass
class ResolveResult:
    """Result of a name resolution attempt."""
    found: bool
    name: str
    suggestions: List[str] = field(default_factory=list)


class BaseMongoDBService:
    """Base service — shared utilities for all MongoDB service mixins."""

    async def _ensure_connected(self) -> MongoDBClient:
        """Auto-connect if not connected. Returns the active client."""
        if connection_manager.state != ConnectionState.CONNECTED:
            # logger.info(f"[connection] State={connection_manager.state.value} — initiating auto-connect")
            await connection_manager.connect()
            logger.info(f"[connection] Auto-connect successful")
        return connection_manager.get_client()

    def _check_write_allowed(self) -> None:
        """Raise if server is in read-only mode."""
        if configs.read_only:
            logger.warning("[policy] Write operation blocked — server is in READ_ONLY mode")
            raise PermissionError("Write operations are disabled in read-only mode.")

    def _check_destructive_allowed(self) -> None:
        """Raise if destructive operations are not enabled.

        Destructive = data loss that cannot be undone without a backup:
        delete_one, delete_many, drop_collection, drop_database, drop_index.
        """
        self._check_write_allowed()
        if not configs.allow_destructive:
            logger.warning("[policy] Destructive operation blocked — ALLOW_DESTRUCTIVE is disabled")
            raise PermissionError(
                "Destructive operations are disabled. "
                "Set ALLOW_DESTRUCTIVE=true to enable delete/drop operations."
            )

    def _check_write_target(self, database: str, collection: str | None = None) -> None:
        """Raise if the target db.collection is not in the write allowlist.

        Rules:
        - WRITE_ALLOWLIST not set or empty → allow all
        - "*" → allow all
        - "db.*" → allow all collections in that db
        - "db.col" → exact match only
        """
        allowlist_raw = configs.write_allowlist
        if not allowlist_raw or allowlist_raw.strip() == "":
            return  # not configured → allow all

        patterns = [p.strip() for p in allowlist_raw.split(",") if p.strip()]
        if not patterns:
            return  # empty after parsing → allow all

        if "*" in patterns:
            return  # explicit allow-all

        target = f"{database}.{collection}" if collection else f"{database}.*"

        for pattern in patterns:
            if pattern == target:
                return  # exact match
            # "db.*" matches any collection in that db
            if pattern.endswith(".*"):
                allowed_db = pattern[:-2]
                if allowed_db == database:
                    return

        # No match — block
        logger.warning(f"[policy] Write blocked — target '{target}' not in allowlist: {patterns}")
        raise PermissionError(
            f"Write to '{target}' is not allowed. "
            f"Allowed targets: {', '.join(patterns)}"
        )

    def _validate_name(self, value: str, label: str = "name") -> None:
        """Raise if name is empty or whitespace."""
        if not value or not value.strip():
            logger.warning(f"[validation] {label} is empty or whitespace")
            raise ValueError(f"{label} is required and cannot be empty.")

    async def _resolve_name(
        self,
        name: str,
        fetch_available: Callable[[], Awaitable[list[str]]],
        cutoff: float = 0.5,
        max_suggestions: int = 5,
    ) -> ResolveResult:
        """Generic name resolver — difflib + word matching.

        Called ONLY when an operation returns empty/error.
        Determines whether the name is valid (data genuinely empty)
        or invalid (typo/wrong name → suggest alternatives).

        Strategy:
          1. Exact match → found (name is valid, data is genuinely empty)
          2. difflib fuzzy match → catch typos (uesrs → users)
          3. Word match → catch partial/substring (user log → user_logs)
          4. Fallback → return first N available names
        """
        logger.debug(f"[resolve] Resolving name='{name}' against available list")
        available = await fetch_available()
        logger.debug(f"[resolve] Available names ({len(available)}): {available[:10]}")

        # Name exists in DB — not a typo, data is genuinely empty/error is unrelated
        if name in available:
            logger.debug(f"[resolve] name='{name}' found — data is genuinely empty")
            return ResolveResult(found=True, name=name)

        # Name does NOT exist — find suggestions for user to confirm

        # Strategy 1: difflib — catches character-level typos (uesrs → users)
        suggestions = get_close_matches(name, available, n=max_suggestions, cutoff=cutoff)
        if suggestions:
            logger.info(f"[resolve] name='{name}' not found — difflib suggestions: {suggestions}")

        # Strategy 2: word match — catches partial/substring (user log → user_logs)
        if not suggestions:
            words = [w for w in name.replace("-", " ").replace("_", " ").split() if len(w) > 2]
            if words:
                suggestions = [
                    item for item in available
                    if any(w.lower() in item.lower() for w in words)
                ][:max_suggestions]
                if suggestions:
                    logger.info(f"[resolve] name='{name}' not found — word-match suggestions (words={words}): {suggestions}")

        # Strategy 3: fallback — nothing matched, show what's available
        if not suggestions:
            suggestions = available[:max_suggestions]
            logger.info(f"[resolve] name='{name}' not found — no close match, showing available: {suggestions}")

        logger.warning(f"[resolve] Name '{name}' does not exist. Returning {len(suggestions)} suggestions for user confirmation")
        return ResolveResult(found=False, name=name, suggestions=suggestions)

    async def _get_db_names(self) -> List[str]:
        """Fetch flat list of database names."""
        client = await self._ensure_connected()
        dbs = await client.list_database_names()
        return [d["name"] for d in dbs]

    async def _resolve_db_and_collection(self, database: str, collection: str) -> Dict[str, Any] | None:
        """Resolve DB then collection. Returns not_found dict or None if both exist."""
        logger.info(f"[resolve] Checking existence of db='{database}', collection='{collection}'")
        client = await self._ensure_connected()

        db_result = await self._resolve_name(database, self._get_db_names)
        if not db_result.found:
            logger.warning(f"[resolve] Database '{database}' not found — suggesting alternatives")
            return {
                "status": "not_found",
                "label": "Database",
                "name": db_result.name,
                "suggestions": db_result.suggestions,
            }

        col_result = await self._resolve_name(
            collection,
            lambda: client.list_collection_names(database),
        )
        if not col_result.found:
            logger.warning(f"[resolve] Collection '{collection}' not found in db='{database}' — suggesting alternatives")
            return {
                "status": "not_found",
                "label": "Collection",
                "name": col_result.name,
                "suggestions": col_result.suggestions,
            }

        logger.debug(f"[resolve] Both db='{database}' and collection='{collection}' exist")
        return None