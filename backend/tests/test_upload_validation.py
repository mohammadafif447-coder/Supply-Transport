import io

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.services.storage_service import upload_document


def _make_upload_file(*, content: bytes, content_type: str, filename: str = "file.jpg") -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


async def test_upload_document_rejects_disallowed_content_type():
    file = _make_upload_file(content=b"data", content_type="application/zip")

    with pytest.raises(HTTPException) as exc_info:
        await upload_document(bucket="pod-photos", folder="order-1", filename_prefix="pod", file=file)

    assert exc_info.value.status_code == 400
    assert "tidak didukung" in exc_info.value.detail


async def test_upload_document_rejects_missing_content_type():
    file = UploadFile(file=io.BytesIO(b"data"), filename="file.jpg", headers=Headers({}))
    assert file.content_type is None

    with pytest.raises(HTTPException) as exc_info:
        await upload_document(bucket="pod-photos", folder="order-1", filename_prefix="pod", file=file)

    assert exc_info.value.status_code == 400


async def test_upload_document_rejects_file_over_5mb():
    oversized_content = b"x" * (5 * 1024 * 1024 + 1)
    file = _make_upload_file(content=oversized_content, content_type="image/jpeg")

    with pytest.raises(HTTPException) as exc_info:
        await upload_document(bucket="pod-photos", folder="order-1", filename_prefix="pod", file=file)

    assert exc_info.value.status_code == 400
    assert "melebihi batas" in exc_info.value.detail


async def test_upload_document_accepts_file_at_exactly_5mb(monkeypatch):
    exactly_5mb = b"x" * (5 * 1024 * 1024)
    file = _make_upload_file(content=exactly_5mb, content_type="image/jpeg")

    uploaded = {}

    class _FakeStorageBucket:
        def upload(self, path, contents, options):
            uploaded["path"] = path
            uploaded["contents"] = contents
            uploaded["options"] = options

    class _FakeStorage:
        def from_(self, bucket):
            uploaded["bucket"] = bucket
            return _FakeStorageBucket()

    class _FakeSupabase:
        storage = _FakeStorage()

    monkeypatch.setattr("app.services.storage_service.get_supabase", lambda: _FakeSupabase())

    path = await upload_document(bucket="pod-photos", folder="order-1", filename_prefix="pod", file=file)

    assert uploaded["bucket"] == "pod-photos"
    assert uploaded["contents"] == exactly_5mb
    assert path.startswith("order-1/pod_")
    assert path.endswith(".jpg")


async def test_upload_document_sanitizes_folder_and_prefix(monkeypatch):
    file = _make_upload_file(content=b"data", content_type="image/png")

    class _FakeStorageBucket:
        def upload(self, path, contents, options):
            pass

    class _FakeStorage:
        def from_(self, bucket):
            return _FakeStorageBucket()

    class _FakeSupabase:
        storage = _FakeStorage()

    monkeypatch.setattr("app.services.storage_service.get_supabase", lambda: _FakeSupabase())

    path = await upload_document(
        bucket="driver-documents",
        folder="../../etc/passwd",
        filename_prefix="ktp; rm -rf",
        file=file,
    )

    folder_part, _, filename_part = path.partition("/")
    assert ".." not in folder_part
    assert "/" not in folder_part
    assert ";" not in filename_part
    assert " " not in filename_part
    assert filename_part.endswith(".png")
