"""
Data Designer - Tonic Fabricate-style UI
A Streamlit app for generating and viewing synthetic data.
"""
import streamlit as st
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.duckdb_store import DuckDBStore
from components import sidebar, data_grid, insights, chat


# Page config
st.set_page_config(
    page_title="Data Designer",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Tonic-like styling
st.markdown("""
<style>
    /* Dark theme adjustments */
    .stApp {
        background-color: #1a1a2e;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #16213e;
    }
    
    /* Better table styling */
    .stDataFrame {
        border-radius: 8px;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 4px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Initialize DuckDB
@st.cache_resource
def get_db():
    db_path = os.environ.get("DUCKDB_PATH", "data_designer.duckdb")
    return DuckDBStore(db_path)

db = get_db()

# Auto-import existing CSV files on first load
if "auto_imported" not in st.session_state:
    output_dir = os.environ.get("DATA_OUTPUT_DIR", "./data-designer-output")
    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            if f.endswith(".csv"):
                try:
                    table_name = f.replace(".csv", "").replace("-", "_")
                    db.save_from_csv(table_name, os.path.join(output_dir, f))
                except Exception as e:
                    pass  # Skip files that can't be imported
    st.session_state.auto_imported = True

# Initialize session state
if "selected_table" not in st.session_state:
    tables = db.list_tables()
    st.session_state.selected_table = tables[0] if tables else None

# Layout
with st.sidebar:
    sidebar.render(db)

# Main content area
col_main, col_insights = st.columns([3, 1])

with col_main:
    data_grid.render(db, st.session_state.get("selected_table"))
    
    # Chat at bottom
    def on_job_complete(job_id, csv_path):
        """Callback when job completes - import to DuckDB."""
        table_name = job_id.replace("-", "_")
        db.save_from_csv(table_name, csv_path)
        st.session_state.selected_table = table_name
    
    chat.render(on_job_complete=on_job_complete)

with col_insights:
    insights.render(db, st.session_state.get("selected_table"))
