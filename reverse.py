# Updated code to address the discrepancy
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
        
        # NEW CODE ADDED HERE: Remove elements with the class from the image
        for element in soup.find_all(attrs={"class": ["d-none d-sm-flex align-items-center"]}):
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
                        'text': text,
                        'url': absolute_url
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
        
        # Create URL to type mapping for later use
        url_to_type = dict(zip(data['url'], data['type']))
        
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
                if i != j:
                    if any(link['url'] == target_row['url'] for link in source_links if link['url'] != homepage_url):
                        matrix_data[i][j] = 1
        
        # Create interlinking matrix DataFrame
        matrix_df = pd.DataFrame(
            matrix_data,
            columns=data['type'],
            index=data['type']
        )
        
        # Remove index and column names
        matrix_df.index.name = None
        matrix_df.columns.name = None
        
        # Set diagonal to NA
        np.fill_diagonal(matrix_df.values, np.nan)
        
        # Create tooltip data
        tooltip_data = []
        for i, source_type in enumerate(matrix_df.index):
            tooltip_row = []
            for j, target_type in enumerate(matrix_df.columns):
                if i == j:
                    tooltip_row.append('')
                else:
                    target_url = data[data['type'] == target_type]['url'].values[0]
                    source_links = all_links.get(source_type, [])
                    matching_links = [link for link in source_links if link['url'] == target_url and link['url'] != homepage_url]
                    
                    tooltip_content = []
                    for link in matching_links:
                        tooltip_content.append(f"Text: {link['text']}<br>URL: {link['url']}")
                    tooltip_row.append("<br>".join(tooltip_content))
            tooltip_data.append(tooltip_row)
        
        tooltip_df = pd.DataFrame(tooltip_data, index=matrix_df.index, columns=matrix_df.columns)
        
          # Configure tooltip style
        tooltip_style = [
            ('visibility', 'hidden'),
            ('position', 'absolute'),
            ('z-index', '100'),
            ('background-color', 'white'),
            ('color', 'black'),  # Added text color
            ('border', '1px solid #cccccc'),
            ('padding', '8px'),
            ('font-family', 'sans-serif'),
            ('font-size', '12px'),
            ('box-shadow', '2px 2px 5px rgba(0, 0, 0, 0.1)')
        ]
        
        # Custom color function for the matrix
        def color_cells(val):
            if val == 1:
                return 'background-color: #90EE90'  # Light green
            elif val == 0:
                return 'background-color: #FFCCCB'  # Light red
            return ''
        
        # Create styled matrix
        styled_matrix = (matrix_df
                         .style
                         .set_tooltips(tooltip_df, props=tooltip_style)
                         .format(na_rep="NA", precision=0)
                         .set_properties(**{'text-align': 'center', 
                                          'min-width': '150px',
                                          'font-weight': 'bold'})
                         .applymap(color_cells))
        
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
                st.dataframe(target_links[['text', 'url']].assign(source_page=lambda x: x['url'].map(url_to_type)))
        else:
            st.error("✗ Homepage does not link to Target Page")
            
        if target_to_home:
            st.success("✓ Target Page links to Homepage")
            target_links_df = pd.DataFrame(all_links['Target Page'])
            home_links = target_links_df[target_links_df['url'] == homepage_url]
            if not home_links.empty:
                st.write("Links found:")
                st.dataframe(home_links[['text', 'url']].assign(source_page=lambda x: x['url'].map(url_to_type)))
        else:
            st.error("✗ Target Page does not link to Homepage")

        st.divider()
        st.write("### Blog Interlinking Analysis")
        
        for blog_idx, blog_type in enumerate(data['type'][2:], 1):
            st.write(f"\n**{blog_type} Analysis:**")
            
            # Create a DataFrame for all links from this blog
            blog_links_df = pd.DataFrame(all_links[blog_type])
            if blog_links_df.empty:
                st.warning(f"No internal links found in {blog_type}")
                continue
                
            # Check and display homepage links (excluding the common "Home" link)
            home_links = blog_links_df[blog_links_df['url'] == homepage_url]
            if not home_links.empty:
                st.success("✓ Links to Homepage")
                st.write("Homepage Links:")
                st.dataframe(home_links[['text', 'url']].assign(source_page=lambda x: x['url'].map(url_to_type)))
            else:
                st.error("✗ Does not link to Homepage")
            
            # Check and display target page links
            target_links = blog_links_df[blog_links_df['url'] == target_page_url]
            if not target_links.empty:
                st.success("✓ Links to Target Page")
                st.write("Target Page Links:")
                st.dataframe(target_links[['text', 'url']].assign(source_page=lambda x: x['url'].map(url_to_type)))
            else:
                st.error("✗ Does not link to Target Page")
            
            # Check and display links to other blogs
            other_blogs = [b for b in data['type'][2:] if b != blog_type]
            other_blog_urls = data[data['type'].isin(other_blogs)]['url'].tolist()
            
            # Create a DataFrame for links to other blogs
            other_blog_links = blog_links_df[blog_links_df['url'].isin(other_blog_urls) & (blog_links_df['url'] != homepage_url)]
            if not other_blog_links.empty:
                st.write("Links to Other Blogs:")
                st.dataframe(other_blog_links[['text', 'url']].assign(source_page=lambda x: x['url'].map(url_to_type)))
            
            # Show missing blog links
            linked_urls = other_blog_links['url'].tolist()
            missing_blogs = [b for b, url in zip(other_blogs, other_blog_urls) if url not in linked_urls]
            if missing_blogs:
                st.error(f"✗ Missing links to: {', '.join(missing_blogs)}")
        
        st.divider()
        st.write("### Complete Interlinking Matrix")
        st.write("1 indicates a link exists, 0 indicates no link, and NA indicates no self-linking")

        # Display styled matrix
        st.markdown(styled_matrix.to_html(), unsafe_allow_html=True)
        
        # Reset progress
        progress_bar.empty()
        status_text.empty()