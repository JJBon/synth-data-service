"""Sidebar component - displays list of generated tables."""
import streamlit as st
from utils.duckdb_store import DuckDBStore


def render(db: DuckDBStore):
    """Render the sidebar with table list."""
    st.header("📊 Data Designer")
    st.divider()
    
    # List tables
    tables = db.list_tables()
    
    if tables:
        st.subheader("Generated Tables")
        for table in tables:
            if st.button(f"📋 {table}", key=f"table_{table}", use_container_width=True):
                st.session_state.selected_table = table
                st.rerun()
    else:
        st.info("No tables generated yet. Use the chat to create data!")
    
    st.divider()
    
    # Load existing CSV files
    st.subheader("Import Data")
    import os
    output_dir = os.environ.get("DATA_OUTPUT_DIR", "./data-designer-output")
    
    if os.path.exists(output_dir):
        csv_files = [f for f in os.listdir(output_dir) if f.endswith(".csv")]
        
        if csv_files:
            selected_csv = st.selectbox("Import from CSV:", ["Select..."] + csv_files)
            if selected_csv != "Select..." and st.button("Import"):
                csv_path = os.path.join(output_dir, selected_csv)
                table_name = selected_csv.replace(".csv", "")
                db.save_from_csv(table_name, csv_path)
                st.session_state.selected_table = table_name
                st.success(f"Imported {selected_csv}!")
                st.rerun()
