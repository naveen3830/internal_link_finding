import streamlit as st
import pandas as pd
import os
import subprocess
import sys
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from urllib.parse import urlparse

class OptimizedWebCrawler(CrawlSpider):
    name = 'optimized_web_crawler'
    
    def __init__(self, start_url='https://www.efax.com/', output_file='links.csv', max_depth=3, *args, **kwargs):
        # Parse start URL components
        parsed_url = urlparse(start_url)
        self.start_urls = [start_url]
        self.base_domain = parsed_url.netloc
        self.allowed_domains = [self.base_domain]
        
        # Define crawling rules with link extractor
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
        
        # Set depth limit
        self.custom_settings = {
            'DEPTH_LIMIT': max_depth  # Control depth of crawling
        }
        
        # Initialize spider
        super().__init__(*args, **kwargs)
    
    def parse_item(self, response):
        """
        Process each valid page
        """
        yield {
            'source_url': response.url
        }
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """
        Customize Scrapy settings for performance
        """
        # Optimize Scrapy settings
        crawler.settings.set('CONCURRENT_REQUESTS', 32)
        crawler.settings.set('CONCURRENT_REQUESTS_PER_DOMAIN', 16)
        crawler.settings.set('DOWNLOAD_DELAY', 0.5)
        crawler.settings.set('ROBOTSTXT_OBEY', True)
        crawler.settings.set('LOG_LEVEL', 'INFO')
        
        # Configure output
        crawler.settings.set('FEEDS', {
            kwargs.get('output_file', 'links.csv'): {
                'format': 'csv', 
                'fields': ['source_url'], 
                'overwrite': True
            }
        })
        
        return super().from_crawler(crawler, *args, **kwargs)

def run_crawler(url, max_depth, output_file):
    """
    Run the Scrapy crawler and return the generated CSV
    """
    # Ensure output directory exists
    os.makedirs('crawl_outputs', exist_ok=True)
    
    # Create a CrawlerProcess
    process = CrawlerProcess(settings={
        'FEED_FORMAT': 'csv',
        'FEED_URI': output_file,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    # Configure and run the spider
    process.crawl(OptimizedWebCrawler, 
                  start_url=url, 
                  output_file=output_file, 
                  max_depth=max_depth)
    
    # Block and wait for the crawling to finish
    process.start()

def main():
    st.title("Web Link Crawler 🕸️")
    
    # Input fields
    url = st.text_input("Enter Website URL", placeholder="https://www.example.com")
    max_depth = st.slider("Crawling Depth", min_value=1, max_value=5, value=3)
    
    # Output file path
    output_file = f'crawl_outputs/links_{urlparse(url).netloc.replace(".", "_")}.csv'
    
    # Crawl button
    if st.button("Crawl Website"):
        if not url:
            st.error("Please enter a valid URL")
            return
        
        # Show loading spinner
        with st.spinner('Crawling website and extracting links...'):
            try:
                run_crawler(url, max_depth, output_file)
                
                # Read and display the CSV
                if os.path.exists(output_file):
                    df = pd.read_csv(output_file)
                    
                    # Display summary
                    st.success(f"Crawled {len(df)} unique links from {url}")
                    
                    # Display DataFrame
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