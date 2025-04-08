#!/bin/bash
echo "📦 Installing Chromium & Chromedriver in local folder..."

mkdir -p chrome-bin
cd chrome-bin

# Download latest stable version number of Chrome
LATEST_VERSION=$(curl -sS https://omahaproxy.appspot.com/linux | grep stable | awk -F',' '{print $3}' | head -n1)
CHROMEDRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" | grep -A 1 "\"$LATEST_VERSION\"" | grep "chromedriver-linux64" | grep "url" | cut -d '"' -f 4)

# Fallback if parsing fails
if [ -z "$CHROMEDRIVER_VERSION" ]; then
  echo "❌ Failed to fetch ChromeDriver version for $LATEST_VERSION"
  exit 1
fi

# Download and unzip Chromedriver
wget -q "$CHROMEDRIVER_VERSION" -O chromedriver.zip
unzip -q chromedriver.zip
mv chromedriver-linux64/chromedriver .
chmod +x chromedriver
rm -rf chromedriver.zip chromedriver-linux64

# Use Puppeteer's Chromium (optional, if you're still stuck)
CHROME_URL="https://storage.googleapis.com/chrome-for-testing-public/$LATEST_VERSION/linux64/chrome-linux64.zip"
wget -q $CHROME_URL -O chrome.zip
unzip -q chrome.zip
mv chrome-linux64 chrome
chmod +x chrome/chrome
rm chrome.zip

cd ..

echo "✅ Chromium at: $(pwd)/chrome-bin/chrome/chrome"
echo "✅ Chromedriver at: $(pwd)/chrome-bin/chromedriver"

# Start your app
uvicorn app:app --host 0.0.0.0 --port 10000
