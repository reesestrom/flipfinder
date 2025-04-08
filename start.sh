#!/bin/bash
echo "📦 Installing Chromium & Chromedriver in local folder..."

# Make directory
mkdir -p chrome-bin
cd chrome-bin

# Fetch JSON metadata for last known good versions
JSON=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json)

# Extract URLs using jq
CHROME_URL=$(echo "$JSON" | jq -r '.channels.Stable.downloads.chrome[] | select(.platform == "linux64") | .url')
DRIVER_URL=$(echo "$JSON" | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform == "linux64") | .url')

if [[ -z "$CHROME_URL" || -z "$DRIVER_URL" ]]; then
  echo "❌ Failed to extract download URLs."
  exit 1
fi

# Download and extract Chromium
echo "📥 Downloading Chromium..."
curl -sSL "$CHROME_URL" -o chrome.zip
unzip -q chrome.zip
mv chrome-linux64 chrome
rm chrome.zip

# Download and extract Chromedriver
echo "📥 Downloading Chromedriver..."
curl -sSL "$DRIVER_URL" -o chromedriver.zip
unzip -q chromedriver.zip
mv chromedriver-linux64/chromedriver .
chmod +x chromedriver
rm -rf chromedriver.zip chromedriver-linux64

cd ..

echo "✅ Chromium at: $(pwd)/chrome-bin/chrome/chrome"
echo "✅ Chromedriver at: $(pwd)/chrome-bin/chromedriver"

# Start server
uvicorn app:app --host 0.0.0.0 --port 10000
