"""Filename detection and sanitization."""
import os
import re
import uuid
from typing import Optional
from urllib.parse import urlparse, unquote

from file_detector import detect_file_type, get_extension_from_content_type


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and dangerous characters.
    
    Args:
        filename: Raw filename
        
    Returns:
        Safe filename
    """
    if not filename:
        return f"download_{uuid.uuid4().hex[:8]}"
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove null bytes
    filename = filename.replace("\x00", "")
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")
    
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200] + ext
    
    return filename or f"download_{uuid.uuid4().hex[:8]}"


def get_filename_from_content_disposition(header: str) -> Optional[str]:
    """Extract filename from Content-Disposition header.
    
    Supports both regular and RFC 5987 encoded filenames.
    """
    if not header:
        return None
    
    # Try filename* first (RFC 5987)
    match = re.search(r"filename\*\s*=\s*(['\"]?)(?:UTF-8'')?([^'\"]+)\1", header, re.IGNORECASE)
    if match:
        return unquote(match.group(2))
    
    # Try filename
    match = re.search(r"filename\s*=\s*(['\"]?)([^'\"]+)\1", header, re.IGNORECASE)
    if match:
        return match.group(2)
    
    return None


def get_filename_from_url(url: str) -> Optional[str]:
    """Extract filename from URL."""
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path)
        
        # Get basename
        filename = os.path.basename(path)
        
        # Skip if no extension
        if "." not in filename:
            return None
        
        return filename
    except Exception:
        return None


def determine_filename(
    url: str,
    content_disposition: Optional[str],
    content_type: Optional[str],
    file_data: Optional[bytes] = None
) -> str:
    """Determine filename with priority system.
    
    Priority:
    1. Content-Disposition
    2. URL
    3. Content-Type
    4. Magic bytes
    5. Generated filename
    """
    filename = None
    ext = None
    
    # Priority 1: Content-Disposition
    if content_disposition:
        filename = get_filename_from_content_disposition(content_disposition)
        if filename:
            filename = sanitize_filename(filename)
            return filename
    
    # Priority 2: URL
    if url:
        filename = get_filename_from_url(url)
        if filename:
            return sanitize_filename(filename)
    
    # Priority 3: Content-Type
    if content_type:
        ext = get_extension_from_content_type(content_type)
        if ext:
            return f"download_{uuid.uuid4().hex[:8]}{ext}"
    
    # Priority 4: Magic bytes
    if file_data:
        ext = detect_file_type(file_data[:4096])
        if ext:
            return f"download_{uuid.uuid4().hex[:8]}{ext}"
    
    # Priority 5: Generated
    return f"download_{uuid.uuid4().hex[:8]}.bin"
