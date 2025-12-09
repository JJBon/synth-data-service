"""Insights panel - displays table statistics and patterns."""
import streamlit as st
from utils.duckdb_store import DuckDBStore


def render(db: DuckDBStore, table_name: str | None):
    """Render the insights panel."""
    st.subheader("📈 Insights")
    
    if not table_name:
        st.info("Select a table to see insights")
        return
    
    try:
        info = db.get_table_info(table_name)
        df = db.get_table(table_name)
        
        # Basic stats
        st.markdown("**Statistics**")
        st.write(f"- Rows: **{info['row_count']}**")
        st.write(f"- Columns: **{len(info['columns'])}**")
        
        st.divider()
        
        # Column types
        st.markdown("**Columns**")
        for col in info['columns']:
            st.write(f"- `{col['name']}`: {col['type']}")
        
        st.divider()
        
        # Top values for categorical columns
        st.markdown("**Sample Values**")
        for col in df.columns[:3]:  # First 3 columns
            sample = df[col].head(3).tolist()
            st.write(f"**{col}**: {sample}")
        
        st.divider()
        
        # SQL Query
        st.markdown("**Run SQL**")
        query = st.text_area(
            "Query:",
            value=f"SELECT * FROM {table_name} LIMIT 10",
            height=80,
            label_visibility="collapsed"
        )
        if st.button("Execute", use_container_width=True):
            try:
                result = db.run_sql(query)
                st.dataframe(result, use_container_width=True, height=200)
            except Exception as e:
                st.error(f"Query error: {e}")
        
    except Exception as e:
        st.error(f"Error: {e}")
