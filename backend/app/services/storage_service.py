import re
import time

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.db.supabase_client import get_supabase

DRIVER_DOCUMENTS_BUCKET = "driver-documents"
POD_PHOTOS_BUCKET = "pod-photos"

_ALLOWED_DOCUMENT_MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "application/pdf": "pdf",
}

# Bucket privat: path disimpan di DB, signed URL dibuat on-demand saat dibaca
# (lihat get_signed_url) supaya tidak menyimpan URL yang bisa kedaluwarsa.
_SIGNED_URL_EXPIRES_IN_SECONDS = 60 * 60  # 1 jam


async def upload_document(*, bucket: str, folder: str, filename_prefix: str, file: UploadFile) -> str:
    settings = get_settings()

    extension = _ALLOWED_DOCUMENT_MIME_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Tipe file '{file.content_type}' tidak didukung untuk {filename_prefix}. "
                "Gunakan JPEG, PNG, atau PDF."
            ),
        )

    contents = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ukuran file {filename_prefix} melebihi batas {settings.max_upload_size_mb}MB.",
        )

    safe_folder = re.sub(r"[^a-zA-Z0-9_-]", "_", folder)
    safe_prefix = re.sub(r"[^a-zA-Z0-9_-]", "_", filename_prefix)
    path = f"{safe_folder}/{safe_prefix}_{int(time.time() * 1000)}.{extension}"

    supabase = get_supabase()
    supabase.storage.from_(bucket).upload(
        path,
        contents,
        {"content-type": file.content_type, "upsert": "true"},
    )
    return path


def get_signed_url(bucket: str, path: str | None) -> str | None:
    if not path:
        return None
    supabase = get_supabase()
    result = supabase.storage.from_(bucket).create_signed_url(path, _SIGNED_URL_EXPIRES_IN_SECONDS)
    return result.get("signedURL")
