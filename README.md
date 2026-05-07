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
│       │       ├── metadata.py             # MetadataService (list, schema, indexes, stats, explain, logs)
│       │       └── create.py              # CreateService (insert, create_collection, create_index)
│       │
│       └── tools/                          # Tool definitions (thin layer, delegates to services)
│           ├── __init__.py
│           └── mongodb.py                  # All MongoDB MCP tools (connection + metadata)
│
└── test/
    ├── conftest.py                         # Shared fixtures, env setup
    └── units/
        ├── services/
        │   ├── test_base_service.py
        │   ├── test_connection_manager.py
        │   ├── test_metadata_service.py
        │   └── test_create_service.py
        └── tools/
            ├── test_metadata_tools.py
            └── test_create_tools.py
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
| 4 | � In Progress | CRUD tools: ✅ create (insert, create_collection, create_index) · 🔲 read · 🔲 update · 🔲 delete |

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
python -m pytest test/units/ -v

# Run specific test file
python -m pytest test/units/services/test_base_service.py -v

# Run with short traceback
python -m pytest test/units/ --tb=short

# Run with coverage (if pytest-cov installed)
python -m pytest test/units/ --cov=mongodb_mcp --cov-report=term-missing
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

| Tool | Description | Params | Resolves names? |
|------|-------------|--------|-----------------|
| `connect` | Connect to a MongoDB instance | <ul><li>`connection_string` — MongoDB URI. Default: from env</li></ul> | — |
| `disconnect` | Disconnect from MongoDB | *(none)* | — |
| `list_databases` | List all databases with size | *(none)* | No |
| `list_collections` | List collections in a database | <ul><li>`database` — Database name</li></ul> | No |
| `collection_schema` | Sample documents to infer schema | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`sample_size` — Number of docs to sample. Default: `20`</li></ul> | Yes (lazy) |
| `collection_indexes` | List indexes for a collection | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li></ul> | Yes (lazy) |
| `db_stats` | Get database statistics | <ul><li>`database` — Database name</li></ul> | Yes (lazy) |
| `explain_query` | Explain a query plan (find/aggregate/count) | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`method` — One of: `find`, `aggregate`, `count`</li><li>`args` — JSON string of method arguments</li><li>`verbosity` — Detail level. Default: `"queryPlanner"`</li></ul> | Yes (lazy) |
| `get_logs` | Get MongoDB server log entries | <ul><li>`log_type` — Log category. Default: `"global"`</li><li>`limit` — Max lines to return. Default: `50`</li></ul> | No |
| `insert_one` | Insert a single document | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`document` — JSON string of document</li></ul> | No |
| `insert_many` | Insert multiple documents | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`documents` — JSON array of documents</li><li>`ordered` — Ordered insert. Default: `false`</li></ul> | No |
| `create_collection` | Create a new collection | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li></ul> | No |
| `create_index` | Create an index on a collection | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`keys` — JSON array of `[field, direction]` pairs</li><li>`unique` — Unique index. Default: `false`</li><li>`name` — Custom index name (optional)</li></ul> | Yes (lazy) |

> **Lazy resolve**: On happy path (correct name, data exists), no extra queries. Only when results are empty/error does the service resolve names and suggest fuzzy alternatives for user confirmation.
>
> **Write tools** require `READ_ONLY=false` in configuration.

## License

Apache-2.0