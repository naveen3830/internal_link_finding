import pytest
import hashlib
import streamlit as st
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import hash_password, creds_entered, authenticate_user, logout, main

@pytest.fixture
def mock_streamlit():
    with patch('app.st') as mock_st:
        mock_st.session_state = {}
        yield mock_st

def test_hash_password():
    password = "password"
    expected_hash = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    assert hash_password(password) == expected_hash
    
    # Test with empty string
    assert hash_password("") == hashlib.sha256("".encode()).hexdigest()
    
    # Test with special characters
    special_password = "!@#$%^&*()"
    assert hash_password(special_password) == hashlib.sha256(special_password.encode()).hexdigest()

# Test creds_entered function
def test_creds_entered_valid_credentials(mock_streamlit):
    # Setup
    mock_streamlit.session_state = {
        "user": "user1",
        "passwd": "password"
    }
    
    # Execute
    with patch('app.AUTHORIZED_USERS', {
        "user1": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    }):
        creds_entered()
    
    # Assert
    assert mock_streamlit.session_state["authenticated"] == True
    assert mock_streamlit.session_state["username"] == "user1"
    assert not mock_streamlit.error.called

def test_creds_entered_invalid_credentials(mock_streamlit):
    # Setup
    mock_streamlit.session_state = {
        "user": "user1",
        "passwd": "wrong_password"
    }
    
    # Execute
    with patch('app.AUTHORIZED_USERS', {
        "user1": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    }):
        creds_entered()
    
    # Assert
    assert mock_streamlit.session_state["authenticated"] == False
    assert mock_streamlit.error.called

def test_creds_entered_empty_password(mock_streamlit):
    # Setup
    mock_streamlit.session_state = {
        "user": "user1",
        "passwd": ""
    }
    
    # Execute
    creds_entered()
    
    # Assert
    assert mock_streamlit.session_state["authenticated"] == False
    assert mock_streamlit.warning.called

def test_creds_entered_empty_username(mock_streamlit):
    # Setup
    mock_streamlit.session_state = {
        "user": "",
        "passwd": "password"
    }
    
    # Execute
    creds_entered()
    
    # Assert
    assert mock_streamlit.session_state["authenticated"] == False
    assert mock_streamlit.warning.called

# Test authenticate_user function
def test_authenticate_user_not_authenticated(mock_streamlit):
    # Setup
    mock_streamlit.session_state = {}
    
    # Execute
    result = authenticate_user()
    
    # Assert
    assert result == False
    assert mock_streamlit.session_state["authenticated"] == False
    assert mock_streamlit.session_state["username"] is None
    assert mock_streamlit.text_input.call_count == 2  # Username and password fields

def test_authenticate_user_already_authenticated(mock_streamlit):
    # Setup
    mock_streamlit.session_state = {
        "authenticated": True,
        "username": "user1"
    }
    
    # Execute
    result = authenticate_user()
    
    # Assert
    assert result == True
    assert mock_streamlit.text_input.call_count == 0  # No login form displayed

# Test logout function
def test_logout(mock_streamlit):
    # Setup
    mock_streamlit.session_state = {
        "authenticated": True,
        "username": "user1",
        "user": "user1",
        "passwd": "password"
    }
    
    # Execute
    logout()
    
    # Assert
    assert mock_streamlit.session_state["authenticated"] == False
    assert mock_streamlit.session_state["username"] is None
    assert mock_streamlit.session_state["user"] == ""
    assert mock_streamlit.session_state["passwd"] == ""

# Test main function
def test_main_not_authenticated(mock_streamlit):
    # Setup
    mock_streamlit.session_state = {"authenticated": False}
    
    # Mock authenticate_user to return False
    with patch('app.authenticate_user', return_value=False):
        # Execute
        main()
        
        assert not mock_streamlit.sidebar.called

# Test different menu selections
def test_main_keyword_analysis_selected(mock_streamlit):
    # Setup
    mock_streamlit.session_state = {
        "authenticated": True,
        "username": "user1"
    }
    
    # Mock the necessary functions
    with patch('app.authenticate_user', return_value=True), \
        patch('app.option_menu', return_value="Keyword Analysis"), \
        patch('app.internal_linking_opportunities_finder') as mock_finder:
        
        # Execute
        main()
        
        # Assert
        assert mock_finder.called

def test_main_reverse_silos_selected(mock_streamlit):
    # Setup
    mock_streamlit.session_state = {
        "authenticated": True,
        "username": "user1"
    }
    
    # Mock the necessary functions
    with patch('app.authenticate_user', return_value=True), \
        patch('app.option_menu', return_value="Reverse Silos"), \
        patch('app.analyze_internal_links') as mock_analyze:
        
        # Execute
        main()
        
        # Assert
        assert mock_analyze.called

# Test logout button in main
def test_main_logout_button(mock_streamlit):
    # Setup
    mock_streamlit.session_state = {
        "authenticated": True,
        "username": "user1"
    }
    mock_streamlit.button.return_value = True  
    
    with patch('app.authenticate_user', return_value=True), \
         patch('app.option_menu', return_value="URL Extractor"), \
         patch('app.logout') as mock_logout:
        
        with pytest.raises(SystemExit):
            with patch('app.st.rerun', side_effect=SystemExit):
                main()
        
        assert mock_logout.called