# mongodb-mcp-server

A Python-based MongoDB MCP server built with [FastMCP](https://github.com/jlowin/fastmcp).

This repository exposes MongoDB operations as MCP tools, allowing MCP-compatible clients and AI agents to connect to MongoDB, inspect databases and collections, and execute controlled database operations through a clean tool interface.

## Overview

`mongodb-mcp-server` is designed to provide a structured bridge between MongoDB and the Model Context Protocol.

Instead of letting an agent interact with MongoDB directly, this server exposes selected database capabilities as well-defined MCP tools. This makes database access easier to control, validate, extend, and maintain.

## Features

- Connect to MongoDB from a Python MCP server
- Expose MongoDB operations as FastMCP tools
- List databases and collections
- Inspect collection metadata (schema, indexes, storage size, stats, logs)
- Run controlled queries (find, aggregate, count) against collections
- Full CRUD support (insert, update, delete)
- Destructive operation confirmation (2-step pattern)
- Read-only mode support
- Separate MongoDB client logic from MCP tool definitions
- Designed for agentic workflows and MCP-compatible clients

## Project Structure

```txt
mongodb-mcp-server/
├── pyproject.toml
├── pytest.ini
├── README.md
├── .env
├── src/
│   └── mongodb_mcp/
│       ├── __init__.py
│       ├── server.py                       # FastMCP instance, tool registration
│       ├── configs.py                      # Config via pydantic-settings (env vars)
│       │
│       ├── clients/
│       │   ├── __init__.py
│       │   └── mongodb/                    # MongoDB client (pymongo)
│       │       ├── __init__.py             # MongoDBClient (mixin composition)
│       │       ├── base.py                 # BaseMongoClient (connection, ping, close)
│       │       ├── metadata.py             # list_databases, list_collections, indexes, stats, explain, logs
│       │       ├── read.py                 # find, aggregate, aggregate_db, count_documents
│       │       ├── create.py               # insert_one, insert_many, create_collection, create_index
│       │       ├── update.py               # update_one, update_many, rename_collection
│       │       └── delete.py               # delete_one, delete_many, drop_collection, drop_database, drop_index
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── connection_manager.py       # Connection state machine (singleton)
│       │   └── mongodb/                    # MongoDB service layer (mixin-based)
│       │       ├── __init__.py             # MongoDBService (composed) + singleton
│       │       ├── base.py                 # BaseMongoDBService (ensure_connected, resolve_name, validation)
│       │       └── metadata.py             # MetadataService (list, schema, indexes, stats, explain, logs)
│       │
│       └── tools/                          # Tool definitions (thin layer, delegates to services)
│           ├── __init__.py
│           └── mongodb.py                  # All MongoDB MCP tools (connection + metadata)
│
└── tests/
    ├── conftest.py                         # Shared fixtures, env setup
    └── unit/
        ├── services/
        │   ├── test_base_service.py
        │   ├── test_connection_manager.py
        │   └── test_metadata_service.py
        └── tools/
            └── test_metadata_tools.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Tools Layer (tools/)                                   │
│  - Defines MCP tool name, description, schema           │
│  - Formats output for LLM consumption                  │
│  - Try/except top-level, returns user-friendly messages │
├─────────────────────────────────────────────────────────┤
│  Services Layer (services/mongodb/)                     │
│  - Auto-connect (ensure_connected)                      │
│  - Input validation (_validate_name)                    │
│  - Lazy name resolution with fuzzy suggestions          │
│  - Read-only mode enforcement                           │
│  - Error classification and logging                     │
├─────────────────────────────────────────────────────────┤
│  Clients Layer (clients/mongodb/)                       │
│  - Pure pymongo async calls                             │
│  - No business logic, no error handling                 │
│  - Translates Python params → pymongo operations        │
└─────────────────────────────────────────────────────────┘
            │
            ▼
       MongoDB (via AsyncMongoClient)
```

### Key Design Decisions

- **Lazy Name Resolution**: Tools call MongoDB directly first. Only when results are empty/error does the service layer resolve names and suggest alternatives. Zero overhead on happy path.
- **Mixin Composition**: Both client and service layers use the same pattern — base class + mixins → composed class. Easy to extend with new operation types.
- **Singleton Services**: `connection_manager` and `mongodb_service` are module-level singletons shared across all tools.
- **Structured Logging**: Every layer uses Python `logging` with prefix tags (`[connection]`, `[resolve]`, `[tool:name]`) for easy grep-based debugging.

## Implementation Plan

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Done | Project setup: `pyproject.toml`, FastMCP server skeleton, config |
| 2 | ✅ Done | Client layer: `MongoDBClient` (mixin-based) + `ConnectionManager` |
| 3 | ✅ Done | Service layer + Metadata tools: list-databases, list-collections, collection-schema, db-stats, collection-indexes, explain, logs |
| 4 | 🔲 Next | CRUD tools: find, aggregate, count, insert, update, delete, drop |

## Quick Start

```bash
# Install in editable mode
pip install -e ".[dev]"

# Set connection string
export MONGODB_CONNECTION_STRING="mongodb://localhost:27017"

# Run server (stdio transport)
fastmcp run src/mongodb_mcp/server.py:mcp

# Or use FastMCP dev UI
fastmcp dev src/mongodb_mcp/server.py:mcp
```

## Testing

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all unit tests
python -m pytest tests/unit/ -v

# Run specific test file
python -m pytest tests/unit/services/test_base_service.py -v

# Run with short traceback
python -m pytest tests/unit/ --tb=short

# Run with coverage (if pytest-cov installed)
python -m pytest tests/unit/ --cov=mongodb_mcp --cov-report=term-missing
```

> **Note**: Tests mock all MongoDB interactions — no running MongoDB instance required for unit tests.

## Configuration

Environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_CONNECTION_STRING` | *(required)* | MongoDB connection URI |
| `READ_ONLY` | `true` | Only allow read/metadata operations |
| `DEFAULT_TIMEOUT_MS` | `30000` | Default timeout for MongoDB operations |

## Tech Stack

- **[FastMCP](https://github.com/jlowin/fastmcp)** — MCP server framework (handles transport, protocol, tool registration)
- **[PyMongo](https://pymongo.readthedocs.io/)** — MongoDB driver (`AsyncMongoClient`)
- **[Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)** — Configuration management from env vars
- **[pytest](https://docs.pytest.org/)** + **[pytest-asyncio](https://pytest-asyncio.readthedocs.io/)** — Async-aware testing framework

## Available Tools

| Tool | Description | Resolves names? |
|------|-------------|-----------------|
| `connect` | Connect to a MongoDB instance | — |
| `disconnect` | Disconnect from MongoDB | — |
| `list_databases` | List all databases with size | No |
| `list_collections` | List collections in a database | No |
| `collection_schema` | Sample documents to infer schema | Yes (lazy) |
| `collection_indexes` | List indexes for a collection | Yes (lazy) |
| `db_stats` | Get database statistics | Yes (lazy) |
| `explain_query` | Explain a query plan (find/aggregate/count) | Yes (lazy) |
| `get_logs` | Get MongoDB server log entries | No |

> **Lazy resolve**: On happy path (correct name, data exists), no extra queries. Only when results are empty/error does the service resolve names and suggest fuzzy alternatives for user confirmation.

## License

Apache-2.0