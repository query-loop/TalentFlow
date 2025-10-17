"""
Test endpoint for advanced job extraction with IP rotation.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import logging

from app.utils.advanced_extractor import extract_job_advanced, test_extraction

router = APIRouter()
logger = logging.getLogger(__name__)

class ExtractRequest(BaseModel):
    url: str

@router.post("/test")
async def test_advanced_extraction(request: ExtractRequest) -> Dict[str, Any]:
    """Test advanced job extraction with detailed stats"""
    try:
        result = await test_extraction(request.url)
        return result
    except Exception as e:
        logger.error(f"Test extraction failed: {e}")
        return {
            "url": request.url,
            "success": False,
            "error": str(e),
            "job_data": None,
        }

@router.post("/extract")
async def extract_job_endpoint(request: ExtractRequest) -> Dict[str, Any]:
    """Extract job using advanced techniques"""
    try:
        job_data = await extract_job_advanced(request.url)
        return {
            "success": True,
            "job_data": job_data,
            "url": request.url,
        }
    except Exception as e:
        logger.error(f"Job extraction failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "url": request.url,
        }