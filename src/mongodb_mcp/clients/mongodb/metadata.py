from .base import BaseMongoClient
from typing import List, Dict, Any

class MetadataClient(BaseMongoClient):
    async def list_database_names(self) -> List[Dict[str, Any]]:
        """List all databases with name and size."""
        result = await self._client.admin.command("listDatabases")
        return [
            {"name": db["name"], "size": db.get("sizeOnDisk", 0)}
            for db in result["databases"]
        ]

    async def list_collection_names(self, database: str) -> list[str]:
        """List all collection names in a database."""
        db = self._client[database]
        return await db.list_collection_names()
    
    async def collection_indexes(self, database: str, collection: str) -> List[Dict[str, Any]]:
        """List all indexes for a collection"""
        col = self._client[database][collection]
        cursor = col.list_indexes()
        return await cursor.to_list()
    
    async def collection_schema(self, database: str, collection: str, sample_size: int = 20) -> List[Dict[str, Any]]:
        """Sample documents for schema inference."""
        col = self._client[database][collection]
        cursor = col.aggregate([{"$sample": {"size": sample_size}}])
        return await cursor.to_list(length=sample_size)
    
    async def collection_storage_size(self, database: str, collection: str) -> int:
        """Get storage size of a collection in bytes."""
        col = self._client[database][collection]
        cursor = col.aggregate([
            {"$collStats": {"storageStats": {}}},
            {"$group": {"_id": None, "value": {"$sum": "$storageStats.size"}}},
        ])
        results = await cursor.to_list(length=1)
        if results:
            return results[0]["value"]
        return 0
    
    async def db_stats(self, database: str) -> Dict[str, Any]:
        """Get statistics for a database."""
        db = self._client[database]
        return await db.command("dbStats", scale=1)

    async def explain(
        self,
        database: str,
        collection: str,
        method: str,
        args: dict[str, Any],
        verbosity: str = "queryPlanner",
    ) -> dict[str, Any]:
        """Explain a query plan for find, aggregate, or count."""
        col = self._client[database][collection]

        if method == "aggregate":
            pipeline = args.get("pipeline", [])
            cursor = col.aggregate(pipeline)
            return await cursor.explain(verbosity)
        elif method == "find":
            filter_ = args.get("filter", {})
            cursor = col.find(filter_)
            return await cursor.explain(verbosity)
        elif method == "count":
            # Explain via command
            db = self._client[database]
            return await db.command({
                "explain": {"count": collection, "query": args.get("filter", {})},
                "verbosity": verbosity,
            })
        else:
            raise ValueError(f"Unsupported explain method: {method}")

    async def get_logs(self, log_type: str = "global", limit: int = 50) -> dict[str, Any]:
        """Get recent mongod log entries."""
        result = await self._client.admin.command("getLog", log_type)
        logs = [line.rstrip() for line in result.get("log", [])][:limit]
        return {
            "logs": logs,
            "total_lines_written": result.get("totalLinesWritten", 0),
        }
