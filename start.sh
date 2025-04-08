#!/bin/bash

echo "Current dir: $(pwd)"
ls -l

# Install Chromium and Chromedriver
echo "🔧 Installing Chromium and Chromedriver..."
apt-get update && apt-get install -y \
  chromium \
  chromium-driver \
  wget \
  unzip

# Show confirmation
echo "✅ Chromium and Chromedriver installed."
which chromium
which chromedriver
chromium --version
chromedriver --version

# Launch the FastAPI server
echo "🚀 Starting Uvicorn server..."
uvicorn app:app --host 0.0.0.0 --port 10000
