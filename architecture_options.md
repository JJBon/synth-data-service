# Data Management & Multi-Tenancy Architecture Options

## Current State
- **Storage**: Shared EFS Volume mapped to `/data-designer-output`.
- **Database**: In-Memory DuckDB (Session Scoped).
- **Handoff**: `mcp-server-sdk` writes CSV to EFS; `streamlit-ui` watches folder and loads latest file globally.

## The Challenge: Multi-User Isolation
In the current setup, the "Latest File" logic in the UI is global. If User A generates a file, User B's UI might pick it up if they are the next to check, or both might see it.

## Options for Improvement

### Option 1: S3 Offloading (Recommended for Production)
Instead of using EFS for artifact exchange, use an S3 Bucket.
*   **Workflow**:
    1.  **Agent**: Generates data -> Uploads to `s3://my-bucket/{user_id}/{job_id}.csv` -> Returns S3 Key.
    2.  **UI**: Agent sends S3 Key to Client. Client (Streamlit) downloads object from S3 into its In-Memory DuckDB.
*   **Pros**:
    *   **Isolation**: Strict path-based access (`{user_id}`).
    *   **Scalability**: S3 handles infinite concurrency/storage.
    *   **Stateless**: No dependency on shared disks/volumes.
*   **Cons**:
    *   Requires AWS IAM setup (IRSA) for both pods.
    *   Slightly higher latency than local disk.

### Option 2: Session-Aware EFS Subfolders
Keep EFS but organize by Session ID.
*   **Workflow**:
    1.  **Agent**: Takes `session_id` as input -> Writes to `/data-designer-output/{session_id}/{job_id}.csv`.
    2.  **UI**: File Watcher only watches `/data-designer-output/{current_session_id}/*.csv`.
*   **Pros**:
    *   Keeps current "fast" local disk architecture.
    *   Solves isolation issue.
*   **Cons**:
    *   Agent needs to know the Streamlit `session_id`. Passing this context through the LLM/Agnt to the tool can be tricky.
    *   Cleanup of old session folders required.

### Option 3: Per-User Persistent DuckDB
Give each user a persistent database file.
*   **Workflow**:
    *   Mount EFS.
    *   Streamlit connects to `/data/users/{user_id}.duckdb`.
*   **Pros**:
    *   Data persists across sessions (logout/login).
*   **Cons**:
    *   **Locking**: File-based DBs on NFS (EFS) have historic locking issues.
    *   **Storage Management**: Managing thousands of DB files.

## Recommendation
**Move to Option 1 (S3)**.
It aligns best with cloud-native microservices. The UI holds data in **Memory** (fast, isolated per viewing session), and S3 holds the **Persistence** (cheap, durable, isolated).

For now, the **In-Memory** change we just made is the correct first step (Decoupling storage from view). Ideally, the next step is replacing the EFS Volume with S3 calls.
