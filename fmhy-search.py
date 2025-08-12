import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

st.title("Jumia Product Image Extractor")

uploaded_file = st.file_uploader("Upload Excel/CSV with Jumia product links", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    link_column = st.selectbox("Select the column with product links", df.columns)

    results = []

    for link in df[link_column]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
            }
            resp = requests.get(link, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find all images in the product gallery
            images = []
            for img in soup.select("img"):
                src = img.get("data-src") or img.get("src")
                if src and "jumia.co.ke" in src and src.endswith(".jpg"):
                    images.append(src)

            images = list(dict.fromkeys(images))  # Remove duplicates while keeping order

            row = {"Product Link": link, "Image Count": len(images)}
            for i, img_url in enumerate(images, start=1):
                row[f"Image {i}"] = img_url

            results.append(row)

        except Exception as e:
            results.append({"Product Link": link, "Image Count": 0, "Error": str(e)})

    results_df = pd.DataFrame(results)

    st.write("### Results")
    st.dataframe(results_df)

    # Download results
    output_file = "jumia_image_results.xlsx"
    results_df.to_excel(output_file, index=False)
    with open(output_file, "rb") as f:
        st.download_button("Download Results Excel", f, file_name=output_file)
