"""File type detection using magic bytes."""
import struct
from typing import Optional


# Magic bytes signatures
SIGNATURES = {
    # PDF
    b"%PDF": ".pdf",
    # ZIP (also APK)
    b"PK\\x03\\x04": ".zip",
    # PNG
    b"\\x89PNG\\r\\n\\x1a\\n": ".png",
    # JPEG
    b"\\xff\\xd8\\xff": ".jpg",
    # GIF
    b"GIF87a": ".gif",
    b"GIF89a": ".gif",
    # MP3 (ID3)
    b"ID3": ".mp3",
    # MP3 (MPEG)
    b"\\xff\\xfb": ".mp3",
    b"\\xff\\xf3": ".mp3",
    b"\\xff\\xf2": ".mp3",
    # MP4 (ftyp)
    b"ftyp": ".mp4",
    # RAR
    b"Rar!": ".rar",
    # 7z
    b"7z\\xbc\\xaf\\x27\\x1c": ".7z",
    # GZIP
    b"\\x1f\\x8b\\x08": ".gz",
    # TAR.GZ
    b"\\x1f\\x8b\\x08": ".tar.gz",
    # ELF
    b"\\x7fELF": ".bin",
    # Windows PE
    b"MZ": ".exe",
    # Python bytecode
    b"\\x03\\xf3\\r\\n": ".pyc",
    # SQLite
    b"SQLite format 3": ".db",
    # APK (ZIP with AndroidManifest)
    # Will be detected as ZIP, then we check for Android
}

# APK specific check
APK_SIGNATURES = [
    b"AndroidManifest.xml",
    b"classes.dex",
    b"resources.arsc",
]


def detect_file_type(data: bytes) -> Optional[str]:
    """Detect file type from magic bytes.
    
    Args:
        data: First few KB of file data
        
    Returns:
        Extension or None
    """
    if not data:
        return None
    
    # Check signatures
    for signature, ext in SIGNATURES.items():
        if data[:len(signature)] == signature:
            # Special check for APK
            if ext == ".zip":
                for apk_sig in APK_SIGNATURES:
                    if apk_sig in data[:10240]:  # Check first 10KB
                        return ".apk"
            return ext
    
    # Check for MP4 (ftyp box at offset 4)
    if len(data) >= 8 and data[4:8] == b"ftyp":
        return ".mp4"
    
    return None


def get_extension_from_content_type(content_type: str) -> Optional[str]:
    """Map Content-Type to file extension."""
    mime_map = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "video/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "application/zip": ".zip",
        "application/vnd.android.package-archive": ".apk",
        "text/plain": ".txt",
        "application/json": ".json",
        "application/octet-stream": None,  # Unknown
    }
    
    # Remove parameters
    base_type = content_type.split(";")[0].strip().lower()
    
    return mime_map.get(base_type)
