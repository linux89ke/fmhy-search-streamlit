import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from io import BytesIO

st.title("Jumia Product Image Counter")

uploaded_file = st.file_uploader("Upload Excel or CSV with a column 'url'", type=['xlsx', 'csv'])

def get_sku_from_page(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        # SKU is stored in data-sku attribute
        sku_tag = soup.find(attrs={"data-sku": True})
        if sku_tag:
            return sku_tag['data-sku']
    except Exception as e:
        st.error(f"Error getting SKU for {url}: {e}")
    return None

def get_images_from_sku(sku):
    try:
        json_url = f"https://www.jumia.co.ke/fragment/sp/products/provider/mirakl/page-types/pdp/skus/{sku}/?lang=en"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "x-request-type": "async"
        }
        r = requests.get(json_url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        images = data.get("images", [])
        return images
    except Exception as e:
        return []

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    if 'url' not in df.columns:
        st.error("The file must have a column named 'url'.")
    else:
        result_data = []
        progress = st.progress(0)

        for idx, row in df.iterrows():
            url = row['url']
            sku = get_sku_from_page(url)
            if sku:
                images = get_images_from_sku(sku)
                result_row = {
                    "url": url,
                    "image_count": len(images)
                }
                # Add image URLs into columns
                for i, img_url in enumerate(images, start=1):
                    result_row[f"image_{i}"] = img_url
                result_data.append(result_row)
            else:
                result_data.append({"url": url, "image_count": 0})

            progress.progress((idx + 1) / len(df))

        result_df = pd.DataFrame(result_data)
        st.dataframe(result_df)

        # Download
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            result_df.to_excel(writer, index=False)
        st.download_button("Download Excel", output.getvalue(), "jumia_images.xlsx")
