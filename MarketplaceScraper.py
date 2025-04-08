from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from urllib.parse import quote
import time
import re
import os
from description_refiner import refine_title_and_condition
from price_estimator import refined_avg_price
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_chrome_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/opt/render/project/src/chrome-bin/chrome/chrome"
    service = Service("/opt/render/project/src/chrome-bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)


def search_facebook_marketplace(refined_query, condition, location_city):
    browser = get_chrome_driver()
    encoded_query = quote(refined_query)
    days_listed = 15

    url = f"https://www.facebook.com/marketplace/{location_city}/search?query={encoded_query}&daysSinceListed={days_listed}"
    print(f"🔎 Navigating to: {url}")
    browser.get(url)
    try:
        # Wait up to 12 seconds for listing container to appear
        WebDriverWait(browser, 12).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/marketplace/item/']"))
        )
        print("✅ Listings appear to be loaded.")
    except Exception as e:
        print("⚠️ Listings did not load in time:", e)

    SCROLL_PAUSE = 2
    scroll_attempts = 5

    for i in range(scroll_attempts):
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print(f"🌀 Scrolling... attempt {i+1}")
        time.sleep(SCROLL_PAUSE)


    soup = BeautifulSoup(browser.page_source, 'html.parser')
    # Save full page source for debugging
    with open("fb_debug.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    print("🧪 HTML dumped to fb_debug.html")

    print("🧪 PAGE SOURCE START:")
    print(browser.page_source[:1000])

    browser.quit()

    listings = soup.find_all("a", href=True, class_=lambda x: x and "x1i10hfl" in x)
    print(f"🔗 Found {len(listings)} potential item blocks")

    extracted = []

    for item in listings:
        try:
            href = item["href"]
            url = "https://www.facebook.com" + href

            # Title
            title_tag = item.find("span", class_=lambda x: x and "x1lliihq" in x)
            title = title_tag.get_text(strip=True) if title_tag else None

            # Price
            price_tag = item.find("span", class_=lambda x: x and "x193iq5w" in x)
            price_text = price_tag.get_text(strip=True) if price_tag else None
            price = float(re.sub(r"[^\d.]", "", price_text)) if price_text else None

            # Location
            location_tag = item.find("span", class_=lambda x: x and "xlyipyv" in x)
            location = location_tag.get_text(strip=True) if location_tag else ""

            # Thumbnail
            img_tag = item.find("img")
            thumbnail = img_tag["src"] if img_tag else None

            if not price or not title or not url:
                continue

            refinement = refine_title_and_condition(title, "", condition)
            resale_estimate = refined_avg_price(refinement["refined_query"], refinement["adjusted_condition"])
            if resale_estimate <= 0:
                continue

            profit = (resale_estimate * 0.85) - price
            if profit <= 0:
                continue

            extracted.append({
                "title": title,
                "price": price,
                "profit": profit,
                "url": url,
                "location": location,
                "thumbnail": thumbnail
            })

        except Exception as e:
            print(f"❌ Error extracting item: {e}")
            continue

    top_listings = sorted(extracted, key=lambda x: x["profit"], reverse=True)[:5]
    print(f"✅ Extracted {len(top_listings)} profitable items")
    return top_listings
