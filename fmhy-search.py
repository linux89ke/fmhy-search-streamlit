import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
import json
import time
from io import BytesIO

# Jumia domains map
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

sku_input = st.text_input("Enter a SKU to search for:")
if st.button("Find Link") and sku_input:
    with st.spinner(f"Searching on {country}..."):
        link = get_jumia_link(sku_input, domain)
        images = get_main_product_images_ldjson(link)
    st.write(f"**Result:** {link}")
    st.write(f"**Number of main product images:** {len(images)}")
    for i, img_url in enumerate(images, start=1):
        st.image(img_url, width=150, caption=f"Image {i}")

uploaded_file = st.file_uploader("Upload Excel or CSV file with SKUs", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    if "SKU" not in df.columns:
        st.error("Uploaded file must have a column named 'SKU'.")
    else:
        df["Link"] = ""
        df["Image Count"] = 0

        max_images_found = 0
        progress_bar = st.progress(0)
        result_table = st.empty()

        all_images = []

        for idx, sku in enumerate(df["SKU"]):
            link = get_jumia_link(sku, domain)
            df.at[idx, "Link"] = link

            images = get_main_product_images_ldjson(link)
            img_count = len(images)
            df.at[idx, "Image Count"] = img_count

            all_images.append(images)
            if img_count > max_images_found:
                max_images_found = img_count

            progress_bar.progress((idx + 1) / len(df))
            result_table.dataframe(df)
            time.sleep(0.2)

        # Add columns Image 1 .. Image N
        for i in range(max_images_found):
            col_name = f"Image {i+1}"
            df[col_name] = [imgs[i] if i < len(imgs) else "" for imgs in all_images]

        st.success("Processing complete!")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name=f"jumia_links_images_{country.lower()}.csv",
            mime="text/csv",
        )

        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="LinksAndImages")
        st.download_button(
            label="Download Results as Excel",
            data=output.getvalue(),
            file_name=f"jumia_links_images_{country.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
