import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
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

# Function to get Jumia product link from SKU
def get_jumia_link(sku, domain):
    try:
        search_url = f"https://{domain}/catalog/?q={sku}"
        scraper = cloudscraper.create_scraper()
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

# App UI
st.title("Jumia SKU to Product Link Finder")

# Country selector
country = st.selectbox("Select Jumia Country", list(JUMIA_DOMAINS.keys()))
domain = JUMIA_DOMAINS[country]

# Option 1: Manual SKU input
sku_input = st.text_input("Enter a SKU to search for:")
if st.button("Find Link") and sku_input:
    with st.spinner(f"Searching on {country}..."):
        link = get_jumia_link(sku_input, domain)
    st.write(f"**Result:** {link}")

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
        df["Link"] = ""  # Create an empty column for links
        progress_bar = st.progress(0)
        result_table = st.empty()

        for idx, sku in enumerate(df["SKU"]):
            df.at[idx, "Link"] = get_jumia_link(sku, domain)
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
