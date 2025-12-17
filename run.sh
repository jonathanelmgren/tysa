#!/bin/bash
# TYSA Launcher - handles venv automatically

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Setting up environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run TYSA
python tysa.py "$@"
