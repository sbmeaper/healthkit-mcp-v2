import duckdb
from typing import Optional
from datetime import datetime
from pathlib import Path


def _get_log_path(config: dict) -> str:
    """Expand and return the log database path from config."""
    log_path = config["database"]["log_path"]
    return str(Path(log_path).expanduser())


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
    """Log a single query attempt. Opens and closes connection per call."""
    log_path = _get_log_path(config)

    con = duckdb.connect(log_path)
    try:
        _init_log_table(con)
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
    finally:
        con.close()


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

    # Verify it was logged (transactional read)
    log_path = _get_log_path(config)
    con = duckdb.connect(log_path)
    try:
        result = con.execute("SELECT * FROM query_log ORDER BY timestamp DESC LIMIT 1").fetchall()
        print("Latest log entry:", result)
    finally:
        con.close()