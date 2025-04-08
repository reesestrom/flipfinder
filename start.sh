#!/bin/bash
echo "📦 Installing Chrome & Chromedriver..."

# Download known working version of Chrome (v122) & Chromedriver
wget -O chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -i chrome.deb || apt-get install -fy

wget -O chromedriver.zip https://chromedriver.storage.googleapis.com/122.0.6261.94/chromedriver_linux64.zip
unzip chromedriver.zip
chmod +x chromedriver
mv chromedriver /usr/bin/chromedriver

echo "✅ Installed Chrome & Chromedriver"

# Launch app
echo "🚀 Launching app..."
uvicorn app:app --host 0.0.0.0 --port 10000
