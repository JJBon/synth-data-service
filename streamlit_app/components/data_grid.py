"""Data grid component - displays table data."""
import streamlit as st
from utils.duckdb_store import DuckDBStore


def render(db: DuckDBStore, table_name: str | None):
    """Render the data table."""
    if not table_name:
        return
    
    try:
        df = db.get_table(table_name, limit=1000)
        
        # Row/column count
        st.caption(f"{len(df)} rows × {len(df.columns)} columns")
        
        # Data table - full width, scrollable
        st.dataframe(
            df,
            use_container_width=True,
            height=500
        )
        
    except Exception as e:
        st.error(f"Error loading table: {e}")
