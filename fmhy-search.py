import streamlit as st
import pandas as pd
import requests
import re
import json
import io

# Function to get Jumia product images
def get_jumia_images(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        html = r.text

        # Extract JSON containing images
        match = re.search(r'"mediaList":(\[.*?\])', html)
        if not match:
            return 0, []

        media_list = json.loads(match.group(1))
        image_urls = []

        for item in media_list:
            if "url" in item:
                img_url = item["url"]
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    img_url = "https://www.jumia.co.ke" + img_url
                image_urls.append(img_url)

        return len(image_urls), image_urls
    except:
        return 0, []

# Streamlit UI
st.title("Jumia Product Image Extractor")

uploaded_file = st.file_uploader("Upload Excel file with a column named 'link'", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if "link" not in df.columns:
        st.error("Excel file must have a column named 'link'")
    else:
        result_data = []
        max_images = 0

        st.info("Processing links... please wait")
        progress = st.progress(0)

        for i, row in df.iterrows():
            link = row["link"]
            count, images = get_jumia_images(link)
            max_images = max(max_images, len(images))
            result_data.append([link, count] + images)
            progress.progress((i + 1) / len(df))

        # Create dynamic column names
        columns = ["link", "Number of Images"] + [f"Image {i+1}" for i in range(max_images)]
        result_df = pd.DataFrame(result_data, columns=columns)

        st.dataframe(result_df)

        # Download option
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            result_df.to_excel(writer, index=False)
        st.download_button("Download Results", data=output.getvalue(), file_name="jumia_images.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
