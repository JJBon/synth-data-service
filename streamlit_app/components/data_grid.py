"""Data grid component - displays table data."""
import streamlit as st
from utils.duckdb_store import DuckDBStore


def render(db: DuckDBStore, table_name: str | None):
    """Render the main data grid."""
    if not table_name:
        st.info("👈 Select a table from the sidebar or generate new data below.")
        return
    
    st.subheader(f"📋 {table_name}")
    
    try:
        df = db.get_table(table_name)
        
        # Table toolbar
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        
        with col1:
            st.metric("Rows", len(df))
        with col2:
            st.metric("Columns", len(df.columns))
        with col3:
            # Refresh button
            if st.button("🔄 Refresh"):
                st.rerun()
        with col4:
            # Export buttons
            col_csv, col_parquet = st.columns(2)
            with col_csv:
                csv_data = df.to_csv(index=False)
                st.download_button(
                    "📥 CSV",
                    csv_data,
                    f"{table_name}.csv",
                    "text/csv",
                    use_container_width=True
                )
            with col_parquet:
                import io
                buffer = io.BytesIO()
                df.to_parquet(buffer, index=False)
                st.download_button(
                    "📥 Parquet",
                    buffer.getvalue(),
                    f"{table_name}.parquet",
                    "application/octet-stream",
                    use_container_width=True
                )
        
        st.divider()
        
        # Data table
        st.dataframe(
            df,
            use_container_width=True,
            height=400
        )
        
    except Exception as e:
        st.error(f"Error loading table: {e}")
