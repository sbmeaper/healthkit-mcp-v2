# healthki-mcp-v2

I want to create a mcp server that uses my Apple healthkit data.  Clients can use it to answer nql about my health data.  For example, how many steps did I walk last month. 


Key requirements for the mcp server project:

Code is python.  Editor is Pycharm.  Repo is GIT.  Database is duckdb.   LLM is running locally.  Everything runs locally on my Mac laptop with M4 and 16GB ram.

It is LLM agnostic.  I can change a simple configuration to swap LLMs.  The configuration would have API keys and any other values the mcp server python code needs to use that LLM.  

The mcp server will accumulate input and output token counts and retries.  It will return these diagnostic metrics in addition to the question answer.

The mcp server configuration will include a value for database select retries.

The mcp server input is the user’s nql about health.   The server will send the nql and the database table and column names to the llm.   The llm will return sql.  The mcp server will run the sql select against the duckdb database.   If the first select statement returns an error, the mcp server will send the error to the llm and receive a revised select statement.  It will attempt retries capped by the configuration file value for retries.
