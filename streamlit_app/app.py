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

# Initialize DuckDB - SESSION SCOPED
def get_db():
    db_path = ":memory:" # Always memory for session isolation
    return DuckDBStore(db_path)

if "db" not in st.session_state:
    st.session_state.db = get_db()

db = st.session_state.db

# Auto-import watcher: Monitors shared volume for new CSVs and imports them
# File Watcher (Poll S3 for new files)
# Polling interval to check for new files (in seconds)
POLL_INTERVAL = 2

@st.fragment
def file_watcher():
    if "last_import_mtime" not in st.session_state:
        st.session_state.last_import_mtime = 0.0
        
    # S3 polling logic
    s3_bucket = os.environ.get("S3_ARTIFACTS_BUCKET")
    
    # Get the session ID from session state
    session_id = st.session_state.get("session_id")
    if not session_id:
        return

    # Use the session-specific folder path
    s3_prefix = f"data/{session_id}/"
    print(f"DEBUG: Watcher polling S3 prefix: {s3_prefix} (Bucket: {s3_bucket})", flush=True)

    latest_file_path = None
    mtime = 0.0
    filename_stem = ""

    try:
        if s3_bucket:
             import boto3
             s3 = boto3.client("s3")
             response = s3.list_objects_v2(Bucket=s3_bucket, Prefix=s3_prefix)
             if 'Contents' in response:
                 latest_obj = max(response['Contents'], key=lambda x: x['LastModified'])
                 mtime = latest_obj['LastModified'].timestamp()
                 latest_file_path = f"s3://{s3_bucket}/{latest_obj['Key']}"
                 filename_stem = os.path.splitext(os.path.basename(latest_obj['Key']))[0]
        
        # Fallback for legacy global files (optional, maybe remove for strict isolation)
        # We will SKIP global polling to enforce strict isolation.

        if not latest_file_path:
            return
            
        # Check against session state
        if "last_import_mtime" not in st.session_state:
            st.session_state.last_import_mtime = 0.0

        # If new file detected (allow small buffer)
        if mtime > st.session_state.last_import_mtime:
            # Import it!
            table_name = filename_stem.replace("-", "_")
            
            # Use session db
            st.session_state.db.clear_database() # Clean slate
            st.session_state.db.save_from_csv(table_name, latest_file_path)
            
            st.session_state.last_import_mtime = mtime
            st.session_state.selected_table = table_name
            st.rerun()
            
    except Exception as e:
        print(f"Watcher error: {e}")

# Run the watcher in the background
file_watcher()

# Initialize session state
if "selected_table" not in st.session_state:
    # Use session db
    tables = st.session_state.db.list_tables()
    st.session_state.selected_table = tables[0] if tables else None

# ===========================================
# LEFT SIDEBAR - Database & Tables
# ===========================================
with st.sidebar:
    # Use session db
    sidebar.render(st.session_state.db)

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
                df = st.session_state.db.get_table(selected, limit=10000)
                csv = df.to_csv(index=False)
                st.download_button("📥 CSV", csv, f"{selected}.csv", "text/csv")
            except:
                pass
        with hcol4:
            # Parquet download
            try:
                import io
                df = st.session_state.db.get_table(selected, limit=10000)
                buffer = io.BytesIO()
                df.to_parquet(buffer, index=False)
                st.download_button("📥 Parquet", buffer.getvalue(), f"{selected}.parquet")
            except:
                pass
        
        st.divider()
        
        # Data table
        data_grid.render(st.session_state.db, selected)
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
