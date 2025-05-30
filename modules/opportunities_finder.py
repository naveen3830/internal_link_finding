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

# Disable warnings
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
    soup = BeautifulSoup(html_content, 'html.parser')
    # Remove navigation and other noisy elements
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'meta', 'link',
                                'h1', 'h2', 'h3', 'h4', 'h5', 'h6','strong','a']):
        element.decompose()
    classes_to_remove = [
        "position-relative mt-5 related-blog-post__swiper-container",
        "nav-red", "nav-label",
        "row left-zero__without-shape position-relative z-1 mt-4 mt-md-5 px-0","footer pt-lg-9 pb-lg-10 pb-8 pt-7",
        "related-blog-post related-blog-post--bottom-pattern position-relative overflow-hidden z-1 ps-3 px-sm-0 py-5 py-lg-7 bg-cool","footer pt-lg-9 pb-lg-10 pb-8 pt-7",
        "section-content", "row banner ",
        "contact-form position-relative generic-form gravity-form py-6 dark__form", 
        #"training-container","css-xzv94c e108hv3e5", "faq-area bg-white rounded-0 pb-3 pb-lg-4"
    ]
    for element in soup.find_all(class_=classes_to_remove):
        element.decompose()
    return soup

def check_existing_links(full_soup, keyword, source_url, target_url):
    """Check if keyword exists in any anchor text linking to the target URL"""
    cleaned_keyword = clean_text(keyword)
    keyword_terms = cleaned_keyword.split()
    
    if not keyword_terms:
        return False

    escaped_terms = [re.escape(term) for term in keyword_terms]
    pattern = r'\b' + r'\s+'.join(escaped_terms) + r'\b'

    standardized_target = standardize_url(target_url)
    for a_tag in full_soup.find_all('a'):
        link_text = a_tag.get_text(strip=True)
        if not link_text:
            continue
            
        cleaned_link_text = clean_text(link_text)
        if re.search(pattern, cleaned_link_text):
            href = a_tag.get('href', '')
            if not href:
                continue
            absolute_href = requests.compat.urljoin(source_url, href)
            standardized_href = standardize_url(absolute_href)
            if standardized_href == standardized_target:
                return True
    return False
def find_unlinked_keywords(soup, keyword, target_url):
    """Find unlinked keyword occurrences in cleaned content, excluding first 50 words and forbidden suffixes"""
    keyword = keyword.strip()
    cleaned_keyword = clean_text(keyword)
    keyword_terms = cleaned_keyword.split()
    
    if not keyword_terms:
        return []

    forbidden_terms = ["solution", "service", "software", "app", "platforms","solutions", "services", "softwares", "apps", "platform"]
    keyword_lower = keyword.lower()
    ends_with_forbidden = any(keyword_lower.endswith(term) for term in forbidden_terms)
    
    escaped_terms = [re.escape(term) for term in keyword_terms]
    pattern = r'\b' + r'\s+'.join(escaped_terms) + r'\b'
    unlinked_occurrences = []

    paragraphs = soup.find_all('p')
    original_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
    sentences = re.split(r'(?<=[.!?])\s+', original_text)
    cumulative_word_count = 0
    exclusion_threshold = 50
    
    for sentence in sentences:
        cleaned_sentence = clean_text(sentence)
        sentence_words = cleaned_sentence.split()
        num_words = len(sentence_words)

        if num_words == 0:
            continue
            
        start_count = cumulative_word_count
        end_count = cumulative_word_count + num_words
        cumulative_word_count = end_count
        
        if end_count <= exclusion_threshold:
            continue 
        elif start_count < exclusion_threshold:
            words_to_include = end_count - exclusion_threshold
            relevant_part = ' '.join(sentence_words[-words_to_include:])
        else:
            relevant_part = cleaned_sentence

        if re.search(pattern, relevant_part):
            if ends_with_forbidden:
                unlinked_occurrences.append({
                    'context': sentence.strip(),
                    'keyword': keyword,
                    'target_url': target_url
                })
            else:
                forbidden_pattern = pattern + r'\s+(' + '|'.join(forbidden_terms) + r')\b'
                if not re.search(forbidden_pattern, relevant_part):
                    unlinked_occurrences.append({
                        'context': sentence.strip(),
                        'keyword': keyword,
                        'target_url': target_url
                    })
    
    return unlinked_occurrences


def process_url(url, keyword, target_url):
    url = standardize_url(url)
    target_url = standardize_url(target_url)
    
    if url.rstrip('/').lower() == target_url.rstrip('/').lower():
        return None
    try:
        headers = {
            'User-Agent': ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()

        full_soup = BeautifulSoup(response.text, 'html.parser')
        if check_existing_links(full_soup, keyword, url, target_url):
            logger.info(f"Excluding {url} - existing link found for '{keyword}' to target URL")
            return None

        clean_soup = extract_text_from_html(response.text)
        unlinked_matches = find_unlinked_keywords(clean_soup, keyword, target_url)
        
        return {'url': url, 'unlinked_matches': unlinked_matches} if unlinked_matches else None

    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
        return None

@st.cache_data
def convert_df_to_csv(download_data):
    download_df = pd.DataFrame(download_data)
    return download_df.to_csv(index=False).encode('utf-8')

def manual_input_internal_linking():
    session_vars = [
        'uploaded_df', 'keyword_inputs', 'target_url_inputs',
        'processed_results', 'num_pairs', 'processing_done'
    ]
    for var in session_vars:
        if var not in st.session_state:
            st.session_state[var] = None if var != 'num_pairs' else 1
            if var in ['keyword_inputs', 'target_url_inputs']:
                st.session_state[var] = ['']
            if var == 'processing_done':
                st.session_state[var] = False

    df = None
    if 'filtered_df' in st.session_state and st.session_state.filtered_df is not None:
        st.success("Using filtered data from the previous tab.")
        df = st.session_state.filtered_df
    else:
        uploaded_file = st.file_uploader("Upload CSV or Excel file with URLs",
                                        type=["csv", "xlsx"],
                                        key="url_file_uploader_manual")
        if uploaded_file:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                df.columns = df.columns.str.strip().str.lower()
                st.write("Loaded data:", df.head())
                st.session_state.uploaded_df = df
            except Exception as e:
                st.error(f"An error occurred while reading the file: {str(e)}")
                return

    st.subheader("Keywords and Target URLs")
    num_pairs = st.number_input("Number of keyword-URL pairs", min_value=1, value=st.session_state.num_pairs,
                                key='num_pairs_input_manual')
    st.session_state.num_pairs = num_pairs

    for inputs in ['keyword_inputs', 'target_url_inputs']:
        if len(st.session_state[inputs]) < num_pairs:
            st.session_state[inputs] += [''] * (num_pairs - len(st.session_state[inputs]))

    keyword_inputs = []
    target_url_inputs = []
    for i in range(num_pairs):
        col1, col2 = st.columns([3, 3])
        with col1:
            keyword = st.text_input(
                f"Keyword {i+1}", 
                value=st.session_state.keyword_inputs[i],
                key=f"keyword_input_manual_{i}"
            )
            keyword_inputs.append(keyword)
        with col2:
            target_url = st.text_input(
                f"Target URL {i+1}",
                value=st.session_state.target_url_inputs[i],
                key=f"target_url_input_manual_{i}"
            )
            target_url_inputs.append(target_url)
    st.session_state.keyword_inputs = keyword_inputs
    st.session_state.target_url_inputs = target_url_inputs

    max_workers = st.slider("Concurrent searches", min_value=1, max_value=15, value=15,
                            help="Number of URLs to process simultaneously", key="slider_manual")

    if st.button("Process URLs", key="process_button_manual"):
        keyword_url_pairs = [(k.strip(), u.strip()) 
                            for k, u in zip(keyword_inputs, target_url_inputs) 
                            if k.strip() and u.strip()]
        if df is not None and keyword_url_pairs:
            try:
                if 'source_url' not in df.columns:
                    st.error("File must contain a 'source_url' column")
                    return

                df['source_url'] = df['source_url'].astype(str).str.strip()
                url_regex = r'^(https?://|www\.)[^\s<>"]+'
                valid_urls = df['source_url'].str.match(url_regex)
                df = df[valid_urls].copy()
                
                df['source_url'] = df['source_url'].apply(standardize_url)

                if df.empty:
                    st.error("No valid URLs found in the file")
                    return

                st.info(f"Processing {len(df)} URLs...")
                start_time = time.time()
                progress_bar = st.progress(0)
                processed = 0
                results = []

                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = []
                    for url in df['source_url'].unique():
                        for keyword, target_url in keyword_url_pairs:
                            futures.append(executor.submit(process_url, url, keyword, target_url))
                    total_tasks = len(futures)
                    for future in concurrent.futures.as_completed(futures):
                        processed += 1
                        progress_bar.progress(processed / total_tasks)
                        result = future.result()
                        if result:
                            results.append(result)

                progress_bar.empty()
                duration = time.time() - start_time
                st.info(f"Search completed in {duration:.2f} seconds")

                st.session_state.processed_results = results if results else None
                st.session_state.processing_done = True

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("Please provide all inputs and ensure valid data is available.")
            
    if st.session_state.processing_done:
        if st.session_state.processed_results:
            download_data = []
            
            for result in st.session_state.processed_results:
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

            with st.expander("View Opportunities", expanded=True):
                from collections import defaultdict
                grouped_data = defaultdict(list)
                for item in download_data:
                    grouped_data[item['source_url']].append(item)

                for url, items in grouped_data.items():
                    st.write("---")
                    st.write(f"🔗 **Source URL**: {url}")
                    st.write("Unlinked Keyword Occurrences:")
                    for match_info in items:
                        st.markdown(f"- *{match_info['keyword']}* → {match_info['target_url']}")
                        st.markdown(f"  Context: _{match_info['context']}_")

            if download_data:
                csv = convert_df_to_csv(download_data)
                st.download_button(
                    label="Download Opportunities CSV",
                    data=csv,
                    file_name='unlinked_keyword_opportunities.csv',
                    mime='text/csv',
                    key='download_opportunities_csv'
                )
            else:
                st.info("No interlinking opportunities found.")
        else:
            st.info("No interlinking opportunities found.")

def file_upload_internal_linking():
    session_vars = ['uploaded_urls', 'search_results', 'completed_processing', 'keyword_target_pairs']
    for var in session_vars:
        if var not in st.session_state:
            st.session_state[var] = None
    if 'completed_processing' not in st.session_state:
        st.session_state.completed_processing = False

    df = None
    if 'filtered_df' in st.session_state and st.session_state.filtered_df is not None:
        st.success("Using filtered data from the previous tab.")
        df = st.session_state.filtered_df
    else:
        uploaded_file = st.file_uploader(
            "Upload CSV/Excel with source URLs (must contain 'source_url' column)",
            type=["csv", "xlsx"],
            key="uploaded_urls_uploader_file"
        )
        if uploaded_file:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                df.columns = df.columns.str.strip().str.lower()
                st.write("Loaded source URLs:", df.head())
                if 'source_url' not in df.columns:
                    st.error("File must contain a 'source_url' column")
                    return
                df['source_url'] = df['source_url'].astype(str).str.strip()
                url_regex = r'^(https?://|www\.)[^\s<>"]+'
                valid_urls = df['source_url'].str.match(url_regex)
                df = df[valid_urls].copy()
                df['source_url'] = df['source_url'].apply(standardize_url)
                if df.empty:
                    st.error("No valid URLs found in the file")
                    return
                st.session_state.uploaded_urls = df
            except Exception as e:
                st.error(f"Error reading source URLs file: {str(e)}")
                return
        elif st.session_state.get("uploaded_urls") is not None:
            df = st.session_state.uploaded_urls

    st.subheader("Upload Keyword-Target URL Pairs")
    keyword_url_file = st.file_uploader(
        "Upload CSV/Excel with keyword-target URL pairs (must contain 'keyword' and 'target_url' columns)",
        type=["csv", "xlsx"],
        key="keyword_target_url_uploader_file"
    )
    
    keyword_url_df = None
    if keyword_url_file:
        try:
            if keyword_url_file.name.endswith(".csv"):
                keyword_url_df = pd.read_csv(keyword_url_file)
            else:
                keyword_url_df = pd.read_excel(keyword_url_file)
            keyword_url_df.columns = keyword_url_df.columns.str.strip().str.lower()
            if not {'keyword', 'target_url'}.issubset(keyword_url_df.columns):
                st.error("File must contain both 'keyword' and 'target_url' columns")
                return
                
            keyword_url_df = keyword_url_df.dropna(subset=['keyword', 'target_url'])
            keyword_url_df['keyword'] = keyword_url_df['keyword'].str.strip()
            keyword_url_df['target_url'] = keyword_url_df['target_url'].str.strip()
            keyword_url_df = keyword_url_df[(keyword_url_df['keyword'] != '') & (keyword_url_df['target_url'] != '')]
            
            if keyword_url_df.empty:
                st.error("No valid keyword-URL pairs found in the file")
                return
            
            st.session_state.keyword_target_pairs = keyword_url_df
        except Exception as e:
            st.error(f"Error reading keyword-URL file: {str(e)}")
            return
    elif st.session_state.get("keyword_target_pairs") is not None:
        keyword_url_df = st.session_state.keyword_target_pairs

    max_workers = st.slider(
        "Concurrent searches", 
        min_value=1, 
        max_value=15, 
        value=15,
        help="Number of URLs to process simultaneously",
        key="slider_file"
    )

    if st.button("Process URLs", key="process_urls"):
        if df is None or keyword_url_df is None:
            st.error("Please provide both source URLs and keyword-target URL pairs files")
            return
        try:
            source_urls = df['source_url'].unique()
            keyword_url_pairs = list(keyword_url_df[['keyword', 'target_url']].itertuples(index=False, name=None))
            
            st.info(f"Processing {len(source_urls)} URLs against {len(keyword_url_pairs)} keyword-target URL pairs...")
            start_time = time.time()
            progress_bar = st.progress(0)
            processed = 0
            results = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for url in source_urls:
                    for keyword, target_url in keyword_url_pairs:
                        futures.append(executor.submit(process_url, url, keyword, target_url))
                total_tasks = len(futures)
                for future in concurrent.futures.as_completed(futures):
                    processed += 1
                    progress_bar.progress(processed / total_tasks)
                    result = future.result()
                    if result:
                        results.append(result)

            progress_bar.empty()
            duration = time.time() - start_time
            st.info(f"Search completed in {duration:.2f} seconds")

            st.session_state.search_results = results if results else None
            st.session_state.completed_processing = True

        except Exception as e:
            st.error(f"An error occurred: {e}")

    if st.session_state.completed_processing:
        if st.session_state.search_results:
            download_data = []
            for result in st.session_state.search_results:
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
                with st.expander("View Opportunities", expanded=True):
                    from collections import defaultdict
                    grouped_data = defaultdict(list)
                    for item in download_data:
                        grouped_data[item['source_url']].append(item)

                    for url, items in grouped_data.items():
                        st.write("---")
                        st.write(f"🔗 Source URL: {url}")
                        st.write("Unlinked Keyword Occurrences:")
                        for match_info in items:
                            st.markdown(f"- *{match_info['keyword']}* → {match_info['target_url']}")
                            st.markdown(f"  Context: _{match_info['context']}_")

                csv = convert_df_to_csv(download_data)
                st.download_button(
                    label="Download Opportunities CSV",
                    data=csv,
                    file_name='unlinked_keyword_opportunities.csv',
                    mime='text/csv',
                    key='download_csv'
                )
            else:
                st.info("No interlinking opportunities found.")
        else:
            st.info("No interlinking opportunities found.")

def internal_linking_opportunities_finder():
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
        
    st.header("Internal Linking Opportunities Finder", divider='rainbow')
    st.markdown("This tool finds internal linking opportunities across provided URLs.")
    tab1, tab2 = st.tabs(["User Input", "File Upload"])
    with tab1:
        manual_input_internal_linking()
    with tab2:
        file_upload_internal_linking()
