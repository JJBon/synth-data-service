
import asyncio
import os
import sys
import json
import time

# Ensure we can import mcp
try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
except ImportError:
    print("Error: 'mcp' package not found. Please verify environment.")
    sys.exit(1)

async def run_generation():
    # Matches my_mcp_client.py
    mcp_url = "http://localhost:8000/mcp"
    headers = {"Mcp-Session-Id": "local-dev-session"}
    
    print(f"Connecting to MCP server at {mcp_url}...")

    try:
        async with streamablehttp_client(mcp_url, headers, timeout=600, terminate_on_close=False) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                # List tools to verify connection
                tools_response = await session.list_tools()
                tool_names = [t.name for t in tools_response.tools]
                print(f"Connected! Available tools: {len(tool_names)}")
                
                if "init_config" not in tool_names:
                    print("Error: init_config tool not found.")
                    return

                print("\n--- 1. Initializing Configuration ---")
                await session.call_tool("init_config", {})
                
                print("\n--- 2. Defining Schema (Zuora Invoices) ---")
                
                await session.call_tool("add_uuid_column", {"name": "InvoiceID"})
                print(" - Added InvoiceID (UUID)")
                
                await session.call_tool("add_uuid_column", {"name": "AccountID"})
                print(" - Added AccountID (UUID)")
                
                await session.call_tool("add_float_column", {"name": "Amount", "low": 10.0, "high": 5000.0})
                print(" - Added Amount")
                
                await session.call_tool("add_category_column", {"name": "Status", "values": ["Draft", "Posted", "Canceled", "Paid"]})
                print(" - Added Status")
                
                await session.call_tool("add_datetime_column", {"name": "InvoiceDate", "start": "2023-01-01", "end": "2023-12-31", "unit": "s"})
                print(" - Added InvoiceDate")

                print("\n--- 2.5 Adding Model Config (Required) ---")
                await session.call_tool("add_model_config", {
                    "alias": "default_model",
                    "model": "bedrock-claude-haiku",
                    "provider": "litellm"
                })

                print(" - Added Model Config")

                print("\n--- 2.6 Verifying Config State ---")
                summary_res = await session.call_tool("get_config_summary", {})
                print(f"Server Config Summary: {summary_res.content[0].text}")

                print("\n--- 3. Submitting Job ---")
                job_name = "zuora_invoices_gen"
                create_result = await session.call_tool("create_job", {"job_name": job_name, "num_records": 10})
                
                # Parse Job ID
                res_content = create_result.content[0].text
                print(f"Job Submission Response: {res_content}")
                
                job_id = None
                try:
                    job_data = json.loads(res_content)
                    job_id = job_data.get("job_id")
                except:
                     # Simple regex fallback if JSON parsing fails/is strict
                     import re
                     m = re.search(r"'job_id':\s*'([^']+)'", res_content)
                     if m: job_id = m.group(1)

                if not job_id:
                     print("Could not parse Job ID. Exiting.")
                     return

                print(f"Tracked Job ID: {job_id}")
                
                print("\n--- 4. Polling Status ---")
                status = "unknown"
                start_time = time.time()
                while status not in ["completed", "success", "succeeded", "error", "failed"]:
                    if time.time() - start_time > 60:
                        print("Timeout waiting for job.")
                        return
                    
                    await asyncio.sleep(2.0)
                    status_res = await session.call_tool("get_job_status", {"job_id": job_id})
                    status_text = status_res.content[0].text
                    print(f"Status update: {status_text}")
                    
                    try:
                        status_data = json.loads(status_text)
                        status = status_data.get("status")
                    except:
                        pass
                    
                    if status in ["error", "failed"]:
                        print("Job failed!")
                        return

                print("\n--- 5. Finalizing & Downloading ---")
                finalize_res = await session.call_tool("finalize_submission", {"job_id": job_id})
                fin_text = finalize_res.content[0].text
                print(f"Result: {fin_text}")
                
                try:
                    fin_data = json.loads(fin_text)
                    local_csv = fin_data.get("local_files", {}).get("csv")
                except:
                     import re
                     m = re.search(r"'csv':\s*'([^']+)'", fin_text)
                     local_csv = m.group(1) if m else None
                
                if local_csv and os.path.exists(local_csv):
                    print(f"\nSUCCESS! Data generated at: {local_csv}")
                    print("First 3 lines:")
                    with open(local_csv, 'r') as f:
                        for _ in range(3):
                            print(f.readline().strip())
                else:
                    print("Job finished but local CSV not verified.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_generation())
