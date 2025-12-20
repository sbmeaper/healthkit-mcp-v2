# healthkit-mcp-v2 — Project Status Summary

**Last Updated:** December 19, 2025  
**Status:** Major refactoring complete, awaiting testing with new model

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

## Recent Session: What We Did (Dec 19, 2025)

We identified 4 improvements based on research into Qwen2.5-Coder best practices and implemented all of them:

### Issue #1: Wrong Model Variant
- **Problem:** Was using `qwen2.5:7b` (general model)
- **Solution:** Switch to `qwen2.5-coder:7b` (code-specialized, trained on 5.5T tokens including SQL)
- **Status:** Model was downloading (~30 min). Config updated to use it.
- **Action needed:** Verify `ollama list` shows `qwen2.5-coder:7b` is available

### Issue #2: Prompt Template Structure
- **Problem:** Generic prompt format didn't match Qwen2.5-Coder's training format
- **Solution:** Restructured prompt to match their text-to-SQL training:
  1. Schema as CREATE TABLE DDL
  2. Sample data rows
  3. Additional knowledge/hints as SQL comments
  4. Natural language question
  5. Prompt ends with `SELECT` to prime continuation
- **Status:** ✅ Complete — `semantic_layer.py` and `llm_client.py` rewritten

### Issue #3: DuckDB-Specific Hints
- **Problem:** Model was generating SQLite syntax (julianday, strftime) instead of DuckDB
- **Solution:** Added explicit DuckDB dialect hints with concrete examples:
  - `DATE_DIFF('minute', CAST(start_date AS TIMESTAMP), CAST(end_date AS TIMESTAMP))`
  - Explicit "DO NOT use julianday()" warnings
  - Complete working sleep query example
- **Status:** ✅ Complete — `config.json` rewritten with detailed hints

### Issue #4: Cleaner Table Reference
- **Problem:** LLM prompt included 83-character parquet path (visual noise)
- **Solution:** 
  - Created persistent DuckDB connection at server startup
  - Register `health_data` view pointing to parquet file
  - LLM now generates `SELECT ... FROM health_data` (cleaner, fewer tokens)
- **Status:** ✅ Complete — `query_executor.py` rewritten

---

## Files Modified

All 4 core Python files were rewritten. Copy these from Claude's output to replace existing files:

| File | Changes |
|------|---------|
| `config.json` | New model (`qwen2.5-coder:7b`), detailed DuckDB hints with examples |
| `semantic_layer.py` | Returns structured dict, formats as DDL + samples + hints |
| `llm_client.py` | Qwen-optimized prompt ending with `SELECT`, uses `health_data` table |
| `query_executor.py` | Persistent connection, creates `health_data` view at startup |
| `server.py` | Minor change to call `format_context_for_prompt()` |

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

## Next Steps When Resuming

1. **Verify model downloaded:**
   ```bash
   ollama list
   ```
   Should show `qwen2.5-coder:7b`

2. **Copy all updated files to project** (if not already done)

3. **Restart Claude Desktop** (to reload MCP server)

4. **Test the sleep query that was failing:**
   ```
   "How much did I sleep in November 2025?"
   ```
   Expected: Should now use `DATE_DIFF` and return actual hours

5. **Test a few other queries to verify nothing broke:**
   - "How many steps did I take in 2024?" (should still work)
   - "What was my average heart rate last week?"
   - "How many walking workouts did I do in 2025?"

6. **If sleep query still fails:** Check the generated SQL in diagnostics. The hints may need further refinement, or we may need to add few-shot examples directly in the prompt.

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

---

## Potential Future Work

1. **If current changes don't fix sleep queries:** Add few-shot examples directly in prompt (show input question → output SQL pairs)
2. **Try larger model:** `qwen2.5-coder:14b` or `qwen2.5-coder:32b` if 7B still struggles
3. **Fine-tune on DuckDB:** There's a `motherduckdb/duckdb-text2sql-25k` dataset for DuckDB-specific training
4. **Consider SQLCoder:** Alternative model specifically fine-tuned for SQL generation

---

## Research Findings (from this session)

**Qwen2.5-Coder Technical Report key points:**
- Trained on 5.5 trillion tokens including extensive SQL data
- Text-to-SQL prompt format: DDL schema → sample rows → hints → question
- Outperforms larger models on Spider/BIRD SQL benchmarks
- The `-coder` variant significantly better than base `qwen2.5` for SQL tasks

**DuckDB vs SQLite differences that matter:**
- Date functions: `DATE_DIFF()` not `julianday()`
- Timestamp casting: `CAST(x AS TIMESTAMP)` 
- No `strftime()` — use `YEAR()`, `MONTH()`, etc.

---

## Environment Details

**MCP Server (.venv):**
- Python 3.13
- Packages: `duckdb`, `requests`, `mcp`

**Ollama:**
- Installed via macOS app (runs in menu bar)
- Model: `qwen2.5-coder:7b` (after download completes)

**Hardware:**
- M4 MacBook