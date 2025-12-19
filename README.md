# healthki-mcp-v2

I want to create a mcp server that uses my Apple healthkit data.  Clients can use it to answer nql about my health data.  For example, how many steps did I walk last month.  Or, what what day of the week do i get the most sleep on average last month.


Key requirements for the mcp server project:

Code is python.  Editor is Pycharm.  Repo is GIT.  Database is duckdb on top of a parquet file.   LLM is running locally.  Everything runs locally on my Mac laptop with M4 and 16GB ram.

the mcp server will use a json configuration file.  the config file will reside in the pycharm project folder (and in the git repo).

It is LLM agnostic.  I can change a configuration value to swap LLMs.  The configuration would have API keys and any other values the mcp server python code needs to use that LLM.  

The mcp server will accumulate input and output token counts and retries.  It will return these diagnostic metrics in addition to the question answer.

The mcp server configuration will include a value for database select retries.

The mcp server will send the nql and the database semantic detail to the llm.   The llm will return sql.  The mcp server will run the sql select against the duckdb database.   If the first select statement returns an error, the mcp server will send the error to the llm and receive a revised select statement.  It will attempt retries capped by the configuration file value for retries.

At startup the mcp server will run a series of queries to create a semantic layer in memory.  the semantic memory layer will only be run at startup, and subsequently used for every mcp server call.  if the underlying data table changes, the mcp server must be restarted to reload the semantic layer.
