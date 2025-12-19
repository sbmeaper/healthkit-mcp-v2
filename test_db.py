import duckdb

parquet_path = "/Users/scottbartlow/PycharmProjects/healthkit_export_ripper_one_table/health.parquet"

con = duckdb.connect()
result = con.execute(f"SELECT COUNT(*) FROM '{parquet_path}'").fetchone()
print(f"Total rows: {result[0]}")

# Check the schema
schema = con.execute(f"DESCRIBE SELECT * FROM '{parquet_path}'").fetchall()
print("\nColumns:")
for col in schema:
    print(f"  {col[0]}: {col[1]}")