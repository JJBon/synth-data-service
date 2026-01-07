
import subprocess
import json
import sys
import os

def run():
    cmd = ["uvx", "awslabs.amazon-bedrock-agentcore-mcp-server@latest"]
    print(f"Running: {' '.join(cmd)}")
    
    # Run the process
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0 # Unbuffered
    )
    
    # Initialize message
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "debugger", "version": "0.1"}
        }
    }
    
    try:
        print("Sending initialize...")
        json_line = json.dumps(init_msg) + "\n"
        process.stdin.write(json_line)
        process.stdin.flush()
        
        # Read initialize response
        while True:
            stdout_line = process.stdout.readline()
            if not stdout_line:
                break
            resp = json.loads(stdout_line)
            if resp.get("id") == 1:
                print(f"Initialized: {json.dumps(resp, indent=2)}")
                break
        
        # Call manage_agentcore_gateway
        print("\nCalling manage_agentcore_gateway...")
        mgr_req = {
            "jsonrpc": "2.0", 
            "id": 7, 
            "method": "tools/call", 
            "params": {
                "name": "manage_agentcore_gateway",
                "arguments": {}
            }
        }
        process.stdin.write(json.dumps(mgr_req) + "\n")
        process.stdin.flush()
        
        while True:
            stdout_line = process.stdout.readline()
            if not stdout_line:
                break
            try:
                resp = json.loads(stdout_line)
                if resp.get("id") == 7:
                    print(f"Gateway Info: {json.dumps(resp, indent=2)}")
                    break
            except json.JSONDecodeError:
                pass


    except Exception as e:
        print(f"Error: {e}")
    finally:
        process.kill()

if __name__ == "__main__":
    run()
