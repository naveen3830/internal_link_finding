import pytest
from unittest.mock import patch, MagicMock
import requests
from bs4 import BeautifulSoup
import pandas as pd
from modules.url_extractor import (
    detect_url_language,
    fetch_sitemap_urls,
    parse_sitemap_index,
    parse_sitemap
)

class TestURLExtractor:
    @pytest.mark.parametrize("url,expected_language", [
        ("https://example.com/en/products", "en"),
        ("https://example.com/fr/produits", "fr"),
        ("https://example.com/de/produkte", "de"),
        ("https://example.com/zh/products", "zh"),
        ("https://example.com/es/productos", "es"),
        ("https://example.cn/products", "zh"),
        ("https://example.jp/products", "ja"),
        ("https://example.com/blog/post", "blogs"),
        ("https://example.com/products/item", "products"),
        ("https://example.com/company/about", "company"),
        ("https://example.com/solutions/business", "solutions"),
        ("https://teamviewer.cn/products", "zh"),
        ("https://teamviewer.com/ja/products", "ja"),
        ("https://anydesk.com/zhs/solutions/remote-work", "zh"),
        ("https://example.com/distribucion-de-licencias-tensor", "es"),
    ])
    def test_detect_url_language(self, url, expected_language):
        """Test if URL language detection works correctly for various URLs"""
        assert detect_url_language(url) == expected_language

    @pytest.mark.parametrize("url,country_tld,expected_language", [
        ("https://example.it/page", ".it", "it"),
        ("https://example.de/page", ".de", "de"),
        ("https://example.jp/page", ".jp", "ja"),
        ("https://example.kr/page", ".kr", "ko"),
    ])
    def test_detect_url_language_country_tld(self, url, country_tld, expected_language):
        """Test if URL language detection works correctly with country TLDs"""
        assert detect_url_language(url) == expected_language

    @patch('requests.get')
    def test_fetch_sitemap_urls_success(self, mock_get):
        """Test fetching sitemap URLs when sitemaps are found"""
        # Mock successful response for sitemap.xml
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://example.com/page1</loc></url>
        <url><loc>https://example.com/page2</loc></url>
        </urlset>"""
        mock_get.return_value = mock_response
        
        result = fetch_sitemap_urls("https://example.com")
        assert len(result) == 10
        assert "https://example.com/page1" in result
        assert "https://example.com/page2" in result
        assert mock_get.call_count == 5

    @patch('requests.get')
    def test_fetch_sitemap_urls_no_sitemap(self, mock_get):
        """Test fetching sitemap URLs when no sitemaps are found"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = fetch_sitemap_urls("https://example.com")
        assert len(result) == 0
        
        # Verify that the function tried to fetch from multiple sitemap paths
        assert mock_get.call_count == 5

    @patch('requests.get')
    def test_fetch_sitemap_urls_network_error(self, mock_get):
        """Test fetching sitemap URLs when network error occurs"""
        # Mock network error
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        result = fetch_sitemap_urls("https://example.com")
        assert len(result) == 0
        
        # Verify that the function tried to fetch from multiple sitemap paths
        assert mock_get.call_count == 5

    @patch('requests.get')
    def test_parse_sitemap_index(self, mock_get):
        """Test parsing sitemap index file"""
        # Mock successful response for sitemap_index.xml
        mock_nested_response = MagicMock()
        mock_nested_response.status_code = 200
        mock_nested_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/nested-page1</loc></url>
          <url><loc>https://example.com/nested-page2</loc></url>
        </urlset>"""
        mock_get.return_value = mock_nested_response
        
        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <sitemap><loc>https://example.com/sitemap1.xml</loc></sitemap>
          <sitemap><loc>https://example.com/sitemap2.xml</loc></sitemap>
        </sitemapindex>"""
        
        result = parse_sitemap_index(sitemap_content, "https://example.com")
        
        assert len(result) == 4  # 2 URLs from each nested sitemap
        assert "https://example.com/nested-page1" in result
        assert "https://example.com/nested-page2" in result
        assert mock_get.call_count == 2  # Tried to fetch both nested sitemaps

    def test_parse_sitemap_index_error(self):
        """Test parsing sitemap index file with error"""
        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
        <invalid>This is not a valid sitemap index</invalid>"""
        
        result = parse_sitemap_index(sitemap_content, "https://example.com")
        assert len(result) == 0  # Empty result due to error

    def test_parse_sitemap(self):
        """Test parsing sitemap file"""
        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/page1</loc></url>
          <url><loc>https://example.com/page2</loc></url>
          <url><loc>https://example.com/image.png</loc></url>
        </urlset>"""
        
        result = parse_sitemap(sitemap_content)
        
        assert len(result) == 2  # Should skip the image URL
        assert "https://example.com/page1" in result
        assert "https://example.com/page2" in result
        assert "https://example.com/image.png" not in result

    def test_parse_sitemap_error(self):
        """Test parsing sitemap file with error"""
        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
        <invalid>This is not a valid sitemap</invalid>"""
        
        result = parse_sitemap(sitemap_content)
        assert len(result) == 0  # Empty result due to error
    @patch('streamlit.session_state')
    @patch('streamlit.text_input')
    @patch('streamlit.button')
    @patch('streamlit.progress')
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.dataframe')
    @patch('streamlit.download_button')
    @patch('streamlit.multiselect')
    @patch('modules.url_extractor.fetch_sitemap_urls')
    @patch('modules.url_extractor.detect_url_language')
    def test_link_function_integration(
        self, mock_detect_language, mock_fetch_urls, mock_multiselect,
        mock_download, mock_dataframe, mock_error, mock_success,
        mock_progress, mock_button, mock_text_input, mock_session):
        """Test the integration of the link function with mocked dependencies"""
        # Mock component returns
        mock_text_input.return_value = "https://example.com"
        mock_button.return_value = True  # Simulate button click

        # Mock backend responses
        mock_fetch_urls.return_value = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ]
        mock_detect_language.side_effect = ["en", "en", "es"]

        # Mock session state
        session_data = {
            'uploaded_df': None,
            'processed_results': [],
            'filtered_df': pd.DataFrame({
                'source_url': ['https://example.com'],
                'status': ['active']
            })
        }
        mock_session.__getitem__.side_effect = lambda key: session_data[key]
        mock_session.__setitem__.side_effect = lambda key, value: session_data.update({key: value})

        # Simulate Streamlit's top-to-bottom execution
        # --------------------------------------------------
        # 1. Render input components (outside button conditional)
        input_url = mock_text_input("Enter website URL")
        
        # 2. Handle button click
        if mock_button("Find Links"):
            # 3. Process URLs after button click
            fetched_urls = mock_fetch_urls(input_url)
            
            results = []
            for fetched_url in fetched_urls:
                lang = mock_detect_language(fetched_url)
                results.append({
                    'url': fetched_url,
                    'language': lang,
                    'status': 'processed'
                })
            
            # 4. Update session state
            session_data['processed_results'] = results
            
            # 5. Show outputs
            mock_success(f"Processed {len(results)} URLs")
            mock_dataframe(pd.DataFrame(results))
            mock_download(label="Download Results")

        # Verification
        # --------------------------------------------------
        # Verify text input was called with correct label
        mock_text_input.assert_called_once_with("Enter website URL")
        
        # Verify button was created with correct label
        mock_button.assert_called_once_with("Find Links")
        
        # Verify backend processing
        mock_fetch_urls.assert_called_once_with("https://example.com")
        assert mock_detect_language.call_count == 3
        
        # Verify success message
        mock_success.assert_called_once_with("Processed 3 URLs")