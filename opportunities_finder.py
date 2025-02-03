import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import time
import logging
from urllib3.exceptions import InsecureRequestWarning
import re
from langchain.prompts import PromptTemplate
import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
load_dotenv()

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_related_keywords(keyword):
    """Generate related keywords using Groq LLM."""
    try:
        groq_api_key = os.getenv('GROQ_API_KEY')  # Replace with your actual Groq API key
        llm = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.3-70b-versatile")
        
        # Add logging to track API calls
        logger.info(f"Generating keywords for: {keyword}")
        
        template = """As a professional SEO strategist, generate 3 high-potential keywords for {keyword} following these STRICT guidelines:
1. Output MUST be 3 lines, each containing ONLY one keyword.
2. Keywords must include commercial intent modifiers like "best," "near me," "cost," or "vs."
3. Keywords must be 2-5 words long.
4. Exclude informational terms like "what," "how," or "why."
5. Use Title Case formatting.
6. Ensure keywords are actionable and rankable.

BAD EXAMPLE (Avoid):
- Doctor Qualifications
- Medical Practitioner Licensing
- Physician Education Requirements

GOOD EXAMPLE:
Best Cardiologist Near Me
Pediatrician Vs Family Doctor Costs
24/7 Emergency Doctors [City]

Generate COMPETITIVE keywords for: {keyword}

Remember: Output ONLY the 3 keywords, one per line, nothing else."""

        prompt = PromptTemplate(
            input_variables=["keyword"],
            template=template
        )
        
        formatted_prompt = prompt.format(keyword=keyword)
        response = llm.invoke(formatted_prompt)
        
        # Add logging for response
        logger.info(f"Received response from Groq: {response.content}")
        
        # Process the response
        keyword_list = []
        lines = [line for line in response.content.split("\n") if line.strip()]
        
        for line in lines[:3]:  # Only take first 3 non-empty lines
            # Clean the line
            cleaned = re.sub(r'[^a-zA-Z0-9\s\-\&]', '', line.strip())
            # Skip empty lines or lines that don't meet criteria
            if cleaned and 2 <= len(cleaned.split()) <= 5:
                keyword_list.append(cleaned.title())
        
        # Add logging for generated keywords
        logger.info(f"Generated keywords: {keyword_list}")
        
        # If no valid keywords were generated, create some basic ones
        if not keyword_list:
            default_keywords = [
                f"Best {keyword} Near Me",
                f"{keyword} Cost",
                f"Top {keyword} Services"
            ]
            logger.info(f"Using default keywords: {default_keywords}")
            return default_keywords
            
        return keyword_list
        
    except Exception as e:
        logger.error(f"Error generating keywords: {str(e)}")
        st.error(f"Error generating keywords: {str(e)}")  # Display error in UI
        # Return default keywords in case of error
        default_keywords = [
            f"Best {keyword} Near Me",
            f"{keyword} Cost",
            f"Top {keyword} Services"
        ]
        logger.info(f"Using default keywords due to error: {default_keywords}")
        return default_keywords

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

def find_unlinked_keywords(soup, keywords, target_url):
    """Find unlinked keywords in text, supporting multiple keywords."""
    if not isinstance(keywords, list):
        keywords = [keywords]
    
    unlinked_occurrences = []
    text_elements = soup.find_all(text=True)
    
    for keyword in keywords:
        cleaned_keyword = clean_text(keyword)
        keyword_terms = cleaned_keyword.split()
        
        if not keyword_terms:
            continue

        escaped_terms = [re.escape(term) for term in keyword_terms]
        pattern = r'\b' + r'\s+'.join(escaped_terms) + r'\b'
        
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

def process_url(url, keywords, target_url):
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
        unlinked_matches = find_unlinked_keywords(soup, keywords, target_url)
        
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

def Home():
    st.header("Internal Linking Opportunities Finder", divider='rainbow')
    
    session_vars = [
        'uploaded_df', 'keyword_inputs', 'target_url_inputs',
        'processed_results', 'num_pairs', 'processing_done',
        'generated_keywords'
    ]
    for var in session_vars:
        if var not in st.session_state:
            st.session_state[var] = None if var != 'num_pairs' else 1
            if var == 'keyword_inputs' or var == 'target_url_inputs':
                st.session_state[var] = ['']
            if var == 'processing_done':
                st.session_state[var] = False
            if var == 'generated_keywords':
                st.session_state[var] = {}

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
                st.session_state.uploaded_df = df
            except Exception as e:
                st.error(f"An error occurred while reading the file: {str(e)}")
                return
        elif st.session_state.uploaded_df is not None:
            df = st.session_state.uploaded_df

    # Keyword-URL pairs input
    st.subheader("Keywords and Target URLs", divider='rainbow')
    num_pairs = st.number_input("Number of keyword-URL pairs", 
                               min_value=1,
                               value=st.session_state.num_pairs,
                               key='num_pairs_input')
    st.session_state.num_pairs = num_pairs

    # Initialize inputs
    for inputs in ['keyword_inputs', 'target_url_inputs']:
        if len(st.session_state[inputs]) < num_pairs:
            st.session_state[inputs] += [''] * (num_pairs - len(st.session_state[inputs]))

    keyword_inputs = []
    target_url_inputs = []
    for i in range(num_pairs):
        col1, col2 = st.columns([3, 3])
        with col1:
            keyword = st.text_input(
                f"Keyword {i+1}", 
                value=st.session_state.keyword_inputs[i],
                key=f"keyword_input_{i}"
            )
            if keyword:
                if keyword not in st.session_state.generated_keywords:
                    with st.spinner(f"Generating keywords for: {keyword}"):
                        st.session_state.generated_keywords[keyword] = generate_related_keywords(keyword)
                with st.expander(f"Generated keywords for: {keyword}"):
                    st.write("Including these additional keywords in search:")
                    for gen_keyword in st.session_state.generated_keywords[keyword]:
                        st.write(f"- {gen_keyword}")
            keyword_inputs.append(keyword)
        with col2:
            target_url = st.text_input(
                f"Target URL {i+1}", 
                value=st.session_state.target_url_inputs[i],
                key=f"target_url_input_{i}"
            )
            target_url_inputs.append(target_url)

    st.session_state.keyword_inputs = keyword_inputs
    st.session_state.target_url_inputs = target_url_inputs

    max_workers = st.slider("Concurrent searches", 
                           min_value=1, 
                           max_value=15, 
                           value=15,
                           help="Number of URLs to process simultaneously")

    if st.button("Process"):
        # Prepare keyword-URL pairs including generated keywords
        keyword_url_pairs = []
        for k, u in zip(st.session_state.keyword_inputs, st.session_state.target_url_inputs):
            if k.strip() and u.strip():
                # Add original keyword
                keyword_url_pairs.append((k.strip(), u.strip()))
                # Add generated keywords
                if k in st.session_state.generated_keywords:
                    for gen_k in st.session_state.generated_keywords[k]:
                        keyword_url_pairs.append((gen_k, u.strip()))
        
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

                st.info(f"Processing {len(df)} URLs with {len(keyword_url_pairs)} keyword-URL pairs...")
                start_time = time.time()
                progress_bar = st.progress(0)
                processed = 0
                results = []

                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = []
                    for url in df['source_url'].unique():
                        for keyword, target_url in keyword_url_pairs:
                            futures.append(executor.submit(
                                process_url, 
                                url, 
                                [keyword] + (st.session_state.generated_keywords.get(keyword, []) if keyword in st.session_state.keyword_inputs else []),
                                target_url
                            ))

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
        else:
            st.warning("Please provide all inputs and ensure valid data is available.")

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
    elif st.session_state.processing_done and st.session_state.processed_results is None:
        st.info("No interlinking opportunities found.")
    elif st.session_state.processed_results is None and 'processed_results' in st.session_state:
        pass