import streamlit as st
from streamlit_option_menu import option_menu
from demo import Home
from link import link
import hashlib
from reverse import analyze_internal_links

st.set_page_config(page_title="Internal Linking Opportunities", layout="wide")

AUTHORIZED_USERS = {
    "user1": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # password: 'password'
    "user2": "6cf615d5bcaac778352a8f1f3360d23f02f34ec182e259897fd6ce485d7870d4",  # password: 'password2'
    "admin": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",  # password: 'admin'
    "naveen":"664895d207631fc1390d48165f2d0c67a3063007db9ebf60fe83490823e3151c",  # password:'naveen3830' 
}

# AUTHORIZED_USERS = {
#     username: password 
#     for username, password in st.secrets.auth.items()
# }

st.markdown(
        """
        <style>
        
        .main {
            background-color: #222f3b;
            color: #d2d2d6;
        }

        h1, h2, h3 {
            color: #1cb3e0;
            font-family: 'sans-serif';
        }

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

        .stDataFrame {
            background-color: #344758;
            color: #d2d2d6;
            border: none;
        }

        .sidebar .sidebar-content {
            background-color: #344758;
        }
        .sidebar .sidebar-content h1 {
            color: #1cb3e0;
        }

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

        input, textarea {
            background-color: #344758;
            color: #d2d2d6;
            border: 1px solid #1cb3e0;
            border-radius: 4px;
            padding: 8px;
        }
        
        .stWarning {
        color: #000000 !important;
        }
        .stWarning > div {
            color: #000000 !important;
        }
        .stWarning p {
            color: #000000 !important;
        }
        .stWarning div[data-testid="StyledLinkIconContainer"] {
            color: #000000 !important;
        }
        /* Spinner styling */
        .stSpinner {
            color: #1cb3e0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def creds_entered():
    """Verify credentials when entered."""
    username = st.session_state["user"].strip()
    password = st.session_state["passwd"].strip()
    hashed_password = hash_password(password)
    
    if username in AUTHORIZED_USERS and AUTHORIZED_USERS[username] == hashed_password:
        st.session_state["authenticated"] = True
        st.session_state["username"] = username
    else:
        st.session_state["authenticated"] = False
        if not password:
            st.warning("Please enter password.")
        elif not username:
            st.warning("Please enter username.")
        else:
            st.error("Invalid Username/Password :face_with_raised_eyebrow:")

def authenticate_user():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["username"] = None
    
    if not st.session_state["authenticated"]:
        st.markdown("""
            <style>
            .stApp {
                background-color: #f3f4f6;
            }
            div[data-testid="stVerticalBlock"] {
                padding: 2rem;
                max-width: 28rem;
                margin: 0 auto;
            }
            .stTextInput > div > div {
                background-color: #ffffff;
                color: #1f2937;
                border: 1px solid #d1d5db;
                border-radius: 0.375rem;
            }
            .stWarning{
            color: #000000 !important;
            }
            .stTextInput input {
            color: #000000 !important;
            }
            .stTextInput > label {
                color: #374151;
                font-weight: 500;
            }
            .stButton > button {
                background-color: #2563eb;
                color: white;
                width: 100%;
            }
            .stButton > button:hover {
                background-color: #1d4ed8;
            }
            .stWarning {
                color: #000000 !important;
            }
            .stWarning > div {
                color: #000000 !important;
            }
            .stWarning p {
                color: #000000 !important;
            }
            .stWarning div[data-testid="StyledLinkIconContainer"] {
                color: #000000 !important;
            }
            div.stAlert {
                color: #000000 !important;
                background-color: #fff3cd !important;
            }
            div.stAlert p {
                color: #000000 !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div style="text-align: center; margin-bottom: 2rem;"><h1 style="color: #1f2937;">Welcome Back</h1><p style="color: #4b5563;">Please sign in to continue</p></div>', unsafe_allow_html=True)
            st.text_input(label="Username:", value="", key="user", on_change=creds_entered)
            st.text_input(label="Password:", value="", key="passwd", type="password", on_change=creds_entered)
        return False
    
    return True

def logout():
    """Handle user logout."""
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.session_state["user"] = ""
    st.session_state["passwd"] = ""

def main():
    if authenticate_user():
        with st.sidebar:
            st.markdown("<h2 style='text-align: center;'>Menu</h2>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='text-align: center;'>Welcome, {st.session_state['username']}!</h4>", 
                    unsafe_allow_html=True)
            
            selected = option_menu(
                'Main Menu',
                ['URL Extractor', 'Keyword Analysis','Reverse Silos'],
                icons=['house', 'list-check','crosshair'],
                default_index=0,
                menu_icon="cast"
            )
            
            if st.button("Logout"):
                logout()
                st.rerun()

        if selected == "URL Extractor":
            link()
        elif selected == "Keyword Analysis":
            Home()
        elif selected == "Reverse Silos":
            analyze_internal_links()
        
if __name__ == "__main__":
    main()