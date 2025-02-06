import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import time
import logging
from urllib3.exceptions import InsecureRequestWarning
import re

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text(text):
    """Clean and normalize text for consistent matching."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def extract_text_from_html(html_content):
    """Extract meaningful text from HTML while preserving structure."""
    soup = BeautifulSoup(html_content, 'html.parser')
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'meta', 'link', 'h1', 'h2', 'h3','h4','h5','h6']):
        element.decompose()

    for element in soup.find_all(attrs={"class": [
        "position-relative mt-5 related-blog-post__swiper-container", 
        "row left-zero__without-shape position-relative z-1 mt-4 mt-md-5 px-0"
    ]}):
        element.decompose()
    
    return soup

def find_unlinked_keywords(soup, keyword, target_url):
    keyword = keyword.strip()
    cleaned_keyword = clean_text(keyword)
    keyword_terms = cleaned_keyword.split()
    
    if not keyword_terms:
        return []

    escaped_terms = [re.escape(term) for term in keyword_terms]
    pattern = r'\b' + r'\s+'.join(escaped_terms) + r'\b'
    unlinked_occurrences = []
    text_elements = soup.find_all(text=True)
    
    for element in text_elements:
        if not element.strip() or element.find_parents('a'):
            continue
        
        original_text = element.strip()
        sentences = re.split(r'(?<=[.!?])\s+', original_text)
        
        for sentence in sentences:
            cleaned_sentence = clean_text(sentence)
            matches = re.findall(pattern, cleaned_sentence)
            if matches:
                for _ in matches:
                    unlinked_occurrences.append({
                        'context': sentence.strip(),
                        'keyword': keyword,
                        'target_url': target_url
                    })
    
    return unlinked_occurrences

def process_url(url, keyword, target_url):
    """Process a single URL to find unlinked keyword opportunities."""
    if url.strip().rstrip('/') == target_url.strip().rstrip('/'):
        return None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = extract_text_from_html(response.text)
        unlinked_matches = find_unlinked_keywords(soup, keyword, target_url)
        
        if unlinked_matches:
            return {
                'url': url,
                'unlinked_matches': unlinked_matches
            }
        return None
    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
        return None

@st.cache_data
def convert_df_to_csv(download_data):
    """Cache the CSV generation to prevent re-computation."""
    download_df = pd.DataFrame(download_data)
    return download_df.to_csv(index=False).encode('utf-8')

def file_uploader_feature():
    st.header("Internal Linking Opportunities Finder", divider='rainbow')
    session_vars = ['uploaded_df', 'processed_results', 'processing_done', 'keyword_url_pairs_df']
    for var in session_vars:
        if var not in st.session_state:
            st.session_state[var] = None
    if 'processing_done' not in st.session_state:
        st.session_state.processing_done = False

    df = None
    if 'filtered_df' in st.session_state and st.session_state.filtered_df is not None:
        st.success("Using filtered data from the previous tab.")
        df = st.session_state.filtered_df
    else:
        uploaded_file = st.file_uploader("Upload CSV/Excel with source URLs (must contain 'source_url' column)",type=["csv", "xlsx"],key="url_file_uploader")
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                if 'source_url' not in df.columns:
                    st.error("File must contain a 'source_url' column")
                    return
                
                df['source_url'] = df['source_url'].astype(str).str.strip()
                valid_urls = df['source_url'].str.match(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
                df = df[valid_urls].copy()
                
                if df.empty:
                    st.error("No valid URLs found in the file")
                    return
                
                st.session_state.uploaded_df = df
            except Exception as e:
                st.error(f"Error reading source URLs file: {str(e)}")
                return
        elif st.session_state.uploaded_df is not None:
            df = st.session_state.uploaded_df

    st.subheader("Keyword-Target URL Pairs Upload", divider='rainbow')
    keyword_url_file = st.file_uploader("Upload CSV/Excel with keyword-target URL pairs (must contain 'keyword' and 'target_url' columns)",type=["csv", "xlsx"],key="keyword_url_uploader")
    
    keyword_url_df = None
    if keyword_url_file:
        try:
            if keyword_url_file.name.endswith(".csv"):
                keyword_url_df = pd.read_csv(keyword_url_file)
            else:
                keyword_url_df = pd.read_excel(keyword_url_file)
            
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
            
            st.session_state.keyword_url_pairs_df = keyword_url_df
        except Exception as e:
            st.error(f"Error reading keyword-URL file: {str(e)}")
            return
    elif 'keyword_url_pairs_df' in st.session_state and st.session_state.keyword_url_pairs_df is not None:
        keyword_url_df = st.session_state.keyword_url_pairs_df

    max_workers = st.slider("Concurrent searches", 
                        min_value=1, 
                        max_value=15, 
                        value=15,
                        help="Number of URLs to process simultaneously")

    if st.button("Process"):
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
                    progress = processed / total_tasks
                    progress_bar.progress(progress)
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

    if st.session_state.processed_results:
        download_data = []
        matched_urls = len({res['url'] for res in st.session_state.processed_results})
        st.success(f"Found {len(st.session_state.processed_results)} opportunities across {matched_urls} URLs")

        with st.expander("View Opportunities", expanded=True):
            for result in st.session_state.processed_results:
                st.write("---")
                st.write(f"🔗 Source URL: {result['url']}")

                if result.get('unlinked_matches'):
                    st.write("Unlinked Keyword Occurrences:")
                    for match in result['unlinked_matches']:
                        st.markdown(f"- *{match['keyword']}* → {match['target_url']}")
                        st.markdown(f"  Context: _{match['context']}_")
                        download_data.append({
                            'source_url': result['url'],
                            'keyword': match['keyword'],
                            'target_url': match['target_url'],
                            'context': match['context']
                        })

        if download_data:
            csv = convert_df_to_csv(download_data)
            st.download_button(
                label="Download Opportunities CSV",
                data=csv,
                file_name='unlinked_keyword_opportunities.csv',
                mime='text/csv'
            )
    elif st.session_state.processing_done and not st.session_state.processed_results:
        st.info("No interlinking opportunities found.")