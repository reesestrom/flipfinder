#!/bin/bash

echo "📦 Installing Chromium & Chromedriver in local folder..."

mkdir -p chrome-bin
cd chrome-bin

# Download stable Chromium build (v117 works well)
wget https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/1172525/chrome-linux.zip
unzip chrome-linux.zip
mv chrome-linux chrome
rm chrome-linux.zip

# Download matching Chromedriver for Chromium v117
wget https://chromedriver.storage.googleapis.com/117.0.5938.62/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
chmod +x chromedriver
rm chromedriver_linux64.zip

cd ..

export CHROME_PATH=$(pwd)/chrome-bin/chrome/chrome
export CHROMEDRIVER_PATH=$(pwd)/chrome-bin/chromedriver

echo "✅ Chromium at: $CHROME_PATH"
echo "✅ Chromedriver at: $CHROMEDRIVER_PATH"

echo "🚀 Starting app..."
uvicorn app:app --host 0.0.0.0 --port 10000
