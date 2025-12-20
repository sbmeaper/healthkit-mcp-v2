import duckdb
import uuid
import time
from typing import Optional
from query_logger import log_attempt

# Persistent connection - created once, reused for all queries
_connection: Optional[duckdb.DuckDBPyConnection] = None


def get_connection(config: dict) -> duckdb.DuckDBPyConnection:
    """Get or create a persistent DuckDB connection with health_data view."""
    global _connection

    if _connection is None:
        parquet_path = config["database"]["parquet_path"]
        _connection = duckdb.connect()

        # Create a view so LLM can reference 'health_data' instead of full path
        _connection.execute(f"""
            CREATE OR REPLACE VIEW health_data AS 
            SELECT * FROM '{parquet_path}'
        """)

    return _connection


def execute_query(sql: str, config: dict) -> dict:
    """Execute SQL against the health_data view and return results with metadata."""

    con = get_connection(config)

    start_time = time.perf_counter()
    try:
        result = con.execute(sql).fetchall()
        columns = [desc[0] for desc in con.description]
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)

        return {
            "success": True,
            "columns": columns,
            "rows": result,
            "row_count": len(result),
            "error": None,
            "execution_time_ms": execution_time_ms
        }
    except Exception as e:
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "success": False,
            "columns": None,
            "rows": None,
            "row_count": 0,
            "error": str(e),
            "execution_time_ms": execution_time_ms
        }
    # Note: no finally/close - we keep the connection alive


def execute_with_retry(
        question: str,
        semantic_context: str,
        config: dict,
        generate_sql_fn,
        client_name: str = "unknown"
) -> dict:
    """Execute a query with LLM-assisted retry on failure."""

    request_id = str(uuid.uuid4())
    max_retries = config["database"]["max_retries"]
    errors = []
    total_input_tokens = 0
    total_output_tokens = 0

    # Generate initial SQL
    llm_result = generate_sql_fn(question, semantic_context, config)
    sql = llm_result["sql"]
    total_input_tokens += llm_result["input_tokens"]
    total_output_tokens += llm_result["output_tokens"]

    for attempt in range(max_retries + 1):
        query_result = execute_query(sql, config)

        # Log this attempt
        log_attempt(
            config=config,
            request_id=request_id,
            attempt_number=attempt + 1,
            client=client_name,
            nlq=question,
            sql=sql,
            success=query_result["success"],
            error_message=query_result["error"],
            row_count=query_result["row_count"] if query_result["success"] else None,
            execution_time_ms=query_result["execution_time_ms"]
        )

        if query_result["success"]:
            return {
                "success": True,
                "columns": query_result["columns"],
                "rows": query_result["rows"],
                "row_count": query_result["row_count"],
                "sql": sql,
                "retry_count": attempt,
                "errors": errors,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens
            }

        # Query failed
        errors.append({"sql": sql, "error": query_result["error"]})

        if attempt < max_retries:
            # Ask LLM to fix the SQL
            llm_result = generate_sql_fn(
                f"{question}\n\nPrevious SQL failed with error: {query_result['error']}\nFailed SQL: {sql}\nPlease fix the SQL.",
                semantic_context,
                config
            )
            sql = llm_result["sql"]
            total_input_tokens += llm_result["input_tokens"]
            total_output_tokens += llm_result["output_tokens"]

    # All retries exhausted
    return {
        "success": False,
        "columns": None,
        "rows": None,
        "row_count": 0,
        "sql": sql,
        "retry_count": max_retries,
        "errors": errors,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens
    }


if __name__ == "__main__":
    from semantic_layer import load_config, build_semantic_context, format_context_for_prompt
    from llm_client import generate_sql

    config = load_config()
    context = build_semantic_context(config)
    formatted_context = format_context_for_prompt(context)

    # Test with a simple question
    question = "How many rows are in the table?"
    print(f"Question: {question}\n")

    result = execute_with_retry(question, formatted_context, config, generate_sql, client_name="test_harness")

    if result["success"]:
        print(f"Columns: {result['columns']}")
        print(f"Rows: {result['rows']}")
        print(f"SQL: {result['sql']}")
        print(f"Retries: {result['retry_count']}")
    else:
        print(f"Query failed after {result['retry_count']} retries")
        print(f"Errors: {result['errors']}")