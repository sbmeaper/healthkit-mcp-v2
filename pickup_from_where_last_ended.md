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
| Query Logs | `~/PycharmProjects/healthkit-mcp-v2/query_logs.duckdb` |

## Core Files

| File | Purpose |
|------|---------|
| `config.json` | Model config, parquet path, log path, semantic layer hints |
| `llm_client.py` | Sends prompt to Ollama, parses SQL response |
| `query_executor.py` | DuckDB connection, creates `health_data` view, executes SQL, retry logic, logging calls |
| `query_logger.py` | Initializes log table, provides `log_attempt()` function (transactional — no persistent lock) |
| `semantic_layer.py` | Builds context from auto-queries + static hints |
| `server.py` | MCP server entry point, extracts client name from Context |

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

## Query Log Schema (query_logs.duckdb)

| Column | Type | Notes |
|--------|------|-------|
| request_id | VARCHAR | UUID, ties retry attempts together |
| attempt_number | INTEGER | 1, 2, 3... |
| timestamp | TIMESTAMP | When attempt occurred |
| client | VARCHAR | From MCP context (e.g., "claude-ai") |
| nlq | VARCHAR | Natural language question |
| sql | VARCHAR | Generated SQL for this attempt |
| success | BOOLEAN | Did this attempt execute without error? |
| error_message | VARCHAR | Null if success |
| row_count | INTEGER | Null if failed |
| execution_time_ms | INTEGER | Query execution time |

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

## Querying the Logs

With transactional logging (completed Dec 2025), log queries work even while Claude Desktop is running:

```bash
cd ~/PycharmProjects/healthkit-mcp-v2
source .venv/bin/activate
python -c "import duckdb; con = duckdb.connect('query_logs.duckdb'); print(con.execute('SELECT * FROM query_log ORDER BY timestamp DESC LIMIT 10').fetchall()); con.close()"
```

Useful queries:
```sql
-- Failed queries (for semantic layer improvement)
SELECT nlq, sql, error_message FROM query_log WHERE success = FALSE;

-- Retry patterns
SELECT request_id, COUNT(*) as attempts FROM query_log GROUP BY request_id HAVING COUNT(*) > 1;

-- Queries by client
SELECT client, COUNT(*) FROM query_log GROUP BY client;
```

---

## Next Up: Log Analyzer MCP

### Architecture Decision
Build a **log analyzer as a separate MCP server**. The log is the central artifact — decouple how queries get generated from how they get analyzed.

### What It Does
- Reads `query_logs.duckdb`
- Identifies patterns (failures, retries, common error types)
- Suggests semantic layer improvements
- Accessed via Claude Desktop with natural language (e.g., "analyze the health server logs for the past 2 days")

### Why This Approach
- Log entries come from anywhere: normal Claude Desktop usage, future automated test bots, etc.
- Analysis is independent of query source
- Natural language interface via MCP keeps workflow consistent

---

## Completed: Transactional Logging (Dec 2025)

**Problem:** `query_logger.py` previously used a persistent cached connection (`_log_connection` global). This locked `query_logs.duckdb` while Claude Desktop was running, blocking other processes from reading.

**Solution:** Refactored to transactional: open connection, write, close — per `log_attempt()` call. Lock held only milliseconds. Verified working Dec 20, 2025.

---

*Ask me for: full config.json, Claude Desktop config, debugging commands, data stats, or environment details*