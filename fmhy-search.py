import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO

# ----------------------------
# Function to get product images from a Jumia product link
# ----------------------------
def get_product_images(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return 0, []

        soup = BeautifulSoup(r.text, "html.parser")

        # Find all <img> tags and filter likely product images
        images = []
        for img_tag in soup.find_all("img"):
            src = img_tag.get("data-src") or img_tag.get("src")
            if src and "jumia" in src and "product" in src:
                images.append(src.split("?")[0])  # remove tracking params

        # Remove duplicates
        images = list(dict.fromkeys(images))
        return len(images), images
    except Exception:
        return 0, []

# ----------------------------
# Streamlit App UI
# ----------------------------
st.title("Jumia Product Image Extractor")
st.write("Upload an Excel file with a column named **link** containing Jumia product URLs.")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Validate column name
    if 'link' not in df.columns:
        st.error("❌ The Excel file must have a column named 'link'.")
    else:
        results = []
        max_images = 0

        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, row in df.iterrows():
            url = row['link']
            status_text.text(f"Processing {idx+1}/{len(df)}: {url}")
            img_count, img_links = get_product_images(url)

            result_row = {"link": url, "image_count": img_count}
            for i, link in enumerate(img_links):
                result_row[f"image_{i+1}"] = link

            results.append(result_row)
            max_images = max(max_images, img_count)

            progress_bar.progress((idx + 1) / len(df))

        result_df = pd.DataFrame(results)

        # Ensure all image columns exist
        for i in range(1, max_images + 1):
            col = f"image_{i}"
            if col not in result_df.columns:
                result_df[col] = None

        # Reorder columns
        ordered_cols = ["link", "image_count"] + [f"image_{i}" for i in range(1, max_images + 1)]
        result_df = result_df[ordered_cols]

        st.write("### Results", result_df)

        # Download Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            result_df.to_excel(writer, index=False)
        st.download_button(
            label="⬇️ Download results as Excel",
            data=output.getvalue(),
            file_name="jumia_product_images.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
