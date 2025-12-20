import duckdb
from typing import Optional
from datetime import datetime
from pathlib import Path

# Persistent connection for logging - separate from health data
_log_connection: Optional[duckdb.DuckDBPyConnection] = None


def get_log_connection(config: dict) -> duckdb.DuckDBPyConnection:
    """Get or create a persistent DuckDB connection for query logs."""
    global _log_connection

    if _log_connection is None:
        log_path = config["database"]["log_path"]
        # Expand ~ to home directory
        log_path = str(Path(log_path).expanduser())

        _log_connection = duckdb.connect(log_path)
        _init_log_table(_log_connection)

    return _log_connection


def _init_log_table(con: duckdb.DuckDBPyConnection) -> None:
    """Create the query_log table if it doesn't exist."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS query_log (
            request_id VARCHAR,
            attempt_number INTEGER,
            timestamp TIMESTAMP,
            client VARCHAR,
            nlq VARCHAR,
            sql VARCHAR,
            success BOOLEAN,
            error_message VARCHAR,
            row_count INTEGER,
            execution_time_ms INTEGER
        )
    """)


def log_attempt(
        config: dict,
        request_id: str,
        attempt_number: int,
        client: str,
        nlq: str,
        sql: str,
        success: bool,
        error_message: Optional[str],
        row_count: Optional[int],
        execution_time_ms: int
) -> None:
    """Log a single query attempt."""
    con = get_log_connection(config)

    con.execute("""
        INSERT INTO query_log (
            request_id, attempt_number, timestamp, client, nlq, sql,
            success, error_message, row_count, execution_time_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        request_id,
        attempt_number,
        datetime.now(),
        client,
        nlq,
        sql,
        success,
        error_message,
        row_count,
        execution_time_ms
    ])


if __name__ == "__main__":
    # Quick test
    from semantic_layer import load_config
    import uuid

    config = load_config()

    # Log a test entry
    log_attempt(
        config=config,
        request_id=str(uuid.uuid4()),
        attempt_number=1,
        client="test",
        nlq="How many steps today?",
        sql="SELECT SUM(value) FROM health_data WHERE type='StepCount'",
        success=True,
        error_message=None,
        row_count=1,
        execution_time_ms=42
    )

    # Verify it was logged
    con = get_log_connection(config)
    result = con.execute("SELECT * FROM query_log ORDER BY timestamp DESC LIMIT 1").fetchall()
    print("Latest log entry:", result)