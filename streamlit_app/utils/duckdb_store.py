"""DuckDB store for managing generated datasets."""
import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional


class DuckDBStore:
    """Manage generated datasets in DuckDB."""
    
    def __init__(self, db_path: str = "data_designer.duckdb"):
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
    
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
        df = pd.read_csv(csv_path)
        self.save_dataframe(table_name, df)
    
    def list_tables(self) -> list[str]:
        """List all tables in the database."""
        result = self.conn.execute("SHOW TABLES").fetchall()
        return [row[0] for row in result]
    
    def get_table(self, name: str, limit: int = 100) -> pd.DataFrame:
        """Get a table as DataFrame."""
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        return self.conn.execute(f"SELECT * FROM {safe_name} LIMIT {limit}").df()
    
    def get_table_info(self, name: str) -> dict:
        """Get table statistics."""
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        
        # Row count
        row_count = self.conn.execute(f"SELECT COUNT(*) FROM {safe_name}").fetchone()[0]
        
        # Column info
        columns = self.conn.execute(f"DESCRIBE {safe_name}").fetchall()
        
        return {
            "name": name,
            "row_count": row_count,
            "columns": [{"name": col[0], "type": col[1]} for col in columns]
        }
    
    def run_sql(self, query: str) -> pd.DataFrame:
        """Execute a SQL query and return results."""
        return self.conn.execute(query).df()
    
    def close(self):
        """Close the database connection."""
        self.conn.close()
