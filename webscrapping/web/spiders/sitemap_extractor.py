import scrapy
from scrapy.crawler import CrawlerProcess
import xml.etree.ElementTree as ET

class SitemapToCSVSpider(scrapy.Spider):
    name = 'sitemap_to_csv_spider'

    def __init__(self, start_url=None, output_file=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not start_url or not output_file:
            raise ValueError("Both 'start_url' and 'output_file' arguments are required.")
        self.start_urls = [start_url]
        self.output_file = output_file

    def parse(self, response):
        # Check robots.txt for sitemap location
        robots_url = response.urljoin("/robots.txt")
        yield scrapy.Request(robots_url, callback=self.parse_robots)

        # Check for sitemap links in the current page
        sitemap_links = response.css('a[href*="sitemap"]::attr(href)').getall()
        for link in sitemap_links:
            yield response.follow(link, callback=self.parse_sitemap)

    def parse_robots(self, response):
        # Extract sitemap location from robots.txt
        for line in response.text.splitlines():
            if 'Sitemap:' in line:
                sitemap_url = line.split(':', 1)[-1].strip()
                yield scrapy.Request(sitemap_url, callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        # Extract URLs from sitemap
        try:
            root = ET.fromstring(response.text)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for url in root.findall('.//ns:loc', namespace):
                yield {'url': url.text}  # Yield items for Scrapy to handle
        except ET.ParseError as e:
            self.logger.error(f"Error parsing sitemap: {e}")


# Correctly handle CSV file output
if __name__ == "__main__":
    import sys
    from scrapy.utils.project import get_project_settings

    # Collect command-line arguments for start_url and output_file
    if len(sys.argv) < 3:
        print("Usage: python sitemap_to_csv_spider.py <start_url> <output_file>")
        sys.exit(1)

    start_url = sys.argv[1]
    output_file = sys.argv[2]

    # Configure Scrapy with CSV output
    process = CrawlerProcess(settings={
        'FEEDS': {
            output_file: {
                'format': 'csv',  # Set file format to CSV
                'encoding': 'utf8',  # Ensure correct encoding
            },
        },
        'USER_AGENT': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    })

    # Start the crawl
    process.crawl(SitemapToCSVSpider, start_url=start_url, output_file=output_file)
    process.start()
