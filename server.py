from mcp.server.fastmcp import FastMCP
from semantic_layer import load_config, build_semantic_context
from query_executor import execute_with_retry
from llm_client import generate_sql

# Initialize MCP server
mcp = FastMCP("healthkit")

# Load config and build semantic context at startup
config = load_config()
semantic_context = build_semantic_context(config)


@mcp.tool()
def query_health_data(question: str) -> dict:
    """
    Query Apple HealthKit data using natural language.

    Args:
        question: A natural language question about your health data

    Returns:
        Query results with columns, rows, SQL used, and diagnostic metrics
    """
    result = execute_with_retry(question, semantic_context, config, generate_sql)

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