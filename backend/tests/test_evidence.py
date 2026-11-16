"""Evidence upload: type validation, metadata removal, encryption, access control."""

from __future__ import annotations

import subprocess
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from app.config import get_settings
from app.models import EvidenceFile
from app.services.evidence import EvidenceRejected, find_ffmpeg, process_upload
from tests.conftest import jpeg_bytes, submit


def gps_jpeg() -> bytes:
    exif = Image.Exif()
    exif[0x010F] = "SecretPhoneMaker"
    exif[0x0110] = "ModelXYZ-123"
    exif[0x8825] = {1: "N", 2: (28.0, 36.0, 50.0), 3: "E", 4: (77.0, 12.0, 30.0)}
    data = jpeg_bytes(exif=exif)
    reopened = Image.open(BytesIO(data)).getexif()
    assert reopened.get_ifd(0x8825), "test image should contain GPS data"
    return data


def pdf_with_js_and_metadata() -> bytes:
    from pypdf import PdfWriter
    from pypdf.actions import JavaScript
    from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject, TextStringObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Author": "Raju Kumar Secret", "/Title": "Private"})
    writer.add_open_action(JavaScript("app.alert('owned');"))  # document-level script
    link = DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Link"),
        NameObject("/Rect"): ArrayObject([FloatObject(0), FloatObject(0), FloatObject(100), FloatObject(100)]),
        NameObject("/A"): DictionaryObject({NameObject("/S"): NameObject("/JavaScript"),
                                            NameObject("/JS"): TextStringObject("app.launchURL('x');")}),
    })
    page[NameObject("/Annots")] = ArrayObject([writer._add_object(link)])  # annotation-level script
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Unit level
# ---------------------------------------------------------------------------
def test_photo_exif_and_gps_are_removed():
    original = gps_jpeg()
    assert b"SecretPhoneMaker" in original
    result = process_upload("IMG_20260101_raju.jpg", original)
    assert result.media_kind == "image" and result.metadata_stripped
    assert b"SecretPhoneMaker" not in result.data and b"ModelXYZ" not in result.data
    cleaned = Image.open(BytesIO(result.data))
    assert len(cleaned.getexif()) == 0
    assert cleaned.size == (64, 48)


def test_png_text_chunks_are_removed():
    from PIL import PngImagePlugin

    info = PngImagePlugin.PngInfo()
    info.add_text("Author", "Secret Person 9876543210")
    buf = BytesIO()
    Image.new("RGBA", (20, 20), (0, 255, 0, 128)).save(buf, "PNG", pnginfo=info)
    result = process_upload("screen.png", buf.getvalue())
    assert b"Secret Person" not in result.data
    assert result.mime_type == "image/png"


def test_polyglot_payload_is_dropped():
    data = jpeg_bytes() + b"<script>alert(1)</script><?php system($_GET['c']); ?>"
    result = process_upload("photo.jpg", data)
    assert b"<script>" not in result.data and b"<?php" not in result.data


def test_pdf_javascript_and_metadata_removed():
    original = pdf_with_js_and_metadata()
    assert b"/JavaScript" in original and b"Raju Kumar Secret" in original
    result = process_upload("letter.pdf", original)
    assert result.media_kind == "pdf"
    assert b"/JavaScript" not in result.data
    assert b"Raju Kumar Secret" not in result.data


@pytest.mark.parametrize("filename,data", [
    ("virus.exe", b"MZ\x90\x00" + b"\x00" * 100),
    ("photo.jpg", b"MZ\x90\x00" + b"\x00" * 100),           # executable disguised as photo
    ("page.html", b"<html><script>alert(1)</script></html>"),
    ("image.svg", b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"),
    ("doc.docx", b"PK\x03\x04" + b"\x00" * 100),
    ("archive.pdf", b"PK\x03\x04" + b"\x00" * 100),           # zip pretending to be a PDF
    ("script.js", b"alert(1)"),
    ("noext", b"\xff\xd8\xff\xe0"),
    ("empty.jpg", b""),
])
def test_dangerous_or_mismatched_files_are_rejected(filename, data):
    with pytest.raises(EvidenceRejected):
        process_upload(filename, data)


def test_extension_must_match_content():
    with pytest.raises(EvidenceRejected):
        process_upload("video.mp4", jpeg_bytes())


def test_damaged_image_rejected():
    with pytest.raises(EvidenceRejected):
        process_upload("photo.jpg", b"\xff\xd8\xff\xe0" + b"garbage" * 50)


@pytest.mark.skipif(find_ffmpeg() is None, reason="ffmpeg not available")
def test_video_metadata_removed(tmp_path: Path):
    src = tmp_path / "in.mp4"
    cmd = [find_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
           "color=c=blue:s=64x64:d=1", "-c:v", "mpeg4", "-metadata", "title=RajuPhoneTitle",
           "-metadata", "location=+28.6139+077.2090/", str(src)]
    subprocess.run(cmd, check=True, capture_output=True, timeout=60)
    original = src.read_bytes()
    assert b"RajuPhoneTitle" in original
    result = process_upload("clip.mp4", original)
    assert result.media_kind == "video" and result.metadata_stripped
    assert b"RajuPhoneTitle" not in result.data
    assert b"+28.6139" not in result.data


# ---------------------------------------------------------------------------
# API level
# ---------------------------------------------------------------------------
def test_upload_through_api_is_encrypted_and_private(client, admin_client, db):
    files = [("files", ("IMG_raju_9876543210.jpg", gps_jpeg(), "image/jpeg")),
             ("files", ("letter.pdf", pdf_with_js_and_metadata(), "application/pdf"))]
    response = submit(client, files=files)
    assert response.status_code == 201, response.text
    assert response.json()["evidence_count"] == 2

    evidence = db.scalars(select(EvidenceFile).order_by(EvidenceFile.display_name)).all()
    assert [e.display_name for e in evidence] == ["evidence-1.jpg", "evidence-2.pdf"]
    # Original phone file names (which may identify people) are never stored.
    for e in evidence:
        assert "raju" not in e.display_name.lower()

    # Files on disk are encrypted: no JPEG/PDF signatures or plaintext.
    stored = list(Path(get_settings().evidence_dir).rglob("*"))
    blobs = [p.read_bytes() for p in stored if p.is_file()]
    assert len(blobs) == 2
    for blob in blobs:
        assert blob.startswith(b"GSE1")
        assert b"\xff\xd8\xff" not in blob[:16] and b"%PDF" not in blob

    # Authenticated admins can view the cleaned file.
    image = next(e for e in evidence if e.media_kind == "image")
    viewed = admin_client.get(f"/api/admin/evidence/{image.id}")
    assert viewed.status_code == 200
    assert viewed.headers["content-type"] == "image/jpeg"
    assert "sandbox" in viewed.headers["content-security-policy"]
    assert len(Image.open(BytesIO(viewed.content)).getexif()) == 0

    pdf = next(e for e in evidence if e.media_kind == "pdf")
    downloaded = admin_client.get(f"/api/admin/evidence/{pdf.id}")
    assert downloaded.headers["content-disposition"].startswith("attachment")


def test_evidence_requires_admin_login(client, db):
    submit(client, files=[("files", ("a.jpg", jpeg_bytes(), "image/jpeg"))])
    evidence = db.scalar(select(EvidenceFile))
    client.cookies.clear()
    assert client.get(f"/api/admin/evidence/{evidence.id}").status_code == 401


def test_viewer_role_cannot_open_evidence(client, make_admin, db):
    from tests.conftest import login

    submit(client, files=[("files", ("a.jpg", jpeg_bytes(), "image/jpeg"))])
    evidence = db.scalar(select(EvidenceFile))
    make_admin(username="viewer1", role="viewer")
    login(client, "viewer1")
    assert client.get(f"/api/admin/evidence/{evidence.id}").status_code == 403


def test_video_range_requests(client, admin_client, db, tmp_path):
    if find_ffmpeg() is None:
        pytest.skip("ffmpeg not available")
    src = tmp_path / "in.mp4"
    subprocess.run([find_ffmpeg(), "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=32x32:d=1",
                    "-c:v", "mpeg4", str(src)], check=True, capture_output=True, timeout=60)
    assert submit(client, files=[("files", ("v.mp4", src.read_bytes(), "video/mp4"))]).status_code == 201
    evidence = db.scalar(select(EvidenceFile))
    partial = admin_client.get(f"/api/admin/evidence/{evidence.id}", headers={"Range": "bytes=0-99"})
    assert partial.status_code == 206
    assert len(partial.content) == 100
    assert partial.headers["content-range"].startswith("bytes 0-99/")


def test_too_many_files_rejected(client):
    files = [("files", (f"p{i}.jpg", jpeg_bytes(), "image/jpeg")) for i in range(6)]
    response = submit(client, files=files)
    assert response.status_code == 400
    assert "at most 5" in response.json()["detail"]


def test_oversized_file_rejected(client):
    settings = get_settings()
    original = settings.max_image_mb
    settings.max_image_mb = 1
    try:
        big = Image.frombytes("RGB", (900, 900), bytes(range(256)) * (900 * 900 * 3 // 256) + b"\x00" * (900 * 900 * 3 % 256))
        buf = BytesIO()
        big.save(buf, "PNG")
        data = buf.getvalue()
        while len(data) <= 1024 * 1024:
            data += data  # inflate beyond the limit (still starts with PNG signature)
        response = submit(client, files=[("files", ("big.png", data, "image/png"))])
        assert response.status_code == 400
        assert "limit" in response.json()["detail"] or "larger" in response.json()["detail"]
    finally:
        settings.max_image_mb = original


def test_request_body_limit(client):
    settings = get_settings()
    response = client.post("/api/public/track", content=b"x" * (300 * 1024),
                           headers={"content-type": "application/json"})
    assert response.status_code == 413
    assert settings.max_total_upload_mb > 1


def test_failed_upload_does_not_create_complaint(client, db):
    from app.models import Complaint

    response = submit(client, files=[("files", ("bad.jpg", b"MZ" + b"\x00" * 50, "image/jpeg"))])
    assert response.status_code == 400
    assert db.scalar(select(Complaint)) is None
