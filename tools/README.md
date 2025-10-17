# TalentFlow Job Scraper

Production-ready job posting scraper with headless rendering, multi-method extraction, schema validation, and provenance tracking.

## Features

✅ **Headless Browser Rendering** - Uses Playwright for JavaScript-heavy sites  
✅ **Multi-Method Extraction** - JSON-LD → Microdata → DOM selectors → Regex fallbacks  
✅ **Schema Validation** - Strict JSON Schema with auto-repair for missing fields  
✅ **Provenance Tracking** - Records extraction methods and confidence scores  
✅ **Anti-Bot Hygiene** - Realistic headers, delays, and retry logic  
✅ **Comprehensive CLI** - Rich command-line interface with detailed options  
✅ **Unit Tested** - Full test coverage for reliability  
✅ **TalentFlow Integration** - Seamless integration with existing workflow  

## Quick Start

### 1. Setup
```bash
cd tools/
chmod +x setup_scraper.sh
./setup_scraper.sh
```

### 2. Basic Usage
```bash
# Scrape a job posting
./scrape_job.py --url https://company.com/careers/senior-engineer --out job.json

# With verbose logging
./scrape_job.py --url https://example.com/job/123 --out job.json --verbose

# Custom retries and timeout
./scrape_job.py --url https://jobs.company.com/posting --out job.json --retries 5 --timeout 60
```

### 3. View Results
```bash
cat job.json | jq .
```

## Output Format

The scraper produces structured JSON with comprehensive job data:

```json
{
  "title": "Senior Software Engineer",
  "company": "TechCorp Inc",
  "location": "San Francisco, CA, US",
  "level": "senior",
  "employment_type": "full-time",
  "posted_date": "2024-01-15",
  "description": "We are looking for a senior software engineer...",
  "responsibilities": [
    "Design and implement scalable systems",
    "Lead technical architecture decisions"
  ],
  "qualifications": [
    "5+ years of software development experience",
    "Strong background in distributed systems"
  ],
  "skills": ["Python", "React", "AWS", "Docker"],
  "salary": {
    "min": 120000,
    "max": 180000,
    "currency": "USD",
    "period": "yearly"
  },
  "benefits": ["Health insurance", "401k matching"],
  "apply_url": "https://company.com/apply/123",
  "source_url": "https://company.com/careers/senior-engineer",
  "retrieved_at": "2024-01-20T15:30:00Z",
  "provenance": {
    "extraction_method": "json-ld",
    "confidence_score": 0.95,
    "field_sources": {
      "title": "json-ld",
      "company": "json-ld",
      "skills": "regex",
      "description": "dom"
    },
    "warnings": []
  }
}
```

## CLI Options

```bash
scrape-job --help
```

### Required Arguments
- `--url, -u` - Job posting URL to scrape
- `--out, -o` - Output JSON file path

### Optional Arguments
- `--schema, -s` - Custom JSON schema file for validation
- `--retries, -r` - Max retry attempts (default: 3)
- `--timeout, -t` - Page load timeout in seconds (default: 30)
- `--verbose, -v` - Enable verbose logging
- `--quiet, -q` - Suppress all output except errors
- `--no-validate` - Skip JSON schema validation
- `--headful` - Run browser in headful mode (for debugging)

## Integration with TalentFlow

### Backend Integration

Add to your FastAPI router:

```python
from tools.talentflow_integration import TalentFlowJobImporter

@router.post("/api/jd/import-enhanced")
async def import_job_enhanced(request: ImportJobRequest):
    importer = TalentFlowJobImporter()
    result = await importer.import_job_from_url(request.url)
    return result
```

### Frontend Integration

Replace the existing import logic:

```javascript
async function importFromUrlEnhanced(url) {
    const response = await fetch('/api/jd/import-enhanced', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ url })
    });
    return response.json();
}
```

## Architecture

### Extraction Strategy Priority

1. **JSON-LD Structured Data** (confidence: 0.9)
   - Looks for `<script type="application/ld+json">` with JobPosting schema
   - Extracts standardized fields with high reliability

2. **Microdata** (confidence: 0.8)
   - Parses `itemtype="JobPosting"` elements
   - Extracts data from `itemprop` attributes

3. **DOM Selectors** (confidence: 0.6)
   - Uses common CSS selectors for job sites
   - Searches for `.job-title`, `.company-name`, etc.

4. **Regex Fallbacks** (confidence: 0.4)
   - Pattern matching on page text
   - Extracts skills, salary ranges, employment types

### Anti-Bot Features

- Realistic browser headers and viewport
- Random delays and human-like behavior
- Exponential backoff on retries
- Error handling for rate limiting

### Validation & Repair

- Required field validation with auto-repair
- Company name extraction from URL hostname
- Title extraction from description
- Employment type normalization
- Date format standardization

## Schema

The output follows a strict JSON Schema located at:
```
contracts/schemas/job_scraper.json
```

Key validation rules:
- `title` and `company` are required (auto-repaired if missing)
- `description` must be at least 50 characters
- `skills` array with unique items (max 100)
- `salary` object with min/max validation
- `employment_type` enum validation
- URL format validation for links

## Testing

Run the comprehensive test suite:

```bash
python3 test_scraper.py
```

Test coverage includes:
- JSON-LD parsing
- Microdata extraction
- DOM selector logic
- Regex fallbacks
- Data merging priority
- Validation and repair
- CLI argument validation
- Integration scenarios

## Error Handling

The scraper provides detailed error messages:

- **Timeout errors** - Suggests increasing timeout or checking connection
- **404/403 errors** - Indicates invalid or blocked URLs
- **Connection errors** - Network troubleshooting guidance
- **Parsing errors** - Fallback extraction methods activated

## Performance

- **Memory efficient** - Caps response size at 1MB
- **Fast execution** - Disables images and unnecessary resources
- **Concurrent safe** - Async/await throughout
- **Resource cleanup** - Proper browser session management

## Supported Job Sites

Tested and optimized for:
- Lever-based career pages
- Greenhouse job boards
- Workday recruiting
- LinkedIn job postings
- Meta Careers
- Company career pages with structured data
- ATS systems with standard markup

## Dependencies

- **Python 3.8+**
- **Playwright** - Headless browser automation
- **jsonschema** - Schema validation
- **python-dateutil** - Date parsing
- **aiofiles** - Async file operations

## License

Part of the TalentFlow project. See main project license.

## Contributing

1. Add test cases for new extraction patterns
2. Update schema for new field types
3. Enhance site-specific selectors
4. Improve validation and repair logic

## Troubleshooting

### Common Issues

**Browser installation fails:**
```bash
playwright install chromium --force
```

**Permission denied:**
```bash
chmod +x scrape_job.py setup_scraper.sh
```

**Import errors:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Sites block requests:**
- Try adding delays: `--timeout 60`
- Use headful mode for debugging: `--headful`
- Check site's robots.txt and terms of service

### Debugging

Enable verbose logging to see extraction details:
```bash
./scrape_job.py --url https://example.com/job --out debug.json --verbose
```

Use headful mode to watch the browser:
```bash
./scrape_job.py --url https://example.com/job --out debug.json --headful
```

## Bridge to the app (backend + frontend)

This repo includes a no-new-deps bridge so the frontend can import job posts reliably:

- Backend (FastAPI):
  - POST /api/extract/job — server fetches the URL and extracts structured fields
  - POST /api/extract/from-html — accepts { url, html } and extracts structured fields
- Frontend (SvelteKit server route):
  - POST /proxy/fetch — fetches remote HTML with realistic headers and returns { html }

Frontend Extract page flow:
1) POST /proxy/fetch with the pasted URL to get the HTML (avoids CORS).
2) POST /api/extract/from-html with { url, html } to get structured fields.
3) If that fails, fall back to client-side parsing of the HTML.

This makes sites like Meta Careers work more consistently without Playwright. When you’re ready for full headless rendering, install Playwright and switch the backend extractor to use tools/job_scraper.py.


**Example Commands:**

```bash
# Basic scraping
./scrape_job.py --url https://jobs.lever.co/company/senior-engineer --out lever_job.json

# High-confidence extraction
./scrape_job.py --url https://greenhouse.io/company/backend-dev --out greenhouse_job.json --verbose

# Retry problematic sites
./scrape_job.py --url https://workday.com/company/job123 --out workday_job.json --retries 5 --timeout 90

# Custom schema validation
./scrape_job.py --url https://company.com/job --out job.json --schema custom_schema.json
```