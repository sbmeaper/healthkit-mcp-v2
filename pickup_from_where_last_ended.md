# healthkit-mcp-v2 — Quick Reference

**Status:** Stable and working (Dec 2025)

## What It Does

MCP server for natural language queries against Apple HealthKit data. Claude Desktop → MCP Server (Python) → Ollama (qwen2.5-coder:7b) → DuckDB (Parquet)

## Locations

| What | Path |
|------|------|
| MCP Server | `~/PycharmProjects/healthkit-mcp-v2/` |
| Export Parser | `~/PycharmProjects/healthkit_export_ripper_one_table/` |
| Parquet File | `~/PycharmProjects/healthkit_export_ripper_one_table/health.parquet` |

## Core Files

| File | Purpose |
|------|---------|
| `config.json` | Model config, parquet path, semantic layer hints |
| `llm_client.py` | Sends prompt to Ollama, parses SQL response |
| `query_executor.py` | DuckDB connection, creates `health_data` view, executes SQL, retry logic |
| `semantic_layer.py` | Builds context from auto-queries + static hints |
| `server.py` | MCP server entry point |

## Schema (health.parquet)

| Column | Type | Notes |
|--------|------|-------|
| type | VARCHAR | e.g., "StepCount", "SleepAnalysis", "WorkoutWalking" |
| value | DOUBLE | numeric measurements (steps, heart rate) |
| value_category | VARCHAR | categorical (sleep stages, stand hours) |
| unit | VARCHAR | quantity types only |
| start_date | VARCHAR | "YYYY-MM-DD HH:MM:SS" |
| end_date | VARCHAR | "YYYY-MM-DD HH:MM:SS" |
| duration_min | DOUBLE | workouts only |
| distance_km | DOUBLE | workouts only |
| energy_kcal | DOUBLE | workouts only |
| source_name | VARCHAR | device/app |

## Critical Gotchas

**DuckDB, not SQLite:**
- Use `DATE_DIFF('minute', CAST(start_date AS TIMESTAMP), CAST(end_date AS TIMESTAMP))`
- NOT `julianday()` or `strftime()`

**Sleep queries:** type='SleepAnalysis' uses `value_category`, not `value`
- Actual sleep = AsleepCore + AsleepDeep + AsleepREM (exclude Awake, InBed)

**Aggregation:**
- Steps/distance/calories: `SUM(value)` — rows are partial measurements
- Heart rate/weight: `AVG(value)` or single value
- Events: `COUNT(*)`

**Restart required:** Changes to config.json or semantic layer need full Claude Desktop restart

---

## Next Up: Query Logging

### Goal
Add observability to systematically improve the semantic layer, rather than ad-hoc debugging.

### Design Decisions Made

**Log storage:** DuckDB table (same database as health data, or separate file—TBD)

**Schema (Option B: one row per attempt):**
| Column | Type | Notes |
|--------|------|-------|
| request_id | VARCHAR | UUID, ties attempts together |
| attempt_number | INTEGER | 1, 2, 3... |
| timestamp | TIMESTAMP | When attempt occurred |
| client | VARCHAR | From MCP context (e.g., "Claude Desktop", "QA harness") |
| nlq | VARCHAR | Natural language question |
| sql | VARCHAR | Generated SQL for this attempt |
| success | BOOLEAN | Did this attempt execute without error? |
| error_message | VARCHAR | Null if success |
| row_count | INTEGER | Null if failed |
| execution_time_ms | INTEGER | Query execution time |

**Dropped:** `user` column—not available via MCP protocol for local stdio servers, and not useful for semantic layer analysis.

**Client identity:** Available via FastMCP Context: `ctx.session.client_params.clientInfo.name`

### Implementation Plan

1. **New file: `query_logger.py`**
   - Initialize/create log table
   - `log_attempt()` function

2. **Modify: `query_executor.py`**
   - Generate request_id (UUID) at start of `execute_with_retry()`
   - Wrap `execute_query()` with timing
   - Call `log_attempt()` after each execution inside the retry loop
   - Pass Context through to access client info

3. **Modify: `server.py`**
   - Add Context parameter to `query_health_data()` tool
   - Pass context to `execute_with_retry()`

### Future: QA Harness (Phase 2)
Separate Python program that:
- Generates health-related NLQ test cases
- Calls the MCP server (with logging capturing results)
- Uses LLM-as-judge to evaluate if SQL logic matches intent
- Identifies patterns for semantic layer improvements

---

*Ask me for: full config.json, Claude Desktop config, debugging commands, data stats, or environment details*