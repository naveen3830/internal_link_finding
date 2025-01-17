import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from urllib.parse import urljoin, urlparse
import numpy as np

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_main_content_anchor_tags(url, page_type):
    """Scrape anchor tags from the main content area of a given URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove common non-main content elements
        for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 
                                    'meta', 'link', 'sidebar', 'aside', '.nav', 
                                    '.header', '.footer', '.sidebar', '.menu',
                                    '[role="navigation"]', '[role="banner"]', 
                                    '[role="contentinfo"]']):
            element.decompose()
        
        # Try to find main content area using common selectors
        main_content = None
        content_selectors = ['main', 'article', '#content', '.content', 
                        '#main', '.main', '[role="main"]']
        
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # If no main content area found, use the body after cleaning
        if not main_content:
            main_content = soup.body
        
        links = []
        if main_content:
            for link in main_content.find_all('a', href=True):
                href = link.get('href')
                text = ' '.join(link.get_text().strip().split())  # Normalize whitespace
                
                if not text or text.isspace():
                    continue
                
                # Convert relative URLs to absolute URLs
                absolute_url = urljoin(url, href)
                
                # Only include links from the same domain
                if urlparse(absolute_url).netloc == urlparse(url).netloc:
                    links.append({
                        'page_source': page_type,  # Add the source page type
                        'text': text,
                        'url': absolute_url,
                        'source': 'Main Content'
                    })
        
        return links
    except Exception as e:
        st.error(f"Error scraping {url}: {str(e)}")
        return []

def analyze_internal_links():
    st.header("Internal Link Analysis", divider='rainbow')
    
    col1, col2 = st.columns(2)
    with col1:
        homepage_url = st.text_input("Homepage URL", placeholder="https://www.example.com")
    with col2:
        target_page_url = st.text_input("Target Page URL", placeholder="https://www.example.com/target")
    
    # Number of blog pages
    num_blogs = st.number_input("Number of Blog Pages to Analyze", min_value=1, max_value=10, value=3)
    
    # Blog URLs input
    blog_urls = []
    for i in range(num_blogs):
        blog_url = st.text_input(f"Blog {i+1} URL", placeholder=f"https://www.example.com/blog-{i+1}")
        if blog_url:
            blog_urls.append(blog_url)
    
    # Validate inputs before proceeding
    all_urls = [homepage_url, target_page_url] + blog_urls
    if not all(all_urls) or not all(is_valid_url(url) for url in all_urls):
        st.warning("Please enter valid URLs for all fields")
        return
    
    # Create DataFrame with the input URLs
    data = pd.DataFrame({
        'type': ['Homepage', 'Target Page'] + [f'Blog {i+1}' for i in range(len(blog_urls))],
        'url': [homepage_url, target_page_url] + blog_urls
    })
    
    if st.button("Start Analysis"):
        st.write("Analyzing pages:", data)
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Dictionary to store all links for each page
        all_links = {}
        
        # Scrape links from each page
        for idx, row in data.iterrows():
            status_text.text(f"Analyzing {row['type']}...")
            progress_bar.progress((idx + 1) / len(data))
            
            page_links = get_main_content_anchor_tags(row['url'], row['type'])
            all_links[row['type']] = page_links
        
        # Create interlinking matrix
        matrix_data = np.zeros((len(data), len(data)))
        
        for i, source_row in data.iterrows():
            source_links = all_links[source_row['type']]
            for j, target_row in data.iterrows():
                # Skip self-linking (diagonal elements)
                if i != j:
                    if any(link['url'] == target_row['url'] for link in source_links):
                        matrix_data[i][j] = 1
        
        # Create interlinking matrix DataFrame
        matrix_df = pd.DataFrame(
            matrix_data,
            columns=data['type'],
            index=data['type']
        )
        
        st.divider()
        st.subheader("Detailed Link Analysis")
        
        # Check Homepage <-> Target Page linking
        st.write("### Homepage and Target Page Interlinking")
        home_to_target = matrix_df.loc['Homepage', 'Target Page'] == 1
        target_to_home = matrix_df.loc['Target Page', 'Homepage'] == 1
        
        if home_to_target:
            st.success("✓ Homepage links to Target Page")
            homepage_links_df = pd.DataFrame(all_links['Homepage'])
            target_links = homepage_links_df[homepage_links_df['url'] == target_page_url]
            if not target_links.empty:
                st.write("Links found:")
                st.dataframe(target_links[['page_source', 'text', 'url', 'source']])
        else:
            st.error("✗ Homepage does not link to Target Page")
            
        if target_to_home:
            st.success("✓ Target Page links to Homepage")
            target_links_df = pd.DataFrame(all_links['Target Page'])
            home_links = target_links_df[target_links_df['url'] == homepage_url]
            if not home_links.empty:
                st.write("Links found:")
                st.dataframe(home_links[['page_source', 'text', 'url', 'source']])
        else:
            st.error("✗ Target Page does not link to Homepage")

        st.divider()
        st.write("### Blog Interlinking Analysis")
        
        for blog_idx, blog_type in enumerate(data['type'][2:], 1):  # Skip Homepage and Target Page
            st.write(f"\n**{blog_type} Analysis:**")
            
            # Create a DataFrame for all links from this blog
            blog_links_df = pd.DataFrame(all_links[blog_type])
            if blog_links_df.empty:
                st.warning(f"No internal links found in {blog_type}")
                continue
                
            # Check and display target page links
            target_links = blog_links_df[blog_links_df['url'] == target_page_url]
            if not target_links.empty:
                st.success(f"✓ Links to Target Page")
                st.write("Target Page Links:")
                st.dataframe(target_links[['page_source', 'text', 'url', 'source']])
            else:
                st.error(f"✗ Does not link to Target Page")
            
            # Check and display links to other blogs
            other_blogs = [b for b in data['type'][2:] if b != blog_type]  # Skip Homepage and Target Page
            other_blog_urls = data[data['type'].isin(other_blogs)]['url'].tolist()
            
            # Create a DataFrame for links to other blogs
            other_blog_links = blog_links_df[blog_links_df['url'].isin(other_blog_urls)]
            if not other_blog_links.empty:
                st.write("Links to Other Blogs:")
                st.dataframe(other_blog_links[['page_source', 'text', 'url', 'source']])
            
            # Show missing blog links
            linked_urls = other_blog_links['url'].tolist()
            missing_blogs = [b for b, url in zip(other_blogs, other_blog_urls) if url not in linked_urls]
            if missing_blogs:
                st.error(f"✗ Missing links to: {', '.join(missing_blogs)}")
        
        st.divider()
        st.write("### Complete Interlinking Matrix")
        st.write("1 indicates a link exists, 0 indicates no link (diagonal shows no self-linking)")
        st.dataframe(matrix_df)
        
        # Reset progress
        progress_bar.empty()
        status_text.empty()
        
# if __name__ == "__main__":
#     analyze_internal_links()