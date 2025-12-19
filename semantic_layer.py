import json
import duckdb
from pathlib import Path


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        # Get the directory where this script lives
        script_dir = Path(__file__).parent
        config_path = script_dir / "config.json"

    with open(config_path, "r") as f:
        return json.load(f)


def build_semantic_context(config: dict) -> str:
    """Run auto queries and combine with static context to build LLM context."""

    parquet_path = config["database"]["parquet_path"]
    con = duckdb.connect()

    context_parts = []

    # Add static context first
    context_parts.append("=== Data Context ===")
    for hint in config["semantic_layer"]["static_context"]:
        context_parts.append(hint)

    # Run auto queries and add results
    context_parts.append("\n=== Schema Discovery ===")

    for query_template in config["semantic_layer"]["auto_queries"]:
        query = query_template.format(parquet_path=parquet_path)
        try:
            result = con.execute(query).fetchall()
            columns = [desc[0] for desc in con.description]

            context_parts.append(f"\nQuery: {query}")
            context_parts.append(f"Columns: {columns}")
            context_parts.append(f"Results ({len(result)} rows):")

            # Limit output for large result sets
            display_rows = result[:50] if len(result) > 50 else result
            for row in display_rows:
                context_parts.append(f"  {row}")
            if len(result) > 50:
                context_parts.append(f"  ... and {len(result) - 50} more rows")

        except Exception as e:
            context_parts.append(f"\nQuery failed: {query}")
            context_parts.append(f"Error: {e}")

    con.close()
    return "\n".join(context_parts)


if __name__ == "__main__":
    # Test the semantic layer
    config = load_config()
    context = build_semantic_context(config)
    print(context)