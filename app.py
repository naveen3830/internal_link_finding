import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import time
import logging
from urllib3.exceptions import InsecureRequestWarning
import re
from streamlit_option_menu import option_menu
from demo import Home
from link import link


st.set_page_config(page_title="Internal Linking Opportunities", layout="wide")
st.markdown(
        """
        <style>
        /* Main container adjustments */
        .main {
            background-color: #222f3b;
            color: #d2d2d6;
        }

        /* Title and headings styling */
        h1, h2, h3 {
            color: #1cb3e0;
            font-family: 'sans-serif';
        }

        /* Button adjustments */
        .stButton>button {
            background-color: #1cb3e0;
            color: #ffffff;
            border-radius: 8px;
            padding: 10px 20px;
            border: none;
            transition: 0.3s ease-in-out;
        }
        .stButton>button:hover {
            background-color: #148bb5;
        }

        /* Table styling */
        .stDataFrame {
            background-color: #344758;
            color: #d2d2d6;
            border: none;
        }

        /* Sidebar tweaks */
        .sidebar .sidebar-content {
            background-color: #344758;
        }
        .sidebar .sidebar-content h1 {
            color: #1cb3e0;
        }

        /* Download button styling */
        .stDownloadButton>button {
            background-color: #1cb3e0;
            color: #ffffff;
            border-radius: 8px;
            padding: 8px 16px;
            transition: 0.3s ease-in-out;
        }
        .stDownloadButton>button:hover {
            background-color: #148bb5;
        }

        /* Input field styling */
        input, textarea {
            background-color: #344758;
            color: #d2d2d6;
            border: 1px solid #1cb3e0;
            border-radius: 4px;
            padding: 8px;
        }

        /* Spinner styling */
        .stSpinner {
            color: #1cb3e0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# Sidebar menu
with st.sidebar:
    # Title with centered alignment
    st.markdown("<h2 style='text-align: center;'>Menu</h2>", unsafe_allow_html=True)

    # Subtitle with centered alignment
    st.markdown("<h4 style='text-align: center;'>Navigate through the sections:</h4>", unsafe_allow_html=True)
    
    selected = option_menu(
        'Main Menu',
        ['URL Extractor', 'Keyword Analysis'],
        icons=['house','list-check'],
        default_index=0,
        menu_icon="cast"
    )

# Load respective page based on user selection
if selected == "URL Extractor":
    link()
elif selected == "Keyword Analysis":
    Home()
