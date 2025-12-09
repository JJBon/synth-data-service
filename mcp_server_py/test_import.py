
import sys
import os

# Ensure we can import server_sdk
sys.path.append("/mcp_server_py")

try:
    import server_sdk
    print("Import successful")
    
    # Try calling a simple tool
    try:
        res = server_sdk.init_config()
        print(f"init_config result: {res}")
    except Exception as e:
        print(f"Error calling init_config: {e}")
        # In case the decorator makes it not callable, print type
        print(f"Type of init_config: {type(server_sdk.init_config)}")

except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
