import streamlit as st
import pandas as pd
import re
import requests
from io import BytesIO

st.title("Jumia Product Image Extractor")

st.write("Upload an Excel file with a column named **url** containing Jumia product links.")

uploaded_file = st.file_uploader("Upload Excel", type=["xlsx"])

def get_product_id(url):
    # Extract product ID from URL (the part before .html, after the last hyphen)
    match = re.search(r'-([A-Z0-9]+)\.html', url)
    if match:
        return match.group(1)
    return None

def get_images_from_jumia(product_id):
    api_url = f"https://www.jumia.co.ke/fragment/sp/products/provider/mirakl/page-types/pdp/skus/{product_id}/?lang=en"
    headers = {
        "x-request-type": "async",
        "User-Agent": "Mozilla/5.0"
    }
    try:
        r = requests.get(api_url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            media = data.get("data", {}).get("media", [])
            image_urls = [m.get("url") for m in media if m.get("url")]
            return image_urls
    except Exception as e:
        st.write(f"Error fetching {product_id}: {e}")
    return []

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if "url" not in df.columns:
        st.error("Excel file must contain a column named 'url'")
    else:
        results = []
        max_images = 0

        for _, row in df.iterrows():
            product_url = row["url"]
            product_id = get_product_id(product_url)
            if product_id:
                images = get_images_from_jumia(product_id)
                max_images = max(max_images, len(images))
                results.append([product_url, len(images)] + images)
            else:
                results.append([product_url, 0])

        # Create columns dynamically
        col_names = ["url", "num_images"] + [f"image_{i+1}" for i in range(max_images)]
        result_df = pd.DataFrame(results, columns=col_names)

        st.write("### Extracted Data")
        st.dataframe(result_df)

        # Download button
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            result_df.to_excel(writer, index=False)
        st.download_button("Download Excel", data=output.getvalue(),
                           file_name="jumia_images.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
