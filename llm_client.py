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
    """Generate SQL from a natural language question."""

    prompt = f"""You are a SQL expert. Given the following data context and a user question, generate a DuckDB SQL SELECT statement to answer the question.

{semantic_context}

Important rules:
- Return ONLY the SQL statement, no explanations
- The table is a Parquet file, reference it as: '{config["database"]["parquet_path"]}'
- Use single quotes for string literals
- The 'type' column contains values like 'StepCount', 'HeartRate', etc. (without the HKQuantityTypeIdentifier prefix)

User question: {question}

SQL:"""

    result = call_llm(prompt, config)

    # Extract SQL from response (strip whitespace and any markdown formatting)
    sql = result["text"].strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1] if "\n" in sql else sql[3:]
    if sql.endswith("```"):
        sql = sql.rsplit("```", 1)[0]
    sql = sql.strip()

    return {
        "sql": sql,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"]
    }


if __name__ == "__main__":
    from semantic_layer import load_config, build_semantic_context

    config = load_config()
    context = build_semantic_context(config)

    # Test with a simple question
    question = "How many steps did I take in 2024?"
    print(f"Question: {question}\n")

    result = generate_sql(question, context, config)
    print(f"Generated SQL:\n{result['sql']}\n")
    print(f"Input tokens: {result['input_tokens']}")
    print(f"Output tokens: {result['output_tokens']}")
