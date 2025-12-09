
import sys
import os
import unittest.mock

# Add path for container
sys.path.append("/")

# Import agent
try:
    from langgraph.agent import run_agent
    print("Import successful.")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_fix():
    # Mock inputs simulating a user flow
    mock_inputs = [
        "Zuora Data , generate invoices",
        "ok",
        "ok",
        "ok",
        "ok",
        "q"
    ]
    
    print("--- STARTING FIX VERIFICATION ---")
    try:
        with unittest.mock.patch('builtins.input', side_effect=mock_inputs):
            run_agent()
    except StopIteration:
        print("--- INPUT EXHAUSTED ---")
    except SystemExit:
        print("--- AGENT EXITED (Expected) ---")
    except Exception as e:
        print(f"--- ERROR: {e} ---")
        raise e

if __name__ == "__main__":
    test_fix()
