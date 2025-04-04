import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, call
import tempfile
import os
from io import StringIO

from modules.reverse_silos import (
    is_valid_url,
    get_main_content_anchor_tags,
    run_analysis,
    create_detailed_report_html,
    generate_pdf_report,
    manual_input_tab,
    file_upload_tab,
    analyze_internal_links,
    inject_custom_css,
    display_analysis_results,
)

@pytest.fixture
def sample_data():
    """Fixture to provide sample page data."""
    return pd.DataFrame({
        'type': ['Homepage', 'Target Page', 'Blog 1', 'Blog 2'],
        'url': [
            'https://example.com',
            'https://example.com/target',
            'https://example.com/blog1',
            'https://example.com/blog2'
        ]
    })

@pytest.fixture
def sample_links():
    """Fixture to provide sample link data."""
    return {
        'Homepage': [
            {'text': 'Target Page', 'url': 'https://example.com/target'},
            {'text': 'Blog 1', 'url': 'https://example.com/blog1'}
        ],
        'Target Page': [
            {'text': 'Homepage', 'url': 'https://example.com'},
            {'text': 'Blog 2', 'url': 'https://example.com/blog2'}
        ],
        'Blog 1': [
            {'text': 'Target Page', 'url': 'https://example.com/target'},
            {'text': 'Blog 2', 'url': 'https://example.com/blog2'}
        ],
        'Blog 2': [
            {'text': 'Target Page', 'url': 'https://example.com/target'},
            {'text': 'Blog 1', 'url': 'https://example.com/blog1'}
        ]
    }

@pytest.fixture
def mock_streamlit():
    """Mock Streamlit functions with proper session state handling."""
    with patch('modules.reverse_silos.st') as mock_st:
        mock_st.session_state = {}
        mock_st.get_option.return_value = "#ffffff"
        mock_st.button.return_value = False
        mock_st.tabs.return_value = [MagicMock(), MagicMock()]
        yield mock_st

def test_is_valid_url():
    """Test the is_valid_url function."""
    assert is_valid_url('https://example.com') == True
    assert is_valid_url('http://example.com') == True
    assert is_valid_url('example.com') == False
    assert is_valid_url('') == False
    assert is_valid_url('not a url') == False

@patch('modules.reverse_silos.requests.get')
def test_get_main_content_anchor_tags(mock_get):
    """Test the get_main_content_anchor_tags function with proper HTML parsing."""
    mock_response = MagicMock()
    mock_response.text = """
    <html>
        <body>
            <header>
                <a href="/header-link">Header Link</a>
            </header>
            <main id="main-content">
                <a href="/internal-link">Internal Link</a>
                <article>
                    <a href="/nested-link">Nested Link</a>
                </article>
            </main>
            <footer>
                <a href="/footer-link">Footer Link</a>
            </footer>
        </body>
    </html>
    """
    mock_get.return_value = mock_response
    
    result = get_main_content_anchor_tags('https://example.com', 'Homepage')
    
    assert len(result) == 2
    assert result[0]['url'] == 'https://example.com/internal-link'
    assert result[1]['url'] == 'https://example.com/nested-link'

@patch('modules.reverse_silos.get_main_content_anchor_tags')
def test_run_analysis(mock_get_tags, sample_data, mock_streamlit):
    """Test the run_analysis function with proper session state handling."""
    mock_get_tags.side_effect = [
        [{'text': 'Target Page', 'url': 'https://example.com/target'}],
        [{'text': 'Homepage', 'url': 'https://example.com'}],
        [{'text': 'Target Page', 'url': 'https://example.com/target'}],
        [{'text': 'Target Page', 'url': 'https://example.com/target'}]
    ]
    
    with patch.dict('modules.reverse_silos.st.session_state', {}):
        run_analysis(sample_data, source="manual")
        
        assert 'manual_data' in mock_streamlit.session_state
        assert 'manual_all_links' in mock_streamlit.session_state
        
        matrix_df = mock_streamlit.session_state["manual_matrix_df"]
        assert matrix_df.loc['Homepage', 'Target Page'] == 1
        assert matrix_df.loc['Target Page', 'Homepage'] == 1
        assert matrix_df.loc['Blog 1', 'Target Page'] == 1
        assert matrix_df.loc['Blog 2', 'Target Page'] == 1

def test_create_detailed_report_html(sample_data, sample_links, mock_streamlit):
    """Test the create_detailed_report_html function."""
    with patch.dict('modules.reverse_silos.st.session_state', {
        "manual_data": sample_data,
        "manual_all_links": sample_links,
        "manual_url_to_type": dict(zip(sample_data['url'], sample_data['type'])),
        "manual_matrix_df": pd.DataFrame(np.ones((4, 4))), 
        "manual_styled_matrix_html": "<table>Test Matrix</table>"
    }):
        html = create_detailed_report_html(source="manual")
        assert "<html>" in html
        assert "Complete Interlinking Matrix" in html

# Fixed test_generate_pdf_report
@patch('modules.reverse_silos.pdfkit.configuration')
@patch('modules.reverse_silos.platform')
@patch('modules.reverse_silos.pdfkit.from_string')
@patch('modules.reverse_silos.os.remove')
def test_generate_pdf_report(mock_remove, mock_from_string, mock_platform, mock_config):
    """Test PDF generation with proper file handling"""
    mock_platform.system.return_value = "Windows"
    mock_config.return_value = MagicMock()
    
    with patch('tempfile.NamedTemporaryFile') as mock_temp:
        mock_temp.return_value.__enter__.return_value.name = "dummy.pdf"
        mock_temp.return_value.__enter__.return_value.read.return_value = b"PDF content"
        result = generate_pdf_report("<html>test</html>")
        
        assert result == b"PDF content"
        mock_config.assert_called_once()
        mock_from_string.assert_called_once()
        mock_remove.assert_called_once()

# Fixed test_display_analysis_results
@patch('modules.reverse_silos.create_detailed_report_html')
@patch('modules.reverse_silos.generate_pdf_report')
def test_display_analysis_results(mock_pdf, mock_html, mock_streamlit):
    """Test full results display with PDF download"""
    # Mock complete analysis data
    mock_html.return_value = "<html>report</html>"
    mock_pdf.return_value = b"PDF bytes"
    
    with patch.dict('modules.reverse_silos.st.session_state', {
        "manual_data": pd.DataFrame({
            'type': ['Homepage', 'Target Page'],
            'url': ['https://example.com', 'https://example.com/target']
        }),
        "manual_all_links": {
            'Homepage': [{'text': 'Target', 'url': 'https://example.com/target'}],
            'Target Page': [{'text': 'Home', 'url': 'https://example.com'}]
        },
        "manual_url_to_type": {
            'https://example.com': 'Homepage',
            'https://example.com/target': 'Target Page'
        },
        "manual_matrix_df": pd.DataFrame(
            [[np.nan, 1], [1, np.nan]],
            columns=['Homepage', 'Target Page'],
            index=['Homepage', 'Target Page']
        ),
        "manual_styled_matrix_html": "<table>matrix</table>"
    }):
        # Simulate PDF download button click
        mock_streamlit.button.return_value = True
        display_analysis_results(source="manual")
        
        # Verify PDF download was triggered
        mock_streamlit.download_button.assert_called_once_with(
            label="Download PDF Report",
            data=b"PDF bytes",
            file_name="internal_link_analysis.pdf",
            mime="application/pdf"
        )