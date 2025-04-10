#!/bin/bash
echo "Current dir: $(pwd)"
ls -l
uvicorn app:app --host 0.0.0.0 --port 10000
