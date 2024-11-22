import streamlit as st
import pandas as pd
import os
from scrapy.crawler import CrawlerProcess
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse

# Scrapy Spider
class OptimizedWebCrawler(CrawlSpider):
    name = 'optimized_web_crawler'

    def __init__(self, start_url, max_depth, *args, **kwargs):
        parsed_url = urlparse(start_url)
        self.start_urls = [start_url]
        self.base_domain = parsed_url.netloc
        self.allowed_domains = [self.base_domain]
        self.rules = (
            Rule(
                LinkExtractor(
                    allow=(f'^https?://{self.base_domain}'),
                    deny=(
                        '.*\\.pdf$', '.*\\.jpg$', '.*\\.png$', '.*\\.gif$', 
                        '.*\\.zip$', '.*\\.exe$',
                        'facebook\\.com', 'instagram\\.com', 'twitter\\.com', 
                        'linkedin\\.com', 'youtube\\.com', 'tiktok\\.com', 
                        'reddit\\.com', 'javascript:void\\(0\\)', 
                        'tel:', 'mailto:', '#', 'javascript:', 'data:'
                    ),
                    unique=True
                ), 
                callback='parse_item', 
                follow=True
            ),
        )
        self.custom_settings = {
            'DEPTH_LIMIT': max_depth
        }
        super().__init__(*args, **kwargs)

    def parse_item(self, response):
        yield {'source_url': response.url}

def run_crawler(url, max_depth, output_file):
    process = CrawlerProcess(settings={
        'FEEDS': {
            output_file: {
                'format': 'csv',
                'fields': ['source_url'],
                'overwrite': True
            }
        },
        'USER_AGENT': 'Mozilla/5.0 (compatible; WebCrawler/1.0)'
    })
    process.crawl(OptimizedWebCrawler, start_url=url, max_depth=max_depth)
    process.start()

def main():
    st.title("Web Link Crawler 🕸️")

    # Input fields
    url = st.text_input("Enter Website URL", placeholder="https://www.example.com")
    max_depth = st.slider("Crawling Depth", min_value=1, max_value=5, value=3)

    # Output directory
    OUTPUT_DIR = "crawl_outputs"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Crawl button
    if st.button("Start Crawling"):
        if not url:
            st.error("Please enter a valid URL.")
            return

        output_file = os.path.join(OUTPUT_DIR, f"links_{urlparse(url).netloc.replace('.', '_')}.csv")

        with st.spinner("Crawling website and extracting links..."):
            try:
                run_crawler(url, max_depth, output_file)
                if os.path.exists(output_file):
                    df = pd.read_csv(output_file)
                    st.success(f"Successfully crawled {len(df)} links!")
                    st.dataframe(df)

                    # Download button
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
