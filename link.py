import streamlit as st
import requests
import pandas as pd
import xml.etree.ElementTree as ET
import re
from urllib.parse import urlparse,urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import concurrent.futures
import time

def link():
    st.header("URL Extractor", divider='rainbow')
    with st.container():
        st.write("""
        *   **URL Extractor Using Sitemap**: This feature allows you to extract URLs from a website's sitemap.
    """)

    def detect_url_language(url):
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        hostname = parsed_url.hostname.lower() if parsed_url.hostname else ''

        # Country-specific TLD mapping
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
        }

        specific_domain_patterns = {
            'zh': [r'teamviewer\.cn', r'teamviewer\.com\.cn'],
            'ja': [r'teamviewer\.com/ja'],
            'it': [r'teamviewer\.com/it'],
            'es': [r'teamviewer\.com/latam']
        }

        # First check specific domain patterns
        for lang, patterns in specific_domain_patterns.items():
            if any(re.search(pattern, url, re.IGNORECASE) for pattern in patterns):
                return lang

        # Check TLD
        for domain_suffix, lang in country_lang_map.items():
            if hostname.endswith(domain_suffix):
                return lang

        # Check language patterns with word boundaries
        path_parts = path.split('/')
        for lang, patterns in language_patterns.items():
            for pattern in patterns:
                clean_pattern = pattern.strip('/')
                if clean_pattern in path_parts:
                    return lang

        # Check query parameters for language
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

    def fetch_sitemap(sitemap_url: str, base_url: str) -> List[str]:
        try:
            response = requests.get(sitemap_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            if response.status_code == 200:
                sitemap_urls = parse_sitemap_index(response.text, base_url)
                if not sitemap_urls:
                    sitemap_urls = parse_sitemap(response.text)
                return sitemap_urls
        except requests.exceptions.RequestException as e:
            st.warning(f"Error accessing {sitemap_url}: {e}")
        return []

    def fetch_sitemap_urls(website_url: str) -> List[str]:
        sitemap_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-1.xml", "/sitemaps/sitemap.xml", "/sitemaps/sitemap_index.xml"]
        base_url = website_url.rstrip('/')
        all_urls = []

        # Create a thread pool for parallel sitemap fetching
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {
                executor.submit(fetch_sitemap, base_url + path, base_url): path
                for path in sitemap_paths
            }

            for future in as_completed(future_to_url):
                urls = future.result()
                if urls:
                    all_urls.extend(urls)

        return list(set(all_urls))  # Remove duplicates

    def process_url_batch(urls: List[str]) -> List[Dict]:
        results = []
        for url in urls:
            url_lang = detect_url_language(url)
            results.append({
                'source_url': url,
                'Language': url_lang
            })
        return results

    def parse_sitemap_index(sitemap_content: str, base_url: str) -> List[str]:
        """Recursively processes sitemap indexes and nested sitemaps"""
        all_urls = []
        try:
            root = ET.fromstring(sitemap_content)
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # Check if this is a sitemap index
            sitemap_locs = root.findall('.//ns:sitemap/ns:loc', namespaces)
            if sitemap_locs:
                with ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_url = {}
                    for loc in sitemap_locs:
                        nested_sitemap_url = urljoin(base_url, loc.text)
                        future = executor.submit(requests.get, nested_sitemap_url,
                                            timeout=15,
                                            headers={'User-Agent': 'Mozilla/5.0...'})
                        future_to_url[future] = nested_sitemap_url

                    for future in as_completed(future_to_url):
                        try:
                            response = future.result()
                            if response.status_code == 200:
                                # Recursive call to handle nested indexes
                                nested_urls = parse_sitemap_index(response.text, base_url) or parse_sitemap(response.text)
                                all_urls.extend(nested_urls)
                        except Exception as e:
                            st.warning(f"Error processing {future_to_url[future]}: {e}")
            else:
                # Process regular sitemap
                all_urls.extend(parse_sitemap(sitemap_content))
                
        except ET.ParseError as e:
            st.warning(f"XML Parse Error: {e}")
        return all_urls

    def parse_sitemap(sitemap_content: str) -> List[str]:
        """Improved sitemap parser with namespace-agnostic search"""
        urls = []
        try:
            root = ET.fromstring(sitemap_content)
            # Namespace-agnostic search for <loc> tags
            for elem in root.iter():
                if 'loc' in elem.tag:
                    url = elem.text.strip()
                    urls.append(url)
        except ET.ParseError:
            try:  # Fallback to text parsing for malformed XML
                urls = re.findall(r'<loc>(.*?)</loc>', sitemap_content)
            except:
                pass
        return list(set(urls))  # Remove duplicates

    # Streamlit UI setup
    st.write("Enter a website URL to fetch sitemap URLs.")
    website_url = st.text_input("Website URL", placeholder="https://www.example.com")

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

    if st.button("Extract URLs", key="extract_links") and website_url:
        if not website_url.startswith("http"):
            st.error("Please enter a valid URL starting with http or https.")
        else:
            if not st.session_state.all_urls:
                start_time = time.time() 
                with st.spinner("Fetching sitemap..."):
                    st.session_state.all_urls = fetch_sitemap_urls(website_url)
                    if st.session_state.all_urls:
                        st.success(f"Found {len(st.session_state.all_urls)} total URLs.")
                        progress_bar = st.progress(0)

                        # Process URLs in parallel batches
                        batch_size = 50  # Adjust based on your needs
                        url_batches = [st.session_state.all_urls[i:i + batch_size]
                                     for i in range(0, len(st.session_state.all_urls), batch_size)]

                        st.session_state.language_results = []
                        with ThreadPoolExecutor(max_workers=10) as executor:
                            future_to_batch = {
                                executor.submit(process_url_batch, batch): i
                                for i, batch in enumerate(url_batches)
                            }

                            completed = 0
                            total_batches = len(url_batches)

                            for future in as_completed(future_to_batch):
                                batch_results = future.result()
                                st.session_state.language_results.extend(batch_results)
                                completed += 1
                                progress_bar.progress(int((completed / total_batches) * 100))

                        progress_bar.empty()
                        st.session_state.lang_df = pd.DataFrame(st.session_state.language_results)
                    else:
                        st.error("No sitemap or URLs found.")

                end_time = time.time()  # Record end time
                elapsed_time = end_time - start_time
                st.success(f"Elapsed time: {elapsed_time:.2f} seconds")

    if st.session_state.lang_df is not None:
        st.dataframe(st.session_state.lang_df)
        unique_languages = st.session_state.lang_df['Language'].dropna().unique().tolist()
        selected_languages = st.multiselect(
            "Select languages to keep:",
            unique_languages,
            default=unique_languages,
            key='language_selector')

        filtered_df = st.session_state.lang_df[st.session_state.lang_df['Language'].isin(selected_languages)]

        st.session_state.filtered_df = filtered_df
        st.success(f"Found {len(filtered_df)} URLs in selected languages.")
        st.dataframe(filtered_df)

        filtered_urls = filtered_df[['source_url']].rename(columns={'source_url': 'source_url'})
        csv_data = filtered_urls.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Filtered URLs",
            data=csv_data,
            file_name="filtered_urls.csv",
            mime="text/csv"
        )
        
        