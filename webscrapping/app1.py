import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="Keyword Search", layout="wide", initial_sidebar_state="collapsed")

def scrape_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove header, footer, and navigation elements
        for element in soup.select('header, footer, nav, aside'):
            element.extract()

        # Find main content, using common tags or classes
        main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': 'main-content'})
        if not main_content:
            main_content = soup.body  # Fallback to the body if main content is not found

        # Get the text content
        text_content = main_content.get_text(separator=' ')
        
        # Remove any remaining HTML tags and entities
        text_content = re.sub(r'<[^>]+>', '', text_content)
        text_content = re.sub(r'&\w+;', '', text_content)
        
        return text_content.lower()
    except Exception as e:
        st.error(f"Error scraping {url}: {e}")
        return None

def search_keyword_in_content(content, keyword):
    if content:
        return keyword.lower() in content
    return False

st.title("Keyword Search in URL Content")
uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])
user_keyword = st.text_input("Enter keyword to search")

if uploaded_file and user_keyword:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write("Data Preview:")
    st.write(df.head())

    if 'source_url' in df.columns:
        matching_urls = []
        for index, row in df.iterrows():
            url = row['source_url']
            content = scrape_content(url)
            if search_keyword_in_content(content, user_keyword):
                matching_urls.append(url)

        if matching_urls:
            results_df = pd.DataFrame(matching_urls, columns=['link'])
            st.write("Matching URLs:")
            st.write(results_df)

            # Download option for the CSV file
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
