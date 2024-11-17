import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import concurrent.futures
import time
import logging

# Custom CSS for better styling
st.set_page_config(
    page_title="Keyword Search",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .main {
        padding: 2rem 3rem;
    }
    .stButton button {
        width: 100%;
        border-radius: 5px;
        height: 3rem;
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
    }
    .stButton button:hover {
        background-color: #ff3333;
    }
    .upload-btn {
        border: 2px dashed #cccccc;
        border-radius: 5px;
        padding: 2rem;
        text-align: center;
    }
    .stProgress > div > div > div > div {
        background-color: #ff4b4b;
    }
    h1 {
        color: #333333;
        margin-bottom: 2rem;
    }
    .stDataFrame {
        width: 100%;
    }
    .success-msg {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d4edda;
        color: #155724;
        margin: 1rem 0;
    }
    .info-msg {
        padding: 1rem;
        border-radius: 5px;
        background-color: #cce5ff;
        color: #004085;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Keyword Search", layout="wide", initial_sidebar_state="collapsed")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('--window-size=1920,1080')  # Set a consistent window size
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e1:
        try:
            debian_paths = [
                '/usr/bin/chromedriver',
                '/usr/lib/chromium/chromedriver',
                '/snap/bin/chromium.chromedriver'
            ]
            
            for path in debian_paths:
                try:
                    service = Service(executable_path=path)
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    return driver
                except Exception:
                    continue
            
            st.error("Could not find ChromeDriver. Please check if chromium and chromium-driver are installed.")
            return None
            
        except Exception as e2:
            st.error(f"Failed to initialize Chrome driver: {str(e1)}\n{str(e2)}")
            return None

def wait_for_page_load(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)
        
        return driver.execute_script("return document.readyState") == "complete"
    except Exception as e:
        logger.error(f"Error waiting for page load: {str(e)}")
        return False

def clean_text(text):
    """Clean and normalize text content"""
    if not text:
        return ""
    
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&\w+;', '', text)
    text = ''.join(char for char in text if char.isprintable())
    return text.strip().lower()

def process_url(url, user_keyword):
    if not url or not isinstance(url, str):
        logger.warning(f"Invalid URL: {url}")
        return None, None
        
    driver = get_chrome_driver()
    if not driver:
        return None, None
    
    try:
        driver.set_page_load_timeout(30)
        driver.get(url)
        if not wait_for_page_load(driver):
            logger.warning(f"Page load timeout for URL: {url}")
            return url, False
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        for element in soup.select('header, footer, nav, aside, script, style, iframe, noscript'):
            element.extract()
            
        # Try different content areas
        content_areas = [
            soup.find('main'),
            soup.find('article'),
            soup.find('div', {'class': ['main-content', 'content', 'post-content']}),
            soup.find('div', {'id': ['main-content', 'content', 'post-content']}),
            soup.body
        ]
        
        # Use the first non-None content area
        main_content = next((area for area in content_areas if area is not None), None)
            
        if main_content:
            # Get text content
            text_content = main_content.get_text(separator=' ')
            # Clean and normalize text
            text_content = clean_text(text_content)
            
            # Log content length for debugging
            logger.info(f"Content length for {url}: {len(text_content)} characters")
            
            # Search for keyword
            keyword_found = user_keyword.lower() in text_content
            logger.info(f"Keyword search result for {url}: {keyword_found}")
            
            return url, keyword_found
            
        logger.warning(f"No main content found for URL: {url}")
        return url, False
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        return url, False
    finally:
        try:
            driver.quit()
        except:
            pass

def main():
    st.markdown("<h1>🔍 URL Content Keyword Search</h1>", unsafe_allow_html=True)
    
    # Create two columns for the interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
            <div class="upload-section">
                <p>Upload a CSV or Excel file containing URLs to search through.</p>
            </div>
        """, unsafe_allow_html=True)
        uploaded_file = st.file_uploader("", type=["csv", "xlsx"])

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        user_keyword = st.text_input("🎯 Enter keyword to search", placeholder="Type your keyword here...")
        if st.button("🗑️ Clear Cache", key="clear_cache"):
            st.cache_data.clear()
            st.success("Cache cleared successfully!")

    if uploaded_file and user_keyword:
        try:
            # Load the data
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Data preview with improved styling
            st.markdown("### 📊 Data Preview")
            st.markdown('<div style="border: 1px solid #e6e6e6; border-radius: 5px; padding: 1rem; margin: 1rem 0;">', 
                       unsafe_allow_html=True)
            
            # Show full dataset with pagination
            page_size = 50
            total_rows = len(df)
            num_pages = (total_rows + page_size - 1) // page_size
            
            if num_pages > 1:
                page = st.selectbox("Select page:", range(1, num_pages + 1)) - 1
                start_idx = page * page_size
                end_idx = min(start_idx + page_size, total_rows)
                st.dataframe(df.iloc[start_idx:end_idx], use_container_width=True)
                st.markdown(f"Showing rows {start_idx + 1} to {end_idx} of {total_rows}")
            else:
                st.dataframe(df, use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            if 'source_url' not in df.columns:
                st.error("❌ The file must contain a 'source_url' column.")
                return
            
            # Clean and validate URLs
            df['source_url'] = df['source_url'].astype(str).str.strip()
            valid_urls = df['source_url'].str.match(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
            df = df[valid_urls].copy()
            
            if df.empty:
                st.error("❌ No valid URLs found in the file.")
                return
            
            start_time = time.time()
            
            with st.spinner('🔄 Processing URLs...'):
                matching_urls = []
                progress_container = st.container()
                with progress_container:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                
                total_urls = len(df)
                completed = 0
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    future_to_url = {
                        executor.submit(process_url, url, user_keyword): url 
                        for url in df['source_url']
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_url):
                        completed += 1
                        progress = completed / total_urls
                        progress_bar.progress(progress)
                        status_text.markdown(f"⏳ Processed **{completed}** of **{total_urls}** URLs...")
                        
                        try:
                            url, found = future.result()
                            if found:
                                matching_urls.append(url)
                        except Exception as e:
                            logger.error(f"Error processing URL: {str(e)}")
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            status_text.empty()
            st.markdown(f"""
                <div class="success-msg">
                    ✅ Task completed in {elapsed_time:.2f} seconds
                </div>
            """, unsafe_allow_html=True)
            
            if matching_urls:
                results_df = pd.DataFrame(matching_urls, columns=['link'])
                st.markdown(f"### 🎯 Found {len(matching_urls)} matching URLs:")
                st.dataframe(results_df, use_container_width=True)
                
                # Download results with styled button
                csv = results_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Results CSV",
                    data=csv,
                    file_name='matching_urls.csv',
                    mime='text/csv',
                )
            else:
                st.markdown("""
                    <div class="info-msg">
                        ℹ️ No matching URLs found.
                    </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            st.error(f"❌ An error occurred: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()