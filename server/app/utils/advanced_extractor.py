"""
Main interface for advanced job extraction with IP rotation.
"""
from __future__ import annotations

import asyncio
from typing import Dict, Any
import logging

from .advanced_fetch import IPRotationManager
from .job_parser import parse_job_from_html

logger = logging.getLogger(__name__)

class AdvancedJobExtractor:
    """
    Legacy advanced job extractor - now using new IP rotation system.
    """
    def extract(self, url: str, html: str) -> Dict[str, Any]:
        """Extract job information from HTML - legacy interface"""
        return parse_job_from_html(url, html)

async def extract_job_advanced(url: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    Extract job information from URL using advanced techniques:
    - IP rotation (free proxies, Tor, anti-bot providers)
    - Multiple parsing strategies (JSON-LD, ATS-specific, generic)
    - Anti-blocking measures (rate limiting, caching, header rotation)
    
    Args:
        url: Job posting URL
        max_retries: Maximum retry attempts
        
    Returns:
        Dictionary with job information
        
    Raises:
        RuntimeError: If extraction fails after all retries
    """
    if not url or not url.strip():
        raise ValueError("URL is required")
    
    url = url.strip()
    logger.info(f"Starting advanced extraction for: {url}")
    
    # Initialize IP rotation manager
    manager = IPRotationManager()
    
    try:
        # Fetch with rotation and anti-blocking
        html, status, blocked_reason = await manager.fetch_with_rotation(url, max_retries)
        
        if not html or blocked_reason:
            error_msg = f"Failed to fetch {url}: {blocked_reason or f'HTTP {status}'}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info(f"Successfully fetched {url} (status: {status}, length: {len(html)})")
        
        # Parse job information
        job_data = parse_job_from_html(url, html)
        
        # Validate required fields
        if not job_data.get("title"):
            job_data["title"] = "Job"
        
        if not job_data.get("description"):
            logger.warning(f"No description extracted from {url}")
            job_data["description"] = ""
        
        logger.info(f"Successfully extracted job: {job_data.get('title')} at {job_data.get('company', 'Unknown Company')}")
        
        return job_data
        
    except Exception as e:
        logger.error(f"Job extraction failed for {url}: {e}")
        raise RuntimeError(f"Job extraction failed: {e}")

async def test_extraction(url: str) -> Dict[str, Any]:
    """Test job extraction and return detailed results"""
    manager = IPRotationManager()
    
    result = {
        "url": url,
        "success": False,
        "job_data": None,
        "error": None,
        "stats": manager.get_stats(),
        "current_ip": None,
    }
    
    try:
        # Get current IP
        result["current_ip"] = await manager.get_current_ip()
        
        # Extract job
        job_data = await extract_job_advanced(url)
        result["success"] = True
        result["job_data"] = job_data
        
    except Exception as e:
        result["error"] = str(e)
    
    result["final_stats"] = manager.get_stats()
    return result

# Legacy compatibility
async def extract_job(url: str) -> Dict[str, Any]:
    """Legacy wrapper for backward compatibility"""
    return await extract_job_advanced(url)
