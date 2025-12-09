import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure environment variables are loaded for tests (fixes 401 in agent)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass
