import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from io import BytesIO

def get_jumia_product_info(search_term, country_code="ke"):
    base_url = f"https://www.jumia.{country_code}/catalog/?q={search_term.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(base_url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"search": search_term, "error": str(e)}

    soup = BeautifulSoup(resp.text, "html.parser")
    product_card = soup.select_one("article.prd")
    if not product_card:
        return {"search": search_term, "error": "No product found"}

    product_link = "https://www.jumia.{}/".format(country_code) + product_card.a.get("href").lstrip("/")
    img_tag = product_card.select_one("img")
    if img_tag and "data-src" in img_tag.attrs:
        img_url = img_tag["data-src"]
    else:
        img_url = img_tag["src"] if img_tag else None

    product_id = None
    if img_url:
        match = re.search(r"/(\d{6,})/", img_url)
        if match:
            product_id = match.group(1)

    return {
        "search": search_term,
        "product_link": product_link,
        "image_url": img_url,
        "product_id": product_id
    }


st.title("Jumia Product Info Extractor")

uploaded_file = st.file_uploader("Upload Excel or CSV file", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    column_name = st.selectbox("Select the column with search terms or URLs", df.columns)

    if st.button("Process"):
        results = []
        progress = st.progress(0)

        for idx, val in enumerate(df[column_name]):
            info = get_jumia_product_info(str(val))
            results.append(info)
            progress.progress((idx + 1) / len(df))

        result_df = pd.DataFrame(results)
        st.dataframe(result_df)

        output = BytesIO()
        result_df.to_excel(output, index=False)
        st.download_button("Download Excel", data=output.getvalue(), file_name="jumia_results.xlsx")
