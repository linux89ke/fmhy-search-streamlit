import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO

def get_product_images(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return 0, []

        soup = BeautifulSoup(response.text, 'html.parser')

        # Try main image selector first
        images = soup.find_all("img", {"data-testid": "main-image"})
        if not images:
            # Fallback: common lazy-loaded class
            images = soup.find_all("img", {"class": "lazy"})

        img_links = []
        for img in images:
            src = img.get("data-src") or img.get("src")
            if src and src.startswith("http"):
                img_links.append(src)

        img_links = list(dict.fromkeys(img_links))  # remove duplicates
        return len(img_links), img_links
    except Exception:
        return 0, []

st.title("Product Image Extractor")
st.write("Upload an Excel file with a column named 'link' containing Jumia product URLs.")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    if 'link' not in df.columns:
        st.error("The Excel file must have a column named 'link'")
    else:
        results = []
        max_images = 0

        progress_bar = st.progress(0)
        for idx, row in df.iterrows():
            url = row['link']
            img_count, img_links = get_product_images(url)
            result_row = {"link": url, "image_count": img_count}
            for i, link in enumerate(img_links):
                result_row[f"image_{i+1}"] = link
            results.append(result_row)
            if img_count > max_images:
                max_images = img_count
            progress_bar.progress((idx + 1) / len(df))

        result_df = pd.DataFrame(results)

        # Ensure all image columns exist
        for i in range(1, max_images + 1):
            col = f"image_{i}"
            if col not in result_df.columns:
                result_df[col] = None

        # Reorder columns: link, image_count, then images
        ordered_cols = ["link", "image_count"] + [f"image_{i}" for i in range(1, max_images + 1)]
        result_df = result_df[ordered_cols]

        st.write("### Results", result_df)

        # Download as Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            result_df.to_excel(writer, index=False)
        st.download_button(
            label="Download results as Excel",
            data=output.getvalue(),
            file_name="jumia_product_images.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
