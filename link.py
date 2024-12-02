import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
from urllib.parse import urlparse


def link():
    st.header("URL Extractor",divider='rainbow')
    with st.container():
        st.write("""
        This app is designed to help extract URLs from a given website or sitemap. It provides two main functionalities:
        *   **URL Extractor Using Sitemap**: This feature allows you to extract URLs from a website's sitemap.
        *   **URL Extractor**: This feature enables you to extract URLs from a specific webpage.
    """)
    
    tab1, tab2 = st.tabs([ "URL Extractor Using Sitemap","URL Extractor"])
    with tab1:
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
                
                # Country-specific TLDs for European languages
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
                # Major languages with more specific markers
                'en': ['/en','/en/', '/en-', 'english', '/us/', '/uk/', '/au/', '/international/'],
                'it': ['/it','/it/', '/it-', 'italiano', 'italian', '/ch/', '/teamviewer.com/it/'],
                'es': ['/es','/es/', '/es-', 'espanol', 'spanish','/mx/', '/cl/', '/co/', '/latam/','teamviewer.com/latam/','https://www.teamviewer.com/latam/'],
                'fr': ['/fr','/fr/', '/fr-', 'french', '/ca/', '/ch/', '/be/'],
                'de': ['/de','/de/', '/de-', 'deutsch', 'german', '/at/', '/ch/'],
                'pt': ['/pt','/pt/', '/pt-', 'portuguese', '/br/', '/pt/', '/ao/'],
                'ru': ['/ru','/ru/', '/ru-', 'russian', '/by/', '/kz/'],
                'nl': ['/nl','/nl/', '/nl-', 'dutch', '/netherlands/'],
                'tw': ['/tw','/tw/', '/tw-', 'taiwanese', '/taiwan/'],
                'vi': ['/vi','/vi/', '/vi-', 'vietnamese'],
                'pl': ['/pl','/pl/', '/pl-', 'polish'],
                'hu': ['/hu','/hu/', '/hu-', 'hungarian'],
                'tr': ['/tr','/tr/', '/tr-', 'turkish'],
                'th': ['/th','/th/', '/th-', 'thai'],
                'cs': ['/cs','/cs/', '/cs-', 'czech'],
                'el': ['/el','/el/','/el-','greek'],
                
                # Asian languages with more specific detection
                'ja': ['/ja','/ja/', '/ja-', 'japanese', '/jp/', '/teamviewer.com/ja/'],
                'zh': ['/zh','/zh/', '/zh-', '/zhs/','chinese','/cn/', '/hk/', '/tw/','/teamviewer.cn/', '/teamviewer.com.cn/','/zh-cn/', '/zh-tw/', '/zh-hk/','/zht/','/anydesk.com/zhs/'],
                'ko': ['/ko','/ko/', '/ko-', 'korean', '/kr/'],
                'ar': ['/ar','/ar/', '/ar-', 'arabic', '/sa/', '/ae/']}
            
            for domain_suffix, lang in country_lang_map.items():
                if hostname.endswith(domain_suffix):
                    return lang
            
            for lang, patterns in language_patterns.items():
                if f'.{lang}.' in hostname or f'/{lang}/' in path or f'/{lang}-' in path:
                    return lang
            
            for lang, patterns in language_patterns.items():
                if any(pattern in hostname or pattern in path for pattern in patterns):
                    return lang
            
            if parsed_url.query:
                for lang in language_patterns.keys():
                    if re.search(fr'lang[=_]({lang}|{lang.upper()})', parsed_url.query, re.IGNORECASE):
                        return lang

            teamviewer_lang_map = {'it': ['teamviewer.com/it/'],'ja': ['teamviewer.com/ja/'],'zh': ['teamviewer.cn/', 'teamviewer.com.cn/', '/cn/','/anydesk.com/zhs/solutions/'],'es': ['teamviewer.com/latam/']}
            
            for lang, patterns in teamviewer_lang_map.items():
                if any(pattern in url for pattern in patterns):
                    return lang
            
            additional_lang_patterns = {'it': r'/it[\-_/]','ja': r'/ja[\-_/]','zh': r'/zh[\-_/]|/cn[\-_/]','ko': r'/ko[\-_/]',
            'es': r'/es[\-_/]|/latam[\-_/]|/distribucion-de-licencias-tensor'}
            
            for lang, pattern in additional_lang_patterns.items():
                if re.search(pattern, url, re.IGNORECASE):
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
                root = ET.fromstring(sitemap_content)
                namespaces = {'sitemaps': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                sitemap_locs = root.findall('.//sitemaps:loc', namespaces)
                
                for loc in sitemap_locs:
                    nested_sitemap_url = loc.text
                    if not nested_sitemap_url.startswith('http'):
                        nested_sitemap_url = base_url + (nested_sitemap_url if nested_sitemap_url.startswith('/') else f'/{nested_sitemap_url}')
                
                    try:
                        nested_response = requests.get(nested_sitemap_url, timeout=10, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
                        if nested_response.status_code == 200:
                            nested_urls = parse_sitemap(nested_response.text)
                            all_urls.extend(nested_urls)
                    except requests.exceptions.RequestException as e:
                        st.warning(f"Error accessing nested sitemap {nested_sitemap_url}: {e}")
            except ET.ParseError:
                pass
            return all_urls

        def parse_sitemap(sitemap_content):
            urls = []
            try:
                root = ET.fromstring(sitemap_content)
                namespaces = {'sitemaps': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                location_tags = [".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc",
                    ".//sitemaps:loc"]
                
                for tag in location_tags:
                    elements = root.findall(tag, namespaces)
                    if elements:
                        urls = [element.text for element in elements]
                        break
            
            except ET.ParseError:
                pass
            return urls
        
        # st.subheader("Sitemap URL Fetcher")
        st.write("Enter a website URL to fetch sitemap URLs.")
        website_url = st.text_input("Website URL (e.g., https://example.com):", "")

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

        if website_url:
            if not website_url.startswith("http"):
                st.error("Please enter a valid URL starting with http or https.")
            else:
                if not st.session_state.all_urls:
                    with st.spinner("Fetching sitemap..."):
                        st.session_state.all_urls = fetch_sitemap_urls(website_url)
                        if st.session_state.all_urls:
                            st.success(f"Found {len(st.session_state.all_urls)} total URLs.")
                            progress_bar = st.progress(0)
                            st.session_state.language_results = []
                            
                            for i, url in enumerate(st.session_state.all_urls):
                                progress_bar.progress(int((i + 1) / len(st.session_state.all_urls) * 100))
                                url_lang = detect_url_language(url)
                                st.session_state.language_results.append({
                                    'URL': url,
                                    'Language': url_lang})
                            progress_bar.empty()
                            st.session_state.lang_df = pd.DataFrame(st.session_state.language_results)
                        else:
                            st.error("No sitemap or URLs found.")
                            
                if st.session_state.lang_df is not None:
                    st.dataframe(st.session_state.lang_df)
                    unique_languages = st.session_state.lang_df['Language'].dropna().unique().tolist()
                    selected_languages = st.multiselect(
                        "Select languages to keep:", 
                        unique_languages, 
                        default=unique_languages,
                        key='language_selector')
                    filtered_df = st.session_state.lang_df[st.session_state.lang_df['Language'].isin(selected_languages)]
                    st.success(f"Found {len(filtered_df)} URLs in selected languages.")
                    st.dataframe(filtered_df)
                    
                    filtered_urls = filtered_df[['URL']].rename(columns={'URL': 'source_url'})
                    csv_data = filtered_urls.to_csv(index=False).encode('utf-8')
                    st.download_button(label="Download Filtered URLs",data=csv_data,file_name="filtered_urls.csv",mime="text/csv")
                
    with tab2:
        def extract_links(url):
            try:
                response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    links = []
                    for a_tag in soup.find_all('a', href=True):
                        full_url = urljoin(url, a_tag['href'])
                        links.append(full_url)
                    return links
                else:
                    st.error(f"Error: Received status code {response.status_code}")
                    return []

            except requests.exceptions.RequestException as e:
                st.error(f"Error: Unable to fetch the URL. {e}")
                return []

        # st.subheader("URL Extractor")
        st.write("Enter a webpage URL to extract all the links from it.")
        page_url = st.text_input("Enter the URL (e.g., https://pages.ebay.com/sitemap.html):", "")

        if st.button("Extract Links"):
            if page_url:
                if not page_url.startswith("http"):
                    st.error("Please enter a valid URL starting with http or https.")
                else:
                    with st.spinner("Extracting links..."):
                        links = extract_links(page_url)

                        if links:
                            st.success(f"Found {len(links)} links.")
                            st.dataframe(pd.DataFrame(links, columns=["Links"]))
                            csv_data = pd.DataFrame(links, columns=["Links"]).to_csv(index=False).encode('utf-8')
                            st.download_button("Download Links as CSV", data=csv_data, file_name="extracted_links.csv", mime="text/csv")
                        else:
                            st.warning("No links found on the provided webpage.")
            else:
                st.error("Please enter a URL.")