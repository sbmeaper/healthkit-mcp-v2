import requests
from typing import Optional


def call_llm(prompt: str, config: dict) -> dict:
    """Send a prompt to the LLM and return the response with diagnostics."""

    endpoint = config["llm"]["endpoint"]
    model = config["llm"]["model"]

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(endpoint, json=payload)
    response.raise_for_status()

    result = response.json()

    return {
        "text": result.get("response", ""),
        "input_tokens": result.get("prompt_eval_count", 0),
        "output_tokens": result.get("eval_count", 0)
    }


def generate_sql(question: str, semantic_context: str, config: dict) -> dict:
    """
    Generate SQL from a natural language question.

    Uses prompt format aligned with Qwen2.5-Coder's text-to-SQL training:
    1. Schema as CREATE TABLE DDL
    2. Sample data rows
    3. Additional knowledge/hints
    4. Natural language question
    """

    # Qwen2.5-Coder optimized prompt structure
    prompt = f"""Generate a DuckDB SQL query to answer the question based on the schema and data below.

{semantic_context}

/* Query Rules */
-- Return ONLY a valid DuckDB SQL SELECT statement
-- The table is named: health_data
-- Use single quotes for strings; escape apostrophes by doubling: 'Scott''s Watch'
-- For date filtering, cast strings to TIMESTAMP: CAST(start_date AS TIMESTAMP)
-- For date arithmetic, use DATE_DIFF: DATE_DIFF('minute', CAST(start_date AS TIMESTAMP), CAST(end_date AS TIMESTAMP))

Question: {question}

SELECT"""

    result = call_llm(prompt, config)

    # Extract SQL from response
    sql_text = result["text"].strip()

    # Clean markdown formatting FIRST (before prepending SELECT)
    if "```" in sql_text:
        lines = sql_text.split("\n")
        clean_lines = []
        in_code_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            clean_lines.append(line)
        sql_text = "\n".join(clean_lines).strip()

    # The prompt ends with "SELECT" so model should continue from there
    # But sometimes model includes SELECT anyway - check before prepending
    if sql_text.upper().startswith("SELECT"):
        sql = sql_text
    else:
        sql = "SELECT " + sql_text

    # Remove any trailing explanation the model might add
    # Look for common patterns that indicate end of SQL
    for terminator in ["\n\nThis query", "\n\nExplanation", "\n\nNote:", "\n\n--"]:
        if terminator in sql:
            sql = sql.split(terminator)[0]

    sql = sql.strip()

    # Remove trailing semicolon issues (multiple semicolons)
    while sql.endswith(";;"):
        sql = sql[:-1]

    return {
        "sql": sql,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"]
    }


if __name__ == "__main__":
    from semantic_layer import load_config, build_semantic_context, format_context_for_prompt

    config = load_config()
    context = build_semantic_context(config)
    formatted_context = format_context_for_prompt(context)

    # Test with a simple question
    question = "How many steps did I take in 2024?"
    print(f"Question: {question}\n")

    result = generate_sql(question, formatted_context, config)
    print(f"Generated SQL:\n{result['sql']}\n")
    print(f"Input tokens: {result['input_tokens']}")
    print(f"Output tokens: {result['output_tokens']}")