import requests
import xml.etree.ElementTree as ET

def fetch_sitemap_urls(website_url):
    sitemap_paths = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap-1.xml",
        "/sitemaps/sitemap.xml",
        "/sitemaps/sitemap_index.xml"
    ]

    base_url = website_url.rstrip('/')
    for path in sitemap_paths:
        sitemap_url = base_url + path
        print(f"Trying {sitemap_url}...")
        try:
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                print(f"Sitemap found: {sitemap_url}")
                return parse_sitemap(response.text)
        except requests.exceptions.RequestException as e:
            print(f"Error accessing {sitemap_url}: {e}")

    print("No sitemap found using common paths.")
    return []

def parse_sitemap(sitemap_content):
    urls = []
    try:
        root = ET.fromstring(sitemap_content)
        for element in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            urls.append(element.text)
    except ET.ParseError as e:
        print(f"Error parsing sitemap: {e}")
    return urls

def main():
    website_url = input("Enter the website URL (e.g., https://example.com): ").strip()
    if not website_url.startswith("http"):
        print("Please enter a valid URL starting with http or https.")
        return

    urls = fetch_sitemap_urls(website_url)
    if urls:
        print("\nFound URLs in sitemap:")
        for url in urls:
            print(url)
    else:
        print("No URLs found in the sitemap.")

if __name__ == "__main__":
    main()