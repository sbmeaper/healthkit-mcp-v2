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


def build_semantic_context(config: dict) -> dict:
    """
    Build semantic context optimized for Qwen2.5-Coder text-to-SQL format.

    Returns a dict with separate components that llm_client can assemble
    into the optimal prompt structure.
    """

    parquet_path = config["database"]["parquet_path"]
    con = duckdb.connect()

    context = {
        "schema_ddl": "",
        "sample_data": "",
        "type_values": [],
        "value_categories": {},
        "date_range": {},
        "hints": []
    }

    # 1. Generate CREATE TABLE DDL (what Qwen2.5-Coder was trained on)
    # Note: The actual table is a view called 'health_data' pointing to the parquet file
    context["schema_ddl"] = """CREATE TABLE health_data (
    type VARCHAR,           -- measurement type (e.g., 'StepCount', 'HeartRate', 'SleepAnalysis', 'WorkoutWalking')
    value DOUBLE,           -- numeric value for quantity types (steps, heart rate bpm, etc.)
    value_category VARCHAR, -- categorical value for category types (sleep stages, stand hours)
    unit VARCHAR,           -- unit of measurement (count, bpm, kcal, km, etc.)
    start_date VARCHAR,     -- timestamp as 'YYYY-MM-DD HH:MM:SS'
    end_date VARCHAR,       -- timestamp as 'YYYY-MM-DD HH:MM:SS'
    duration_min DOUBLE,    -- workout duration in minutes (workouts only)
    distance_km DOUBLE,     -- workout distance in km (workouts only)
    energy_kcal DOUBLE,     -- workout energy in kcal (workouts only)
    source_name VARCHAR     -- device/app that recorded the data
);
-- Query this table as: SELECT ... FROM health_data WHERE ..."""

    # 2. Get sample data rows
    try:
        sample_query = f"""
        SELECT type, value, value_category, unit, start_date, end_date, source_name
        FROM '{parquet_path}'
        WHERE type IN ('StepCount', 'HeartRate', 'SleepAnalysis', 'WorkoutWalking')
        ORDER BY RANDOM()
        LIMIT 8
        """
        rows = con.execute(sample_query).fetchall()
        sample_lines = []
        for row in rows:
            sample_lines.append(f"  {row}")
        context["sample_data"] = "\n".join(sample_lines)
    except Exception as e:
        context["sample_data"] = f"  (sample query failed: {e})"

    # 3. Get distinct type values
    try:
        types_query = f"SELECT DISTINCT type FROM '{parquet_path}' ORDER BY type"
        types = con.execute(types_query).fetchall()
        context["type_values"] = [t[0] for t in types]
    except:
        pass

    # 4. Get value_category mappings (important for sleep, stand hours)
    try:
        cat_query = f"""
        SELECT DISTINCT type, value_category 
        FROM '{parquet_path}' 
        WHERE value_category IS NOT NULL 
        ORDER BY type, value_category
        """
        cats = con.execute(cat_query).fetchall()
        for type_name, cat_value in cats:
            if type_name not in context["value_categories"]:
                context["value_categories"][type_name] = []
            context["value_categories"][type_name].append(cat_value)
    except:
        pass

    # 5. Get date range
    try:
        date_query = f"SELECT MIN(start_date), MAX(start_date) FROM '{parquet_path}'"
        min_date, max_date = con.execute(date_query).fetchone()
        context["date_range"] = {"min": min_date, "max": max_date}
    except:
        pass

    # 6. Add static hints from config
    context["hints"] = config["semantic_layer"].get("static_context", [])

    con.close()
    return context


def format_context_for_prompt(context: dict) -> str:
    """
    Format the semantic context into Qwen2.5-Coder's expected text-to-SQL format.
    """
    parts = []

    # Schema as DDL
    parts.append("/* Table Schema */")
    parts.append(context["schema_ddl"])

    # Sample data
    parts.append("\n/* Sample Data */")
    parts.append(context["sample_data"])

    # Value categories (critical for sleep queries)
    if context["value_categories"]:
        parts.append("\n/* Category Values */")
        for type_name, cats in context["value_categories"].items():
            parts.append(f"-- {type_name}: {', '.join(cats)}")

    # Date range
    if context["date_range"]:
        parts.append(
            f"\n/* Data spans from {context['date_range'].get('min', '?')} to {context['date_range'].get('max', '?')} */")

    # Domain hints
    if context["hints"]:
        parts.append("\n/* Important Notes */")
        for hint in context["hints"]:
            parts.append(f"-- {hint}")

    return "\n".join(parts)


if __name__ == "__main__":
    # Test the semantic layer
    config = load_config()
    context = build_semantic_context(config)
    formatted = format_context_for_prompt(context)
    print(formatted)