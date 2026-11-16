"""Evidence validation and sanitisation.

Every uploaded file goes through these steps before it is stored:

1. Size and count limits.
2. The *real* file type is detected from its first bytes ("magic bytes");
   the browser-supplied name and content type are not trusted. Only photos
   (JPG/PNG/WebP), videos (MP4/MOV/3GP/WebM) and PDF documents are accepted.
   Executables, scripts, archives, HTML, SVG and Office files are rejected.
3. Sanitisation, which also removes hidden metadata that can identify people:
   * photos are decoded and re-encoded from raw pixels, which drops EXIF,
     GPS location, camera serial numbers and any embedded payload;
   * videos are re-muxed with ffmpeg without global/stream metadata (GPS,
     device model, creation time) and without data tracks;
   * PDFs are rebuilt page-by-page, dropping document metadata, JavaScript,
     auto-actions, embedded files and form actions.
4. Optional malware scan with ClamAV (when ``CLAMAV_HOST`` is configured).

The sanitised file is then encrypted and stored privately (see storage.py).
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import socket
import struct
import subprocess
import tempfile
from dataclasses import dataclass, field
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings

log = logging.getLogger("gaon_saathi.evidence")

Image.MAX_IMAGE_PIXELS = 60_000_000  # decompression-bomb guard
MAX_IMAGE_EDGE = 4096

ALLOWED_EXTENSIONS = {
    "jpg": "image", "jpeg": "image", "png": "image", "webp": "image",
    "mp4": "video", "m4v": "video", "mov": "video", "3gp": "video", "webm": "video",
    "pdf": "pdf",
}
BLOCKED_HINT = {
    "heic": "HEIC photos are not supported. Please share the photo as JPG.",
    "heif": "HEIF photos are not supported. Please share the photo as JPG.",
    "doc": "Word files are not accepted for safety reasons. Please save the document as PDF.",
    "docx": "Word files are not accepted for safety reasons. Please save the document as PDF.",
    "svg": "SVG images are not accepted for safety reasons. Please use JPG or PNG.",
}
MP4_BRANDS = {
    b"isom", b"iso2", b"iso4", b"iso5", b"iso6", b"mp41", b"mp42", b"avc1", b"M4V ", b"M4VH",
    b"M4VP", b"dash", b"mmp4", b"MSNV", b"NDAS", b"f4v ", b"XAVC",
}
HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"avif"}


class EvidenceRejected(Exception):
    """A file was refused. The message is safe to show to the reporter."""


@dataclass
class ProcessedFile:
    media_kind: str
    mime_type: str
    extension: str
    data: bytes
    metadata_stripped: bool
    scan_status: str
    sha256: str
    notices: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Type detection
# ---------------------------------------------------------------------------
def sniff(data: bytes) -> tuple[str, str, str] | None:
    """Return (media_kind, mime_type, extension) from content, or None."""
    head = data[:64]
    if head.startswith(b"\xff\xd8\xff"):
        return "image", "image/jpeg", "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", "image/png", "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image", "image/webp", "webp"
    if head.startswith(b"%PDF-"):
        return "pdf", "application/pdf", "pdf"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in HEIF_BRANDS:
            raise EvidenceRejected(BLOCKED_HINT["heic"])
        if brand.startswith(b"3g"):
            return "video", "video/3gpp", "3gp"
        if brand == b"qt  ":
            return "video", "video/quicktime", "mov"
        if brand in MP4_BRANDS:
            return "video", "video/mp4", "mp4"
        return None
    if head.startswith(b"\x1a\x45\xdf\xa3") and b"webm" in data[:4096]:
        return "video", "video/webm", "webm"
    return None


def _extension(filename: str | None) -> str:
    name = (filename or "").strip().lower()
    return name.rsplit(".", 1)[-1] if "." in name else ""


# ---------------------------------------------------------------------------
# Sanitisers
# ---------------------------------------------------------------------------
def sanitise_image(data: bytes, mime: str) -> tuple[bytes, str, str]:
    try:
        with Image.open(BytesIO(data)) as probe:
            probe.verify()
        with Image.open(BytesIO(data)) as img:
            img.seek(0)
            img = ImageOps.exif_transpose(img)  # keep correct orientation before EXIF is dropped
            has_alpha = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
            target_mode = "RGBA" if (has_alpha and mime != "image/jpeg") else "RGB"
            img = img.convert(target_mode)
            img.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
            # Rebuild from raw pixels so no metadata (EXIF/GPS/XMP/ICC/text chunks) survives.
            clean = Image.frombytes(img.mode, img.size, img.tobytes())
    except Image.DecompressionBombError as exc:
        raise EvidenceRejected("A photo is too large in resolution to process.") from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise EvidenceRejected("A photo could not be read. It may be damaged.") from exc

    out = BytesIO()
    if mime == "image/png":
        clean.save(out, format="PNG", optimize=True)
        return out.getvalue(), "image/png", "png"
    if mime == "image/webp":
        clean.save(out, format="WEBP", quality=90)
        return out.getvalue(), "image/webp", "webp"
    clean.save(out, format="JPEG", quality=90, optimize=True, progressive=True)
    return out.getvalue(), "image/jpeg", "jpg"


@lru_cache
def find_ffmpeg() -> str | None:
    configured = get_settings().ffmpeg_path
    if configured:
        return configured if Path(configured).exists() else None
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # noqa: PLC0415

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - optional dependency
        return None


_FFMPEG_FORMATS = {"mp4": "mp4", "mov": "mov", "3gp": "3gp", "webm": "webm"}


def sanitise_video(data: bytes, ext: str) -> tuple[bytes, bool]:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return data, False
    with tempfile.TemporaryDirectory(prefix="gs-") as tmp:
        src = Path(tmp) / f"in.{ext}"
        dst = Path(tmp) / f"out.{ext}"
        src.write_bytes(data)
        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-i", str(src),
            "-map", "0:v?", "-map", "0:a?",            # drop data/subtitle tracks (e.g. GPS tracks)
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-map_metadata:s:v", "-1", "-map_metadata:s:a", "-1",
            "-c", "copy", "-fflags", "+bitexact",
            "-f", _FFMPEG_FORMATS[ext], str(dst),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=180, check=False)
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise EvidenceRejected("A video could not be processed. Please try a shorter video.") from exc
        if result.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
            raise EvidenceRejected("A video could not be processed. It may be damaged or in an unsupported format.")
        return dst.read_bytes(), True


def sanitise_pdf(data: bytes) -> bytes:
    from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
    from pypdf.errors import PdfReadError  # noqa: PLC0415
    from pypdf.generic import ArrayObject, NameObject  # noqa: PLC0415

    dangerous_actions = {"/JavaScript", "/Launch", "/SubmitForm", "/ImportData", "/GoToE", "/ResetForm", "/Rendition"}
    settings = get_settings()
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise EvidenceRejected("Password-protected PDF files cannot be accepted. Please remove the password.")
        if len(reader.pages) > settings.max_pdf_pages:
            raise EvidenceRejected(f"PDF files can have at most {settings.max_pdf_pages} pages.")
        writer = PdfWriter()
        for page in reader.pages:
            for key in ("/AA", "/Metadata", "/PieceInfo"):
                if key in page:
                    del page[NameObject(key)]
            annots = page.get("/Annots")
            if annots is not None:
                kept = ArrayObject()
                for ref in annots.get_object():
                    annot = ref.get_object()
                    if annot.get("/Subtype") in ("/FileAttachment", "/Movie", "/Sound", "/Screen", "/RichMedia"):
                        continue
                    if "/AA" in annot:
                        del annot[NameObject("/AA")]
                    action = annot.get("/A")
                    if action is not None and action.get_object().get("/S") in dangerous_actions:
                        del annot[NameObject("/A")]
                    kept.append(ref)
                page[NameObject("/Annots")] = kept
            writer.add_page(page)
        out = BytesIO()
        writer.write(out)
        return out.getvalue()
    except EvidenceRejected:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, AttributeError, RecursionError, OSError) as exc:
        raise EvidenceRejected("A PDF file could not be read. It may be damaged.") from exc


# ---------------------------------------------------------------------------
# Malware scanning (ClamAV clamd INSTREAM protocol)
# ---------------------------------------------------------------------------
def scan_with_clamav(data: bytes) -> str:
    """Return 'clean', 'not_scanned' or 'error'. Raises EvidenceRejected if infected."""
    settings = get_settings()
    if not settings.clamav_host:
        return "not_scanned"
    try:
        with socket.create_connection((settings.clamav_host, settings.clamav_port),
                                      timeout=settings.clamav_timeout_seconds) as sock:
            sock.sendall(b"zINSTREAM\0")
            for i in range(0, len(data), 64 * 1024):
                chunk = data[i:i + 64 * 1024]
                sock.sendall(struct.pack(">I", len(chunk)) + chunk)
            sock.sendall(struct.pack(">I", 0))
            reply = b""
            while not reply.endswith(b"\0"):
                part = sock.recv(4096)
                if not part:
                    break
                reply += part
    except OSError:
        log.warning("Malware scanner unreachable; evidence stored with scan_status=error")
        return "error"
    text = reply.rstrip(b"\0").decode("utf-8", "replace")
    if text.endswith("FOUND"):
        raise EvidenceRejected("A file was blocked by our security scanner and was not accepted.")
    if text.endswith("OK"):
        return "clean"
    return "error"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def limit_for(kind: str) -> int:
    s = get_settings()
    return s.mb({"image": s.max_image_mb, "video": s.max_video_mb, "pdf": s.max_pdf_mb}[kind])


def process_upload(filename: str | None, data: bytes) -> ProcessedFile:
    ext = _extension(filename)
    if not data:
        raise EvidenceRejected("An empty file was uploaded.")
    if ext in BLOCKED_HINT:
        raise EvidenceRejected(BLOCKED_HINT[ext])
    if ext not in ALLOWED_EXTENSIONS:
        raise EvidenceRejected("This file type is not accepted. Please upload photos (JPG, PNG, WebP), "
                               "videos (MP4, MOV, 3GP, WebM) or PDF documents.")
    detected = sniff(data)
    if detected is None:
        raise EvidenceRejected("A file's content does not match an accepted type. It was not accepted.")
    kind, mime, real_ext = detected
    if ALLOWED_EXTENSIONS[ext] != kind:
        raise EvidenceRejected("A file's name does not match its content. It was not accepted.")
    if len(data) > limit_for(kind):
        raise EvidenceRejected(f"A {kind if kind != 'pdf' else 'PDF'} file is larger than the "
                               f"{limit_for(kind) // (1024 * 1024)} MB limit.")

    notices: list[str] = []
    if kind == "image":
        clean, mime, real_ext = sanitise_image(data, mime)
        stripped = True
    elif kind == "video":
        clean, stripped = sanitise_video(data, real_ext)
        if not stripped:
            notices.append("Hidden information (like location) could not be removed from a video. "
                           "Our team will handle it carefully.")
    else:
        clean = sanitise_pdf(data)
        stripped = True

    scan_status = scan_with_clamav(clean)
    return ProcessedFile(
        media_kind=kind, mime_type=mime, extension=real_ext, data=clean,
        metadata_stripped=stripped, scan_status=scan_status,
        sha256=hashlib.sha256(clean).hexdigest(), notices=notices,
    )
