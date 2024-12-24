import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Keyword Search", layout="wide", initial_sidebar_state="collapsed")
def scrape_content(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return BeautifulSoup(response.content, 'html.parser')
        else:
            return f"Failed to retrieve content, status code: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

def search_anchor_text_and_links(soup, keyword):
    found = False
    linked = False

    for a_tag in soup.find_all('a'):
        if keyword.lower() in a_tag.get_text().lower():
            found = True
            if a_tag.has_attr('href'):
                linked = True
                break  
            
    if not linked and keyword.lower() in soup.get_text().lower():
        found = True
    
    return found, linked

st.title("Internal Linking Opportunity Finder")
uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write("Data Preview:")
    st.write(df.head())

    if 'keyword' in df.columns and 'source_url' in df.columns:
        results = []
        for index, row in df.iterrows():
            keyword = row['keyword']
            url = row['source_url']
            soup = scrape_content(url)

            if isinstance(soup, str): 
                found = False
                linked = False
                content_preview = soup  
            else:
                found, linked = search_anchor_text_and_links(soup, keyword)
                content_preview = soup.get_text()[:500] 

            results.append({
                'keyword': keyword,
                'source_url': url,
                'found': found,
                'linked': linked,
                'content_preview': content_preview
            })

        results_df = pd.DataFrame(results)
        linking_opportunities = results_df[(results_df['found'] == True) & (results_df['linked'] == False)]

        st.write("Internal Linking Opportunities:")
        if not linking_opportunities.empty:
            st.write(linking_opportunities[['keyword', 'source_url', 'content_preview']])
        else:
            st.write("No internal linking opportunities found.")

        for index, row in linking_opportunities.iterrows():
            with st.expander(f"Full Content for URL: {row['source_url']}"):
                st.write(f"Keyword: {row['keyword']}")
                st.text(row['content_preview'] + "..." if len(row['content_preview']) == 500 else row['content_preview'])
    else:
        st.error("The file must contain 'keyword' and 'source_url' columns.")
