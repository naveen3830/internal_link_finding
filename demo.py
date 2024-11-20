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

st.set_page_config(page_title="Keyword Search", layout="wide")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text(text):
    """Clean text content for better keyword matching"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def extract_text_from_html(html_content):
    """Extract meaningful text from HTML while preserving some structure"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'meta', 'link']):
        element.decompose()
    content_areas = []
    
    main_content = soup.find(['main', 'article', 'div'], class_=lambda x: x and any(term in str(x).lower() for term in ['content', 'main', 'article']))
    if main_content:
        content_areas.append(main_content.get_text(' ', strip=True))
    
    if not content_areas:
        content_areas.append(soup.body.get_text(' ', strip=True) if soup.body else '')
    
    return soup, ' '.join(content_areas)

def check_keyword(soup, text, keyword):
    """
    Check if keyword exists in text, handling various cases
    Returns: (bool, list of matches with context, bool indicating if hyperlinked)
    """
    text = clean_text(text)
    keyword = keyword.lower().strip()
    
    variations = [keyword]
    if ' ' in keyword:
        variations.append(keyword.replace(' ', '-'))
        variations.append(keyword.replace(' ', ''))
    
    matches = []
    found = False
    
    for variation in variations:
        pattern = r'\b' + re.escape(variation) + r'\b'
        
        for match in re.finditer(pattern, text):
            found = True
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = f"...{text[start:end]}..."
            
            # Check if the keyword is hyperlinked
            hyperlinked = False
            for link in soup.find_all('a'):
                link_text = clean_text(link.get_text())
                if variation in link_text:
                    hyperlinked = True
                    break
            
            matches.append({
                'context': context.strip(),
                'hyperlinked': hyperlinked
            })
    
    return found, matches

def process_url(url, keyword):
    """Process a single URL and check for keyword presence"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        # Extract text content
        soup, text_content = extract_text_from_html(response.text)
        found, matches = check_keyword(soup, text_content, keyword)
        
        if found:
            return {
                'url': url,
                'found': True,
                'matches': matches[:3]  # Limit to first 3 matches for brevity
            }
        return None
        
    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
        return None

@st.cache_data
def convert_df_to_csv(download_data):
    """Cache the CSV generation to prevent re-computation"""
    download_df = pd.DataFrame(download_data)
    return download_df.to_csv(index=False).encode('utf-8')

def main():
    st.title("Keyword Search in URLs")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader("Upload CSV or Excel file with URLs", type=["csv", "xlsx"])
    
    with col2:
        keyword = st.text_input("Enter keyword to search", help="Enter the exact keyword you want to find")
        max_workers = st.slider("Concurrent searches", min_value=1, max_value=10, value=2,
                                help="Number of URLs to process simultaneously")
    
    if uploaded_file and keyword:
        if 'results' not in st.session_state:
            st.session_state.results = []
        try:
            # Read the file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
                st.info("Input data")
                st.dataframe(df,use_container_width=False)
            else:
                df = pd.read_excel(uploaded_file)
                st.info("Input data")
                st.dataframe(df,use_container_width=True)
            
            if 'source_url' not in df.columns:
                st.error("File must contain a 'source_url' column")
                return
            
            # Clean and validate URLs
            df['source_url'] = df['source_url'].astype(str).str.strip()
            valid_urls = df['source_url'].str.match(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
            df = df[valid_urls].copy()
            
            if df.empty:
                st.error("No valid URLs found in the file")
                return
            
            # Avoid reprocessing if results are already in session state
            if not st.session_state.results:
                st.info(f"Processing {len(df)} URLs...")
                start_time = time.time()
                
                progress_bar = st.progress(0)
                processed = 0
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_url = {
                        executor.submit(process_url, url, keyword): url
                        for url in df['source_url'].unique()
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_url):
                        processed += 1
                        progress = processed / len(df)
                        progress_bar.progress(progress)
                        
                        result = future.result()
                        if result:
                            st.session_state.results.append(result)
                
                progress_bar.empty()
                duration = time.time() - start_time
                st.info(f"Search completed in {duration:.2f} seconds")
            
            results = st.session_state.results
            
            if results:
                st.success(f"Found keyword in {len(results)} URLs")
                
                with st.expander("View Results", expanded=True):
                    for result in results:
                        st.write("---")
                        st.write(f"🔗 {result['url']}")
                        st.write("Matches found:")
                        for match in result['matches']:
                            hyperlink_status = "🔗 Hyperlinked" if match['hyperlinked'] else "❌ Not Hyperlinked"
                            st.markdown(f"- _{match['context']}_ ({hyperlink_status})")
                
                download_data = []
                for result in results:
                    for match in result['matches']:
                        download_data.append({
                            'url': result['url'],
                            'context': match['context'],
                            'hyperlinked': match['hyperlinked']
                        })
                
                csv = convert_df_to_csv(download_data)
                st.download_button(
                    label="Download Results CSV",
                    data=csv,
                    file_name=f'keyword_matches_{keyword}.csv',
                    mime='text/csv'
                )
            else:
                st.warning(f"No URLs containing '{keyword}' were found")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logger.exception("Error in main execution")

if __name__ == "__main__":
    main()
