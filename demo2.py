import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import time
import logging
from urllib3.exceptions import InsecureRequestWarning
import re

# Disable warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Streamlit and logging configuration
st.set_page_config(page_title="Internal Linking Opportunities", layout="wide")
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
    
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'meta', 'link']):
        element.decompose()
    
    return soup

def find_unlinked_keywords(soup, keyword, target_url):
    """Find occurrences of a keyword that are not already hyperlinked."""
    keyword = keyword.strip()
    unlinked_occurrences = []
    
    text_elements = soup.find_all(text=True)
    existing_links = set(clean_text(link.get_text()) for link in soup.find_all('a'))
    
    for element in text_elements:
        if not element.strip() or element.parent.name == 'a':
            continue
        
        clean_element = clean_text(element)
        matches = list(re.finditer(r'\b' + re.escape(keyword) + r'\b', clean_element))
        
        for match in matches:
            match_text = element[match.start():match.end()]
            
            if clean_text(match_text) not in existing_links:
                start = max(0, match.start() - 50)
                end = min(len(element), match.end() + 50)
                context = element[start:end].strip()
                
                unlinked_occurrences.append({
                    'context': context,
                    'keyword': keyword
                })
    
    return unlinked_occurrences

def process_url(url, keyword, target_url):
    """Process a single URL to find unlinked keyword opportunities."""
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

def main():
    st.title("Internal Linking Opportunities Finder")
    
    # Create columns for inputs
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        uploaded_file = st.file_uploader("Upload CSV or Excel file with URLs", 
                                         type=["csv", "xlsx"], 
                                         key="url_file_uploader")
    
    with col2:
        keyword = st.text_input("Enter keyword to find", 
                                help="Find this keyword without existing links",
                                key="keyword_input")
    
    with col3:
        target_url = st.text_input("Target URL for linking", 
                                   help="URL to suggest for internal linking",
                                   key="target_url_input")
    
    max_workers = st.slider("Concurrent searches", min_value=1, max_value=10, value=2, 
                             help="Number of URLs to process simultaneously")

    if uploaded_file and keyword and target_url:
        # Reset results each time the inputs change
        st.session_state.results = []
        
        try:
            # Read the file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Validate URL column
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
                future_to_url = {executor.submit(process_url, url, keyword, target_url): url for url in df['source_url'].unique()}
                
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
                                st.markdown(f"- *{match['keyword']}*: _{match['context']}_")
                                download_data.append({
                                    'source_url': result['url'],
                                    'keyword': match['keyword'],
                                    'context': match['context']
                                })
                
                if download_data:
                    csv = convert_df_to_csv(download_data)
                    st.download_button(
                        label="Download Opportunities CSV", 
                        data=csv, 
                        file_name=f'unlinked_keyword_opportunities_{keyword}.csv', 
                        mime='text/csv'
                    )
            else:
                st.warning(f"No unlinked keyword opportunities found for '{keyword}'")
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logger.exception("Error in main execution")

if __name__ == "__main__":
    main()