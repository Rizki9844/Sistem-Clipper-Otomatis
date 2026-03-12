"""
Azure Blob Storage Service
=============================
Upload, download, and manage video files
in Azure Blob Storage (or Azurite for local dev).
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from azure.storage.blob import (
    BlobServiceClient,
    BlobClient,
    generate_blob_sas,
    BlobSasPermissions,
)

from app.config import settings


class AzureBlobStorage:
    """Handles video file storage on Azure Blob Storage."""

    def __init__(self):
        self.connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        self.client = BlobServiceClient.from_connection_string(self.connection_string)
        self._ensure_containers()

    def _ensure_containers(self):
        """Create containers if they don't exist."""
        for container_name in [
            settings.AZURE_STORAGE_CONTAINER_RAW,
            settings.AZURE_STORAGE_CONTAINER_CLIPS,
        ]:
            try:
                self.client.create_container(container_name)
            except Exception:
                pass  # Container already exists

    async def upload_video(
        self,
        content: bytes,
        original_filename: str,
        content_type: str = "video/mp4",
        container: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Upload video to Azure Blob Storage.

        Returns:
            tuple[blob_name, blob_url]
        """
        container = container or settings.AZURE_STORAGE_CONTAINER_RAW

        # Generate unique blob name
        ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "mp4"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"{timestamp}_{uuid.uuid4().hex[:8]}.{ext}"

        # Upload
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)
        blob_client.upload_blob(
            content,
            content_type=content_type,
            overwrite=True,
        )

        blob_url = blob_client.url
        return blob_name, blob_url

    async def download_video(
        self,
        blob_name: str,
        container: Optional[str] = None,
    ) -> bytes:
        """Download video content from blob storage."""
        container = container or settings.AZURE_STORAGE_CONTAINER_RAW
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)
        download = blob_client.download_blob()
        return download.readall()

    async def download_to_file(
        self,
        blob_name: str,
        local_path: str,
        container: Optional[str] = None,
    ) -> str:
        """Download blob directly to a local file (for FFmpeg processing)."""
        container = container or settings.AZURE_STORAGE_CONTAINER_RAW
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)

        with open(local_path, "wb") as f:
            download = blob_client.download_blob()
            download.readinto(f)

        return local_path

    async def upload_from_file(
        self,
        local_path: str,
        blob_name: str,
        content_type: str = "video/mp4",
        container: Optional[str] = None,
    ) -> str:
        """Upload a local file to blob storage (for processed clips)."""
        container = container or settings.AZURE_STORAGE_CONTAINER_CLIPS
        blob_client = self.client.get_blob_client(container=container, blob=blob_name)

        with open(local_path, "rb") as f:
            blob_client.upload_blob(
                f,
                content_type=content_type,
                overwrite=True,
            )

        return blob_client.url

    def get_sas_url(
        self,
        blob_name: str,
        container: Optional[str] = None,
        expiry_hours: int = 24,
    ) -> str:
        """Generate a time-limited SAS URL for secure access."""
        container = container or settings.AZURE_STORAGE_CONTAINER_CLIPS

        # Parse account details from connection string
        account_name = None
        account_key = None
        for part in self.connection_string.split(";"):
            if part.startswith("AccountName="):
                account_name = part.split("=", 1)[1]
            elif part.startswith("AccountKey="):
                account_key = part.split("=", 1)[1]

        if not account_name or not account_key:
            # Fallback for Azurite/local dev
            blob_client = self.client.get_blob_client(container=container, blob=blob_name)
            return blob_client.url

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
        )

        return f"https://{account_name}.blob.core.windows.net/{container}/{blob_name}?{sas_token}"

    async def delete_blob(
        self,
        container: str,
        blob_name: str,
    ):
        """Delete a blob from storage."""
        try:
            blob_client = self.client.get_blob_client(container=container, blob=blob_name)
            blob_client.delete_blob()
        except Exception:
            pass  # Blob might already be deleted
