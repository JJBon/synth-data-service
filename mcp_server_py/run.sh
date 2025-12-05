#!/bin/bash

# Navigate to script directory
cd "$(dirname "$0")"

# Activate venv
source venv/bin/activate

# Run server
python server.py
