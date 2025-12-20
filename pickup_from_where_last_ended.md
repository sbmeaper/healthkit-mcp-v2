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
| `query_executor.py` | DuckDB connection, creates `health_data` view, executes SQL |
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

*Ask me for: full config.json, Claude Desktop config, debugging commands, data stats, or environment details*