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
mongodb-mcp-server-python/
├── pyproject.toml
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
│       │   ├── mongodb/                    # MongoDB client (pymongo)
│       │   │   ├── __init__.py             # MongoDBClient (mixin composition)
│       │   │   ├── base.py                 # BaseMongoClient (connection, ping, close)
│       │   │   ├── metadata.py             # list_databases, list_collections, indexes, stats, explain, logs
│       │   │   ├── read.py                 # find, aggregate, aggregate_db, count_documents
│       │   │   ├── create.py               # insert_one, insert_many, create_collection, create_index
│       │   │   ├── update.py               # update_one, update_many, rename_collection
│       │   │   └── delete.py               # delete_one, delete_many, drop_collection, drop_database, drop_index
│       │   └── atlas/                      # (Future) Atlas Admin API client
│       │       └── __init__.py
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   └── connection_manager.py       # Connection state machine (singleton)
│       │
│       └── tools/                          # Tool definitions (thin layer, delegates to services/clients)
│           ├── __init__.py
│           ├── metadata.py                 # list-databases, list-collections, collection-schema, etc.
│           ├── read.py                     # find, aggregate, count
│           ├── create.py                   # insert-many, create-collection, create-index
│           ├── update.py                   # update-many, rename-collection
│           └── delete.py                   # delete-many, drop-collection, drop-database
│
└── tests/
    ├── unit/
    ├── integration/
    └── conftest.py
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Tools Layer (server.py + tools/)                   │
│  - Defines MCP tool name, description, schema       │
│  - Formats output for LLM consumption              │
│  - Handles errors with user-friendly messages       │
├─────────────────────────────────────────────────────┤
│  Services Layer (services/)                         │
│  - Connection state management                      │
│  - Read-only mode enforcement                       │
│  - Confirmation flow for destructive operations     │
│  - Input validation, timeout, error classification  │
├─────────────────────────────────────────────────────┤
│  Clients Layer (clients/)                           │
│  - Pure pymongo async calls                         │
│  - No business logic, no error handling             │
│  - Translates Python params → pymongo operations    │
└─────────────────────────────────────────────────────┘
            │
            ▼
       MongoDB (via AsyncMongoClient)
```

## Implementation Plan

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Done | Project setup: `pyproject.toml`, FastMCP server skeleton, config |
| 2 | ✅ Done | Client layer: `MongoDBClient` (mixin-based) + `ConnectionManager` |
| 3 | 🔲 Next | Metadata tools: list-databases, list-collections, collection-schema, db-stats, collection-indexes, explain, logs |
| 4 | 🔲 | CRUD tools: find, aggregate, count, insert, update, delete, drop |

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Set connection string
export MONGODB_CONNECTION_STRING="mongodb://localhost:27017"

# Run server (stdio transport)
fastmcp run src/mongodb_mcp/server.py:mcp
```

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
- **[pytest](https://docs.pytest.org/)** — Testing framework

## License

Apache-2.0 