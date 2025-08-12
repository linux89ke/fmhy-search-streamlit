import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO

# Browser-like headers to bypass 403
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.jumia.co.ke/",
    "Connection": "keep-alive"
}

def get_sku_from_url(product_url):
    try:
        resp = requests.get(product_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        match = re.search(r'"sku"\s*:\s*"([^"]+)"', resp.text)
        return match.group(1) if match else None
    except Exception as e:
        st.write(f"Error getting SKU for {product_url}: {e}")
        return None

def get_images_for_sku(sku):
    try:
        json_url = f"https://www.jumia.co.ke/fragment/sp/products/provider/mirakl/page-types/pdp/skus/{sku}/?lang=en"
        resp = requests.get(json_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        images = data.get("data", {}).get("media", {}).get("images", [])
        return [img.get("url") for img in images if img.get("url")]
    except Exception as e:
        return []

st.title("Jumia Product Image Checker")

uploaded_file = st.file_uploader("Upload Excel or CSV with a 'url' column", type=["xlsx", "csv"])

if uploaded_file:
    # Load file
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(".xlsx") else pd.read_csv(uploaded_file)
    
    if "url" not in df.columns:
        st.error("File must have a 'url' column")
    else:
        results = []
        progress = st.progress(0)
        total = len(df)

        for idx, row in df.iterrows():
            url = row["url"]
            sku = get_sku_from_url(url)
            if sku:
                images = get_images_for_sku(sku)
                results.append({
                    "url": url,
                    "sku": sku,
                    "image_count": len(images),
                    "images": ", ".join(images)
                })
            else:
                results.append({
                    "url": url,
                    "sku": None,
                    "image_count": 0,
                    "images": ""
                })
            progress.progress((idx + 1) / total)

        results_df = pd.DataFrame(results)
        st.dataframe(results_df)

        # Download button
        output = BytesIO()
        results_df.to_excel(output, index=False)
        st.download_button("Download Results", data=output.getvalue(), file_name="jumia_image_results.xlsx")
