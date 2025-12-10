"""DuckDB store for managing generated datasets."""
import os
import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional


class DuckDBStore:
    """Manage generated datasets in DuckDB."""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        
        # Configure S3 if credentials present
        if os.environ.get("AWS_ACCESS_KEY_ID"):
            try:
                self.conn.sql("INSTALL httpfs; LOAD httpfs;")
                key = os.environ.get("AWS_ACCESS_KEY_ID")
                secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
                region = os.environ.get("AWS_REGION", "us-east-1")
                token = os.environ.get("AWS_SESSION_TOKEN", "")
                
                secret_sql = f"CREATE SECRET (TYPE S3, KEY_ID '{key}', SECRET '{secret}', REGION '{region}'"
                if token:
                    secret_sql += f", SESSION_TOKEN '{token}'"
                secret_sql += ");"
                
                self.conn.sql(secret_sql)
            except Exception as e:
                print(f"Warning: S3 setup failed: {e}")
    
    def save_dataframe(self, table_name: str, df: pd.DataFrame) -> None:
        """Save a DataFrame as a table in DuckDB."""
        # Sanitize table name
        safe_name = table_name.lower().replace(" ", "_").replace("-", "_")
        self.conn.execute(f"DROP TABLE IF EXISTS {safe_name}")
        self.conn.register("temp_df", df)
        self.conn.execute(f"CREATE TABLE {safe_name} AS SELECT * FROM temp_df")
        self.conn.unregister("temp_df")
    
    def save_from_csv(self, table_name: str, csv_path: str) -> None:
        """Load a CSV file and save as a table."""
        print(f"DEBUG: Reading CSV from {csv_path}", flush=True)
        try:
             df = pd.read_csv(csv_path)
             print(f"DEBUG: Read {len(df)} rows", flush=True)
             self.save_dataframe(table_name, df)
             print(f"DEBUG: Saved dataframe to {table_name}", flush=True)
        except Exception as e:
             print(f"DEBUG: Error reading/saving CSV: {e}", flush=True)
             raise e
    
    def list_tables(self) -> list[str]:
        """List all tables in the database."""
        try:
            tables = self.conn.execute("SHOW TABLES").fetchall()
            return [t[0] for t in tables]
        except:
            return []

    def get_table(self, table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Get table as DataFrame."""
        try:
            query = f"SELECT * FROM {table_name}"
            if limit:
                query += f" LIMIT {limit}"
            return self.conn.execute(query).fetchdf()
        except:
            return pd.DataFrame()

    def get_table_info(self, table_name: str) -> dict:
        """Get table schema and row count."""
        try:
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            schema = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
            columns = [{"name": s[0], "type": s[1]} for s in schema]
            return {"rows": count, "columns": columns}
        except:
            return {"rows": 0, "columns": []}

    def clear_database(self):
        """Drop all tables in the database."""
        try:
            tables = self.conn.execute("SHOW TABLES").fetchall()
            for (t,) in tables:
                self.conn.execute(f"DROP TABLE IF EXISTS {t}")
        except:
            pass
    
    def run_sql(self, query: str) -> pd.DataFrame:
        """Execute a SQL query and return results."""
        return self.conn.execute(query).df()
    
    def close(self):
        """Close the database connection."""
        self.conn.close()
