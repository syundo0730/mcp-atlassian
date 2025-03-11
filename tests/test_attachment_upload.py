"""Test for Confluence attachment upload functionality."""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import requests

from mcp_atlassian.confluence import ConfluenceFetcher
from mcp_atlassian.models.confluence import ConfluenceAttachment


@pytest.fixture
def mock_confluence_fetcher():
    """Create a mock ConfluenceFetcher instance."""
    with mock.patch("mcp_atlassian.confluence.client.Confluence") as mock_confluence:
        # Mock the config
        mock_config = mock.MagicMock()
        mock_config.url = "https://example.atlassian.net/wiki"
        mock_config.username = "test_user"
        mock_config.api_token = "test_token"
        
        # Create the fetcher with the mock config
        fetcher = ConfluenceFetcher(config=mock_config)
        
        # Return the fetcher and the mock confluence instance
        yield fetcher, mock_confluence


def test_upload_attachment(mock_confluence_fetcher):
    """Test uploading an attachment to a Confluence page."""
    fetcher, mock_confluence = mock_confluence_fetcher
    
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_file.write(b"test image content")
        temp_file_path = temp_file.name
    
    try:
        # Mock the requests.post response
        with mock.patch("requests.post") as mock_post:
            mock_response = mock.MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "id": "att12345",
                        "type": "attachment",
                        "title": os.path.basename(temp_file_path),
                        "metadata": {
                            "mediaType": "image/png",
                            "comment": "Test comment"
                        },
                        "version": {
                            "number": 1,
                            "when": "2023-01-01T00:00:00.000Z"
                        }
                    }
                ]
            }
            mock_post.return_value = mock_response
            
            # Call the upload_attachment method
            result = fetcher.upload_attachment(
                page_id="12345",
                file_path=temp_file_path,
                comment="Test comment"
            )
            
            # Verify the result
            assert isinstance(result, ConfluenceAttachment)
            assert result.id == "att12345"
            assert result.title == os.path.basename(temp_file_path)
            assert result.media_type == "image/png"
            
            # Verify the request was made correctly
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://example.atlassian.net/wiki/rest/api/content/12345/child/attachment"
            assert kwargs["auth"] == ("test_user", "test_token")
            assert kwargs["headers"] == {"X-Atlassian-Token": "nocheck"}
            assert "file" in kwargs["files"]
            assert kwargs["data"] == {"comment": "Test comment"}
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def test_get_attachments(mock_confluence_fetcher):
    """Test getting attachments from a Confluence page."""
    fetcher, mock_confluence = mock_confluence_fetcher
    
    # Mock the get_attachments_from_content method
    mock_confluence.return_value.get_attachments_from_content.return_value = {
        "results": [
            {
                "id": "att12345",
                "type": "attachment",
                "title": "test.png",
                "metadata": {
                    "mediaType": "image/png"
                },
                "version": {
                    "number": 1,
                    "when": "2023-01-01T00:00:00.000Z"
                }
            }
        ]
    }
    
    # Call the get_attachments method
    result = fetcher.get_attachments(page_id="12345")
    
    # Verify the result
    assert len(result) == 1
    assert isinstance(result[0], ConfluenceAttachment)
    assert result[0].id == "att12345"
    assert result[0].title == "test.png"
    assert result[0].media_type == "image/png"
    
    # Verify the method was called correctly
    mock_confluence.return_value.get_attachments_from_content.assert_called_once_with(
        page_id="12345", start=0, limit=50, expand="version"
    )


def test_add_attachment_to_page_content(mock_confluence_fetcher):
    """Test adding an attachment to a page's content."""
    fetcher, mock_confluence = mock_confluence_fetcher
    
    # Mock the get_page_content method
    with mock.patch.object(fetcher, "get_page_content") as mock_get_page:
        mock_page = mock.MagicMock()
        mock_page.id = "12345"
        mock_page.title = "Test Page"
        mock_page.content = "<p>Existing content</p>"
        mock_get_page.return_value = mock_page
        
        # Mock the update_page method
        with mock.patch.object(fetcher, "update_page") as mock_update_page:
            mock_update_page.return_value = mock_page
            
            # Call the add_attachment_to_page_content method
            result = fetcher.add_attachment_to_page_content(
                page_id="12345",
                attachment_filename="test.png",
                display_type="image",
                height=300,
                width=400,
                alt_text="Test image",
                title="Test Title"
            )
            
            # Verify the result
            assert result is True
            
            # Verify the methods were called correctly
            mock_get_page.assert_called_once_with("12345", convert_to_markdown=False)
            mock_update_page.assert_called_once()
            args, kwargs = mock_update_page.call_args
            assert kwargs["page_id"] == "12345"
            assert kwargs["title"] == "Test Page"
            assert "<ac:image ac:height=\"300\" ac:width=\"400\" ac:title=\"Test Title\" ac:alt=\"Test image\">" in kwargs["body"]
            assert "<ri:attachment ri:filename=\"test.png\" />" in kwargs["body"]
            assert kwargs["is_minor_edit"] is True


def test_upload_and_add_to_page(mock_confluence_fetcher):
    """Test uploading an attachment and adding it to a page in one operation."""
    fetcher, mock_confluence = mock_confluence_fetcher
    
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_file.write(b"test image content")
        temp_file_path = temp_file.name
    
    try:
        # Mock the upload_attachment method
        with mock.patch.object(fetcher, "upload_attachment") as mock_upload:
            mock_attachment = mock.MagicMock(spec=ConfluenceAttachment)
            mock_attachment.id = "att12345"
            mock_attachment.title = os.path.basename(temp_file_path)
            mock_upload.return_value = mock_attachment
            
            # Mock the add_attachment_to_page_content method
            with mock.patch.object(fetcher, "add_attachment_to_page_content") as mock_add:
                mock_add.return_value = True
                
                # Call the upload_and_add_to_page method
                success, attachment = fetcher.upload_and_add_to_page(
                    page_id="12345",
                    file_path=temp_file_path,
                    display_type="image",
                    height=300,
                    width=400,
                    alt_text="Test image",
                    title="Test Title",
                    comment="Test comment"
                )
                
                # Verify the result
                assert success is True
                assert attachment is mock_attachment
                
                # Verify the methods were called correctly
                mock_upload.assert_called_once_with(
                    page_id="12345",
                    file_path=Path(temp_file_path),
                    comment="Test comment",
                    minor_edit=True
                )
                
                mock_add.assert_called_once_with(
                    page_id="12345",
                    attachment_filename=os.path.basename(temp_file_path),
                    display_type="image",
                    height=300,
                    width=400,
                    alt_text="Test image",
                    title="Test Title"
                )
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path) 
