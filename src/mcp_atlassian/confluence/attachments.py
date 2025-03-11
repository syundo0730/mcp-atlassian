"""Module for Confluence attachment operations."""

import logging
from pathlib import Path
from typing import List, Optional, Union

import requests

from ..models.confluence import ConfluenceAttachment
from .client import ConfluenceClient

logger = logging.getLogger("mcp-atlassian")


class AttachmentsMixin(ConfluenceClient):
    """Mixin for Confluence attachment operations."""

    def attach_file(
        self,
        page_id: str,
        file_path: Union[str, Path],
        comment: Optional[str] = None,
    ) -> ConfluenceAttachment:
        """
        Upload an attachment to a Confluence page.

        Args:
            page_id: The ID of the page to attach the file to
            file_path: Path to the file to upload
            comment: Optional comment for the attachment
            minor_edit: Whether this is a minor edit

        Returns:
            ConfluenceAttachment model containing the attachment data

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file path is invalid
            Exception: If there is an error uploading the attachment
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        try:
            result = self.confluence.attach_file(
                filename=file_path.name,
                page_id=page_id,
                comment=comment,
            )
            return ConfluenceAttachment.from_api_response(result)

        except requests.RequestException as e:
            logger.error(f"Network error when uploading attachment: {str(e)}")
            raise Exception(f"Failed to upload attachment: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error uploading attachment: {str(e)}")
            raise Exception(f"Failed to upload attachment: {str(e)}") from e

    def get_attachments(
        self, page_id: str, start: int = 0, limit: int = 50
    ) -> List[ConfluenceAttachment]:
        """
        Get all attachments for a specific page.

        Args:
            page_id: The ID of the page to get attachments from
            start: The starting index for pagination
            limit: Maximum number of attachments to return

        Returns:
            List of ConfluenceAttachment models containing attachment data
        """
        try:
            # Get the attachments
            result = self.confluence.get_attachments_from_content(
                page_id=page_id, start=start, limit=limit, expand="version"
            )
            attachments = result.get("results", [])
            attachment_models = [
                ConfluenceAttachment.from_api_response(attachment, base_url=self.config.url)
                for attachment in attachments
            ]
            return attachment_models

        except Exception as e:
            logger.error(f"Error getting attachments for page {page_id}: {str(e)}")
            # Log the full traceback at debug level for troubleshooting
            logger.debug("Full exception details:", exc_info=True)
            return []

    def delete_attachment_by_filename(self, page_id: str, filename: str) -> bool:
        """
        Delete an attachment from Confluence.

        Args:
            attachment_id: The ID of the attachment to delete

        Returns:
            True if the attachment was deleted successfully, False otherwise
        """
        try:
            self.confluence.delete_attachment(
                page_id=page_id,
                filename=filename,
            )
            return True

        except Exception as e:
            logger.error(f"Error deleting attachment {filename}: {str(e)}")
            return False

    def delete_attachment_by_id(self, attachment_id: str, version: str) -> bool:
        """
        Delete an attachment from Confluence.

        Args:
            attachment_id: The ID of the attachment to delete

        Returns:
            True if the attachment was deleted successfully, False otherwise
        """
        try:
            self.confluence.delete_attachment_by_id(
                attachment_id=attachment_id,
                version=version,
            )
            return True

        except Exception as e:
            logger.error(f"Error deleting attachment {attachment_id}: {str(e)}")
            return False
