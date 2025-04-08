#!/bin/bash

echo "📦 Installing Chrome and Chromedriver manually..."

# 1. Install Chrome
curl -O https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get update && apt-get install -y ./google-chrome-stable_current_amd64.deb

# 2. Determine Chrome major version
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+' | head -1)
MAJOR_VERSION=$(echo "$CHROME_VERSION" | cut -d '.' -f 1)

# 3. Get matching Chromedriver version
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${MAJOR_VERSION}")
echo "📦 Matching Chromedriver version: $CHROMEDRIVER_VERSION"

# 4. Download and unzip Chromedriver
wget -O chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
unzip chromedriver.zip
chmod +x chromedriver
mv chromedriver /usr/bin/chromedriver

# 5. Clean up
rm -f google-chrome*.deb chromedriver.zip

# Confirm versions
echo "✅ Installed Chrome version: $(google-chrome --version)"
echo "✅ Installed Chromedriver version: $(chromedriver --version)"

# 6. Start app
uvicorn app:app --host 0.0.0.0 --port 10000
