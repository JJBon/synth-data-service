"""
Data Designer - Tonic Fabricate-style UI
Left sidebar: Database/Tables | Center: Data Grid | Right sidebar: Chat
"""
import streamlit as st
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.duckdb_store import DuckDBStore
from components import sidebar, data_grid, chat

# Page config - wide layout
st.set_page_config(
    page_title="Data Designer",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Tonic-like dark theme
st.markdown("""
<style>
    /* Dark theme */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Left sidebar - narrow width */
    [data-testid="stSidebar"] {
        background-color: #1a1a2e;
        min-width: 200px;
        max-width: 200px;
    }
    
    /* Hide default sidebar toggle */
    [data-testid="stSidebarNav"] {
        display: none;
    }
    
    /* Table styling */
    .stDataFrame {
        border-radius: 4px;
    }
    
    /* Compact buttons */
    .stButton > button {
        padding: 0.25rem 0.5rem;
        font-size: 0.85rem;
    }
    
    /* Right chat panel styling */
    .chat-panel {
        background-color: #1a1a2e;
        border-radius: 8px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize DuckDB
@st.cache_resource
def get_db():
    db_path = os.environ.get("DUCKDB_PATH", ":memory:")
    return DuckDBStore(db_path)

db = get_db()

# Auto-import watcher: Monitors shared volume for new CSVs and imports them
@st.fragment(run_every=3)
def file_watcher():
    # Polls shared folder OR S3 for new CSV files and imports into DuckDB
    import time
    try:
        s3_bucket = os.environ.get("S3_ARTIFACTS_BUCKET")
        latest_file_path = None
        mtime = 0.0
        filename_stem = ""

        if s3_bucket:
             import boto3
             s3 = boto3.client("s3")
             response = s3.list_objects_v2(Bucket=s3_bucket, Prefix="data/")
             if 'Contents' in response:
                 latest_obj = max(response['Contents'], key=lambda x: x['LastModified'])
                 mtime = latest_obj['LastModified'].timestamp()
                 latest_file_path = f"s3://{s3_bucket}/{latest_obj['Key']}"
                 filename_stem = os.path.splitext(os.path.basename(latest_obj['Key']))[0]
        else:
             data_dir = os.environ.get("DATA_OUTPUT_DIR", "/data-designer-output")
             files = list(Path(data_dir).glob("*.csv"))
             if files:
                 latest_obj = max(files, key=lambda f: f.stat().st_mtime)
                 mtime = latest_obj.stat().st_mtime
                 latest_file_path = str(latest_obj)
                 filename_stem = latest_obj.stem

        if not latest_file_path:
            return
            
        # Check against session state
        if "last_import_mtime" not in st.session_state:
            st.session_state.last_import_mtime = 0.0

        # If new file detected (allow small buffer)
        if mtime > st.session_state.last_import_mtime:
            # Import it!
            table_name = filename_stem.replace("-", "_")
            
            current_db = get_db()
            current_db.clear_database() # Clean slate
            current_db.save_from_csv(table_name, latest_file_path)
            
            st.session_state.last_import_mtime = mtime
            st.session_state.selected_table = table_name
            st.rerun()
            
    except Exception as e:
        print(f"Watcher error: {e}")
# Run the watcher in the background
file_watcher()

# Initialize session state
if "selected_table" not in st.session_state:
    tables = db.list_tables()
    st.session_state.selected_table = tables[0] if tables else None

# ===========================================
# LEFT SIDEBAR - Database & Tables
# ===========================================
with st.sidebar:
    sidebar.render(db)

# ===========================================
# MAIN AREA - Split: Data Grid (left) | Chat (right)
# ===========================================
col_data, col_chat = st.columns([3, 1])

# CENTER - Data Grid
with col_data:
    # Table header with controls
    selected = st.session_state.get("selected_table")
    if selected:
        # Header row with table name and export buttons
        hcol1, hcol2, hcol3, hcol4 = st.columns([3, 1, 1, 1])
        with hcol1:
            st.markdown(f"### 📋 {selected}")
        with hcol2:
            if st.button("🔄 Refresh"):
                st.rerun()
        with hcol3:
            # CSV download
            try:
                df = db.get_table(selected, limit=10000)
                csv = df.to_csv(index=False)
                st.download_button("📥 CSV", csv, f"{selected}.csv", "text/csv")
            except:
                pass
        with hcol4:
            # Parquet download
            try:
                import io
                df = db.get_table(selected, limit=10000)
                buffer = io.BytesIO()
                df.to_parquet(buffer, index=False)
                st.download_button("📥 Parquet", buffer.getvalue(), f"{selected}.parquet")
            except:
                pass
        
        st.divider()
        
        # Data table
        data_grid.render(db, selected)
    else:
        st.info("No table selected. Generate data using the chat on the right →")

# RIGHT SIDEBAR - Chat
with col_chat:
    st.markdown("### 💬 Chat")
    st.divider()
    
    def on_job_complete(job_id, csv_path):
        """Callback when job completes - import to DuckDB."""
        table_name = job_id.replace("-", "_")
        db.save_from_csv(table_name, csv_path)
        st.session_state.selected_table = table_name
    
    chat.render(on_job_complete=on_job_complete)
