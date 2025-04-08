#!/bin/bash

echo "📦 Installing Chrome and Chromedriver manually..."

# Download latest Chrome .deb (stable)
curl -O https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get update && apt-get install -y ./google-chrome-stable_current_amd64.deb

# Download Chromedriver that matches installed Chrome version
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+' | head -1)
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}")
wget -O chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
unzip chromedriver.zip
mv chromedriver /usr/bin/chromedriver
chmod +x /usr/bin/chromedriver

# Cleanup
rm -f google-chrome*.deb chromedriver.zip

echo "✅ Chrome version: $(google-chrome --version)"
echo "✅ Chromedriver version: $(chromedriver --version)"

# Run your app
echo "🚀 Launching FastAPI..."
uvicorn app:app --host 0.0.0.0 --port 10000
