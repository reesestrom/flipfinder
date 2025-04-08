#!/bin/bash

echo "📦 Installing Chromium and Chromedriver manually (Render-safe)..."

mkdir -p /usr/local/bin/chrome
cd /usr/local/bin/chrome

# Download Chromium (Headless shell from Chromium snapshots)
wget https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/1176782/chrome-linux.zip
unzip chrome-linux.zip
mv chrome-linux chrome
rm chrome-linux.zip

# Download matching chromedriver (version 117.0.5938.62 here)
wget https://storage.googleapis.com/chromedriver/117.0.5938.62/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
mv chromedriver /usr/local/bin/chromedriver
chmod +x /usr/local/bin/chromedriver
rm chromedriver_linux64.zip

# Make Chrome executable accessible
ln -s /usr/local/bin/chrome/chrome /usr/bin/google-chrome

echo "✅ Chrome and Chromedriver installed."

# Launch app
echo "🚀 Launching app..."
uvicorn app:app --host 0.0.0.0 --port 10000
