#!/usr/bin/env python3
"""
CLI to test Lever-specialized AI extractor directly (without running the API).
Usage:
  python tools/lever_tester.py <lever_job_url>
"""

import sys
import asyncio
import json
import httpx

# Import extractor from server package
sys.path.insert(0, '/workspaces/TalentFlow/server')
from app.utils.ai_extractor import AIJobExtractor


async def fetch(url: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        return r.text


async def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/lever_tester.py <lever_job_url>")
        sys.exit(1)
    url = sys.argv[1]
    html = await fetch(url)

    extractor = AIJobExtractor()
    data = extractor.extract_dynamically(url, html)

    # Print compact summary
    summary = {
        'title': data.get('title'),
        'company': data.get('company'),
        'location': data.get('location'),
        'employment_type': data.get('employment_type'),
        'confidence_score': data.get('confidence_score'),
        'extraction_method': data.get('extraction_method'),
        'has_description': bool(data.get('description')),
        'apply_links': len(data.get('links', {}).get('apply', [])),
    }
    print("Summary:")
    print(json.dumps(summary, indent=2))

    # Also save full JSON next to script
    out_path = '/workspaces/TalentFlow/tools/lever_output.json'
    with open(out_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved full extraction to {out_path}")


if __name__ == '__main__':
    asyncio.run(main())
