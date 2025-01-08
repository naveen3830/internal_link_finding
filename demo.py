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
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'meta', 'link', 'h1', 'h2', 'h3']):
        element.decompose()

    for element in soup.find_all(attrs={"class": [
        "position-relative mt-5 related-blog-post__swiper-container", 
        "row left-zero__without-shape position-relative z-1 mt-4 mt-md-5 px-0"
    ]}):
        element.decompose()
    
    return soup

def find_unlinked_keywords(soup, keyword_url_pairs):
    unlinked_occurrences = []
    text_elements = soup.find_all(text=True)
    existing_links = {
        clean_text(link.get_text())
        for link in soup.find_all('a') if link.get_text()
    }
    
    for element in text_elements:
        if not element.strip() or element.parent.name == 'a':
            continue
        
        clean_element = clean_text(element)
        
        for keyword, target_url in keyword_url_pairs:
            matches = list(re.finditer(r'\b' + re.escape(keyword.lower()) + r'\b', clean_element))
            
            for match in matches:
                match_text = element[match.start():match.end()]
                clean_match_text = clean_text(match_text)
                
                if clean_match_text not in existing_links:
                    start = max(0, match.start() - 50)
                    end = min(len(element), match.end() + 50)
                    context = element[start:end].strip()
                    
                    unlinked_occurrences.append({
                        'context': context,
                        'keyword': keyword,
                        'target_url': target_url
                    })
    
    return unlinked_occurrences

def process_url(url, keyword_url_pairs):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = extract_text_from_html(response.text)
        unlinked_matches = find_unlinked_keywords(soup, keyword_url_pairs)
        
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
    download_df = pd.DataFrame(download_data)
    return download_df.to_csv(index=False).encode('utf-8')

def Home():
    st.header("Internal Linking Opportunities Finder", divider='rainbow')

    df = None
    if 'filtered_df' in st.session_state and st.session_state.filtered_df is not None:
        st.success("Using filtered data from the previous tab.")
        df = st.session_state.filtered_df
    else:
        uploaded_file = st.file_uploader("Upload CSV or Excel file with URLs",
                                        type=["csv", "xlsx"],
                                        key="url_file_uploader")
        if uploaded_file:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith(".xlsx"):
                    df = pd.read_excel(uploaded_file)
                else:
                    st.error("Unsupported file format!")
                    return
            except Exception as e:
                st.error(f"An error occurred while reading the file: {str(e)}")
                return

    # Multiple keywords and target URLs input
    keyword_inputs = []
    target_url_inputs = []
    
    st.subheader("Keywords and Target URLs",divider='rainbow')
    num_pairs = st.number_input("Number of keyword-URL pairs", min_value=1, value=1)
    
    for i in range(num_pairs):
        col1, col2 = st.columns([3, 3])
        with col1:
            keyword = st.text_input(f"Keyword {i+1}",
                                  key=f"keyword_input_{i}")
            keyword_inputs.append(keyword)
        
        with col2:
            target_url = st.text_input(f"Target URL {i+1}",
                                     key=f"target_url_input_{i}")
            target_url_inputs.append(target_url)

    max_workers = st.slider("Concurrent searches", min_value=1, max_value=15, value=15,
                          help="Number of URLs to process simultaneously")

    if st.button("Process"):
        # Create keyword-URL pairs, filtering out empty inputs
        keyword_url_pairs = [(k.strip(), u.strip()) 
                           for k, u in zip(keyword_inputs, target_url_inputs) 
                           if k.strip() and u.strip()]
        
        if df is not None and keyword_url_pairs:
            try:
                if 'source_url' not in df.columns:
                    st.error("File must contain a 'source_url' column")
                    return

                df['source_url'] = df['source_url'].astype(str).str.strip()
                valid_urls = df['source_url'].str.match(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
                df = df[valid_urls].copy()

                if df.empty:
                    st.error("No valid URLs found in the file")
                    return

                st.info(f"Processing {len(df)} URLs...")
                start_time = time.time()
                progress_bar = st.progress(0)
                processed = 0
                results = []

                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_url = {executor.submit(process_url, url, keyword_url_pairs): url 
                                   for url in df['source_url'].unique()}

                    for future in concurrent.futures.as_completed(future_to_url):
                        processed += 1
                        progress = processed / len(df)
                        progress_bar.progress(progress)
                        result = future.result()

                        if result:
                            results.append(result)

                progress_bar.empty()
                duration = time.time() - start_time
                st.info(f"Search completed in {duration:.2f} seconds")

                if results:
                    download_data = []
                    st.success(f"Unlinked keyword opportunities found in {len(results)} URLs")

                    with st.expander("View Opportunities", expanded=True):
                        for result in results:
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
                else:
                    st.warning("No unlinked keyword opportunities found")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("Please provide all inputs and ensure valid data is available.")
            
            
    # if __name__ == "__main__":
    #     main()