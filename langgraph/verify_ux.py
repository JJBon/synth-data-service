
import sys
import os
import unittest.mock

# Add path for container
sys.path.append("/")

# Import agent
from langgraph.agent import run_agent

def test_ux():
    # Mock inputs simulating a user flow
    # 1. Intent
    # 2. Clarification answer
    # 3. Approval 1 (for model?)
    # 4. Approval 2 (for schema?)
    # 5. Quit
    mock_inputs = [
        "Generate Zuora invoices",
        "10 records. Enterprise customers. Monthly.",
        "yes",
        "yes",
        "q"
    ]
    
    print("--- STARTING UX VERIFICATION ---")
    try:
        with unittest.mock.patch('builtins.input', side_effect=mock_inputs):
            run_agent()
    except StopIteration:
        print("--- INPUT EXHAUSTED ---")
    except SystemExit:
        print("--- AGENT EXITED (Expected) ---")
    except Exception as e:
        print(f"--- ERROR: {e} ---")

if __name__ == "__main__":
    test_ux()
