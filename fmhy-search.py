import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
import json
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

scraper = cloudscraper.create_scraper(
    browser={
        'custom': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                  ' Chrome/115.0.0.0 Safari/537.36'
    }
)

def get_jumia_link(sku, domain):
    """Searches for an SKU and returns the first product link found."""
    try:
        search_url = f"https://{domain}/catalog/?q={sku}"
        response = scraper.get(search_url, timeout=15)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, "html.parser")
        product_tag = soup.find("a", {"class": "core"})
        if product_tag and product_tag.get("href"):
            return f"https://{domain}{product_tag['href']}"
        return "NONE"
    except Exception as e:
        st.warning(f"Error finding link for SKU '{sku}': {e}")
        return "NONE"

def get_main_product_images(product_url):
    """Extracts main product image URLs from a product page."""
    if product_url == "NONE":
        return []

    images = []
    try:
        response = scraper.get(product_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # --- RECTIFIED METHOD 1: Target the specific JSON-LD structure ---
        # This is now the primary, more precise method.
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        for script in scripts:
            try:
                # Use .string to avoid navigating complex tags
                if not script.string:
                    continue
                data = json.loads(script.string)
                # Directly access the confirmed path from your snippet
                # Use .get() to avoid errors if a key is missing
                images = data.get('mainEntity', {}).get('image', {}).get('contentUrl', [])
                if images and isinstance(images, list):
                    # Found them! Return the list immediately.
                    return list(set(images))
            except (json.JSONDecodeError, KeyError):
                # Ignore errors in this script tag and try the next one
                continue

        # --- METHOD 2: Fallback to finding <img> tags if Method 1 fails ---
        # This part runs only if the JSON-LD method did not find any images.
        image_tags = soup.select('div.-pvs.a-p-v-fl.row a > img')
        for tag in image_tags:
            # Prioritize 'data-src' for lazy-loaded images, then fall back to 'src'
            img_url = tag.get('data-src') or tag.get('src')
            if img_url:
                images.append(img_url)
        
        return list(set(images))  # Use set to remove duplicates

    except Exception as e:
        st.warning(f"Could not fetch images from {product_url}: {e}")
        return []

# --- Streamlit UI (No changes needed here) ---
st.set_page_config(layout="wide")
st.title("Jumia SKU Link & Main Product Images Finder 🔎")

country = st.selectbox("Select Country", list(JUMIA_DOMAINS.keys()))
domain = JUMIA_DOMAINS[country]

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.header("Single SKU Search")
    sku_input = st.text_input("Enter a SKU to search for:")
    if st.button("Find Link & Images") and sku_input:
        with st.spinner(f"Searching for **{sku_input}** on Jumia {country}..."):
            link = get_jumia_link(sku_input, domain)
            images = get_main_product_images(link)
        st.success("Search complete!")
        st.write(f"**Product Link:** {link}")
        st.write(f"**Images Found:** {len(images)}")
        
        if images:
            st.image(images, width=110, caption=[f"Image {i+1}" for i in range(len(images))])

with col2:
    st.header("Bulk SKU Upload")
    uploaded_file = st.file_uploader("Upload Excel or CSV file with a 'SKU' column", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    if "SKU" not in df.columns:
        st.error("Uploaded file must have a column named 'SKU'. Please correct the file and re-upload.")
    else:
        st.info(f"Found {len(df)} SKUs to process. This may take a few minutes.")
        df["Link"] = ""
        df["Image Count"] = 0

        max_images_found = 0
        progress_bar = st.progress(0)
        result_table = st.empty()
        all_images = []

        total_skus = len(df)
        for idx, row in df.iterrows():
            sku = str(row["SKU"]).strip() # Ensure SKU is a string and remove whitespace
            link = get_jumia_link(sku, domain)
            df.at[idx, "Link"] = link

            images = get_main_product_images(link)
            img_count = len(images)
            df.at[idx, "Image Count"] = img_count

            all_images.append(images)
            if img_count > max_images_found:
                max_images_found = img_count
            
            progress_bar.progress((idx + 1) / total_skus, text=f"Processing '{sku}' ({idx+1}/{total_skus})")
            result_table.dataframe(df)
            time.sleep(0.3) # Politeness delay to avoid overwhelming the server

        for i in range(max_images_found):
            col_name = f"Image {i+1}"
            df[col_name] = [imgs[i] if i < len(imgs) else "" for imgs in all_images]

        st.success("✅ Processing complete!")
        st.dataframe(df)

        # --- Download Buttons ---
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Results as CSV",
            data=csv,
            file_name=f"jumia_results_{country.lower()}.csv",
            mime="text/csv",
        )

        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Jumia Results")
        st.download_button(
            label="⬇️ Download Results as Excel",
            data=output.getvalue(),
            file_name=f"jumia_results_{country.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
```
