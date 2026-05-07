from typing import Callable, Awaitable, List
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
            # logger.info("[connection] State=%s — initiating auto-connect", connection_manager.state.value)
            await connection_manager.connect()
            logger.info("[connection] Auto-connect successful")
        return connection_manager.get_client()

    def _check_write_allowed(self) -> None:
        """Raise if server is in read-only mode."""
        if configs.read_only:
            logger.warning("[policy] Write operation blocked — server is in READ_ONLY mode")
            raise PermissionError("Write operations are disabled in read-only mode.")

    def _validate_name(self, value: str, label: str = "name") -> None:
        """Raise if name is empty or whitespace."""
        if not value or not value.strip():
            logger.warning("[validation] %s is empty or whitespace", label)
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
        logger.debug("[resolve] Resolving name='%s' against available list", name)
        available = await fetch_available()
        logger.debug("[resolve] Available names (%d): %s", len(available), available[:10])

        # Name exists in DB — not a typo, data is genuinely empty/error is unrelated
        if name in available:
            logger.debug("[resolve] name='%s' found — data is genuinely empty", name)
            return ResolveResult(found=True, name=name)

        # Name does NOT exist — find suggestions for user to confirm

        # Strategy 1: difflib — catches character-level typos (uesrs → users)
        suggestions = get_close_matches(name, available, n=max_suggestions, cutoff=cutoff)
        if suggestions:
            logger.info("[resolve] name='%s' not found — difflib suggestions: %s", name, suggestions)

        # Strategy 2: word match — catches partial/substring (user log → user_logs)
        if not suggestions:
            words = [w for w in name.replace("-", " ").replace("_", " ").split() if len(w) > 2]
            if words:
                suggestions = [
                    item for item in available
                    if any(w.lower() in item.lower() for w in words)
                ][:max_suggestions]
                if suggestions:
                    logger.info("[resolve] name='%s' not found — word-match suggestions (words=%s): %s", name, words, suggestions)

        # Strategy 3: fallback — nothing matched, show what's available
        if not suggestions:
            suggestions = available[:max_suggestions]
            logger.info("[resolve] name='%s' not found — no close match, showing available: %s", name, suggestions)

        logger.warning("[resolve] Name '%s' does not exist. Returning %d suggestions for user confirmation", name, len(suggestions))
        return ResolveResult(found=False, name=name, suggestions=suggestions)