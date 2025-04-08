import os
import re
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from dotenv import load_dotenv

from description_refiner import refine_title_and_condition
from price_estimator import refined_avg_price

load_dotenv()

def get_chrome_driver():
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium import webdriver

    chrome_path = "/opt/render/project/src/chrome-bin/chrome/chrome"
    driver_path = "/opt/render/project/src/chrome-bin/chromedriver"

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.binary_location = chrome_path

    service = Service(driver_path)
    return webdriver.Chrome(service=service, options=options)



def search_facebook_marketplace(refined_query, condition, location_city):
    print("🌐 Starting Facebook Marketplace scrape...")


    days_listed=15

    options = Options()
    # options.add_argument("--headless=new")  # Disable for debugging
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    browser = get_chrome_driver()

    url = f"https://www.facebook.com/marketplace/{location_city}/search?query={refined_query}&daysSinceListed={days_listed}"
    print(f"🔎 Navigating to: {url}")
    browser.get(url)
    time.sleep(5)

    # Close any popups
    for xpath in [
        '//div[@aria-label="Close" and @role="button"]',
        '//div[@aria-label="Decline optional cookies" and @role="button"]'
    ]:
        try:
            button = browser.find_element(By.XPATH, xpath)
            button.click()
            print(f"✅ Closed popup with XPath: {xpath}")
        except:
            pass

    # Scroll to load more items
    last_height = browser.execute_script("return document.body.scrollHeight")
    for _ in range(3):  # Scroll a few times
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    html = browser.page_source
    browser.quit()
    print("✅ Finished page load, parsing HTML...")

    # Optional: Save HTML to inspect what's being loaded
    with open("facebook_debug.html", "w", encoding="utf-8") as f:
        f.write(html)

    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a")
    print(f"🔗 Found {len(links)} <a> tags")

    query_words = refined_query.lower().split()
    print(query_words)
    matches = [link for link in links if any(word in link.text.lower() for word in query_words)]
    print(f"🔗 Matched {len(matches)} anchor tags containing any of: {query_words}")


    extracted = []

    for link in matches:
        try:
            text = list(link.stripped_strings)
            if len(text) < 3:
                continue

            print(f"🧠 Raw text block: {text}")

            price_line = next((l for l in text if re.search(r"\d[\d,.]*", l)), None)
            price = float(re.sub(r"[^\d.]", "", price_line)) if price_line else None
            title = text[-2]
            city = text[-1]
            href = re.sub(r"\?.*", "", link.get("href"))

            if not price or not href or not title:
                continue

            # Estimate resale value from eBay
            refinement = refine_title_and_condition(title, "", condition)
            resale_estimate = refined_avg_price(refinement["refined_query"], refinement["adjusted_condition"])

            if resale_estimate <= 0:
                continue

            profit = (resale_estimate) - price
            if profit <= 0:
                continue

            # Extract thumbnail image
            img_tag = link.find("img")
            thumbnail = img_tag["src"] if img_tag and "src" in img_tag.attrs else None

            extracted.append({
                "title": title,
                "price": price,
                "profit": profit,
                "url": "https://facebook.com" + href,
                "location": city,
                "thumbnail": thumbnail
            })
        except Exception as e:
            print("❌ Error extracting item:", e)
            continue

    print(f"✅ Extracted {len(extracted)} profitable items")

    # Sort by profit, limit to top 5
    top_listings = sorted(extracted, key=lambda x: x["profit"], reverse=True)[:5]
    return top_listings


if __name__ == "__main__":
    test_query = "KitchenAid Mixer"
    test_condition = "used"
    test_city = "saltlakecity"

    results = search_facebook_marketplace(test_query, test_condition, test_city)

    print("📦 FINAL RESULTS:")
    for i, item in enumerate(results, 1):
        print(f"\nResult #{i}")
        print(f"Title     : {item['title']}")
        print(f"Price     : ${item['price']}")
        print(f"Profit    : ${item['profit']:.2f}")
        print(f"Location  : {item['location']}")
        print(f"Thumbnail : {item['thumbnail']}")
        print(f"URL       : {item['url']}")
