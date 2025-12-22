from mcp.server.fastmcp import FastMCP, Context
from semantic_layer import load_config, build_semantic_context, format_context_for_prompt
from query_executor import execute_with_retry
from llm_client import generate_sql

# Initialize MCP server
mcp = FastMCP("healthkit")

# Load config and build semantic context at startup
config = load_config()
semantic_context_data = build_semantic_context(config)
semantic_context = format_context_for_prompt(semantic_context_data)


@mcp.tool()
def query_health_data(question: str, ctx: Context) -> dict:
    """
    Query Apple HealthKit data using natural language.

    Args:
        question: A natural language question about your health data

    Returns:
        Query results with columns, rows, SQL used, and diagnostic metrics

    Data includes steps, sleep, heart rate, workouts, and other health metrics.
    Filterable by type, date range, source, and GPS coordinates (lat/lon).

    For geographic locations (cities, states, regions), include approximate lat/lon bounding box in your question (e.g., "workouts where start_lat between 42.2 and 42.5 and start_lon between -71.2 and -70.9").
    """
    # Extract client name from MCP context
    try:
        client_name = ctx.session.client_params.clientInfo.name
    except (AttributeError, TypeError):
        client_name = "unknown"

    result = execute_with_retry(question, semantic_context, config, generate_sql, client_name=client_name)

    return {
        "success": result["success"],
        "columns": result["columns"],
        "rows": result["rows"][:100] if result["rows"] else None,  # Limit rows returned
        "row_count": result["row_count"],
        "diagnostics": {
            "sql": result["sql"],
            "retry_count": result["retry_count"],
            "errors": result["errors"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"]
        }
    }


if __name__ == "__main__":
    mcp.run()