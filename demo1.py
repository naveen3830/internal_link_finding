import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
import concurrent.futures
import time

st.set_page_config(page_title="Keyword Search", layout="wide", initial_sidebar_state="collapsed")

def scrape_content(url):
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36')

    service = Service('chromedriver.exe') 
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        time.sleep(1)  

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for element in soup.select('header, footer, nav, aside'):
            element.extract()

        main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': 'main-content'})
        if not main_content:
            main_content = soup.body 

        text_content = main_content.get_text(separator=' ')
        text_content = re.sub(r'<[^>]+>', '', text_content)
        text_content = re.sub(r'&\w+;', '', text_content)
        
        return text_content.lower()
    except Exception as e:
        st.error(f"Error scraping {url}: {e}")
        return None
    finally:
        driver.quit()

def search_keyword_in_content(content, keyword):
    if content:
        return keyword.lower() in content
    return False

st.title("Keyword Search in URL Content")
uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])
user_keyword = st.text_input("Enter keyword to search")

if uploaded_file and user_keyword:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.write("Data Preview:")
        st.write(df.head())

        if 'source_url' in df.columns:
            start_time = time.time()
            with st.spinner('Processing URLs...'):
                matching_urls = []
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    results = [executor.submit(scrape_content, url) for url in df['source_url']]
                    for future in concurrent.futures.as_completed(results):
                        content = future.result()
                        if search_keyword_in_content(content, user_keyword):
                            matching_urls.append(df['source_url'][results.index(future)])

            end_time = time.time()
            elapsed_time = end_time - start_time
            st.success(f"Task completed in {elapsed_time:.2f} seconds")

            if matching_urls:
                results_df = pd.DataFrame(matching_urls, columns=['link'])
                st.write("Matching URLs:")
                st.write(results_df)

                csv = results_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download results as CSV",
                    data=csv,
                    file_name='matching_urls.csv',
                    mime='text/csv',
                )
            else:
                st.write("No matching URLs found.")
        else:
            st.error("The file must contain a 'source_url' column.")
    except Exception as e:
        st.error(f"An error occurred: {e}")