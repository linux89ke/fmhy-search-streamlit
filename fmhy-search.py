import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
import json
import time
from io import BytesIO

# Map for Jumia domains
JUMIA_DOMAINS = {
    "Kenya": "jumia.co.ke",
    "Nigeria": "jumia.com.ng",
    "Uganda": "jumia.ug",
    "Egypt": "jumia.com.eg",
    "Ivory Coast": "jumia.ci",
    "Ghana": "jumia.com.gh",
    "Senegal": "jumia.sn"
}

scraper = cloudscraper.create_scraper(
    browser={
        'custom': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                  ' Chrome/115.0.0.0 Safari/537.36'
    }
)

def get_jumia_link(sku, domain):
    try:
        search_url = f"https://{domain}/catalog/?q={sku}"
        response = scraper.get(search_url)
        if response.status_code != 200:
            return "NONE"
        soup = BeautifulSoup(response.text, "html.parser")
        product_tag = soup.find("a", {"class": "core"})
        if product_tag and product_tag.get("href"):
            return f"https://{domain}" + product_tag["href"]
        else:
            return "NONE"
    except:
        return "NONE"

def get_main_product_images_ldjson(product_url):
    if product_url == "NONE":
        return []
    try:
        response = scraper.get(product_url)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        script = soup.find("script", {"type": "application/ld+json"})
        if not script:
            return []
        data = json.loads(script.string)
        images = data.get("mainEntity", {}).get("image", {}).get("contentUrl", [])
        if isinstance(images, str):
            return [images]
        elif isinstance(images, list):
            return images
        else:
            return []
    except Exception as e:
        st.error(f"Error extracting LD-JSON images: {e}")
        return []

st.title("Jumia SKU Link & Main Product Images Finder")

country = st.selectbox("Select Country", list(JUMIA_DOMAINS.keys()))
domain = JUMIA_DOMAINS[country]
