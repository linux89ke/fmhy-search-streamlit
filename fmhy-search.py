# app.py
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from io import BytesIO
from urllib.parse import urlparse

st.set_page_config(page_title="Jumia Image Extractor", layout="wide")

# -------------------------
# Helper: extract images from HTML (regex + img tags)
# -------------------------
def extract_image_urls_from_html(html):
    urls = set()

    # 1) find absolute URLs ending with common image extensions (jpg|jpeg|png|webp)
    pattern = r'(https?://[^\s\'"<>]+?\.(?:png|jpg|jpeg|webp)(?:\?[^\s\'"<>]*)?)'
    for m in re.findall(pattern, html, flags=re.IGNORECASE):
        urls.add(m.split('?')[0])

    # 2) protocol-relative (//...)
    proto_pattern = r'//[^\s\'"<>]+\.(?:png|jpg|jpeg|webp)(?:\?[^\s\'"<>]*)?'
    for m in re.findall(proto_pattern, html, flags=re.IGNORECASE):
        urls.add(('https:' + m).split('?')[0])

    # 3) parse <img> tags for data-src / src / data-original etc.
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        for attr in ("data-src", "data-original", "src", "data-lazy", "data-image"):
            src = img.get(attr)
            if not src:
                continue
            if src.startswith("//"):
                src = "https:" + src
            if src.startswith("http"):
                urls.add(src.split('?')[0])

    # 4) filter out small assets / logos / svgs / placeholders
    bad_tokens = [
        "logo", "icon", "sprite", "favicon", "facebook", "twitter",
        "apple-touch", "placeholder", "blank.gif", "spacer", ".svg", "data:image"
    ]
    filtered = [u for u in urls if not any(bt in u.lower() for bt in bad_tokens)]

    # optional: prefer product-like hosts (but don't limit strictly)
    # final unique sorted list
    images = sorted(filtered)
    return images

# -------------------------
# Get images (requests or optional JS render)
# -------------------------
def get_product_images(url, session=None, render_js=False):
    """
    Returns (count, [image_urls...])
    If render_js=True it will attempt to use Playwright to render JS (optional; see instructions).
    """
    if session is None:
        session = requests.Session()

    try:
        if not render_js:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            r = session.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return 0, []
            html = r.text
        else:
            # Playwright/render fallback (optional). Only run if Playwright is installed.
            try:
                from playwright.sync_api import sync_playwright
            except Exception:
                # Playwright not installed
                return 0, []
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
                page = browser.new_page()
                page.goto(url, timeout=30000)
                html = page.content()
                browser.close()

        images = extract_image_urls_from_html(html)

        # Extra heuristic: keep images hosted on common CDN domains OR containing 'product' or 'uploads' or 'cms'
        good_images = []
        for u in images:
            parsed = urlparse(u)
            netloc = parsed.netloc.lower()
            path = parsed.path.lower()
            if (("jumia" in netloc) or ("akamaized" in netloc) or ("cloudfront" in netloc)
                or ("amazonaws" in netloc) or ("cdn" in netloc) or
                any(k in path for k in ["/product", "/products", "/uploads", "/images", "/media", "/cms"])):
                good_images.append(u)
            else:
                # keep it anyway (some product images sit on other hosts)
                good_images.append(u)

        # remove duplicates while preserving order
        seen = set()
        final = []
        for u in good_images:
            if u not in seen:
                seen.add(u)
                final.append(u)

        return len(final), final

    except Exception as e:
        # In production you might log this
        return 0, []

# -------------------------
# Streamlit UI
# -------------------------
st.title("Jumia product image extractor")
st.markdown("""
Upload an Excel or CSV with a column containing product URLs (default column name = `link`).
The app returns `image_count` (placed right after the link) and `image_1 .. image_N` columns, plus an Excel download.
""")

col1, col2 = st.columns([3,1])
with col1:
    uploaded = st.file_uploader("Upload Excel (.xlsx/.xls) or CSV", type=["xlsx","xls","csv"])
with col2:
    use_js = st.checkbox("Enable JS rendering (slower, requires Playwright)", value=False)

if uploaded:
    if uploaded.name.lower().endswith((".xls", ".xlsx")):
        df_in = pd.read_excel(uploaded)
    else:
        df_in = pd.read_csv(uploaded)

    # let user choose which column has URLs (flexible naming)
    st.write("Columns detected:", list(df_in.columns))
    url_col = st.selectbox("Select the column that contains product URLs", options=list(df_in.columns), index=0)

    if st.button("Start processing"):
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

        results = []
        max_imgs = 0
        pb = st.progress(0)
        status = st.empty()

        for idx, row in df_in.iterrows():
            url = str(row[url_col]).strip()
            status.text(f"Processing {idx+1}/{len(df_in)}: {url}")
            count, links = get_product_images(url, session=session, render_js=use_js)
            r = {"link": url, "image_count": count}
            for i, l in enumerate(links, start=1):
                r[f"image_{i}"] = l
            results.append(r)
            max_imgs = max(max_imgs, count)
            pb.progress((idx+1)/len(df_in))

        result_df = pd.DataFrame(results)

        # Ensure image columns exist up to max_imgs
        for i in range(1, max_imgs+1):
            colname = f"image_{i}"
            if colname not in result_df.columns:
                result_df[colname] = None

        ordered = ["link", "image_count"] + [f"image_{i}" for i in range(1, max_imgs+1)]
        result_df = result_df[ordered]

        st.success("Done — results below")
        st.dataframe(result_df, use_container_width=True)

        # download button
        out = BytesIO()
        with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
            result_df.to_excel(writer, index=False)
        st.download_button("Download results (xlsx)", data=out.getvalue(),
                           file_name="jumia_images_results.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
