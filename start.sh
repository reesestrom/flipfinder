#!/bin/bash
echo "📦 Installing Chromium & Chromedriver in local folder..."

# Create folder
mkdir -p chrome-bin
cd chrome-bin

# Get latest Chrome for Testing version
LATEST_VERSION=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | grep "version" | head -1 | cut -d '"' -f4)
echo "✅ Latest version: $LATEST_VERSION"

# Get URLs
CHROME_URL=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json \
  | grep -A5 "\"$LATEST_VERSION\"" \
  | grep "chrome-linux64" \
  | grep "url" \
  | head -1 \
  | cut -d '"' -f4)

CHROMEDRIVER_URL=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json \
  | grep -A5 "\"$LATEST_VERSION\"" \
  | grep "chromedriver-linux64" \
  | grep "url" \
  | head -1 \
  | cut -d '"' -f4)

if [[ -z "$CHROME_URL" || -z "$CHROMEDRIVER_URL" ]]; then
  echo "❌ Failed to extract download URLs."
  exit 1
fi

# Download and extract
echo "📥 Downloading Chromium..."
wget -q "$CHROME_URL" -O chrome.zip
unzip -q chrome.zip
mv chrome-linux64 chrome
rm chrome.zip

echo "📥 Downloading Chromedriver..."
wget -q "$CHROMEDRIVER_URL" -O chromedriver.zip
unzip -q chromedriver.zip
mv chromedriver-linux64/chromedriver .
chmod +x chromedriver
rm -rf chromedriver.zip chromedriver-linux64

cd ..

echo "✅ Chromium at: $(pwd)/chrome-bin/chrome/chrome"
echo "✅ Chromedriver at: $(pwd)/chrome-bin/chromedriver"

# Launch your app
uvicorn app:app --host 0.0.0.0 --port 10000
