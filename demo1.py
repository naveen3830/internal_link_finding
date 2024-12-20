import streamlit as st
import pandas as pd
import os
import threading
import concurrent.futures
import requests
import re
import logging
from urllib.parse import urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning


# Disable warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
st.set_page_config(page_title="Keyword Search", layout="wide")
class WebLinkCrawler:
    def __init__(self, start_url, max_depth=3, max_workers=10):
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_workers = max_workers
        self.visited_urls = set()
        self.extracted_links = set()
        self.base_domain = urlparse(start_url).netloc
        self.lock = threading.Lock()

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver

    def is_valid_link(self, link):
        try:
            parsed_link = urlparse(link)
            
            exclusions = [
                '.pdf', '.jpg', '.png', '.gif', '.zip', '.exe', 
                'facebook.com', 'instagram.com', 'twitter.com', 
                'linkedin.com', 'youtube.com', 'tiktok.com', 
                'reddit.com', 'javascript:', 'tel:', 'mailto:', 
                '#', 'data:', 'void(0)'
            ]
            
            return (
                parsed_link.scheme in ['http', 'https'] and
                self.base_domain in parsed_link.netloc and
                not any(exc in link.lower() for exc in exclusions)
            )
        except Exception:
            return False

    def crawl_page(self, url, depth=0):
        with self.lock:
            if depth > self.max_depth or url in self.visited_urls:
                return set()
            self.visited_urls.add(url)

        try:
            driver = self.setup_driver()
            driver.get(url)
            
            links = driver.find_elements('tag name', 'a')
            found_links = set()

            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        absolute_link = urljoin(url, href)
                        if self.is_valid_link(absolute_link):
                            normalized_link = absolute_link.split('#')[0].rstrip('/')
                            found_links.add(normalized_link)
                except Exception:
                    continue
            
            driver.quit()
            return found_links

        except Exception:
            return set()

    def crawl(self):
        initial_links = self.crawl_page(self.start_url, 0)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for depth in range(1, self.max_depth + 1):
                futures = {}
                
                for link in initial_links - self.extracted_links:
                    futures[executor.submit(self.crawl_page, link, depth)] = link
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        new_links = future.result()
                        with self.lock:
                            self.extracted_links.update(new_links)
                            initial_links.update(new_links)
                    except Exception:
                        continue

        return list(self.extracted_links)
    
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text(text):
    """Clean and normalize text for consistent matching."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def extract_text_from_html(html_content):
    """Extract meaningful text from HTML while preserving structure."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'meta', 'link']):
        element.decompose()
    
    return soup

def find_unlinked_keywords(soup, keyword, target_url):
    """Find occurrences of a keyword that are not already hyperlinked."""
    keyword = keyword.strip()
    unlinked_occurrences = []
    
    text_elements = soup.find_all(text=True)
    existing_links = set(clean_text(link.get_text()) for link in soup.find_all('a'))
    
    for element in text_elements:
        if not element.strip() or element.parent.name == 'a':
            continue
        
        clean_element = clean_text(element)
        matches = list(re.finditer(r'\b' + re.escape(keyword) + r'\b', clean_element))
        
        for match in matches:
            match_text = element[match.start():match.end()]
            
            if clean_text(match_text) not in existing_links:
                start = max(0, match.start() - 50)
                end = min(len(element), match.end() + 50)
                context = element[start:end].strip()
                
                unlinked_occurrences.append({
                    'context': context,
                    'keyword': keyword
                })
    
    return unlinked_occurrences

def process_url(url, keyword, target_url):
    """Process a single URL to find unlinked keyword opportunities."""
    if url.strip().rstrip('/') == target_url.strip().rstrip('/'):
        return None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = extract_text_from_html(response.text)
        unlinked_matches = find_unlinked_keywords(soup, keyword, target_url)
        
        if unlinked_matches:
            return {
                'url': url,
                'unlinked_matches': unlinked_matches
            }
        return None
    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
        return None

@st.cache_data
def convert_df_to_csv(download_data):
    """Cache the CSV generation to prevent re-computation."""
    download_df = pd.DataFrame(download_data)
    return download_df.to_csv(index=False).encode('utf-8')

def main():
    
    # Global variable to store crawled links
    if 'crawled_links' not in st.session_state:
        st.session_state.crawled_links = None
    
    # Tabs for different functionalities
    tab1, tab2 = st.tabs(["Web Link Crawler", "Keyword Search"])
    
    with tab1:
        st.header("Web Link Crawler")
        url = st.text_input("Enter Website URL", placeholder="https://www.example.com")
        max_depth = st.slider("Crawling Depth", min_value=1, max_value=5, value=3)
        max_workers = st.slider("Concurrent Workers", min_value=1, max_value=20, value=10)

        if st.button("Start Crawling", key="crawler_button"):
            if not url:
                st.error("Please enter a valid URL.")
                return

            OUTPUT_DIR = "crawl_outputs"
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            output_file = os.path.join(OUTPUT_DIR, f"links_{urlparse(url).netloc.replace('.', '_')}.csv")

            with st.spinner("Crawling website and extracting links concurrently..."):
                try:
                    crawler = WebLinkCrawler(url, max_depth, max_workers)
                    extracted_links = crawler.crawl()

                    df = pd.DataFrame(extracted_links, columns=['source_url'])
                    
                    if not df.empty:
                        df.to_csv(output_file, index=False)
                        st.success(f"Successfully crawled {len(df)} links!")
                        st.dataframe(df.head(50))

                        # Store crawled links in session state
                        st.session_state.crawled_links = df

                        with open(output_file, 'rb') as f:
                            st.download_button(
                                label="Download Links CSV",
                                data=f,
                                file_name=f'links_{urlparse(url).netloc.replace(".", "_")}.csv',
                                mime='text/csv',
                                key="download_crawler_csv"
                            )
                    else:
                        st.warning("No links were found or crawling was unsuccessful.")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    
    with tab2:
        st.header("Keyword Search")
        
        # Create columns for inputs
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            # Check if crawled links are available
            if st.session_state.crawled_links is not None:
                st.success("Crawler results available! Ready for analysis.")
                uploaded_file = st.session_state.crawled_links
            else:
                uploaded_file = st.file_uploader("Upload CSV or Excel file with URLs", 
                                                type=["csv", "xlsx"], 
                                                key="url_file_uploader")
        
        with col2:
            keyword = st.text_input("Enter keyword to find", 
                                    help="Find this keyword without existing links",
                                    key="keyword_input")
        
        with col3:
            target_url = st.text_input("Target URL for linking", 
                                    help="URL to suggest for internal linking",
                                    key="target_url_input")
        
        max_workers_linking = st.slider("Concurrent searches", min_value=1, max_value=10, value=2, 
                                help="Number of URLs to process simultaneously")

        if uploaded_file is not None and keyword and target_url:
            try:
                # Read the file (either from crawler or uploaded)
                if isinstance(uploaded_file, pd.DataFrame):
                    df = uploaded_file
                else:
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                
                # Validate URL column
                if 'source_url' not in df.columns:
                    st.error("File must contain a 'source_url' column")
                    return
                
                df['source_url'] = df['source_url'].astype(str).str.strip()
                valid_urls = df['source_url'].str.match(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
                df = df[valid_urls].copy()
                
                if df.empty:
                    st.error("No valid URLs found in the file")
                    return
                
                st.info(f"Processing {len(df)} URLs...")
                results = []
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_linking) as executor:
                    future_to_url = {executor.submit(process_url, url, keyword, target_url): url for url in df['source_url'].unique()}
                    
                    progress_bar = st.progress(0)
                    processed = 0
                    
                    for future in concurrent.futures.as_completed(future_to_url):
                        processed += 1
                        progress = processed / len(df)
                        progress_bar.progress(progress)
                        result = future.result()
                        
                        if result:
                            results.append(result)
                
                progress_bar.empty()
                
                if results:
                    download_data = []
                    st.success(f"Unlinked keyword opportunities found in {len(results)} URLs")
                    
                    with st.expander("View Opportunities", expanded=True):
                        for result in results:
                            st.write("---")
                            st.write(f"🔗 Source URL: {result['url']}")
                            
                            if result.get('unlinked_matches'):
                                st.write("Unlinked Keyword Occurrences:")
                                for match in result['unlinked_matches']:
                                    st.markdown(f"- *{match['keyword']}*: _{match['context']}_")
                                    download_data.append({
                                        'source_url': result['url'],
                                        'keyword': match['keyword'],
                                        'context': match['context']
                                    })
                    
                    if download_data:
                        csv = pd.DataFrame(download_data).to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download Opportunities CSV", 
                            data=csv, 
                            file_name=f'unlinked_keyword_opportunities_{keyword}.csv', 
                            mime='text/csv'
                        )
                else:
                    st.warning(f"No unlinked keyword opportunities found for '{keyword}'")
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")    

if __name__ == "__main__":
    main()