"""Sidebar component - Simple database and table view."""
import streamlit as st
from utils.duckdb_store import DuckDBStore


def render(db: DuckDBStore):
    """Render minimal sidebar with current table info."""
    
    # Database name header
    st.subheader("🗃️ data_designer")
    st.divider()
    
    selected = st.session_state.get("selected_table")
    
    if selected:
        st.info(f"**Current Table**\n\n{selected}")
        
        # Show metadata
        info = db.get_table_info(selected)
        rows = info.get('rows', 0)
        cols = len(info.get('columns', []))
        
        st.caption(f"**Rows:** {rows}")
        st.caption(f"**Columns:** {cols}")
        
    else:
        st.caption("No data generated yet.")
