# MongoDB-FastMCP-Server

A Python-based MongoDB MCP server built with [FastMCP](https://github.com/PrefectHQ/fastmcp).

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
│       │       ├── read.py                 # ReadService (find, aggregate, count_documents, distinct)
│       │       ├── create.py               # CreateService (insert, create_collection, create_index)
│       │       ├── update.py               # UpdateService (update_one, update_many, rename_collection)
│       │       └── delete.py               # DeleteService (delete_one, delete_many, drop_collection, drop_database, drop_index)
│       │
│       └── tools/                          # Tool definitions (thin layer, delegates to services)
│           ├── __init__.py                 # Logging setup
│           ├── connection.py               # connect, disconnect
│           └── mongodb/                    # MongoDB tools package
│               ├── __init__.py             # Re-exports all tools + side-effect imports
│               ├── _utils.py               # _format_not_found helper
│               ├── metadata.py             # list_databases, list_collections, collection_schema, collection_indexes, db_stats, explain_query, get_logs, collection_stats
│               ├── create.py               # insert_one, insert_many, create_collection, create_index
│               ├── read.py                 # find, aggregate, count_documents, distinct
│               ├── update.py               # update_one, update_many, rename_collection
│               └── delete.py              # delete_one, delete_many, drop_collection, drop_database, drop_index
│
└── test/
    ├── conftest.py                         # Shared fixtures, env setup
    └── units/
        ├── services/
        │   ├── test_base_service.py
        │   ├── test_connection_manager.py
        │   ├── test_metadata_service.py
        │   ├── test_create_service.py
        │   ├── test_read_service.py
        │   ├── test_update_service.py
        │   └── test_delete_service.py
        └── tools/
            ├── test_metadata_tools.py
            ├── test_create_tools.py
            ├── test_read_tools.py
            ├── test_update_tools.py
            └── test_delete_tools.py
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
| 3 | ✅ Done | Service layer + Metadata tools: list-databases, list-collections, collection-schema, db-stats, collection-indexes, collection-stats, explain, logs |
| 4 | ✅ Done | CRUD tools: ✅ create (insert, create_collection, create_index) · ✅ read (find, aggregate, count_documents, distinct) · ✅ update (update_one, update_many, rename_collection) · ✅ delete (delete_one, delete_many, drop_collection, drop_database, drop_index) |

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

## MCP Inspector

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a browser-based tool for interactively testing MCP servers and their tools.

```bash
# Run MCP Inspector against this server (npx, no install required)
npx @modelcontextprotocol/inspector fastmcp run src/mongodb_mcp/server.py:mcp
```

Then open `http://localhost:6274` in your browser. From there you can:
- Browse all registered tools and their input schemas
- Call tools manually and inspect structured responses
- Debug tool outputs without needing a full MCP client

> **Note**: Set `MONGODB_CONNECTION_STRING` in your environment or `.env` file before running.

### Install Node.js (required for npx)

**macOS**
```bash
brew install node
```

**Ubuntu / Debian**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Windows**

Download and run the installer from [nodejs.org](https://nodejs.org).

Verify installation:
```bash
node --version   # should be ≥ 18
npx --version
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
| `ALLOW_DESTRUCTIVE` | `false` | Allow destructive operations (delete, drop). Requires `READ_ONLY=false` |
| `DEFAULT_TIMEOUT_MS` | `30000` | Default timeout for MongoDB operations |
| `WRITE_ALLOWLIST` | *(unset)* | Comma-separated `db.collection` patterns allowed for writes (see below) |

### Write Allowlist

When `READ_ONLY=false`, you can further restrict which databases/collections accept writes:

```bash
# Allow specific targets
WRITE_ALLOWLIST=mydb.users,mydb.orders,testdb.*

# Allow all collections in a database
WRITE_ALLOWLIST=prod.*

# Explicit allow-all
WRITE_ALLOWLIST=*

# Not set or empty → allow all (backward compatible)
```

| Pattern | Meaning |
|---------|---------|
| `db.col` | Exact match only |
| `db.*` | All collections in that database |
| `*` | Allow all writes |
| *(empty/unset)* | Allow all writes (backward compatible) |

### Security Model

Write operations go through 3 policy checks:

```
_check_write_allowed()         → READ_ONLY=false?
_check_destructive_allowed()   → ALLOW_DESTRUCTIVE=true? (delete/drop only)
_check_write_target()          → WRITE_ALLOWLIST match?
```

| `READ_ONLY` | `ALLOW_DESTRUCTIVE` | Allowed operations |
|---|---|---|
| `true` (default) | *(ignored)* | Read + metadata only |
| `false` | `false` (default) | insert, update, create_index, create_collection, rename_collection |
| `false` | `true` | All of above + delete_one, delete_many, drop_collection, drop_database, drop_index |

> `rename_collection` with `drop_target=true` also requires `ALLOW_DESTRUCTIVE=true` since it destroys the target collection.

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
| `find` | Query documents from a collection | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`filter` — JSON filter. Default: `"{}"`</li><li>`projection` — JSON projection (optional)</li><li>`sort` — JSON array of `[field, direction]` pairs (optional)</li><li>`skip` — Documents to skip. Default: `0`</li><li>`limit` — Max documents. Default: `10`</li></ul> | Yes (lazy) |
| `aggregate` | Run an aggregation pipeline | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`pipeline` — JSON array of stage objects</li><li>`limit` — Max results. Default: `1000`</li></ul> | Yes (lazy) |
| `count_documents` | Count documents matching a filter | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`filter` — JSON filter. Default: `"{}"`</li></ul> | Yes (lazy) |
| `distinct` | Get distinct values of a field | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`field` — Field name</li><li>`filter` — JSON filter. Default: `"{}"`</li></ul> | Yes (lazy) |
| `collection_stats` | Get storage statistics for a collection | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li></ul> | Yes (lazy) |
| `update_one` | Update a single document matching a filter | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`filter` — JSON filter string</li><li>`update` — JSON update with operators (`$set`, `$inc`, etc.)</li><li>`upsert` — Insert if no match. Default: `false`</li></ul> | Yes (lazy) |
| `update_many` | Update all documents matching a filter | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`filter` — JSON filter string</li><li>`update` — JSON update with operators (`$set`, `$inc`, etc.)</li><li>`upsert` — Insert if no match. Default: `false`</li></ul> | Yes (lazy) |
| `rename_collection` | Rename a collection | <ul><li>`database` — Database name</li><li>`collection` — Current collection name</li><li>`new_name` — New collection name</li><li>`drop_target` — Overwrite if target exists. Default: `false`</li></ul> | Yes (lazy) |
| `delete_one` | Delete a single document matching a filter | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`filter` — JSON filter string</li></ul> | Yes (lazy) |
| `delete_many` | Delete all documents matching a filter | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`filter` — JSON filter string. Use `'{}'` to delete all</li></ul> | Yes (lazy) |
| `drop_collection` | Drop a collection and all its data (irreversible) | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li></ul> | Yes (lazy) |
| `drop_database` | Drop an entire database (irreversible) | <ul><li>`database` — Database name</li></ul> | Yes (lazy) |
| `drop_index` | Drop an index by name | <ul><li>`database` — Database name</li><li>`collection` — Collection name</li><li>`index_name` — Index name (use `collection_indexes` to find names)</li></ul> | Yes (lazy) |

> **Lazy resolve**: On happy path (correct name, data exists), no extra queries. Only when results are empty/error does the service resolve names and suggest fuzzy alternatives for user confirmation.
>
> **Write tools** require `READ_ONLY=false` in configuration.

## License

Apache-2.0