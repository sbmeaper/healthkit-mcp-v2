# healthki-mcp-v2 — Project Specification

## Overview

An MCP server that enables natural language queries against Apple HealthKit data. Users ask health-related questions in plain English via Claude Desktop; the server translates these to SQL, executes against a local database, and returns results with diagnostic metrics.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude Desktop │────▶│   MCP Server    │────▶│     Ollama      │
│   (MCP Client)  │◀────│    (Python)     │◀────│  (Local LLM)    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │     DuckDB      │
                        │   (Parquet)     │
                        └─────────────────┘
```

## Core Flow

1. User asks a natural language question in Claude Desktop
2. MCP server receives the question
3. MCP server sends question + semantic layer context to local LLM (via Ollama)
4. LLM returns a SQL SELECT statement
5. MCP server executes SQL against DuckDB
6. If SQL fails, error is sent back to LLM for revision (up to N retries per config)
7. MCP server returns query results + diagnostic metrics to Claude Desktop
8. Claude Desktop formulates the final answer for the user

## Technical Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Language | Python | |
| IDE | PyCharm | |
| Version Control | Git | |
| Database | DuckDB | Queries a Parquet file |
| Data File | Parquet (~2.5GB) | Single table, all HealthKit record types |
| Local LLM Runtime | Ollama | Serves models via REST API |
| Starting Model | Qwen 2.5 (7B or 14B) | Fits in 16GB RAM |
| MCP Client | Claude Desktop | Standard MCP protocol; swappable later |
| Hardware | Mac M4, 16GB RAM | All processing local |

## Data Schema

Single table with the following columns:

| Column | Type |
|--------|------|
| type | VARCHAR |
| value | DOUBLE |
| unit | VARCHAR |
| start_date | TIMESTAMP |
| end_date | TIMESTAMP |
| duration_min | DOUBLE |
| distance_km | DOUBLE |
| energy_kcal | DOUBLE |
| source_name | VARCHAR |

## Configuration

JSON file stored in the project root (committed to Git). Contains:

- **LLM settings**: Model name, API endpoint, API keys (for future cloud LLM support)
- **Database settings**: Path to Parquet file, retry limit for failed SQL
- **Semantic layer SQL**: Array of SELECT statements that run at startup to build context
- **Semantic layer static**: Optional manual descriptions/hints for the LLM

## Semantic Layer

A hybrid approach to provide the LLM with data context:

**Auto-generated at startup (SQL-driven):**
- Column names and types
- Distinct `type` values (e.g., "HKQuantityTypeIdentifierStepCount")
- Date range of data
- Row counts per type
- Min/max/avg for numeric fields

**Manually curated (config-driven):**
- Business definitions and clarifications
- Query hints or examples
- Relationships or nuances not inferable from data

The semantic layer is built once at startup and cached in memory. If underlying data changes, the MCP server must be restarted.

## MCP Response Structure

Each response includes:

- **Query results**: Data needed to answer the user's question
- **Diagnostics**:
  - Input token count
  - Output token count
  - Retry count
  - Generated SQL (final successful statement)
  - Errors encountered (if any)

## LLM Abstraction

The server is LLM-agnostic by design:

- All LLM-specific settings live in the config file
- Swapping LLMs requires only config changes, no code changes
- Architecture supports both local (Ollama) and cloud (OpenAI, Anthropic, etc.) endpoints

## Key Design Decisions

1. **Local-first**: No cloud dependencies for core functionality; manages token costs
2. **Single table**: Simplified schema; all HealthKit types in one table with a `type` discriminator
3. **Retry logic**: LLM-assisted SQL correction on failure, bounded by config
4. **Protocol-based client**: MCP standard allows future custom frontends without server changes

## Learning Objectives

- Determine how much of a semantic layer can be auto-generated vs. manually curated
- Understand local LLM operation via Ollama
- Build a practical MCP server pattern applicable to enterprise data scenarios