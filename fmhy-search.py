import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
import json
import re
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

scraper = cloudscraper.create_scraper()

# Function to get Jumia product link from SKU
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

# New improved function to count product images
def get_image_count(product_url):
    if product_url == "NONE":
        return 0
    try:
        response = scraper.get(product_url)
        if response.status_code != 200:
            return 0

        soup = BeautifulSoup(response.text, "html.parser")

        # Try to find <script type="application/ld+json"> containing images
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and "image" in data:
                    images = data["image"]
                    if isinstance(images, list):
                        return len(images)
                    elif isinstance(images, str):
                        return 1
            except:
                continue

        # Fallback: regex search for jumia.is jpg URLs in page text
        matches = re.findall(r'https://\w+\.jumia\.is/.+?\.jpg', response.text)
        unique_imgs = set(matches)
        return len(unique_imgs)
    except:
        return 0

# App UI
st.title("Product Link and Image Count Finder")

# Country selector
country = st.selectbox("Select Country", list(JUMIA_DOMAINS.keys()))
domain = JUMIA_DOMAINS[country]

# Option 1: Manual SKU input
sku_input = st.text_input("Enter a SKU to search for:")
if st.button("Find Link") and sku_input:
    with st.spinner(f"Searching on {country}..."):
        link = get_jumia_link(sku_input, domain)
        img_count = get_image_count(link)
    st.write(f"**Result:** {link}")
    st.write(f"**Number of product images:** {img_count}")

# Option 2: File upload
uploaded_file = st.file_uploader("Upload Excel or CSV file with SKUs", type=["xlsx", "csv"])

if uploaded_file:
    # Read file
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    if "SKU" not in df.columns:
        st.error("Uploaded file must have a column named 'SKU'.")
    else:
        df["Link"] = ""          # Create an empty column for links
        df["Image Count"] = 0    # New column for image counts

        progress_bar = st.progress(0)
        result_table = st.empty()

        for idx, sku in enumerate(df["SKU"]):
            link = get_jumia_link(sku, domain)
            df.at[idx, "Link"] = link

            img_count = get_image_count(link)
            df.at[idx, "Image Count"] = img_count

            progress = (idx + 1) / len(df)
            progress_bar.progress(progress)
            result_table.dataframe(df)  # Update table live
            time.sleep(0.2)  # Small delay to visualize progress

        st.success("Processing complete!")
        st.dataframe(df)

        # CSV download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name=f"jumia_links_{country.lower()}.csv",
            mime="text/csv",
        )

        # XLSX download
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Links")
        st.download_button(
            label="Download Results as Excel",
            data=output.getvalue(),
            file_name=f"jumia_links_{country.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
