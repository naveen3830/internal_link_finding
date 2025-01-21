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
        *   **URL Extractor Using Sitemap**: This feature allows you to extract URLs from a website's sitemap.
    """)
    
    # tab1= st.tabs([ "URL Extractor Using Sitemap"])
    # with tab1:
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
            
            # More specific language patterns with word boundaries
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
                'ar': [r'/ar/', r'/ar-', r'/arabic/', r'/sa/', r'/ae/']
            }
            
            # Check domain-specific patterns
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
                    # Remove leading/trailing slashes and create a clean pattern
                    clean_pattern = pattern.strip('/')
                    if clean_pattern in path_parts:
                        return lang
            
            # Check query parameters for language
            if parsed_url.query:
                lang_param = re.search(r'(?:^|&)lang=([a-zA-Z]{2})', parsed_url.query)
                if lang_param and lang_param.group(1).lower() in language_patterns:
                    return lang_param.group(1).lower()
            
            # Additional checks for specific product paths
            product_lang_patterns = {
                'es': [r'/distribucion-de-licencias-tensor'],
                'zh': [r'/anydesk\.com/zhs/solutions/']
            }
            
            for lang, patterns in product_lang_patterns.items():
                if any(re.search(pattern, url, re.IGNORECASE) for pattern in patterns):
                    return lang
            
            # Default to English if no other language is detected
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

        if st.button("Extract URLs",key="extract_links") and website_url:
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
                                    'source_url': url,
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
            
            # Store filtered_df in session_state
            st.session_state.filtered_df = filtered_df
            
            st.success(f"Found {len(filtered_df)} URLs in selected languages.")
            st.dataframe(filtered_df)
                
            filtered_urls = filtered_df[['source_url']].rename(columns={'source_url': 'source_url'})
            csv_data = filtered_urls.to_csv(index=False).encode('utf-8')
            st.download_button(label="Download Filtered URLs",data=csv_data,file_name="filtered_urls.csv",mime="text/csv")


                
    # with tab2:
    #     def extract_links(url):
    #         try:
    #             response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})

    #             if response.status_code == 200:
    #                 soup = BeautifulSoup(response.content, 'html.parser')
    #                 links = []
    #                 for a_tag in soup.find_all('a', href=True):
    #                     full_url = urljoin(url, a_tag['href'])
    #                     links.append(full_url)
    #                 return links
    #             else:
    #                 st.error(f"Error: Received status code {response.status_code}")
    #                 return []

    #         except requests.exceptions.RequestException as e:
    #             st.error(f"Error: Unable to fetch the URL. {e}")
    #             return []

    #     # st.subheader("URL Extractor")
    #     st.write("Enter a webpage URL to extract all the links from it.")
    #     page_url = st.text_input("Enter the URL (e.g., https://pages.ebay.com/sitemap.html):", "")

    #     if st.button("Extract URLs",key="extract_urls"):
    #         if page_url:
    #             if not page_url.startswith("http"):
    #                 st.error("Please enter a valid URL starting with http or https.")
    #             else:
    #                 with st.spinner("Extracting links..."):
    #                     links = extract_links(page_url)

    #                     if links:
    #                         st.success(f"Found {len(links)} links.")
    #                         st.dataframe(pd.DataFrame(links, columns=["Links"]))
    #                         csv_data = pd.DataFrame(links, columns=["Links"]).to_csv(index=False).encode('utf-8')
    #                         st.download_button("Download Links as CSV", data=csv_data, file_name="extracted_links.csv", mime="text/csv")
    #                     else:
    #                         st.warning("No links found on the provided webpage.")
    #         else:
    #             st.error("Please enter a URL.")
            
            
    # with tab2:
    #     def extract_links(url):
    #         try:
    #             response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})

    #             if response.status_code == 200:
    #                 soup = BeautifulSoup(response.content, 'html.parser')
    #                 links = []
    #                 for a_tag in soup.find_all('a', href=True):
    #                     full_url = urljoin(url, a_tag['href'])
    #                     links.append(full_url)
    #                 return links
    #             else:
    #                 st.error(f"Error: Received status code {response.status_code}")
    #                 return []

    #         except requests.exceptions.RequestException as e:
    #             st.error(f"Error: Unable to fetch the URL. {e}")
    #             return []

    #     # st.subheader("URL Extractor")
    #     st.write("Enter a webpage URL to extract all the links from it.")
    #     page_url = st.text_input("Enter the URL (e.g., https://pages.ebay.com/sitemap.html):", "")

    #     if st.button("Extract URLs",key="extract_urls"):
    #         if page_url:
    #             if not page_url.startswith("http"):
    #                 st.error("Please enter a valid URL starting with http or https.")
    #             else:
    #                 with st.spinner("Extracting links..."):
    #                     links = extract_links(page_url)

    #                     if links:
    #                         st.success(f"Found {len(links)} links.")
    #                         st.dataframe(pd.DataFrame(links, columns=["Links"]))
    #                         csv_data = pd.DataFrame(links, columns=["Links"]).to_csv(index=False).encode('utf-8')
    #                         st.download_button("Download Links as CSV", data=csv_data, file_name="extracted_links.csv", mime="text/csv")
    #                     else:
    #                         st.warning("No links found on the provided webpage.")
    #         else:
    #             st.error("Please enter a URL.")