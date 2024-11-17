import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re
import concurrent.futures
import time

st.set_page_config(page_title="Keyword Search", layout="wide", initial_sidebar_state="collapsed")

def get_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # Updated headless mode syntax
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        # First try using the default webdriver manager
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e1:
        try:
            # Try Debian-specific ChromeDriver locations
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

def process_url(url, user_keyword):
    if not url or not isinstance(url, str):
        return None, None
        
    driver = get_chrome_driver()
    if not driver:
        return None, None
    
    try:
        driver.get(url)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.select('header, footer, nav, aside, script, style'):
            element.extract()
            
        # Find main content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': 'main-content'})
        if not main_content:
            main_content = soup.body
            
        if main_content:
            text_content = main_content.get_text(separator=' ')
            text_content = re.sub(r'\s+', ' ', text_content)
            text_content = re.sub(r'<[^>]+>', '', text_content)
            text_content = re.sub(r'&\w+;', '', text_content)
            text_content = text_content.strip().lower()
            
            if user_keyword.lower() in text_content:
                return url, True
            
        return url, False
        
    except Exception as e:
        st.error(f"Error scraping {url}: {str(e)}")
        return url, False
    finally:
        try:
            driver.quit()
        except:
            pass

def main():
    st.title("Keyword Search in URL Content")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])
    
    with col2:
        user_keyword = st.text_input("Enter keyword to search")
    
    if uploaded_file and user_keyword:
        try:
            # Load the data
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
                
            st.write("Data Preview:")
            st.write(df.head())
            
            if 'source_url' not in df.columns:
                st.error("The file must contain a 'source_url' column.")
                return
                
            # Clean and validate URLs
            df['source_url'] = df['source_url'].astype(str).str.strip()
            valid_urls = df['source_url'].str.startswith(('http://', 'https://')).fillna(False)
            df = df[valid_urls].copy()
            
            if df.empty:
                st.error("No valid URLs found in the file.")
                return
            
            start_time = time.time()
            
            with st.spinner('Processing URLs...'):
                matching_urls = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process URLs in parallel with progress tracking
                total_urls = len(df)
                completed = 0
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    future_to_url = {
                        executor.submit(process_url, url, user_keyword): url 
                        for url in df['source_url']
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_url):
                        completed += 1
                        progress = completed / total_urls
                        progress_bar.progress(progress)
                        status_text.text(f"Processed {completed} of {total_urls} URLs...")
                        
                        try:
                            url, found = future.result()
                            if found:
                                matching_urls.append(url)
                        except Exception as e:
                            st.error(f"Error processing URL: {str(e)}")
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            status_text.text("")  # Clear the status text
            st.success(f"Task completed in {elapsed_time:.2f} seconds")
            
            if matching_urls:
                results_df = pd.DataFrame(matching_urls, columns=['link'])
                st.write(f"Found {len(matching_urls)} matching URLs:")
                st.write(results_df)
                
                # Download results
                csv = results_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download results as CSV",
                    data=csv,
                    file_name='matching_urls.csv',
                    mime='text/csv',
                )
            else:
                st.info("No matching URLs found.")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()