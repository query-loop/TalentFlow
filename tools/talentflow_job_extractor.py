"""
Integration endpoint for job scraping with TalentFlow
This demonstrates how to integrate the job scraper with the existing /api/fetch endpoint
"""

from typing import Dict, Any, Optional
import json
import logging
from pathlib import Path

# Import the demo scraper
import sys
sys.path.append(str(Path(__file__).parent))
from job_scraper_demo import JobScraperDemo

logger = logging.getLogger(__name__)


class TalentFlowJobExtractor:
    """Integrates job scraper with TalentFlow's existing infrastructure"""
    
    def __init__(self):
        self.scraper = JobScraperDemo()
    
    def extract_job_from_fetch_response(self, url: str, html_content: str) -> Dict[str, Any]:
        """
        Extract structured job data from the HTML content returned by /api/fetch
        
        This can be used to enhance the existing extract page by adding
        structured data extraction alongside the current text extraction.
        """
        try:
            # Use the demo scraper to extract structured data
            job_data = self.scraper.scrape_job_with_html(url, html_content)
            
            # Convert to TalentFlow format
            talentflow_data = self.convert_to_talentflow_format(job_data)
            
            return {
                'success': True,
                'data': talentflow_data,
                'metadata': {
                    'extraction_method': job_data.get('provenance', {}).get('extraction_method'),
                    'confidence': job_data.get('provenance', {}).get('confidence_score'),
                    'warnings': job_data.get('provenance', {}).get('warnings', [])
                }
            }
            
        except Exception as e:
            logger.error(f"Job extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def convert_to_talentflow_format(self, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert scraped job data to TalentFlow's expected format"""
        
        # Map to the existing JD format used in TalentFlow
        talentflow_jd = {
            'title': scraped_data.get('title', ''),
            'company': scraped_data.get('company', ''),
            'description': scraped_data.get('description', ''),
            'location': scraped_data.get('location', ''),
            'employment_type': scraped_data.get('employment_type', ''),
            'posted_date': scraped_data.get('posted_date', ''),
            'source_url': scraped_data.get('source_url', ''),
            'retrieved_at': scraped_data.get('retrieved_at', ''),
            
            # Additional structured fields
            'req_id': scraped_data.get('req_id', ''),
            'team': scraped_data.get('team', ''),
            'level': scraped_data.get('level', ''),
            'responsibilities': scraped_data.get('responsibilities', []),
            'qualifications': scraped_data.get('qualifications', []),
            'skills': scraped_data.get('skills', []),
            'benefits': scraped_data.get('benefits', []),
            'apply_url': scraped_data.get('apply_url', ''),
            
            # Salary information
            'salary': scraped_data.get('salary', {}),
            
            # Extraction metadata
            'extraction_metadata': scraped_data.get('provenance', {})
        }
        
        # Clean empty fields
        return {k: v for k, v in talentflow_jd.items() if v not in [None, '', [], {}]}


# FastAPI endpoint example (for integration with the backend)
def create_enhanced_extract_endpoint():
    """
    Example of how to add this to the FastAPI backend
    This would go in server/app/routers/jd.py or a new router
    """
    
    example_endpoint = '''
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import httpx
from .talentflow_job_extractor import TalentFlowJobExtractor

router = APIRouter()
extractor = TalentFlowJobExtractor()

@router.post("/api/extract-enhanced")
async def extract_job_enhanced(request: Dict[str, str]):
    """Enhanced job extraction with structured data"""
    
    url = request.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        # Fetch HTML using existing logic (or enhance the existing /api/fetch)
        async with httpx.AsyncClient() as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            html_content = response.text
        
        # Extract structured job data
        extraction_result = extractor.extract_job_from_fetch_response(url, html_content)
        
        if extraction_result['success']:
            return {
                "success": True,
                "data": extraction_result['data'],
                "metadata": extraction_result['metadata']
            }
        else:
            return {
                "success": False,
                "error": extraction_result['error']
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    '''
    
    return example_endpoint


# Frontend integration example
def create_frontend_integration():
    """Example of how to integrate with the Svelte frontend"""
    
    example_svelte = '''
<!-- Enhanced extract page with structured data -->
<script lang="ts">
  import { apiBase } from '$lib/api';
  
  let url = '';
  let extracting = false;
  let result = null;
  let metadata = null;
  
  async function extractEnhanced() {
    if (!url) return;
    
    extracting = true;
    try {
      const response = await fetch(`${apiBase()}/api/extract-enhanced`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      
      const data = await response.json();
      
      if (data.success) {
        result = data.data;
        metadata = data.metadata;
        
        // Save to localStorage for use in other pages
        const jdItem = {
          id: Date.now().toString(),
          title: result.title,
          company: result.company,
          description: result.description,
          url: result.source_url,
          structured_data: result, // Full structured data
          created_at: new Date().toISOString()
        };
        
        const existingJDs = JSON.parse(localStorage.getItem('jd_items') || '[]');
        existingJDs.unshift(jdItem);
        localStorage.setItem('jd_items', JSON.stringify(existingJDs));
        
      } else {
        console.error('Extraction failed:', data.error);
      }
    } catch (error) {
      console.error('Failed to extract:', error);
    } finally {
      extracting = false;
    }
  }
</script>

<div class="space-y-4">
  <div class="flex gap-2">
    <input 
      bind:value={url} 
      placeholder="Job URL" 
      class="flex-1 px-3 py-2 border rounded"
    />
    <button 
      on:click={extractEnhanced}
      disabled={extracting || !url}
      class="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
    >
      {extracting ? 'Extracting...' : 'Extract Job'}
    </button>
  </div>
  
  {#if result}
    <div class="bg-gray-50 p-4 rounded">
      <h3 class="font-semibold">{result.title}</h3>
      <p class="text-gray-600">{result.company}</p>
      {#if result.location}<p class="text-sm text-gray-500">{result.location}</p>{/if}
      {#if result.employment_type}<p class="text-sm text-gray-500">{result.employment_type}</p>{/if}
      
      {#if result.skills && result.skills.length > 0}
        <div class="mt-2">
          <span class="text-sm font-medium">Skills:</span>
          <div class="flex flex-wrap gap-1 mt-1">
            {#each result.skills as skill}
              <span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">{skill}</span>
            {/each}
          </div>
        </div>
      {/if}
      
      {#if result.salary}
        <div class="mt-2 text-sm">
          <span class="font-medium">Salary:</span>
          {result.salary.min || ''}{result.salary.min && result.salary.max ? ' - ' : ''}{result.salary.max || ''}
          {result.salary.currency || 'USD'}
        </div>
      {/if}
    </div>
    
    {#if metadata}
      <div class="text-xs text-gray-500">
        <p>Method: {metadata.extraction_method} (confidence: {(metadata.confidence * 100).toFixed(0)}%)</p>
        {#if metadata.warnings && metadata.warnings.length > 0}
          <p>Warnings: {metadata.warnings.join(', ')}</p>
        {/if}
      </div>
    {/if}
  {/if}
</div>
    '''
    
    return example_svelte


if __name__ == "__main__":
    # Demo the integration
    extractor = TalentFlowJobExtractor()
    
    # Test with sample HTML
    sample_html = """
    <html>
      <head><title>Software Engineer at Meta</title></head>
      <body>
        <script type="application/ld+json">
        {
          "@type": "JobPosting",
          "title": "Software Engineer",
          "hiringOrganization": {"name": "Meta"},
          "jobLocation": {"address": {"addressLocality": "Menlo Park", "addressRegion": "CA"}},
          "employmentType": "FULL_TIME",
          "datePosted": "2025-01-15",
          "description": "We are looking for a talented software engineer to join our team..."
        }
        </script>
        <h1>Software Engineer</h1>
        <div class="company-name">Meta</div>
        <div class="location">Menlo Park, CA</div>
      </body>
    </html>
    """
    
    result = extractor.extract_job_from_fetch_response(
        "https://www.metacareers.com/jobs/1436181490732782",
        sample_html
    )
    
    print("🎯 TalentFlow Integration Demo:")
    print(json.dumps(result, indent=2, default=str))