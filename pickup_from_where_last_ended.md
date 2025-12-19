# healthkit-mcp-v2 — Project Status Summary

**Last Updated:** December 19, 2025  
**Status:** Core functionality complete, minor tuning needed for date arithmetic

---

## What This Project Does

An MCP server that lets users ask natural language questions about their Apple HealthKit data via Claude Desktop. Questions are translated to SQL by a local LLM (Ollama + Qwen 2.5 7B), executed against a DuckDB/Parquet database, and results returned with diagnostics.

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

**Raw HealthKit Export:**
```
/Users/scottbartlow/PycharmProjects/healthkit_export_ripper_one_table/export.xml
```

---

## Architecture

```
Claude Desktop → MCP Server (Python) → Ollama (Qwen 2.5 7B) → DuckDB (Parquet)
```

---

## MCP Server Files (/healthkit-mcp-v2/)

| File | Purpose |
|------|---------|
| `config.json` | All settings: LLM endpoint, Parquet path, retry limit, semantic layer |
| `semantic_layer.py` | Loads config, runs auto-queries at startup, builds LLM context string |
| `llm_client.py` | Calls Ollama API, generates SQL from natural language + context |
| `query_executor.py` | Executes SQL against DuckDB, handles retry logic with LLM correction |
| `server.py` | MCP server entry point, exposes `query_health_data` tool |
| `test_db.py` | One-off test script (can be deleted) |

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
- Dates stored as strings (faster parsing, DuckDB casts on query)
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
- HighHeartRateEvent: NotApplicable
- MindfulSession: NotApplicable

---

## Current config.json

```json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen2.5:7b",
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
      "All HealthKit data is in a single table. The 'type' column indicates the measurement type.",
      "Dates are stored as strings in 'YYYY-MM-DD HH:MM:SS' format. Use date functions for filtering.",
      "The 'value' column contains numeric measurements. The 'value_category' column contains categorical values (like sleep stages).",
      "When asked 'how many' for metrics like steps, calories, or distance, use SUM(value) not COUNT(*). Each row is a measurement interval, not a single unit.",
      "In DuckDB, escape apostrophes in strings by doubling them: 'Scott''s Watch' not 'Scott\\'s Watch'.",
      "For sleep data: 'value_category' contains sleep stages: AsleepCore, AsleepDeep, AsleepREM, AsleepUnspecified, Awake, InBed. To calculate actual sleep time, sum duration of AsleepCore + AsleepDeep + AsleepREM rows only. Calculate duration as (end_date - start_date).",
      "For AppleStandHour: 'value_category' is either 'Stood' or 'Idle'.",
      "To calculate duration between dates: use DATE_DIFF('minute', CAST(start_date AS TIMESTAMP), CAST(end_date AS TIMESTAMP)) to get minutes between two date strings."
    ]
  }
}
```

---

## Claude Desktop Configuration

File: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "preferences": {
    "quickEntryShortcut": "off"
  },
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

---

## Environment Details

**MCP Server (.venv):**
- Python 3.13
- Packages: `duckdb`, `requests`, `mcp`

**Export Parser (.venv):**
- Python (version in that project)
- Packages: `duckdb`, `lxml`, `pyarrow`

**Ollama:**
- Installed via macOS app (runs in menu bar)
- Model: `qwen2.5:7b`

---

## What's Working

- ✅ Natural language → SQL generation via Qwen 2.5 7B
- ✅ SQL execution against Parquet via DuckDB
- ✅ MCP server connected to Claude Desktop
- ✅ Semantic layer auto-generates context at startup
- ✅ Diagnostics returned (SQL, tokens, retries, errors)
- ✅ Sleep stages captured in `value_category` column
- ✅ Export parser runs in 29 seconds (was ~60 minutes)

**Tested queries that work:**
- "How many steps did I take in 2024?" → 7,681,979 steps (uses SUM correctly)

---

## Current Issue / Next Step

**Sleep duration queries failing.** The LLM struggles with date arithmetic because dates are strings. Last attempt used SQLite syntax (`julianday`) which doesn't exist in DuckDB.

Added hint to config:
```
"To calculate duration between dates: use DATE_DIFF('minute', CAST(start_date AS TIMESTAMP), CAST(end_date AS TIMESTAMP)) to get minutes between two date strings."
```

**Next action:** After reboot, test this query:
```
"How much did I sleep in November 2025?"
```

If it still fails, the static_context hint may need refinement, or we may need to consider storing dates as proper TIMESTAMP in the Parquet file.

---

## Debugging Tips

**MCP server logs:**
```
tail -50 ~/Library/Logs/Claude/mcp-server-healthkit.log
```

**Test server manually:**
```
cd /Users/scottbartlow/PycharmProjects/healthkit-mcp-v2
.venv/bin/python server.py
```

**Test Ollama:**
```
ollama run qwen2.5:7b "SELECT 1"
```

**Query Parquet directly:**
```
python -c "import duckdb; print(duckdb.execute(\"SELECT * FROM '/Users/scottbartlow/PycharmProjects/healthkit_export_ripper_one_table/health.parquet' LIMIT 5\").fetchall())"
```

---

## Potential Future Work

1. Tune prompts for edge cases (date arithmetic, complex aggregations)
2. Test retry logic intentionally
3. Try SQLCoder or larger Qwen model for better SQL generation
4. Consider storing dates as TIMESTAMP in Parquet for simpler queries
5. Clean up test files
6. Add README documentation