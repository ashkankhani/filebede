"""Stream-based file downloader with retry and resume support."""
import os
import time
import logging
import asyncio
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass

import aiohttp

from config import config
from security import is_safe_url
from filename import determine_filename

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of a download operation."""
    success: bool
    filepath: Optional[str] = None
    filename: Optional[str] = None
    total_size: int = 0
    error: Optional[str] = None


class Downloader:
    """Stream-based downloader with retry and resume support."""
    
    def __init__(self):
        self.download_dir = config.DOWNLOAD_DIR
        os.makedirs(self.download_dir, exist_ok=True)
    
    async def download(
        self,
        url: str,
        progress_callback: Optional[Callable[[int, int, float], Awaitable[None]]] = None
    ) -> DownloadResult:
        """Download file from URL with retry and resume.
        
        Args:
            url: URL to download from
            progress_callback: Optional callback(downloaded, total, percentage)
            
        Returns:
            DownloadResult with file info
        """
        # Validate URL
        is_safe, reason = is_safe_url(url)
        if not is_safe:
            return DownloadResult(success=False, error=f"Unsafe URL: {reason}")
        
        last_error = None
        filepath = None
        
        for attempt in range(config.MAX_RETRIES):
            try:
                result = await self._download_attempt(url, progress_callback, attempt)
                if result.success:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
            
            # Exponential backoff
            if attempt < config.MAX_RETRIES - 1:
                wait_time = min(2 ** (attempt + 1), 64)
                logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        # Clean up failed download
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Removed failed download: {filepath}")
        
        return DownloadResult(
            success=False,
            error=f"Download failed after {config.MAX_RETRIES} attempts: {last_error}"
        )
    
    async def _download_attempt(
        self,
        url: str,
        progress_callback: Optional[Callable],
        attempt: int
    ) -> DownloadResult:
        """Single download attempt with resume support."""
        temp_filepath = None
        
        try:
            timeout = aiohttp.ClientTimeout(
                total=None,
                connect=config.CONNECT_TIMEOUT,
                sock_read=config.READ_TIMEOUT
            )
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Check for existing partial file
                headers = {}
                existing_size = 0
                
                # First request to get filename and size
                async with session.get(url, allow_redirects=True) as resp:
                    resp.raise_for_status()
                    
                    # Get filename
                    content_disp = resp.headers.get("Content-Disposition", "")
                    content_type = resp.headers.get("Content-Type", "")
                    total_size = int(resp.headers.get("Content-Length", 0))
                    
                    # Check max size
                    if total_size > config.MAX_DOWNLOAD_SIZE:
                        return DownloadResult(
                            success=False,
                            error=f"File too large: {total_size / 1024 / 1024:.1f}MB"
                        )
                    
                    # Read first chunk for magic bytes detection
                    first_chunk = await resp.content.read(4096)
                    
                    filename = determine_filename(url, content_disp, content_type, first_chunk)
                    temp_filepath = os.path.join(self.download_dir, f"{filename}.part")
                    
                    # Check for resume
                    if os.path.exists(temp_filepath):
                        existing_size = os.path.getsize(temp_filepath)
                        if total_size > 0 and existing_size >= total_size:
                            # File already complete
                            final_path = os.path.join(self.download_dir, filename)
                            os.rename(temp_filepath, final_path)
                            return DownloadResult(
                                success=True,
                                filepath=final_path,
                                filename=filename,
                                total_size=total_size
                            )
                        
                        if total_size > 0:
                            headers["Range"] = f"bytes={existing_size}-"
                            logger.info(f"Resuming from {existing_size} bytes")
                    
                    # Download with resume support
                    async with session.get(url, headers=headers, allow_redirects=True) as dl_resp:
                        if dl_resp.status == 206:
                            # Partial content - resume
                            mode = "ab"
                            start_size = existing_size
                        elif dl_resp.status == 200:
                            # Full content - restart
                            mode = "wb"
                            start_size = 0
                        else:
                            return DownloadResult(
                                success=False,
                                error=f"Unexpected status: {dl_resp.status}"
                            )
                        
                        total_size = int(dl_resp.headers.get("Content-Length", 0)) + start_size
                        
                        downloaded = start_size
                        last_progress_time = time.time()
                        
                        with open(temp_filepath, mode) as f:
                            async for chunk in dl_resp.content.iter_chunked(config.CHUNK_SIZE):
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Progress callback with rate limiting
                                current_time = time.time()
                                if progress_callback and (current_time - last_progress_time) >= config.PROGRESS_UPDATE_INTERVAL:
                                    percentage = (downloaded / total_size * 100) if total_size > 0 else 0
                                    try:
                                        await progress_callback(downloaded, total_size, percentage)
                                    except Exception:
                                        pass
                                    last_progress_time = current_time
                
                # Verify download
                actual_size = os.path.getsize(temp_filepath)
                if total_size > 0 and actual_size != total_size:
                    logger.warning(f"Size mismatch: expected {total_size}, got {actual_size}")
                
                # Atomic rename
                final_path = os.path.join(self.download_dir, filename)
                os.rename(temp_filepath, final_path)
                
                logger.info(f"Download complete: {filename} ({actual_size} bytes)")
                
                return DownloadResult(
                    success=True,
                    filepath=final_path,
                    filename=filename,
                    total_size=actual_size
                )
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error: {e}")
            return DownloadResult(success=False, error=f"HTTP error: {e}")
        except Exception as e:
            logger.error(f"Download error: {e}")
            return DownloadResult(success=False, error=str(e))
        finally:
            # Don't cleanup partial files on error (for resume)
            pass


downloader = Downloader()
