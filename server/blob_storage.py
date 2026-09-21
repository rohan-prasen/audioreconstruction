"""Azure Blob Storage: SAS minting and blob transfer.

Knows nothing about HTTP or FastAPI. Callers translate BlobStorageError
into whatever their transport speaks.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from azure.core.exceptions import AzureError
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    generate_blob_sas,
)


class BlobStorageError(Exception):
    """A storage operation did not succeed."""


ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT", "")
KEY = os.getenv("AZURE_STORAGE_KEY", "")
UPLOAD_CONTAINER = os.getenv("AZURE_UPLOAD_CONTAINER", "uploads")
OUTPUT_CONTAINER = os.getenv("AZURE_OUTPUT_CONTAINER", "outputs")
ACCOUNT_URL = os.getenv(
    "AZURE_BLOB_ENDPOINT",
    f"https://{ACCOUNT}.blob.core.windows.net",
)

UPLOAD_SAS_MINUTES = 15
DOWNLOAD_SAS_HOURS = 1

_service: BlobServiceClient | None = None


def _require_config() -> None:
    if not ACCOUNT or not KEY:
        raise BlobStorageError(
            "AZURE_STORAGE_ACCOUNT and AZURE_STORAGE_KEY must be set."
        )


def _client() -> BlobServiceClient:
    global _service
    if _service is None:
        _require_config()
        _service = BlobServiceClient(account_url=ACCOUNT_URL, credential=KEY)
    return _service


def _blob(container: str, name: str):
    return _client().get_blob_client(container=container, blob=name)


def _expires_in(**kwargs) -> datetime:
    return datetime.now(timezone.utc) + timedelta(**kwargs)


def _sas(container: str, name: str, permission, expiry, **extra) -> str:
    _require_config()
    token = generate_blob_sas(
        account_name=ACCOUNT,
        container_name=container,
        blob_name=name,
        account_key=KEY,
        permission=permission,
        expiry=expiry,
        **extra,
    )
    return f"{ACCOUNT_URL}/{container}/{name}?{token}"


def new_blob_name(suffix: str = ".mp3") -> str:
    """Server-chosen blob name. Clients never pick their own."""
    return f"{uuid.uuid4().hex}{suffix}"


def make_upload_sas(blob_name: str) -> str:
    """Timed key card: may create/write this one blob. Cannot read."""
    return _sas(
        UPLOAD_CONTAINER,
        blob_name,
        BlobSasPermissions(create=True, write=True),
        _expires_in(minutes=UPLOAD_SAS_MINUTES),
    )


def make_download_sas(blob_name: str, filename: str) -> str:
    """Timed key card: may read this one blob, served as a FLAC download."""
    return _sas(
        OUTPUT_CONTAINER,
        blob_name,
        BlobSasPermissions(read=True),
        _expires_in(hours=DOWNLOAD_SAS_HOURS),
        content_type="audio/flac",
        content_disposition=f'attachment; filename="{filename}"',
    )


def blob_size(blob_name: str, container: str | None = None) -> int:
    target = container or UPLOAD_CONTAINER
    try:
        return _blob(target, blob_name).get_blob_properties().size
    except AzureError as exc:
        raise BlobStorageError(f"Cannot stat {blob_name}: {exc}") from exc


def download_to_path(blob_name: str, dest: Path) -> None:
    try:
        with open(dest, "wb") as f:
            _blob(UPLOAD_CONTAINER, blob_name).download_blob().readinto(f)
    except AzureError as exc:
        raise BlobStorageError(f"Cannot download {blob_name}: {exc}") from exc


def upload_flac(src: Path, blob_name: str) -> None:
    try:
        with open(src, "rb") as f:
            _blob(OUTPUT_CONTAINER, blob_name).upload_blob(f, overwrite=True)
    except AzureError as exc:
        raise BlobStorageError(f"Cannot upload {blob_name}: {exc}") from exc


def delete_blob(blob_name: str, container: str | None = None) -> None:
    """Best-effort cleanup. Never raises."""
    target = container or UPLOAD_CONTAINER
    try:
        _blob(target, blob_name).delete_blob(delete_snapshots="include")
    except AzureError:
        pass


def ensure_containers() -> None:
    """Create the containers if missing. For local dev and first run."""
    for name in (UPLOAD_CONTAINER, OUTPUT_CONTAINER):
        try:
            _client().create_container(name)
        except AzureError:
            pass
