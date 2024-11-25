import streamlit as st
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
import threading

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
        # Prevent revisiting and exceeding depth
        with self.lock:
            if depth > self.max_depth or url in self.visited_urls:
                return set()
            self.visited_urls.add(url)

        try:
            driver = self.setup_driver()
            driver.get(url)
            
            # Find all links
            links = driver.find_elements('tag name', 'a')
            found_links = set()

            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        absolute_link = urljoin(url, href)
                        if self.is_valid_link(absolute_link):
                            # Normalize the link
                            normalized_link = absolute_link.split('#')[0].rstrip('/')
                            found_links.add(normalized_link)
                except Exception:
                    continue
            
            driver.quit()
            return found_links

        except Exception:
            return set()

    def crawl(self):
        # Initial crawl of start URL
        initial_links = self.crawl_page(self.start_url, 0)
        
        # Concurrent crawling of subsequent depths
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for depth in range(1, self.max_depth + 1):
                futures = {}
                
                # Create futures for uncrawled links
                for link in initial_links - self.extracted_links:
                    futures[executor.submit(self.crawl_page, link, depth)] = link
                
                # Process completed futures
                for future in as_completed(futures):
                    try:
                        new_links = future.result()
                        with self.lock:
                            self.extracted_links.update(new_links)
                            initial_links.update(new_links)
                    except Exception:
                        continue

        return list(self.extracted_links)

def main():
    st.title("Concurrent Web Link Crawler 🕸️")

    url = st.text_input("Enter Website URL", placeholder="https://www.example.com")
    max_depth = st.slider("Crawling Depth", min_value=1, max_value=5, value=3)
    max_workers = st.slider("Concurrent Workers", min_value=1, max_value=20, value=10)

    OUTPUT_DIR = "crawl_outputs"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if st.button("Start Crawling"):
        if not url:
            st.error("Please enter a valid URL.")
            return

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

                    with open(output_file, 'rb') as f:
                        st.download_button(
                            label="Download Links CSV",
                            data=f,
                            file_name=f'links_{urlparse(url).netloc.replace(".", "_")}.csv',
                            mime='text/csv'
                        )
                else:
                    st.warning("No links were found or crawling was unsuccessful.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()