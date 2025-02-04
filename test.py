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

def generate_keywords(keyword: str) -> list:
    """Generate related keywords using Groq LLM."""
    try:
        groq_api_key = os.getenv('GROQ_API_KEY')
        llm = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.3-70b-versatile")
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
        logger.info(f"Received response from Groq: {response.content}")

        keyword_list = []
        lines = [line for line in response.content.split("\n") if line.strip()]
        
        for line in lines[:3]:
            cleaned = re.sub(r'[^a-zA-Z0-9\s\-\&]', '', line.strip())
            if cleaned and 2 <= len(cleaned.split()) <= 5:
                keyword_list.append(cleaned.title())

        logger.info(f"Generated keywords: {keyword_list}")
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
        st.error(f"Error generating keywords: {str(e)}")
        
