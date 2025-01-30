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

def run_analysis(data):
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
    
    np.fill_diagonal(matrix_df.values, np.nan)
    
    blog_types = [typ for typ in matrix_df.columns if typ.startswith('Blog')]
    if blog_types:
        matrix_df.loc['Homepage', blog_types] = np.nan
        matrix_df.loc[blog_types, 'Homepage'] = np.nan
    
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
            return 'background-color: white; color: black'
        elif val == 1:
            return 'background-color: #C8E6C9; color: black'
        else:
            return 'background-color: #FFCDD2; color: black'
        
    font_family = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'

    styled_matrix = (matrix_df
                    .style
                    .set_tooltips(tooltip_df, props=tooltip_style)
                    .format(na_rep="NA", precision=0)
                    .set_properties(**{
                        'text-align': 'center',
                        'min-width': '150px',
                        'font-weight': 'bold',
                        'background-color': 'white', 
                        'color': 'black', 
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
                        ]}, 
                        {
                        'selector': 'th',
                        'props': [
                            ('background-color', 'white'), 
                            ('color','black !important'),
                            ('font-weight', 'bold'),
                            ('font-family', font_family),
                            ('font-size', '13px')
                        ]}]))
    
    st.divider()
    st.subheader("Complete Interlinking Matrix")
    st.write("In the below matrix 1 indicates a link exists, 0 indicates no link, and NA indicates not applicable (self-link)")
    st.markdown(styled_matrix.to_html(), unsafe_allow_html=True)
    
    progress_bar.empty()
    status_text.empty()
    
    st.divider()
    
    if 'Homepage' in data['type'].values and 'Target Page' in data['type'].values:
        with st.expander("Homepage & Target Page Links", expanded=False):
            st.write("### Homepage and Target Page Interlinking")
            home_to_target = matrix_df.loc['Homepage', 'Target Page'] == 1
            target_to_home = matrix_df.loc['Target Page', 'Homepage'] == 1
            
            if home_to_target:
                st.success("✓ Homepage links to Target Page")
                homepage_links_df = pd.DataFrame(all_links['Homepage'])
                target_links = homepage_links_df[homepage_links_df['url'] == data[data['type'] == 'Target Page']['url'].values[0]]
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
                home_links = target_links_df[target_links_df['url'] == data[data['type'] == 'Homepage']['url'].values[0]]
                if not home_links.empty:
                    st.write("Links found:")
                    st.dataframe(home_links.assign(
                        type=home_links['url'].map(url_to_type)
                    )[['text', 'url', 'type']])
            else:
                st.error("✗ Target Page does not link to Homepage")

    blog_types = [typ for typ in data['type'] if typ.startswith('Blog')]
    if blog_types:
        with st.expander("Blog Interlinking Details", expanded=False):
            st.write("### Blog Interlinking Analysis")
            
            for blog_type in blog_types:
                st.write(f"\n**{blog_type} Analysis:**")
                
                blog_links_df = pd.DataFrame(all_links.get(blog_type, []))
                if blog_links_df.empty:
                    st.warning(f"No internal links found in {blog_type}")
                    continue
                
                target_url = data[data['type'] == 'Target Page']['url'].values[0]
                target_links = blog_links_df[blog_links_df['url'] == target_url]
                if not target_links.empty:
                    st.success("✓ Links to Target Page")
                    st.dataframe(target_links.assign(
                        type=target_links['url'].map(url_to_type)
                    )[['text', 'url', 'type']])
                else:
                    st.error("✗ Does not link to Target Page")
                
                other_blogs = [b for b in blog_types if b != blog_type]
                other_blog_urls = data[data['type'].isin(other_blogs)]['url'].tolist()
                other_blog_links = blog_links_df[blog_links_df['url'].isin(other_blog_urls)]
                
                if not other_blog_links.empty:
                    st.write("Links to Other Blogs:")
                    st.dataframe(other_blog_links.assign(
                        type=other_blog_links['url'].map(url_to_type)
                    )[['text', 'url', 'type']])
                
                missing_blogs = [b for b in other_blogs 
                               if data[data['type'] == b]['url'].values[0] not in other_blog_links['url'].tolist()]
                if missing_blogs:
                    st.error(f"Missing links to: {', '.join(missing_blogs)}")

def manual_input_tab():
    st.subheader("Manual Input Analysis")
    col1, col2 = st.columns(2)
    with col1:
        homepage_url = st.text_input("Homepage URL", placeholder="https://www.example.com")
    with col2:
        target_page_url = st.text_input("Target Page URL", placeholder="https://www.example.com/target")
    
    num_blogs = st.number_input("Number of Blog Pages to Analyze", min_value=1, max_value=10, value=3)
    
    blog_urls = []
    for i in range(num_blogs):
        blog_url = st.text_input(f"Blog {i+1} URL", placeholder=f"https://www.example.com/blog-{i+1}", key=f"blog_{i}")
        blog_urls.append(blog_url)
    
    all_urls = [homepage_url, target_page_url] + blog_urls
    if not all(all_urls) or not all(is_valid_url(url) for url in all_urls):
        st.warning("Please enter valid URLs for all fields")
        return
    
    data = pd.DataFrame({
        'type': ['Homepage', 'Target Page'] + [f'Blog {i+1}' for i in range(num_blogs)],
        'url': [homepage_url, target_page_url] + blog_urls
    })
    
    if st.button("Start Analysis"):
        run_analysis(data)

def file_upload_tab():
    st.subheader("File Upload Analysis")
    # st.info("🔎 No file uploaded yet. Please upload a file to begin the analysis.")
    
    st.warning("""File Requirements:
            - Must be an Excel or CSV file,
            - Must contain the columns 'type' and 'url'
            """)
    
    example_data = pd.read_csv('example_data.csv')
    st.dataframe(example_data)

    uploaded_file = st.file_uploader("Upload Excel or CSV file for the analysis", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                data = pd.read_csv(uploaded_file)
            else:
                data = pd.read_excel(uploaded_file)
            
            if 'type' not in data.columns or 'url' not in data.columns:
                st.error("Uploaded file must contain 'type' and 'url' columns.")
                return
            
            homepage_count = (data['type'] == 'Homepage').sum()
            target_page_count = (data['type'] == 'Target Page').sum()
            
            if homepage_count != 1:
                st.error("Uploaded file must contain exactly one 'Homepage' entry.")
                return
            if target_page_count != 1:
                st.error("Uploaded file must contain exactly one 'Target Page' entry.")
                return
            
            if not data['url'].apply(is_valid_url).all():
                st.error("Some URLs in the uploaded file are invalid.")
                return
            
            if st.button("Start Analysis for the Uploaded File"):
                run_analysis(data)
        
        except Exception as e:
            st.error(f"Error reading file: {e}")
            
def analyze_internal_links():
    st.header("Reverse Content Silos Analysis", divider='rainbow')
    
    with st.expander("Understanding Reverse Content Silos"):
        st.markdown("""
        Reverse content silos represent a strategic internal linking structure where supporting content pieces 
        interlink with each other and point to a central target page.In this structure:
        
    - Supporting articles link to each other to share authority
    - All supporting content points to a main target page
    - The target page connects with the homepage
    - Each supporting article can receive external backlinks
    
        """)
    
    col1, col2, col3 = st.columns([0.4,2,0.6])
    with col2:
        st.image(r"reverse_silos.png", caption="Reverse Content Silos Analysis", width=700)
    
    tab1, tab2 = st.tabs(["Manual Input", "File Upload"])
    
    with tab1:
        manual_input_tab()
    
    with tab2:
        file_upload_tab()