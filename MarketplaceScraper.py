import os
import re
import time
import statistics
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
load_dotenv()

from description_refiner import refine_title_and_condition
from app import refined_avg_price



# --- Main search function ---
def search_facebook_marketplace(refined_query, condition, location_city):
    chrome_install = ChromeDriverManager().install()
    folder = os.path.dirname(chrome_install)
    chromedriver_path = os.path.join(folder, "chromedriver.exe")

    options = Options()
    #options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    browser = webdriver.Chrome(service=Service(chromedriver_path), options=options)

    url = f"https://www.facebook.com/marketplace/{location_city}/search?query={refined_query}"
    browser.get(url)

    # Close any pop-ups (login/cookies)
    for xpath in [
        '//div[@aria-label="Close" and @role="button"]',
        '//div[@aria-label="Decline optional cookies" and @role="button"]'
    ]:
        try:
            button = browser.find_element(By.XPATH, xpath)
            button.click()
        except:
            pass

    # Scroll to load more listings
    last_height = browser.execute_script("return document.body.scrollHeight")
    while True:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # Parse results
    soup = BeautifulSoup(browser.page_source, "html.parser")
    browser.quit()

    links = soup.find_all("a")
    matches = [link for link in links if refined_query.lower() in link.text.lower()]
    extracted = []

    for link in matches:
        try:
            text = list(link.stripped_strings)
            if len(text) < 3:
                continue

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

            profit = (resale_estimate * 0.85) - price
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

    # Sort by profit, limit to top 5
    top_listings = sorted(extracted, key=lambda x: x["profit"], reverse=True)[:5]
    return top_listings
if __name__ == "__main__":
    test_query = "KitchenAid Stand Mixer"
    test_condition = "used"
    test_city = "saltlakecity"  # or any city supported by Facebook Marketplace

    results = search_facebook_marketplace(test_query, test_condition, test_city)

    for i, item in enumerate(results, 1):
        print(f"\nResult #{i}")
        print(f"Title     : {item['title']}")
        print(f"Price     : ${item['price']}")
        print(f"Profit    : ${item['profit']:.2f}")
        print(f"Location  : {item['location']}")
        print(f"Thumbnail : {item['thumbnail']}")
        print(f"URL       : {item['url']}")
