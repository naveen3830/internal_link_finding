import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import time
import logging
from urllib3.exceptions import InsecureRequestWarning
import re
import requests.compat
from collections import defaultdict

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[^\w\s]', ' ', text)  
    text = re.sub(r'\s+', ' ', text)       
    return text.lower().strip()

def standardize_url(url):
    url = url.strip()
    if url.startswith("www."):
        url = "https://" + url
    elif not url.startswith(('http://', 'https://')):
        url = "https://" + url
    parsed = requests.compat.urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
    standardized = requests.compat.urlunparse(
        (parsed.scheme, netloc, path, '', '', '')
    )
    return standardized

def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'meta', 'link',
                                'h1', 'h2', 'h3', 'h4', 'h5', 'h6','strong','a']):
        element.decompose()
    classes_to_remove = [
        "position-relative mt-5 related-blog-post__swiper-container", "nav-red", "nav-label",
        "row left-zero__without-shape position-relative z-1 mt-4 mt-md-5 px-0","footer pt-lg-9 pb-lg-10 pb-8 pt-7",
        "related-blog-post related-blog-post--bottom-pattern position-relative overflow-hidden z-1 ps-3 px-sm-0 py-5 py-lg-7 bg-cool",
        "section-content", "row banner ",
        "contact-form position-relative generic-form gravity-form py-6 dark__form",
    ]
    for element in soup.find_all(class_=classes_to_remove):
        element.decompose()
    return soup

def check_existing_links(full_soup, keyword, source_url, target_url):
    cleaned_keyword = clean_text(keyword)
    keyword_terms = cleaned_keyword.split()
    if not keyword_terms:
        return False
    escaped_terms = [re.escape(term) for term in keyword_terms]
    pattern = re.compile(r'\b' + r'\s+'.join(escaped_terms) + r'\b', re.IGNORECASE)
    standardized_target = standardize_url(target_url)
    for a_tag in full_soup.find_all('a', href=True):
        link_text = a_tag.get_text(strip=True)
        if not link_text:
            continue
        cleaned_link_text = clean_text(link_text)
        if pattern.search(cleaned_link_text):
            href = a_tag.get('href', '')
            absolute_href = requests.compat.urljoin(source_url, href)
            standardized_href = standardize_url(absolute_href)
            if standardized_href == standardized_target:
                return True
    return False

def find_unlinked_keywords(soup, keyword, target_url):
    keyword = keyword.strip()
    cleaned_keyword = clean_text(keyword)
    keyword_terms = cleaned_keyword.split()
    if not keyword_terms:
        return []
    forbidden_terms = ["solution", "service", "software", "app", "platforms", "solutions", "services", "softwares", "apps", "platform"]
    keyword_lower = keyword.lower()
    ends_with_forbidden = any(keyword_lower.endswith(term) for term in forbidden_terms)
    escaped_terms = [re.escape(term) for term in keyword_terms]
    keyword_pattern = re.compile(r'\b' + r'\s+'.join(escaped_terms) + r'\b', re.IGNORECASE)
    forbidden_pattern = None
    if not ends_with_forbidden:
        forbidden_regex_str = r'\s+(' + '|'.join(forbidden_terms) + r')\b'
        forbidden_pattern = re.compile(keyword_pattern.pattern + forbidden_regex_str, re.IGNORECASE)
    unlinked_occurrences = []
    paragraphs = soup.find_all('p')
    word_count = 0
    exclusion_threshold = 50
    for p_tag in paragraphs:
        original_paragraph_text = p_tag.get_text(strip=True)
        if not original_paragraph_text:
            continue
        cleaned_paragraph_text = clean_text(original_paragraph_text)
        paragraph_word_count = len(cleaned_paragraph_text.split())
        if word_count + paragraph_word_count < exclusion_threshold:
            word_count += paragraph_word_count
            continue
        if keyword_pattern.search(cleaned_paragraph_text):
            if forbidden_pattern and forbidden_pattern.search(cleaned_paragraph_text):
                continue
            unlinked_occurrences.append({
                'context': original_paragraph_text,
                'keyword': keyword,
                'target_url': target_url
            })
            break
        word_count += paragraph_word_count
    return unlinked_occurrences

def process_single_url_for_all_keywords(url, keyword_url_pairs, session):
    try:
        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        }
        response = session.get(url, headers=headers, timeout=20, verify=False)
        response.raise_for_status()
        html_content = response.text
        
        full_soup = BeautifulSoup(html_content, 'lxml')
        clean_soup = extract_text_from_html(html_content)
        
        results_for_this_url = []
        for keyword, target_url in keyword_url_pairs:
            if check_existing_links(full_soup, keyword, url, target_url):
                continue
            unlinked_matches = find_unlinked_keywords(clean_soup, keyword, target_url)
            if unlinked_matches:
                results_for_this_url.extend(unlinked_matches)
        
        return {'url': url, 'unlinked_matches': results_for_this_url} if results_for_this_url else None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing {url}: {str(e)}")
        return None

@st.cache_data
def convert_df_to_csv(download_data):
    download_df = pd.DataFrame(download_data)
    return download_df.to_csv(index=False).encode('utf-8')

def manual_input_internal_linking():
    session_vars = [
        'uploaded_df_manual', 'keyword_inputs_manual', 'target_url_inputs_manual',
        'processed_results_manual', 'num_pairs_manual', 'processing_done_manual'
    ]
    for var in session_vars:
        if var not in st.session_state:
            st.session_state[var] = None if 'num_pairs' not in var else 1
            if 'inputs' in var:
                st.session_state[var] = ['']
            if 'done' in var:
                st.session_state[var] = False
    
    df = None
    if 'filtered_df' in st.session_state and st.session_state.filtered_df is not None:
        st.success("Using filtered data from a previous module.")
        df = st.session_state.filtered_df
    else:
        uploaded_file = st.file_uploader("Upload CSV or Excel file with a 'source_url' column",
                                        type=["csv", "xlsx"],
                                        key="url_file_uploader_manual")
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
                df.columns = df.columns.str.strip().str.lower()
                st.write("Loaded data:", df.head())
                st.session_state.uploaded_df_manual = df
            except Exception as e:
                st.error(f"An error occurred while reading the file: {str(e)}")
                return
        elif 'uploaded_df_manual' in st.session_state and st.session_state.uploaded_df_manual is not None:
            df = st.session_state.uploaded_df_manual

    st.subheader("Keywords and Target URLs")
    num_pairs = st.number_input("Number of keyword-URL pairs", min_value=1, value=st.session_state.num_pairs_manual,
                                key='num_pairs_input_manual')
    st.session_state.num_pairs_manual = num_pairs

    for inputs in ['keyword_inputs_manual', 'target_url_inputs_manual']:
        if len(st.session_state[inputs]) < num_pairs:
            st.session_state[inputs].extend([''] * (num_pairs - len(st.session_state[inputs])))
        elif len(st.session_state[inputs]) > num_pairs:
            st.session_state[inputs] = st.session_state[inputs][:num_pairs]

    keyword_url_pairs = []
    for i in range(num_pairs):
        col1, col2 = st.columns(2)
        keyword = col1.text_input(f"Keyword {i+1}", value=st.session_state.keyword_inputs_manual[i], key=f"keyword_input_manual_{i}")
        target_url = col2.text_input(f"Target URL {i+1}", value=st.session_state.target_url_inputs_manual[i], key=f"target_url_input_manual_{i}")
        st.session_state.keyword_inputs_manual[i] = keyword
        st.session_state.target_url_inputs_manual[i] = target_url
        if keyword.strip() and target_url.strip():
            keyword_url_pairs.append((keyword.strip(), target_url.strip()))

    max_workers = st.slider("Concurrent searches", min_value=1, max_value=20, value=15,
                            help="Number of URLs to process simultaneously", key="slider_manual")

    if st.button("Process URLs", key="process_button_manual"):
        if df is not None and keyword_url_pairs:
            try:
                if 'source_url' not in df.columns:
                    st.error("File must contain a 'source_url' column")
                    return
                source_urls = df['source_url'].dropna().astype(str).str.strip().unique()
                target_urls_set = {standardize_url(u) for k, u in keyword_url_pairs}
                urls_to_process = [standardize_url(url) for url in source_urls if standardize_url(url) not in target_urls_set]
                if not urls_to_process:
                    st.warning("All source URLs are also target URLs. Nothing to process.")
                    return
                st.info(f"Processing {len(urls_to_process)} URLs...")
                start_time = time.time()
                progress_bar = st.progress(0)
                status_text = st.empty()
                processed = 0
                results = []
                with requests.Session() as session:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_url = {
                            executor.submit(process_single_url_for_all_keywords, url, keyword_url_pairs, session): url
                            for url in urls_to_process
                        }
                        total_tasks = len(future_to_url)
                        for future in concurrent.futures.as_completed(future_to_url):
                            processed += 1
                            progress_bar.progress(processed / total_tasks)
                            status_text.text(f"Processed {processed}/{total_tasks} URLs...")
                            result = future.result()
                            if result:
                                results.append(result)
                progress_bar.empty()
                status_text.empty()
                duration = time.time() - start_time
                st.info(f"Search completed in {duration:.2f} seconds")
                st.session_state.processed_results_manual = results if results else []
                st.session_state.processing_done_manual = True
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("Please provide all inputs and ensure valid data is available.")
            
    if st.session_state.processing_done_manual:
        results = st.session_state.processed_results_manual
        if results:
            download_data = []
            for result in results:
                if result.get('unlinked_matches'):
                    for match in result['unlinked_matches']:
                        download_data.append({
                            'source_url': result['url'],
                            'keyword': match['keyword'],
                            'target_url': match['target_url'],
                            'context': match['context']
                        })
            num_opportunities = len(download_data)
            matched_urls = len(set(item['source_url'] for item in download_data))
            st.success(f"Found {num_opportunities} opportunities across {matched_urls} URLs")

            # UPDATED DISPLAY LOGIC
            with st.expander("View Opportunities", expanded=True):
                grouped_data = defaultdict(list)
                for item in download_data:
                    grouped_data[item['source_url']].append(item)
                for url, items in grouped_data.items():
                    st.write("---")
                    st.markdown(f"🔗 **Source URL:** [{url}]({url})")
                    st.write("Unlinked Keyword Occurrences:")
                    for match_info in items:
                        st.markdown(f"- *{match_info['keyword']}* → [{match_info['target_url']}]({match_info['target_url']})")
                        st.markdown(f"Context: *{match_info['context']}*")
                        st.write("") # Adds a small space for readability
            # END UPDATED BLOCK

            if download_data:
                csv = convert_df_to_csv(download_data)
                st.download_button(
                    label="Download Opportunities CSV",
                    data=csv,
                    file_name='unlinked_keyword_opportunities.csv',
                    mime='text/csv',
                    key='download_opportunities_csv_manual'
                )
        else:
            st.info("No interlinking opportunities found.")

def file_upload_internal_linking():
    session_vars = ['uploaded_urls_file', 'search_results_file', 'completed_processing_file', 'keyword_target_pairs_file']
    for var in session_vars:
        if var not in st.session_state:
            st.session_state[var] = None
    if 'completed_processing_file' not in st.session_state:
        st.session_state.completed_processing_file = False
    
    df_urls, df_keywords = None, None
    if 'filtered_df' in st.session_state and st.session_state.filtered_df is not None:
        st.success("Using filtered data from a previous module.")
        df_urls = st.session_state.filtered_df
    else:
        uploaded_urls_file = st.file_uploader(
            "Upload CSV/Excel with source URLs (must contain 'source_url' column)",
            type=["csv", "xlsx"], key="uploaded_urls_uploader_file"
        )
        if uploaded_urls_file:
            try:
                df_urls = pd.read_csv(uploaded_urls_file) if uploaded_urls_file.name.endswith('.csv') else pd.read_excel(uploaded_urls_file)
                df_urls.columns = df_urls.columns.str.strip().str.lower()
                if 'source_url' not in df_urls.columns:
                    st.error("File must contain a 'source_url' column.")
                    return
                st.session_state.uploaded_urls_file = df_urls
            except Exception as e:
                st.error(f"Error reading source URLs file: {e}")
                return
        elif 'uploaded_urls_file' in st.session_state and st.session_state.uploaded_urls_file is not None:
            df_urls = st.session_state.uploaded_urls_file

    keyword_url_file = st.file_uploader(
        "Upload CSV/Excel with keywords & targets (must contain 'keyword' and 'target_url' columns)",
        type=["csv", "xlsx"], key="keyword_target_url_uploader_file"
    )
    if keyword_url_file:
        try:
            df_keywords = pd.read_csv(keyword_url_file) if keyword_url_file.name.endswith('.csv') else pd.read_excel(keyword_url_file)
            df_keywords.columns = df_keywords.columns.str.strip().str.lower()
            if not {'keyword', 'target_url'}.issubset(df_keywords.columns):
                st.error("File must contain both 'keyword' and 'target_url' columns.")
                return
            st.session_state.keyword_target_pairs_file = df_keywords
        except Exception as e:
            st.error(f"Error reading keyword-URL file: {e}")
            return
    elif 'keyword_target_pairs_file' in st.session_state and st.session_state.keyword_target_pairs_file is not None:
        df_keywords = st.session_state.keyword_target_pairs_file

    max_workers = st.slider("Concurrent searches", min_value=1, max_value=20, value=15,
        help="Number of URLs to process simultaneously", key="slider_file")

    if st.button("Process URLs", key="process_files"):
        if df_urls is None or df_keywords is None:
            st.error("Please upload both source URLs and keyword-target URL pairs files.")
            return
        try:
            source_urls = df_urls['source_url'].dropna().astype(str).str.strip().unique()
            df_keywords.dropna(subset=['keyword', 'target_url'], inplace=True)
            keyword_url_pairs = list(df_keywords[['keyword', 'target_url']].itertuples(index=False, name=None))
            target_urls_set = {standardize_url(u) for k, u in keyword_url_pairs}
            urls_to_process = [standardize_url(url) for url in source_urls if standardize_url(url) not in target_urls_set]
            if not urls_to_process:
                st.warning("All provided source URLs are also target URLs. Nothing to process.")
                return
            st.info(f"Processing {len(urls_to_process)} URLs against {len(keyword_url_pairs)} keyword pairs...")
            start_time = time.time()
            progress_bar = st.progress(0)
            status_text = st.empty()
            processed = 0
            results = []
            with requests.Session() as session:
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_url = {
                        executor.submit(process_single_url_for_all_keywords, url, keyword_url_pairs, session): url
                        for url in urls_to_process
                    }
                    total_tasks = len(future_to_url)
                    for future in concurrent.futures.as_completed(future_to_url):
                        processed += 1
                        progress_bar.progress(processed / total_tasks)
                        status_text.text(f"Processed {processed}/{total_tasks} URLs...")
                        result = future.result()
                        if result:
                            results.append(result)
            progress_bar.empty()
            status_text.empty()
            duration = time.time() - start_time
            st.info(f"Search completed in {duration:.2f} seconds")
            st.session_state.search_results_file = results if results else []
            st.session_state.completed_processing_file = True
        except Exception as e:
            st.error(f"An error occurred: {e}")

    if st.session_state.completed_processing_file:
        results = st.session_state.search_results_file
        if results:
            download_data = []
            for result in results:
                if result.get('unlinked_matches'):
                    for match in result['unlinked_matches']:
                        download_data.append({
                            'source_url': result['url'],
                            'keyword': match['keyword'],
                            'target_url': match['target_url'],
                            'context': match['context']
                        })
            num_opportunities = len(download_data)
            matched_urls = len({item['source_url'] for item in download_data})
            st.success(f"Found {num_opportunities} opportunities across {matched_urls} URLs")

            if num_opportunities > 0:
                # UPDATED DISPLAY LOGIC
                with st.expander("View Opportunities", expanded=True):
                    grouped_data = defaultdict(list)
                    for item in download_data:
                        grouped_data[item['source_url']].append(item)
                    for url, items in grouped_data.items():
                        st.write("---")
                        st.markdown(f"🔗 **Source URL:** [{url}]({url})")
                        st.write("Unlinked Keyword Occurrences:")
                        for match_info in items:
                            st.markdown(f"- *{match_info['keyword']}* → [{match_info['target_url']}]({match_info['target_url']})")
                            st.markdown(f"Context: *{match_info['context']}*")
                            st.write("") # Adds a small space for readability
                # END UPDATED BLOCK
                
                csv = convert_df_to_csv(download_data)
                st.download_button(
                    label="Download Opportunities CSV",
                    data=csv,
                    file_name='unlinked_keyword_opportunities.csv',
                    mime='text/csv',
                    key='download_csv_file'
                )
        else:
            st.info("No interlinking opportunities found.")

def internal_linking_opportunities_finder():
    st.set_page_config(page_title="Internal Linking Finder", layout="wide")
    st.markdown("""
    <style>
        .stTabs [data-baseweb="tab"] { height: 45px; padding: 15px 25px; font-size: 18px; background-color: #f0f2f6; border-radius: 10px 10px 0 0; margin: 0 5px; transition: all 0.3s ease; }
        .stTabs [data-baseweb="tab"]:hover { background-color: #e1e3e7; }
        .stTabs [aria-selected="true"] { background-color: #2e7d32 !important; color: white !important; font-weight: bold; }
        .stTabs [data-baseweb="tab-list"] { gap: 5px; padding: 10px 0; }
    </style>
    """, unsafe_allow_html=True)
        
    st.header("Internal Linking Opportunities Finder", divider='rainbow')
    st.markdown("This tool finds internal linking opportunities across provided URLs.")
    tab1, tab2 = st.tabs(["User Input", "File Upload"])
    with tab1:
        manual_input_internal_linking()
    with tab2:
        file_upload_internal_linking()