# healthkit-mcp-v2 — Project Status Summary

**Last Updated:** December 20, 2025  
**Status:** Stable and working

---

## What This Project Does

An MCP server that lets users ask natural language questions about their Apple HealthKit data via Claude Desktop. Questions are translated to SQL by a local LLM (Ollama), executed against a DuckDB/Parquet database, and results returned with diagnostics.

---

## Project Locations

**MCP Server Project:**
```
/Users/scottbartlow/PycharmProjects/healthkit-mcp-v2/
```

**HealthKit Export Parser Project:**
```
/Users/scottbartlow/PycharmProjects/healthkit_export_ripper_one_table/
```

**Parquet Data File:**
```
/Users/scottbartlow/PycharmProjects/healthkit_export_ripper_one_table/health.parquet
```

---

## Architecture

```
Claude Desktop → MCP Server (Python) → Ollama (Qwen 2.5 Coder 7B) → DuckDB (Parquet)
```

---

## Recent Changes (Dec 19, 2025)

Four improvements were implemented based on Qwen2.5-Coder best practices:

1. **Switched to code-specialized model** — `qwen2.5-coder:7b` instead of general `qwen2.5:7b`
2. **Restructured prompt template** — Matches Qwen2.5-Coder's text-to-SQL training format (DDL schema → sample rows → hints → question → `SELECT` prefix)
3. **Added DuckDB-specific hints** — Explicit guidance on `DATE_DIFF()`, `CAST()`, and warnings against SQLite syntax
4. **Cleaner table reference** — Created `health_data` view at startup instead of embedding full parquet path in prompts

All changes are deployed and the system is working well.

---

## Core Files

| File | Purpose |
|------|---------|
| `config.json` | Model config, parquet path, semantic layer hints |
| `semantic_layer.py` | Builds context from auto-queries and static hints, formats as DDL + samples |
| `llm_client.py` | Sends prompt to Ollama, parses SQL response |
| `query_executor.py` | Persistent DuckDB connection, creates `health_data` view, executes SQL |
| `server.py` | MCP server entry point |

---

## Current config.json

```json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen2.5-coder:7b",
    "endpoint": "http://localhost:11434/api/generate"
  },
  "database": {
    "parquet_path": "/Users/scottbartlow/PycharmProjects/healthkit_export_ripper_one_table/health.parquet",
    "max_retries": 3
  },
  "semantic_layer": {
    "auto_queries": [
      "SELECT DISTINCT type FROM '{parquet_path}' ORDER BY type",
      "SELECT MIN(start_date) as min_date, MAX(start_date) as max_date FROM '{parquet_path}'",
      "SELECT type, COUNT(*) as row_count FROM '{parquet_path}' GROUP BY type ORDER BY row_count DESC",
      "SELECT DISTINCT type, value_category FROM '{parquet_path}' WHERE value_category IS NOT NULL ORDER BY type, value_category"
    ],
    "static_context": [
      "DATABASE: DuckDB (not SQLite, not PostgreSQL)",
      
      "DATE HANDLING - dates are stored as VARCHAR in 'YYYY-MM-DD HH:MM:SS' format:",
      "  - Cast to timestamp: CAST(start_date AS TIMESTAMP)",
      "  - Extract year: YEAR(CAST(start_date AS TIMESTAMP))",
      "  - Extract month: MONTH(CAST(start_date AS TIMESTAMP))",
      "  - Filter by year: WHERE YEAR(CAST(start_date AS TIMESTAMP)) = 2024",
      "  - Filter by month: WHERE start_date >= '2024-11-01' AND start_date < '2024-12-01'",
      
      "DURATION CALCULATION - to get duration between start_date and end_date:",
      "  - Minutes: DATE_DIFF('minute', CAST(start_date AS TIMESTAMP), CAST(end_date AS TIMESTAMP))",
      "  - Hours: DATE_DIFF('minute', CAST(start_date AS TIMESTAMP), CAST(end_date AS TIMESTAMP)) / 60.0",
      "  - DO NOT use julianday() or strftime() - those are SQLite, not DuckDB",
      
      "SLEEP QUERIES - type='SleepAnalysis' uses value_category, NOT value:",
      "  - Sleep stages: AsleepCore, AsleepDeep, AsleepREM, AsleepUnspecified, Awake, InBed",
      "  - Actual sleep = AsleepCore + AsleepDeep + AsleepREM (exclude Awake, InBed)",
      "  - Sleep duration example: SELECT SUM(DATE_DIFF('minute', CAST(start_date AS TIMESTAMP), CAST(end_date AS TIMESTAMP))) / 60.0 AS hours_slept FROM health_data WHERE type = 'SleepAnalysis' AND value_category IN ('AsleepCore', 'AsleepDeep', 'AsleepREM')",
      
      "AGGREGATION RULES:",
      "  - Steps, distance, calories: use SUM(value), each row is a partial measurement",
      "  - Heart rate, weight: use AVG(value) for averages, or just value for point-in-time",
      "  - Counting events: use COUNT(*)",
      
      "WORKOUT QUERIES - type starts with 'Workout' (e.g., 'WorkoutWalking', 'WorkoutCycling'):",
      "  - Has duration_min, distance_km, energy_kcal columns",
      "  - Example: SELECT SUM(duration_min) FROM health_data WHERE type = 'WorkoutWalking'",
      
      "STRING ESCAPING: double apostrophes, not backslash: 'Scott''s Watch'"
    ]
  }
}
```

---

## Claude Desktop Configuration

File: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "healthkit": {
      "command": "/Users/scottbartlow/PycharmProjects/healthkit-mcp-v2/.venv/bin/python",
      "args": [
        "/Users/scottbartlow/PycharmProjects/healthkit-mcp-v2/server.py"
      ]
    }
  }
}
```

**Note:** Changes to config.json or semantic layer require a full Claude Desktop restart since context is built once at startup.

---

## Data Schema (Parquet)

```
type              VARCHAR     -- normalized type name (e.g., "StepCount", "SleepAnalysis", "WorkoutWalking")
value             DOUBLE      -- numeric value (quantity types like steps, heart rate)
value_category    VARCHAR     -- categorical value (category types like sleep stages)
unit              VARCHAR     -- unit (quantity types only)
start_date        VARCHAR     -- timestamp as string "YYYY-MM-DD HH:MM:SS"
end_date          VARCHAR     -- timestamp as string "YYYY-MM-DD HH:MM:SS"
duration_min      DOUBLE      -- workouts only
distance_km       DOUBLE      -- workouts only
energy_kcal       DOUBLE      -- workouts only
source_name       VARCHAR     -- device/app that recorded the data
```

**Key design decisions:**
- `value` for numeric measurements, `value_category` for categorical (sleep stages, stand hours)
- Dates stored as strings (DuckDB casts on query)
- ActivitySummary and Correlation records are skipped (computed/derived data)

---

## Data Stats

- **Total rows:** 5,631,852 (5,628,491 records + 3,361 workouts)
- **Date range:** December 2020 – December 2025
- **Metric types:** 98 distinct types
- **File size:** 49.2 MB

**Category values in data:**
- SleepAnalysis: AsleepCore, AsleepDeep, AsleepREM, AsleepUnspecified, Awake, InBed
- AppleStandHour: Stood, Idle
- AudioExposureEvent: MomentaryLimit

---

## Debugging Tips

**MCP server logs:**
```bash
tail -50 ~/Library/Logs/Claude/mcp-server-healthkit.log
```

**Test server manually:**
```bash
cd /Users/scottbartlow/PycharmProjects/healthkit-mcp-v2
.venv/bin/python server.py
```

**Test Ollama directly:**
```bash
ollama run qwen2.5-coder:7b "Write a DuckDB SQL query to count rows in a table called health_data"
```

**Query Parquet directly (bypass LLM):**
```bash
python -c "import duckdb; print(duckdb.execute(\"SELECT SUM(DATE_DIFF('minute', CAST(start_date AS TIMESTAMP), CAST(end_date AS TIMESTAMP))) / 60.0 AS hours FROM '/Users/scottbartlow/PycharmProjects/healthkit_export_ripper_one_table/health.parquet' WHERE type = 'SleepAnalysis' AND value_category IN ('AsleepCore', 'AsleepDeep', 'AsleepREM') AND start_date >= '2025-11-01' AND start_date < '2025-12-01'\").fetchall())"
```

**Check Ollama model:**
```bash
ollama list
```

---

## Potential Future Work

1. **Add few-shot examples** — Include input question → output SQL pairs directly in prompt if complex queries still struggle
2. **Try larger model** — `qwen2.5-coder:14b` or `qwen2.5-coder:32b` if 7B has accuracy issues
3. **Fine-tune on DuckDB** — `motherduckdb/duckdb-text2sql-25k` dataset available
4. **Consider SQLCoder** — Alternative model specifically fine-tuned for SQL generation

---

## Key Learnings

**Prompt engineering for semantic layer:**
- Static context should include specific guidance on when to use `SUM(value)` vs `COUNT(*)` 
- DuckDB-specific syntax hints are essential (`DATE_DIFF` not `julianday`)
- Complete working examples in hints significantly improve SQL generation

**Data quality approach:**
- Fix issues at semantic layer for scalability (vs fixing at source)
- Auto-queries for schema discovery help LLM understand categorical data structures

**Qwen2.5-Coder best practices:**
- Text-to-SQL format: DDL schema → sample rows → hints → question
- End prompt with `SELECT` to prime continuation
- The `-coder` variant significantly better than base model for SQL tasks

---

## Environment Details

**MCP Server (.venv):**
- Python 3.13
- Packages: `duckdb`, `requests`, `mcp`

**Ollama:**
- Installed via macOS app (runs in menu bar)
- Model: `qwen2.5-coder:7b`

**Hardware:**
- M4 MacBook, 16GB RAM