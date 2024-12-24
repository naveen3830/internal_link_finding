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
