# healthkit-mcp-v2 — Project Status Summary

**Last Updated:** December 19, 2025  
**Status:** Core functionality complete and working

---

## What This Project Does

An MCP server that lets users ask natural language questions about their Apple HealthKit data via Claude Desktop. Questions are translated to SQL by a local LLM (Ollama + Qwen 2.5 7B), executed against a DuckDB/Parquet database, and results returned with diagnostics.

---

## Project Location

```
/Users/scottbartlow/PycharmProjects/healthkit-mcp-v2/
```

---

## Current Architecture

```
Claude Desktop → MCP Server (Python) → Ollama (Qwen 2.5 7B) → DuckDB (Parquet)
```

---

## Files in the Project

| File | Purpose |
|------|---------|
| `config.json` | All settings: LLM endpoint, Parquet path, retry limit, semantic layer |
| `semantic_layer.py` | Loads config, runs auto-queries at startup, builds LLM context string |
| `llm_client.py` | Calls Ollama API, generates SQL from natural language + context |
| `query_executor.py` | Executes SQL against DuckDB, handles retry logic with LLM correction |
| `server.py` | MCP server entry point, exposes `query_health_data` tool |
| `test_db.py` | One-off test script (can be deleted) |
| `project_specs_for_llm.md` | Original project specification |

---

## Environment Details

- **Python:** 3.13 (virtual environment at `.venv/`)
- **Key packages:** `duckdb`, `requests`, `mcp`
- **Ollama:** Installed via macOS app, model `qwen2.5:7b` downloaded
- **Hardware:** Mac M4, 16GB RAM

---

## Data Details

- **Parquet file:** `/Users/scottbartlow/PycharmProjects/healthkit_export_ripper_one_table/health.parquet`
- **Rows:** 5,631,852
- **Date range:** December 2020 – December 2025
- **Metric types:** 98 distinct types (steps, heart rate, sleep, workouts, nutrition, etc.)
- **Schema:** `type`, `value`, `unit`, `start_date`, `end_date`, `duration_min`, `distance_km`, `energy_kcal`, `source_name`

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

## What's Working

- ✅ Natural language → SQL generation via Qwen 2.5 7B
- ✅ SQL execution against Parquet via DuckDB
- ✅ MCP server connected to Claude Desktop
- ✅ Semantic layer auto-generates context at startup
- ✅ Diagnostics returned (SQL, tokens, retries, errors)
- ✅ Tested successfully: "How many steps did I take in 2024?" → 7,681,979 steps

---

## Key Decisions Made

1. **Qwen 2.5 7B** chosen as starting model (good SQL generation, fits in 16GB RAM)
2. **Config-driven design** — swap models by editing `config.json`, no code changes
3. **Absolute path fix** — `semantic_layer.py` uses `Path(__file__).parent` to find `config.json` because Claude Desktop doesn't set working directory
4. **Prompt tuning** — Added hint: "When asked 'how many' for metrics like steps, use SUM(value) not COUNT(*)"

---

## Known Issues / Gotchas

1. **Working directory:** Claude Desktop runs the server without setting cwd, so all file paths must be absolute or relative to the script location
2. **Restart required:** Changes to `config.json` require Claude Desktop restart (semantic context is built once at startup)
3. **Logs location:** `~/Library/Logs/Claude/mcp-server-healthkit.log` for debugging

---

## Not Yet Tested

- Retry logic (no SQL failures encountered yet to trigger it)
- Edge case queries
- Alternative models (SQLCoder, Qwen 14B)

---

## Potential Future Work

1. More prompt tuning as edge cases are discovered
2. Expand `auto_queries` in config (units per type, sample values)
3. Test retry logic intentionally
4. Try SQLCoder or larger Qwen model
5. Clean up test files and `if __name__` blocks
6. Add README for project documentation

---

## Quick Start When Resuming

1. Ensure Ollama is running (check menu bar icon)
2. Claude Desktop should auto-connect to MCP server
3. If issues, check logs: `tail -50 ~/Library/Logs/Claude/mcp-server-healthkit.log`
4. To test server manually: `cd /Users/scottbartlow/PycharmProjects/healthkit-mcp-v2 && .venv/bin/python server.py`