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
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36')
    
    try:
        # Try using the default ChromeDriver location
        driver = webdriver.Chrome(options=chrome_options)
    except:
        try:
            # Try alternative ChromeDriver locations
            driver_paths = [
                '/usr/lib/chromium-browser/chromedriver',
                '/usr/bin/chromedriver',
                'chromedriver'
            ]
            
            for path in driver_paths:
                try:
                    service = Service(path)
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    return driver
                except:
                    continue
            
            st.error("Could not initialize ChromeDriver. Please check if chromium-browser and chromium-driver are installed.")
            return None
            
        except Exception as e:
            st.error(f"Failed to initialize Chrome driver: {e}")
            return None
    
    return driver

def scrape_content(url):
    if not url or not isinstance(url, str):
        return None
        
    driver = get_chrome_driver()
    if not driver:
        return None
    
    try:
        driver.get(url)
        time.sleep(2)  # Increased wait time for better page loading
        
        # Wait for body to be present
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
            text_content = re.sub(r'\s+', ' ', text_content)  # Normalize whitespace
            text_content = re.sub(r'<[^>]+>', '', text_content)
            text_content = re.sub(r'&\w+;', '', text_content)
            return text_content.strip().lower()
        return None
        
    except Exception as e:
        st.error(f"Error scraping {url}: {e}")
        return None
    finally:
        try:
            driver.quit()
        except:
            pass

def search_keyword_in_content(content, keyword):
    if content and keyword:
        return keyword.lower() in content
    return False

def main():
    st.title("Keyword Search in URL Content")
    
    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])
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
            df = df[valid_urls]
            
            if df.empty:
                st.error("No valid URLs found in the file.")
                return
            
            start_time = time.time()
            
            with st.spinner('Processing URLs...'):
                matching_urls = []
                progress_bar = st.progress(0)
                
                # Process URLs in parallel with progress tracking
                total_urls = len(df)
                completed = 0
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_url = {executor.submit(scrape_content, url): url for url in df['source_url']}
                    
                    for future in concurrent.futures.as_completed(future_to_url):
                        url = future_to_url[future]
                        completed += 1
                        progress_bar.progress(completed / total_urls)
                        
                        try:
                            content = future.result()
                            if search_keyword_in_content(content, user_keyword):
                                matching_urls.append(url)
                        except Exception as e:
                            st.error(f"Error processing {url}: {e}")
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
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
                st.write("No matching URLs found.")
                
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.exception(e)

if __name__ == "__main__":
    main()