import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import xml.etree.ElementTree as ET
import re
from urllib.parse import urlparse

def link():
    st.markdown("""
        <style>
            .stDownloadButton, .stButton>button {
                width: 100%;
                justify-content: center;
                transition: all 0.3s ease;
            }
            .stDownloadButton>button, .stButton>button {
                background-color: #4CAF50 !important;
                color: white !important;
                border: none !important;
            }
            .stDownloadButton>button:hover, .stButton>button:hover {
                background-color: #45a049 !important;
                transform: scale(1.05);
            }
            .stTextInput>div>div>input {
                border: 2px solid #4CAF50 !important;
                border-radius: 5px !important;
            }
            .stProgress > div > div > div {
                background-color: #4CAF50 !important;
            }
            .stMarkdown {
                margin-bottom: 1rem !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.header("🌐 URL Extractor", divider='rainbow')
    
    # Main functionality container
    with st.container():
        st.markdown("""
        **How to use:**
        1. Enter a website URL below (e.g., `https://example.com`)
        2. Click 'Extract URLs' to find sitemap content
        3. Filter results by detected languages/categories
        4. Download your filtered results as CSV
        """)

        website_url = st.text_input(
            "**Enter Website URL:**",
            placeholder="https://example.com",
            help="Please include http:// or https://",
            key="url_input"
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            extract_clicked = st.button(
                "✨ Extract URLs", 
                key="extract_links",
                help="Start scanning for sitemaps and URLs",
                disabled=not website_url
            )

        # Session state management
        if 'previous_url' not in st.session_state:
            st.session_state.previous_url = ""
        if 'all_urls' not in st.session_state:
            st.session_state.all_urls = []
        if 'language_results' not in st.session_state:
            st.session_state.language_results = []
        if 'lang_df' not in st.session_state:
            st.session_state.lang_df = None

        if website_url and website_url != st.session_state.previous_url:
            st.session_state.all_urls = []
            st.session_state.language_results = []
            st.session_state.lang_df = None
            st.session_state.previous_url = website_url

        if extract_clicked and website_url:
            if not website_url.startswith("http"):
                st.error("❌ Please enter a valid URL starting with http or https.")
            else:
                if not st.session_state.all_urls:
                    with st.spinner("🔍 Scanning website for sitemaps..."):
                        st.session_state.all_urls = fetch_sitemap_urls(website_url)
                        if st.session_state.all_urls:
                            st.success(f"✅ Found {len(st.session_state.all_urls)} total URLs!")
                            progress_bar = st.progress(0)
                            st.session_state.language_results = []
                            
                            for i, url in enumerate(st.session_state.all_urls):
                                progress_bar.progress(int((i + 1) / len(st.session_state.all_urls) * 100))
                                url_lang = detect_url_language(url)
                                st.session_state.language_results.append({
                                    'source_url': url,
                                    'Language/Category': url_lang})
                            
                            progress_bar.empty()
                            st.session_state.lang_df = pd.DataFrame(st.session_state.language_results)
                        else:
                            st.error("⚠️ No sitemap or URLs found. Please check the website URL.")

        if st.session_state.lang_df is not None:
            st.markdown("---")
            st.subheader("📊 Results Overview")
            
            with st.expander("🔍 View Raw Data", expanded=True):
                st.dataframe(
                    st.session_state.lang_df,
                    use_container_width=True,
                    height=300
                )

            unique_languages = st.session_state.lang_df['Language/Category'].dropna().unique().tolist()
            selected_languages = st.multiselect(
                "**Filter by Detected Languages/Categories:**",
                unique_languages, 
                default=unique_languages,
                help="Select which language/category to keep",
                key='language_selector'
            )

            filtered_df = st.session_state.lang_df[st.session_state.lang_df['Language/Category'].isin(selected_languages)]
            st.session_state.filtered_df = filtered_df

            st.success(f"**✅ Found {len(filtered_df)} URLs matching selected languages/categories!**")
            
            with st.expander("📑 Preview Filtered Results"):
                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    height=250
                )

            st.markdown("---")
            st.subheader("💾 Download Results")
            csv_data = filtered_df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Download Filtered URLs as CSV",
                data=csv_data,
                file_name="filtered_urls.csv",
                mime="text/csv",
                help="Download the filtered URL list in CSV format"
            )

def detect_url_language(url):
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    hostname = parsed_url.hostname.lower() if parsed_url.hostname else ''

    country_lang_map = {
        '.cn': 'zh',    # China
        '.jp': 'ja',    # Japan
        '.kr': 'ko',    # Korea
        '.tw': 'zh',    # Taiwan
        '.hk': 'zh',    # Hong Kong
        '.it': 'it',    # Italy
        '.es': 'es',    # Spain
        '.fr': 'fr',    # France
        '.de': 'de',    # Germany
        '.pt': 'pt',    # Portugal
        '.nl': 'nl',    # Netherlands
        '.pl': 'pl',    # Poland
        '.se': 'sv',    # Sweden
        '.no': 'no',    # Norway
        '.fi': 'fi',    # Finland
        '.dk': 'da',    # Denmark
        '.cz': 'cs',    # Czech Republic
        '.hu': 'hu',    # Hungary
        '.ro': 'ro',    # Romania
        '.hr': 'hr',    # Croatia
        '.rs': 'sr',    # Serbia
        '.bg': 'bg',    # Bulgaria
        '.sk': 'sk',    # Slovakia
        '.si': 'sl'     # Slovenia
    }

    language_patterns = {
        'en': [r'/en/', r'/en-', r'/english/', r'/us/', r'/uk/', r'/au/', r'/international/'],
        'it': [r'/it/', r'/it-', r'/italiano/', r'/italian/', r'/ch/'],
        'es': [r'/es/', r'/es-', r'/espanol/', r'/spanish/', r'/mx/', r'/cl/', r'/co/', r'/latam/'],
        'fr': [r'/fr/', r'/fr-', r'/french/', r'/ca/', r'/ch/', r'/be/'],
        'de': [r'/de/', r'/de-', r'/deutsch/', r'/german/', r'/at/', r'/ch/'],
        'pt': [r'/pt/', r'/pt-', r'/portuguese/', r'/br/', r'/pt/', r'/ao/'],
        'ru': [r'/ru/', r'/ru-', r'/russian/', r'/by/', r'/kz/'],
        'nl': [r'/nl/', r'/nl-', r'/dutch/', r'/netherlands/'],
        'vi': [r'/vi/', r'/vi-', r'/vietnamese/'],
        'pl': [r'/pl/', r'/pl-', r'/polish/'],
        'hu': [r'/hu/', r'/hu-', r'/hungarian/'],
        'tr': [r'/tr/', r'/tr-', r'/turkish/'],
        'th': [r'/th/', r'/th-', r'/thai/'],
        'cs': [r'/cs/', r'/cs-', r'/czech/'],
        'el': [r'/el/', r'/el-', r'/greek/'],
        'ja': [r'/ja/', r'/ja-', r'/japanese/', r'/jp/'],
        'zh': [r'/zh/', r'/zh-', r'/zhs/', r'/chinese/', r'/cn/', r'/hk/', r'/tw/', r'/zh-cn/', r'/zh-tw/', r'/zh-hk/', r'/zht/'],
        'ko': [r'/ko/', r'/ko-', r'/korean/', r'/kr/'],
        'ar': [r'/ar/', r'/ar-', r'/arabic/', r'/sa/', r'/ae/'],
        'blogs': [r'/blogs/',r'/blogs-',r'/en/blogs/',r'/blog/'],
        'corporate': [r'/corporate/',r'/corporate-',r'/en/corporate/',r'/corp/'],
        'how-to': [r'/how-to/',r'/how-to-',r'/en/how-to/',r'/howto/'],
        'products': [r'/products/','/products-'],
        'resources': [r'/resources/','/resources-'],
        'company': [r'/company/','/company-'],
        'partners': [r'/partners/','/partners-'],
        'solutions': [r'/solutions/','/solutions-'],
    }

    specific_domain_patterns = {
        'zh': [r'teamviewer\.cn', r'teamviewer\.com\.cn'],
        'ja': [r'teamviewer\.com/ja'],
        'it': [r'teamviewer\.com/it'],
        'es': [r'teamviewer\.com/latam']
    }

    for lang, patterns in specific_domain_patterns.items():
        if any(re.search(pattern, url, re.IGNORECASE) for pattern in patterns):
            return lang

    for domain_suffix, lang in country_lang_map.items():
        if hostname.endswith(domain_suffix):
            return lang

    path_parts = path.split('/')
    for lang, patterns in language_patterns.items():
        for pattern in patterns:
            clean_pattern = pattern.strip('/')
            if clean_pattern in path_parts:
                return lang

    if parsed_url.query:
        lang_param = re.search(r'(?:^|&)lang=([a-zA-Z]{2})', parsed_url.query)
        if lang_param and lang_param.group(1).lower() in language_patterns:
            return lang_param.group(1).lower()

    product_lang_patterns = {
        'es': [r'/distribucion-de-licencias-tensor'],
        'zh': [r'/anydesk\.com/zhs/solutions/']
    }

    for lang, patterns in product_lang_patterns.items():
        if any(re.search(pattern, url, re.IGNORECASE) for pattern in patterns):
            return lang

    return 'en'

def fetch_sitemap_urls(website_url):
    sitemap_paths = ["/sitemap.xml","/sitemap_index.xml", "/sitemap-1.xml","/sitemaps/sitemap.xml","/sitemaps/sitemap_index.xml"]
    base_url = website_url.rstrip('/')
    all_urls = []

    for path in sitemap_paths:
        sitemap_url = base_url + path
        try:
            response = requests.get(sitemap_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
            if response.status_code == 200:
                sitemap_urls = parse_sitemap_index(response.text, base_url)
                if not sitemap_urls:
                    sitemap_urls = parse_sitemap(response.text)
                all_urls.extend(sitemap_urls)
        except requests.exceptions.RequestException as e:
            st.warning(f"Error accessing {sitemap_url}: {e}")
            continue
    return all_urls

def parse_sitemap_index(sitemap_content, base_url):
    all_urls = []
    try:
        soup = BeautifulSoup(sitemap_content, 'lxml-xml')
        sitemap_tags = soup.find_all('sitemap')
        for sitemap in sitemap_tags:
            loc = sitemap.find('loc')
            if loc:
                nested_sitemap_url = loc.get_text().strip()
                if not nested_sitemap_url.startswith('http'):
                    nested_sitemap_url = urljoin(base_url, nested_sitemap_url)
                try:
                    nested_response = requests.get(nested_sitemap_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
                    if nested_response.status_code == 200:
                        nested_urls = parse_sitemap(nested_response.text)
                        all_urls.extend(nested_urls)
                except requests.exceptions.RequestException as e:
                    st.warning(f"Error accessing nested sitemap {nested_sitemap_url}: {e}")
    except Exception as e:
        st.warning(f"Error parsing sitemap index: {e}")
    return all_urls

def parse_sitemap(sitemap_content):
    urls = []
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg', '.tiff', '.ico'}
    
    try:
        soup = BeautifulSoup(sitemap_content, 'lxml-xml')
        loc_tags = soup.find_all('loc')
        for tag in loc_tags:
            url = tag.get_text().strip()
            if any(url.lower().endswith(ext) for ext in image_extensions):
                continue 
            urls.append(url)
    except Exception as e:
        st.warning(f"Error parsing sitemap: {e}")
    return urls