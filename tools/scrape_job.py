#!/usr/bin/env python3
"""
Command-line interface for the job posting scraper.
Usage: scrape-job --url <JOB_URL> --out job.json
"""

import argparse
import asyncio
import json
import sys
import logging
from pathlib import Path
from typing import Optional

from job_scraper import JobScraper


def setup_logging(verbose: bool = False, quiet: bool = False):
    """Configure logging based on verbosity flags"""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def validate_url(url: str) -> bool:
    """Basic URL validation"""
    from urllib.parse import urlparse
    
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except:
        return False


def validate_output_path(path: str) -> bool:
    """Validate output path is writable"""
    try:
        output_path = Path(path)
        
        # Check if parent directory exists and is writable
        parent = output_path.parent
        if not parent.exists():
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                return False
        
        # Check if we can write to the directory
        if not parent.is_dir() or not parent.stat().st_mode & 0o200:
            return False
        
        # If file exists, check if it's writable
        if output_path.exists() and not output_path.stat().st_mode & 0o200:
            return False
        
        return True
        
    except (OSError, PermissionError):
        return False


async def scrape_and_save(url: str, output_path: str, schema_path: Optional[str] = None,
                         max_retries: int = 3, timeout: int = 30) -> bool:
    """Scrape job and save to file"""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize scraper
        logger.info(f"Initializing scraper with schema: {schema_path or 'default'}")
        scraper = JobScraper(schema_path=schema_path)
        
        # Scrape job
        logger.info(f"Scraping job from: {url}")
        job = await scraper.scrape_job(url, max_retries=max_retries)
        
        # Convert to dict
        job_dict = scraper.to_dict(job)
        
        # Save to file
        logger.info(f"Saving results to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(job_dict, f, indent=2, ensure_ascii=False, default=str)
        
        # Log success info
        logger.info(f"✅ Successfully scraped job posting:")
        logger.info(f"   Title: {job.title}")
        logger.info(f"   Company: {job.company}")
        logger.info(f"   Location: {job.location or 'Not specified'}")
        logger.info(f"   Extraction method: {job.provenance.extraction_method if job.provenance else 'Unknown'}")
        logger.info(f"   Confidence: {job.provenance.confidence_score:.2f}" if job.provenance else "")
        
        if job.provenance and job.provenance.warnings:
            logger.warning(f"   Warnings: {len(job.provenance.warnings)}")
            for warning in job.provenance.warnings[:3]:  # Show first 3
                logger.warning(f"     - {warning}")
        
        return True
        
    except KeyboardInterrupt:
        logger.error("❌ Operation cancelled by user")
        return False
        
    except Exception as e:
        logger.error(f"❌ Scraping failed: {str(e)}")
        
        # Try to provide helpful error messages
        if "timeout" in str(e).lower():
            logger.error("   The page took too long to load. Try increasing --timeout or check your connection.")
        elif "not found" in str(e).lower() or "404" in str(e):
            logger.error("   The job posting URL appears to be invalid or no longer exists.")
        elif "forbidden" in str(e).lower() or "403" in str(e):
            logger.error("   Access to the job posting was denied. The site may block automated requests.")
        elif "connection" in str(e).lower():
            logger.error("   Network connection failed. Check your internet connection and try again.")
        
        return False


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Scrape job posting data from a URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  scrape-job --url https://example.com/job/123 --out job.json
  scrape-job --url https://company.com/careers/senior-dev --out results/job.json --verbose
  scrape-job --url https://jobs.example.com/posting --out job.json --retries 5 --timeout 60
  scrape-job --url https://example.com/job --out job.json --schema custom_schema.json

Output:
  The tool outputs a JSON file with structured job posting data including:
  - Basic info (title, company, location, etc.)
  - Job details (description, requirements, skills)
  - Metadata (provenance, confidence scores, warnings)
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--url", "-u",
        required=True,
        help="Job posting URL to scrape"
    )
    
    parser.add_argument(
        "--out", "-o",
        required=True,
        help="Output JSON file path"
    )
    
    # Optional arguments
    parser.add_argument(
        "--schema", "-s",
        help="Path to custom JSON schema file for validation"
    )
    
    parser.add_argument(
        "--retries", "-r",
        type=int,
        default=3,
        help="Maximum number of retry attempts (default: 3)"
    )
    
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=30,
        help="Page load timeout in seconds (default: 30)"
    )
    
    # Logging options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress all output except errors"
    )
    
    # Validation options
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip JSON schema validation"
    )
    
    # Browser options
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Run browser in headful mode (for debugging)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose, args.quiet)
    logger = logging.getLogger(__name__)
    
    # Validate arguments
    if not validate_url(args.url):
        logger.error(f"❌ Invalid URL: {args.url}")
        logger.error("   URL must start with http:// or https://")
        sys.exit(1)
    
    if not validate_output_path(args.out):
        logger.error(f"❌ Cannot write to output path: {args.out}")
        logger.error("   Check directory permissions and disk space")
        sys.exit(1)
    
    if args.schema and not Path(args.schema).exists():
        logger.error(f"❌ Schema file not found: {args.schema}")
        sys.exit(1)
    
    if args.retries < 0 or args.retries > 10:
        logger.error("❌ Retries must be between 0 and 10")
        sys.exit(1)
    
    if args.timeout < 5 or args.timeout > 300:
        logger.error("❌ Timeout must be between 5 and 300 seconds")
        sys.exit(1)
    
    if args.verbose and args.quiet:
        logger.error("❌ Cannot use both --verbose and --quiet")
        sys.exit(1)
    
    # Show configuration
    if not args.quiet:
        logger.info(f"🚀 Starting job scraper")
        logger.info(f"   URL: {args.url}")
        logger.info(f"   Output: {args.out}")
        logger.info(f"   Retries: {args.retries}")
        logger.info(f"   Timeout: {args.timeout}s")
        if args.schema:
            logger.info(f"   Schema: {args.schema}")
    
    # Run scraper
    try:
        success = asyncio.run(scrape_and_save(
            url=args.url,
            output_path=args.out,
            schema_path=args.schema,
            max_retries=args.retries,
            timeout=args.timeout
        ))
        
        if success:
            if not args.quiet:
                logger.info(f"🎉 Job scraping completed successfully!")
                logger.info(f"   Results saved to: {args.out}")
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.error("❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()