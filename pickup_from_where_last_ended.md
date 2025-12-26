# healthkit-mcp-v2 — Quick Reference

**Status:** Stable, semantic layer optimized (Dec 2025)

## Architecture

Claude Desktop → MCP Server (Python) → Ollama (qwen2.5-coder:7b) → DuckDB (Parquet)

## Locations

| What | Path |
|------|------|
| MCP Server | `~/PycharmProjects/healthkit-mcp-v2/` |
| Parquet File | `~/PycharmProjects/healthkit_export_ripper_one_table/health.parquet` |
| Query Logs | `~/PycharmProjects/healthkit-mcp-v2/query_logs.duckdb` |

## Core Files

| File | Purpose |
|------|---------|
| `config.json` | LLM config, parquet path, semantic layer hints |
| `semantic_layer.py` | Builds context from auto-queries + static hints |
| `llm_client.py` | Sends prompt to Ollama, parses SQL response |
| `query_executor.py` | DuckDB connection, retry logic, logging |
| `server.py` | MCP server entry point |

## Schema (health.parquet)

| Column | Type | Notes |
|--------|------|-------|
| type | VARCHAR | e.g., "StepCount", "SleepAnalysis", "WorkoutWalking" |
| value | DOUBLE | numeric measurements |
| value_category | VARCHAR | categorical (sleep stages, stand hours) |
| start_date, end_date | VARCHAR | "YYYY-MM-DD HH:MM:SS" |
| duration_min, distance_km, energy_kcal | DOUBLE | workouts only |
| start_lat, start_lon | DOUBLE | GPS for outdoor workouts |

## Semantic Layer Design Principles

1. **Pattern-based hints over exhaustive mappings** — e.g., "Dietary* prefix" covers 30+ types
2. **Disambiguate only where ambiguous** — calories needed explicit mapping (consumed vs burned vs basal)
3. **Include SQL patterns for complex aggregations** — daily average pattern: SUM by day, then AVG
4. **DuckDB-specific syntax** — DATE_DIFF, DATE_TRUNC, no julianday/strftime

## Key Semantic Layer Sections

- **Type patterns**: Dietary*, Workout*, Distance*, Apple* prefixes
- **Calorie disambiguation**: consumed→DietaryEnergyConsumed, burned→ActiveEnergyBurned, basal→BasalEnergyBurned
- **Aggregation rules**: Cumulative (SUM) vs point-in-time (AVG) metrics
- **Daily average pattern**: `SELECT AVG(daily_total) FROM (SELECT SUM(value) ... GROUP BY DATE_TRUNC('day', ...))`
- **Sleep handling**: type='SleepAnalysis' uses value_category, not value; duration via DATE_DIFF

## Critical Gotchas

- **Sleep queries**: Use `value_category` (AsleepCore, AsleepDeep, AsleepREM), not `value`
- **Daily averages**: Must SUM by day first, then AVG across days
- **DuckDB syntax**: Use DATE_DIFF, not julianday(); use >= and < for date ranges, not BETWEEN
- **GPS queries**: Calling LLM (Claude) provides lat/lon bounding boxes, Qwen just filters on coordinates
- **Restart required**: Config changes need Claude Desktop restart

## Query Log Analysis

```bash
cd ~/PycharmProjects/healthkit-mcp-v2
source .venv/bin/activate
python -c "import duckdb; con = duckdb.connect('query_logs.duckdb'); print(con.execute('SELECT * FROM query_log ORDER BY timestamp DESC LIMIT 10').fetchall())"
```

## Sister Project

**log-analyzer-mcp** — Analyzes query logs using Claude Opus 4.5 API for failure patterns and semantic correctness review. Located at `~/PycharmProjects/log-analyzer-mcp/`