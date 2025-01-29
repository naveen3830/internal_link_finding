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
        
        # Remove non-main content elements
        for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 
                                    'meta', 'link', 'sidebar', 'aside', '.nav', 
                                    '.header', '.footer', '.sidebar', '.menu',
                                    '[role="navigation"]', '[role="banner"]', 
                                    '[role="contentinfo"]']):
            element.decompose()
        
        for element in soup.find_all(attrs={"class": ["d-none d-sm-flex align-items-center"]}):
            element.decompose()

        main_content = None
        content_selectors = ['main', 'article', '#content', '.content', 
                        '#main', '.main', '[role="main"]']
        
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.body
        
        links = []
        if main_content:
            for link in main_content.find_all('a', href=True):
                href = link.get('href')
                text = ' '.join(link.get_text().strip().split())
                
                if not text or text.isspace():
                    continue
                
                absolute_url = urljoin(url, href)
                
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
    st.header("Reverse Content Silos Analysis", divider='rainbow')
    
    col1, col2 = st.columns(2)
    with col1:
        homepage_url = st.text_input("Homepage URL", placeholder="https://www.example.com")
    with col2:
        target_page_url = st.text_input("Target Page URL", placeholder="https://www.example.com/target")
    
    num_blogs = st.number_input("Number of Blog Pages to Analyze", min_value=1, max_value=10, value=3)
    
    blog_urls = []
    for i in range(num_blogs):
        blog_url = st.text_input(f"Blog {i+1} URL", placeholder=f"https://www.example.com/blog-{i+1}")
        if blog_url:
            blog_urls.append(blog_url)
    
    all_urls = [homepage_url, target_page_url] + blog_urls
    if not all(all_urls) or not all(is_valid_url(url) for url in all_urls):
        st.warning("Please enter valid URLs for all fields")
        return
    
    data = pd.DataFrame({
        'type': ['Homepage', 'Target Page'] + [f'Blog {i+1}' for i in range(len(blog_urls))],
        'url': [homepage_url, target_page_url] + blog_urls
    })
    
    if st.button("Start Analysis"):
        st.write("Analyzing pages:", data)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_links = {}
        url_to_type = dict(zip(data['url'], data['type']))
        
        for idx, row in data.iterrows():
            status_text.text(f"Analyzing {row['type']}...")
            progress_bar.progress((idx + 1) / len(data))
            page_links = get_main_content_anchor_tags(row['url'], row['type'])
            all_links[row['type']] = page_links
        
        # Create matrix
        matrix_data = np.zeros((len(data), len(data)))
        
        for i, source_row in data.iterrows():
            source_links = all_links[source_row['type']]
            for j, target_row in data.iterrows():
                if i != j:
                    if any(link['url'] == target_row['url'] for link in source_links):
                        matrix_data[i][j] = 1
        
        matrix_df = pd.DataFrame(
            matrix_data,
            columns=data['type'],
            index=data['type']
        ).rename_axis(None, axis=1).rename_axis(None, axis=0)
        
        # Set diagonal to NA
        np.fill_diagonal(matrix_df.values, np.nan)
        
        # Set Homepage to Blog links and Blog to Homepage links to NA
        blog_types = [typ for typ in matrix_df.columns if typ.startswith('Blog')]
        matrix_df.loc['Homepage', blog_types] = np.nan
        matrix_df.loc[blog_types, 'Homepage'] = np.nan
        
        # Tooltips
        tooltip_data = []
        for i, source_type in enumerate(matrix_df.index):
            tooltip_row = []
            for j, target_type in enumerate(matrix_df.columns):
                if i == j:
                    tooltip_row.append('')
                else:
                    target_url = data[data['type'] == target_type]['url'].values[0]
                    source_links = all_links.get(source_type, [])
                    matching_links = [link for link in source_links if link['url'] == target_url]
                    
                    tooltip_content = []
                    for link in matching_links:
                        tooltip_content.append(f"Text: {link['text']}<br>URL: {link['url']}")
                    tooltip_row.append("<br>".join(tooltip_content))
            tooltip_data.append(tooltip_row)
        
        tooltip_df = pd.DataFrame(tooltip_data, index=matrix_df.index, columns=matrix_df.columns)
        
        # Styling
        tooltip_style = [
            ('visibility', 'hidden'),
            ('position', 'absolute'),
            ('z-index', '100'),
            ('background-color', st.get_option("theme.secondaryBackgroundColor")),
            ('color', st.get_option("theme.textColor")),
            ('border', f'2px solid {st.get_option("theme.primaryColor")}'),
            ('padding', '10px'),
            ('font-family', 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'),
            ('font-size', '13px'),
            ('box-shadow', '3px 3px 8px rgba(0, 0, 0, 0.5)'),
            ('border-radius', '5px')
        ]
        
        def color_cells(val):
            if pd.isna(val):
                return f'background-color: {st.get_option("theme.secondaryBackgroundColor")}; color: {st.get_option("theme.textColor")}'
            elif val == 1:
                return 'background-color: #C8E6C9; color: black'  # Light green
            else:
                return 'background-color: #FFCDD2; color: black'  # Light red

        # Define consistent font styling
        font_family = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
        
        styled_matrix = (matrix_df
                        .style
                        .set_tooltips(tooltip_df, props=tooltip_style)
                        .format(na_rep="NA", precision=0)
                        .set_properties(**{
                            'text-align': 'center',
                            'min-width': '150px',
                            'font-weight': 'bold',
                            'background-color': st.get_option("theme.backgroundColor"),
                            'color': st.get_option("theme.textColor"),
                            'border': f'1px solid {st.get_option("theme.primaryColor")}',
                            'font-family': font_family,
                            'font-size': '14px'
                        })
                        .applymap(color_cells)
                        .set_table_styles([{
                            'selector': 'th, td',
                            'props': [
                                ('border', f'1px solid {st.get_option("theme.primaryColor")}'),
                                ('padding', '8px 12px'),
                                ('font-family', font_family),
                                ('font-size', '14px')
                            ]
                        }, {
                            'selector': 'th',
                            'props': [
                                ('background-color', st.get_option("theme.secondaryBackgroundColor")),
                                ('color', st.get_option("theme.primaryColor")),
                                ('font-weight', 'bold'),
                                ('font-family', font_family),
                                ('font-size', '14px')
                            ]
                        }]))

        st.divider()
        st.subheader("Complete Interlinking Matrix")
        st.write("In the below matrix 1 indicates a link exists, 0 indicates no link, and NA indicates not applicable (self-link)")
        st.markdown(styled_matrix.to_html(), unsafe_allow_html=True)
        
        progress_bar.empty()
        status_text.empty()
        
        st.divider()
        
        with st.expander("Homepage & Target Page Links", expanded=False):
            st.write("### Homepage and Target Page Interlinking")
            home_to_target = matrix_df.loc['Homepage', 'Target Page'] == 1
            target_to_home = matrix_df.loc['Target Page', 'Homepage'] == 1
            
            if home_to_target:
                st.success("✓ Homepage links to Target Page")
                homepage_links_df = pd.DataFrame(all_links['Homepage'])
                target_links = homepage_links_df[homepage_links_df['url'] == target_page_url]
                if not target_links.empty:
                    st.write("Links found:")
                    st.dataframe(target_links.assign(
                        type=target_links['url'].map(url_to_type)
                    )[['text', 'url', 'type']])
            else:
                st.error("✗ Homepage does not link to Target Page")
                
            if target_to_home:
                st.success("✓ Target Page links to Homepage")
                target_links_df = pd.DataFrame(all_links['Target Page'])
                home_links = target_links_df[target_links_df['url'] == homepage_url]
                if not home_links.empty:
                    st.write("Links found:")
                    st.dataframe(home_links.assign(
                        type=home_links['url'].map(url_to_type)
                    )[['text', 'url', 'type']])
            else:
                st.error("✗ Target Page does not link to Homepage")

        with st.expander("Blog Interlinking Details", expanded=False):
            st.write("### Blog Interlinking Analysis")
            
            for blog_type in data['type'][2:]:
                st.write(f"\n**{blog_type} Analysis:**")
                
                blog_links_df = pd.DataFrame(all_links[blog_type])
                if blog_links_df.empty:
                    st.warning(f"No internal links found in {blog_type}")
                    continue
                
                # Target Page links
                target_links = blog_links_df[blog_links_df['url'] == target_page_url]
                if not target_links.empty:
                    st.success("✓ Links to Target Page")
                    st.dataframe(target_links.assign(
                        type=target_links['url'].map(url_to_type)
                    )[['text', 'url', 'type']])
                else:
                    st.error("✗ Does not link to Target Page")
                
                # Other Blog links
                other_blogs = [b for b in data['type'][2:] if b != blog_type]
                other_blog_urls = data[data['type'].isin(other_blogs)]['url'].tolist()
                other_blog_links = blog_links_df[blog_links_df['url'].isin(other_blog_urls)]
                
                if not other_blog_links.empty:
                    st.write("Links to Other Blogs:")
                    st.dataframe(other_blog_links.assign(
                        type=other_blog_links['url'].map(url_to_type)
                    )[['text', 'url', 'type']])
                
                missing_blogs = [b for b, url in zip(other_blogs, other_blog_urls) 
                               if url not in other_blog_links['url'].tolist()]
                if missing_blogs:
                    st.error(f"Missing links to: {', '.join(missing_blogs)}")