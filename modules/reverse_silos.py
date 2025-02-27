import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from urllib.parse import urljoin, urlparse
import numpy as np
import pdfkit
import tempfile
import platform
import os

default_keys = {
    "manual_homepage_url": "",
    "manual_target_page_url": "",
    "manual_blog_urls": [],
    "manual_num_blogs": 3,
    "manual_data": None,
    "manual_all_links": {},
    "manual_url_to_type": {},
    "manual_matrix_df": None,
    "manual_tooltip_df": None,
    "manual_styled_matrix_html": "",
    "file_data": None,
    "file_all_links": {},
    "file_url_to_type": {},
    "file_matrix_df": None,
    "file_tooltip_df": None,
    "file_styled_matrix_html": "",
    "uploaded_file": None
}

for key, default_value in default_keys.items():
    st.session_state.setdefault(key, default_value)

def inject_custom_css():
    st.markdown(
        """
        <style>
        h1, h2, h3, h4 {
            color: black !important;
            font-weight: bold !important;
        }
        .error {
            color: #B71C1C !important;
            font-weight: bold !important;
        }
        table, th, td {
            border: 2px solid black !important;
            text-align: center !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def generate_pdf_report(html_content):
    current_os = platform.system() 
    if current_os == "Windows":
        config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
    else:
        config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        pdfkit.from_string(html_content, tmpfile.name, configuration=config)
        tmpfile.seek(0)
        pdf_bytes = tmpfile.read()

    os.remove(tmpfile.name)
    return pdf_bytes

def create_detailed_report_html(source="manual"):
    if source == "manual":
        data = st.session_state.get("manual_data")
        matrix_html = st.session_state.get("manual_styled_matrix_html", "")
        all_links = st.session_state.get("manual_all_links", {})
        url_to_type = st.session_state.get("manual_url_to_type", {})
    else:
        data = st.session_state.get("file_data")
        matrix_html = st.session_state.get("file_styled_matrix_html", "")
        all_links = st.session_state.get("file_all_links", {})
        url_to_type = st.session_state.get("file_url_to_type", {})

    homepage_url = data[data['type'] == 'Homepage']['url'].values[0]
    target_url = data[data['type'] == 'Target Page']['url'].values[0]
    homepage_section = ""
    homepage_links_df = pd.DataFrame(all_links.get('Homepage', []))
    if not homepage_links_df.empty:
        ht = homepage_links_df[homepage_links_df['url'] == target_url]
        if not ht.empty:
            homepage_section += "<p class='success'>✓ Homepage links to Target Page</p>"
        else:
            homepage_section += "<p class='error'>✗ Homepage does not link to Target Page</p>"
    else:
        homepage_section += "<p>No internal links found on the Homepage.</p>"

    target_section = ""
    target_links_df = pd.DataFrame(all_links.get('Target Page', []))
    if not target_links_df.empty:
        th = target_links_df[target_links_df['url'] == homepage_url]
        if not th.empty:
            target_section += "<p class='success'>✓ Target Page links to Homepage</p>"
        else:
            target_section += "<p class='error'>✗ Target Page does not link to Homepage</p>"
    else:
        target_section += "<p>No internal links found on the Target Page.</p>"

    blog_section = ""
    blog_types = [typ for typ in data['type'] if typ.startswith('Blog')]
    for blog_type in blog_types:
        blog_section += f"<h3>{blog_type} Analysis</h3>"
        blog_links_df = pd.DataFrame(all_links.get(blog_type, []))
        if blog_links_df.empty:
            blog_section += "<p class='warning'>No internal links found in this blog.</p>"
            continue
        blog_links_df['linked_type'] = blog_links_df['url'].map(url_to_type)

        # Links to Target Page
        target_links = blog_links_df[blog_links_df['url'] == target_url]
        if not target_links.empty:
            blog_section += "<p class='success'>✓ Links to Target Page:</p>"
            blog_section += target_links[['text', 'url']].to_html(index=False, border=1)
        else:
            blog_section += "<p class='error'>✗ Does not link to Target Page</p>"

        # Links to other Blogs
        other_blogs = [b for b in blog_types if b != blog_type]
        other_blog_links = blog_links_df[blog_links_df['linked_type'].isin(other_blogs)]
        if not other_blog_links.empty:
            blog_section += "<p>Links to Other Blogs:</p>"
            blog_section += other_blog_links[['text', 'url', 'linked_type']].to_html(index=False, border=1)

        missing_blogs = [
            b for b in other_blogs   
            if data[data['type'] == b]['url'].values[0] not in other_blog_links['url'].tolist()
        ]
        if missing_blogs:
            blog_section += f"<p class='error'>Missing links to: {', '.join(missing_blogs)}</p>"

    full_html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Internal Link Analysis Report</title>
        <style>
        body {{
            font-family: "Helvetica Neue", Arial, sans-serif;
            margin: 30px;
            line-height: 1.6;
            color: #333;
        }}
        
        h1, h2, h3, h4 {{
            color: black;
            font-weight: bold;
            margin-top: 1.2em;
            margin-bottom: 0.8em;
        }}
        
        .subtitle {{
            font-size: 16px;
            color: #555;
            margin-bottom: 2em;
        }}
            
        table {{
            border-collapse: collapse;
            margin-bottom: 1em;
        }}
        
        table, th, td {{
            border: 1px solid #999;
            border: 2px solid black !important;
        }}
            
        th, td {{
            padding: 8px 12px;
            text-align: center;
            font-size: 14px;
        }}
            
        .success {{
            color: green;
            font-weight: bold;
        }}
            
        .error {{
            color: #B71C1C;
            font-weight: bold;
        }}
            
        .warning {{
            color: orange;
            font-weight: bold;
        }}
            
        .matrix-container {{
            margin-bottom: 2em;
        }}
            
        .analysis-container {{
            margin-bottom: 2em;
        }}
            
        .section-divider {{
            margin: 2em 0;
            border: 0;
            border-top: 2px solid #ccc;
        }}
        </style>
    </head>
    <body>
        <h1 style="text-align:center;">Internal Link Analysis Report</h1>
        <p class="subtitle">
        This report contains your complete interlinking matrix and detailed analysis 
        of Homepage, Target Page, and Blog links.
        </p>
        
        <div class="matrix-container">
        <h2>Complete Interlinking Matrix</h2>
        {matrix_html}
        </div>
        <hr class="section-divider" />

        <div class="analysis-container">
        <h2>Homepage Links Analysis</h2>
        {homepage_section}
        </div>
        <hr class="section-divider" />

        <div class="analysis-container">
        <h2>Target Page Links Analysis</h2>
        {target_section}
        </div>
        <hr class="section-divider" />

        <div class="analysis-container">
        <h2>Blog Interlinking Analysis</h2>
        {blog_section}
        </div>
        <hr class="section-divider" />
    </body>
    </html>
    """
    return full_html

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def get_main_content_anchor_tags(url, page_type):
    """Scrape main content area and extract internal anchor tags."""
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.124 Safari/537.36'
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup.find_all([
            'script', 'style', 'nav', 'header', 'footer', 
            'meta', 'link', 'sidebar', 'aside', '.nav', 
            '.header', '.footer', '.sidebar', '.menu',
            '[role="navigation"]', '[role="banner"]', 
            '[role="contentinfo"]'
        ]):
            element.decompose()
        
        for element in soup.find_all(attrs={"class": ["d-none d-sm-flex align-items-center"]}):
            element.decompose()

        main_content = None
        content_selectors = [
            'main', 'article', '#content', '.content', 
            '#main', '.main', '[role="main"]'
        ]
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
                # Keep only internal links
                if urlparse(absolute_url).netloc == urlparse(url).netloc:
                    links.append({
                        'text': text,
                        'url': absolute_url
                    })
        return links
    except Exception as e:
        st.error(f"Error scraping {url}: {str(e)}")
        return []

def run_analysis(data, source="manual"):
    if source == "manual":
        st.session_state["manual_data"] = data
    else:
        st.session_state["file_data"] = data

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
    
    # Build adjacency matrix
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
    
    # If there are blog types, set blog <-> homepage to NaN
    blog_types = [typ for typ in matrix_df.columns if typ.startswith('Blog')]
    if blog_types:
        matrix_df.loc['Homepage', blog_types] = np.nan
        matrix_df.loc[blog_types, 'Homepage'] = np.nan
    
    # Build tooltip data
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
    
    # Style for the matrix (this styling is used to generate the HTML for both PDF and Streamlit)
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
            return 'background-color: #FA615A; color: white'

    font_family = ('system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",'
                'Roboto, "Helvetica Neue", Arial, sans-serif')
    
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
            ]}])
    )
    
    # Clear progress display
    progress_bar.empty()
    status_text.empty()
    
    # Store results
    if source == "manual":
        st.session_state["manual_all_links"] = all_links
        st.session_state["manual_url_to_type"] = url_to_type
        st.session_state["manual_matrix_df"] = matrix_df
        st.session_state["manual_tooltip_df"] = tooltip_df
        st.session_state["manual_styled_matrix_html"] = styled_matrix.to_html()
    else:
        st.session_state["file_all_links"] = all_links
        st.session_state["file_url_to_type"] = url_to_type
        st.session_state["file_matrix_df"] = matrix_df
        st.session_state["file_tooltip_df"] = tooltip_df
        st.session_state["file_styled_matrix_html"] = styled_matrix.to_html()

def display_analysis_results(source="manual"):
    inject_custom_css()

    if source == "manual":
        if (st.session_state.get("manual_data") is None or
            st.session_state.get("manual_matrix_df") is None):
            st.write("No manual analysis results available yet. Please click 'Start Analysis'.")
            return
        data = st.session_state["manual_data"]
        all_links = st.session_state["manual_all_links"]
        url_to_type = st.session_state["manual_url_to_type"]
        matrix_df = st.session_state["manual_matrix_df"]
        styled_matrix_html = st.session_state["manual_styled_matrix_html"]
    else:
        if (st.session_state.get("file_data") is None or
            st.session_state.get("file_matrix_df") is None):
            st.write("No file upload analysis results available yet. Please click 'Start Analysis for the Uploaded File'.")
            return
        data = st.session_state["file_data"]
        all_links = st.session_state["file_all_links"]
        url_to_type = st.session_state["file_url_to_type"]
        matrix_df = st.session_state["file_matrix_df"]
        styled_matrix_html = st.session_state["file_styled_matrix_html"]

    # Full Matrix
    st.divider()
    st.subheader("Complete Interlinking Matrix")
    st.write("In the below matrix 1 indicates a link exists, 0 indicates no link, and NA indicates not applicable (self-link)")
    st.markdown(styled_matrix_html, unsafe_allow_html=True)
    
    st.divider()
    if ('Homepage' in data['type'].values and 'Target Page' in data['type'].values
        and 'Homepage' in matrix_df.index and 'Target Page' in matrix_df.columns):
        
        with st.expander("Homepage & Target Page Links", expanded=False):
            st.write("### Homepage and Target Page Interlinking")
            home_to_target = matrix_df.loc['Homepage', 'Target Page'] == 1
            target_to_home = matrix_df.loc['Target Page', 'Homepage'] == 1
            
            # Homepage -> Target
            if home_to_target:
                st.success("✓ Homepage links to Target Page")
                homepage_links_df = pd.DataFrame(all_links['Homepage'])
                target_links = homepage_links_df[
                    homepage_links_df['url'] == data[data['type'] == 'Target Page']['url'].values[0]
                ]
                if not target_links.empty:
                    st.write("Links found:")
                    st.dataframe(
                        target_links.assign(
                            type=target_links['url'].map(url_to_type)
                        )[['text', 'url', 'type']]
                    )
            else:
                st.error("✗ Homepage does not link to Target Page")
                
            # Target -> Homepage
            if target_to_home:
                st.success("✓ Target Page links to Homepage")
                target_links_df = pd.DataFrame(all_links['Target Page'])
                home_links = target_links_df[
                    target_links_df['url'] == data[data['type'] == 'Homepage']['url'].values[0]
                ]
                if not home_links.empty:
                    st.write("Links found:")
                    st.dataframe(
                        home_links.assign(
                            type=home_links['url'].map(url_to_type)
                        )[['text', 'url', 'type']]
                    )
            else:
                st.error("✗ Target Page does not link to Homepage")
            
            # Target Page Internal Links Breakdown
            st.write("### Target Page Internal Links Breakdown")
            target_links = all_links.get('Target Page', [])
            if not target_links:
                st.warning("No internal links found on the Target Page.")
            else:
                target_links_df = pd.DataFrame(target_links)
                target_links_df['linked_type'] = target_links_df['url'].map(url_to_type)
                
                # Remove self-links
                target_links_df = target_links_df[target_links_df['linked_type'] != 'Target Page']
                
                if target_links_df.empty:
                    st.warning("Target Page only contains self-references or invalid links")
                else:
                    grouped = target_links_df.groupby('linked_type')
                    for page_type, group in grouped:
                        st.success(f"✓ Links to {page_type}:")
                        st.dataframe(
                            group[['text', 'url', 'linked_type']]
                            .rename(columns={'linked_type': 'Page Type'})
                            .reset_index(drop=True)
                        )
                    
                    # Check for critical connections
                    critical_pages = ['Homepage'] + [typ for typ in data['type'] if typ.startswith('Blog')]
                    missing = []
                    for page in critical_pages:
                        if page not in target_links_df['linked_type'].values:
                            missing.append(page)
                    
                    # Use the same "Missing links to: X" style:
                    if missing:
                        st.error(f"Missing links to: {', '.join(missing)}")

    # Blog Interlinking
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
                    st.dataframe(
                        target_links.assign(
                            type=target_links['url'].map(url_to_type)
                        )[['text', 'url', 'type']]
                    )
                else:
                    st.error("✗ Does not link to Target Page")
                
                other_blogs = [b for b in blog_types if b != blog_type]
                other_blog_urls = data[data['type'].isin(other_blogs)]['url'].tolist()
                other_blog_links = blog_links_df[blog_links_df['url'].isin(other_blog_urls)]
                if not other_blog_links.empty:
                    st.write("Links to Other Blogs:")
                    st.dataframe(
                        other_blog_links.assign(
                            type=other_blog_links['url'].map(url_to_type)
                        )[['text', 'url', 'type']]
                    )
                
                missing_blogs = [
                    b for b in other_blogs 
                    if data[data['type'] == b]['url'].values[0] 
                    not in other_blog_links['url'].tolist()
                ]
                if missing_blogs:
                    st.error(f"Missing links to: {', '.join(missing_blogs)}")
                    
    st.divider()
    if st.button("Generate PDF Report", key=f"generate_pdf_{source}"):
        report_html = create_detailed_report_html(source=source)
        pdf_bytes = generate_pdf_report(report_html)
        st.download_button(
            label="Download PDF Report",
            data=pdf_bytes,
            file_name="internal_link_analysis.pdf",
            mime="application/pdf"
        )

def manual_input_tab():
    col1, col2 = st.columns(2)
    with col1:
        st.session_state["manual_homepage_url"] = st.text_input(
            "Homepage URL", 
            value=st.session_state.get("manual_homepage_url", ""), 
            placeholder="https://www.example.com"
        )
    with col2:
        st.session_state["manual_target_page_url"] = st.text_input(
            "Target Page URL", 
            value=st.session_state.get("manual_target_page_url", ""), 
            placeholder="https://www.example.com/target"
        )
    
    st.session_state["manual_num_blogs"] = st.number_input(
        "Number of Blog Pages to Analyze", 
        min_value=1, max_value=10, 
        value=st.session_state.get("manual_num_blogs", 3)
    )
    
    manual_blog_urls = st.session_state.get("manual_blog_urls", [])
    blog_urls = []
    num_blogs = int(st.session_state.get("manual_num_blogs", 3))
    for i in range(num_blogs):
        default_blog = manual_blog_urls[i] if i < len(manual_blog_urls) else ""
        blog_url = st.text_input(
            f"Blog {i+1} URL", 
            value=default_blog, 
            placeholder=f"https://www.example.com/blog-{i+1}", 
            key=f"manual_blog_{i}"
        )
        blog_urls.append(blog_url)
    st.session_state["manual_blog_urls"] = blog_urls
    
    all_urls = [st.session_state["manual_homepage_url"], st.session_state["manual_target_page_url"]] + blog_urls
    if not all(all_urls) or not all(is_valid_url(url) for url in all_urls):
        st.warning("Please enter valid URLs for all fields")
        return
    
    data = pd.DataFrame({
        'type': ['Homepage', 'Target Page'] + [f'Blog {i+1}' for i in range(len(blog_urls))],
        'url': all_urls
    })
    
    if st.button("Start Analysis"):
        run_analysis(data, source="manual")
        st.success("Manual analysis complete!")

def file_upload_tab():
    st.subheader("Smart Internal Linking Analysis")
    st.warning(
        """File Requirements:
        - Must be an Excel or CSV file
        - Must contain the columns 'type' and 'url'
        """
    )
    
    try:
        example_data = pd.read_csv('data/example_data.csv')
        st.dataframe(example_data)
    except Exception:
        st.info("Example file not found. Please upload your file.")
    
    uploaded_file = st.file_uploader("Upload Excel or CSV file for the analysis", type=['xlsx', 'csv'])
    if uploaded_file is not None:
        st.session_state["uploaded_file"] = uploaded_file
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
                run_analysis(data, source="file")
                st.success("File upload analysis complete!")

        except Exception as e:
            st.error(f"Error reading file: {e}")

def analyze_internal_links():
    st.header("Smart Internal Linking Analysis", divider='rainbow')
    
    # Custom tab styling
    st.markdown("""
    <style>
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            padding: 15px 25px;
            font-size: 18px;
            background-color: #f0f2f6;
            border-radius: 10px 10px 0 0;
            margin: 0 5px;
            transition: all 0.3s ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #e1e3e7;
        }
        .stTabs [aria-selected="true"] {
            background-color: #2e7d32 !important;
            color: white !important;
            font-weight: bold;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 5px;
            padding: 10px 0;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.expander("Understanding Reverse Content Silos"):
        st.markdown("""
        Reverse content silos represent a strategic internal linking structure where supporting content pieces interlink with each other and point to a central target page. In this structure:
        
        - Supporting articles link to each other to share authority
        - All supporting content points to a main target page
        - The target page connects with the homepage
        - Each supporting article can receive external back links
        """)
        col1, col2, col3 = st.columns([0.4, 2, 0.6])
        with col2:
            st.image(r"reverse_silos1.png", caption="Reverse Content Silos Analysis", width=600)
    
    tab1, tab2 = st.tabs(["User Input", "File Upload"])
    
    with tab1:
        manual_input_tab()
        if st.session_state.get("manual_data") is not None:
            display_analysis_results(source="manual")
    
    with tab2:
        file_upload_tab()
        if st.session_state.get("file_data") is not None:
            display_analysis_results(source="file")