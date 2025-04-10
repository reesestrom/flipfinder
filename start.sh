#!/bin/bash

echo "🚀 Starting Flip Finder server..."

# Start FastAPI server (assuming app.py is your entry point)
uvicorn app:app --host 0.0.0.0 --port 10000
