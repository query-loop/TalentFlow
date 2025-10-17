#!/usr/bin/env python3
"""
Comprehensive unit tests for the job posting scraper.
"""

import unittest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from datetime import datetime, timezone

# Add the tools directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from job_scraper import JobScraper, JobPosting, SalaryInfo, ProvenanceInfo


class TestJobScraper(unittest.TestCase):
    """Test cases for JobScraper class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scraper = JobScraper()
        
        # Sample job data for testing
        self.sample_json_ld = {
            "@type": "JobPosting",
            "title": "Senior Software Engineer",
            "hiringOrganization": {
                "name": "TechCorp Inc"
            },
            "jobLocation": {
                "address": {
                    "addressLocality": "San Francisco",
                    "addressRegion": "CA",
                    "addressCountry": "US"
                }
            },
            "employmentType": "FULL_TIME",
            "datePosted": "2024-01-15",
            "description": "We are looking for a senior software engineer to join our team...",
            "baseSalary": {
                "value": {
                    "minValue": 120000,
                    "maxValue": 180000,
                    "currency": "USD"
                }
            }
        }
        
        self.sample_microdata = {
            "title": "Backend Developer",
            "company": "StartupXYZ",
            "location": "Remote",
            "employment_type": "full-time",
            "description": "Join our backend team to build scalable systems..."
        }

    def test_parse_json_ld_job_posting(self):
        """Test JSON-LD parsing functionality"""
        result = self.scraper._parse_json_ld_job_posting(self.sample_json_ld)
        
        self.assertEqual(result['title'], 'Senior Software Engineer')
        self.assertEqual(result['company'], 'TechCorp Inc')
        self.assertEqual(result['location'], 'San Francisco, CA, US')
        self.assertEqual(result['employment_type'], 'full-time')
        self.assertEqual(result['posted_date'], '2024-01-15')
        self.assertIn('description', result)
        
        # Test salary parsing
        self.assertIn('salary', result)
        salary = result['salary']
        self.assertEqual(salary['min'], 120000)
        self.assertEqual(salary['max'], 180000)
        self.assertEqual(salary['currency'], 'USD')

    def test_normalize_employment_type(self):
        """Test employment type normalization"""
        test_cases = [
            ('full time', 'full-time'),
            ('FULL_TIME', 'full-time'),
            ('part-time', 'part-time'),
            ('contract', 'contract'),
            ('internship', 'internship'),
            ('invalid-type', None)
        ]
        
        for input_type, expected in test_cases:
            result = self.scraper._normalize_employment_type(input_type)
            self.assertEqual(result, expected, f"Failed for input: {input_type}")

    def test_extract_level(self):
        """Test level extraction from text"""
        test_cases = [
            ('Senior Software Engineer', 'senior'),
            ('Junior Developer Position', 'junior'),
            ('Staff Engineer Role', 'staff'),
            ('Engineering Manager', 'manager'),
            ('Principal Architect', 'principal'),
            ('Entry Level Position', 'entry'),
            ('Regular Developer', None)
        ]
        
        for text, expected in test_cases:
            result = self.scraper._extract_level(text)
            self.assertEqual(result, expected, f"Failed for text: {text}")

    def test_extract_employment_type(self):
        """Test employment type extraction from text"""
        test_cases = [
            ('This is a full-time position', 'full-time'),
            ('Part time opportunity available', 'part-time'),
            ('Contract role for 6 months', 'contract'),
            ('Internship program', 'internship'),
            ('Freelance work', 'freelance'),
            ('Regular position', None)
        ]
        
        for text, expected in test_cases:
            result = self.scraper._extract_employment_type(text)
            self.assertEqual(result, expected, f"Failed for text: {text}")

    def test_extract_regex_fallbacks(self):
        """Test regex-based extraction methods"""
        sample_text = """
        We are looking for a Python developer with experience in React and AWS.
        Salary range: $100,000 - $150,000 per year.
        Must have JavaScript, Docker, and PostgreSQL skills.
        """
        
        result = self.scraper._extract_regex_fallbacks(sample_text)
        
        # Test skills extraction
        self.assertIn('skills', result)
        skills = result['skills']
        self.assertIn('Python', skills)
        self.assertIn('React', skills)
        self.assertIn('AWS', skills)
        self.assertIn('JavaScript', skills)
        self.assertIn('Docker', skills)
        self.assertIn('PostgreSQL', skills)
        
        # Test salary extraction
        self.assertIn('salary', result)
        salary = result['salary']
        self.assertEqual(salary['min'], 100000)
        self.assertEqual(salary['max'], 150000)
        self.assertEqual(salary['currency'], 'USD')

    def test_merge_extraction_data(self):
        """Test data merging from different sources"""
        json_ld_data = {'title': 'Senior Engineer', 'company': 'BigCorp'}
        microdata = {'title': 'Engineer', 'location': 'NYC'}
        dom_data = {'description': 'Great opportunity'}
        regex_data = {'skills': ['Python', 'React']}
        
        field_sources = {}
        
        result = self.scraper._merge_extraction_data(
            json_ld_data, microdata, dom_data, regex_data, field_sources
        )
        
        # JSON-LD should have priority for title
        self.assertEqual(result['title'], 'Senior Engineer')
        self.assertEqual(field_sources['title'], 'json-ld')
        
        # Microdata should provide location (not in JSON-LD)
        self.assertEqual(result['location'], 'NYC')
        self.assertEqual(field_sources['location'], 'microdata')
        
        # DOM should provide description
        self.assertEqual(result['description'], 'Great opportunity')
        self.assertEqual(field_sources['description'], 'dom')
        
        # Regex should provide skills
        self.assertEqual(result['skills'], ['Python', 'React'])
        self.assertEqual(field_sources['skills'], 'regex')

    def test_validate_and_repair_missing_title(self):
        """Test validation and repair of missing title"""
        data = {
            'company': 'TestCorp',
            'source_url': 'https://example.com/job',
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'description': 'Software Engineer Position\nGreat opportunity...'
        }
        
        job = self.scraper._validate_and_repair(data)
        
        # Title should be extracted from description
        self.assertEqual(job.title, 'Software Engineer Position')
        self.assertIn('Title extracted from description', 
                     job.provenance.warnings if job.provenance else [])

    def test_validate_and_repair_missing_company(self):
        """Test validation and repair of missing company"""
        data = {
            'title': 'Developer',
            'source_url': 'https://jobs.techcorp.com/job/123',
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'description': 'Great opportunity'
        }
        
        job = self.scraper._validate_and_repair(data)
        
        # Company should be guessed from URL
        self.assertEqual(job.company, 'Techcorp')
        self.assertIn('Company name guessed from URL', 
                     job.provenance.warnings if job.provenance else [])

    def test_validate_and_repair_minimal_description(self):
        """Test validation and repair of minimal description"""
        data = {
            'title': 'Developer',
            'company': 'TestCorp',
            'source_url': 'https://example.com/job',
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'description': 'Short',  # Too short
            'responsibilities': ['Code', 'Test', 'Deploy'],
            'qualifications': ['Python', 'SQL']
        }
        
        job = self.scraper._validate_and_repair(data)
        
        # Description should be generated from lists
        self.assertIn('Responsibilities:', job.description)
        self.assertIn('Qualifications:', job.description)
        self.assertIn('Description generated from extracted lists',
                     job.provenance.warnings if job.provenance else [])

    def test_to_dict_conversion(self):
        """Test JobPosting to dictionary conversion"""
        salary = SalaryInfo(min=100000, max=150000, currency="USD", period="yearly")
        provenance = ProvenanceInfo(
            extraction_method="json-ld",
            confidence_score=0.9,
            field_sources={"title": "json-ld"},
            warnings=[]
        )
        
        job = JobPosting(
            title="Test Engineer",
            company="TestCorp",
            source_url="https://example.com/job",
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            description="Test description",
            salary=salary,
            provenance=provenance
        )
        
        result = self.scraper.to_dict(job)
        
        self.assertEqual(result['title'], 'Test Engineer')
        self.assertEqual(result['company'], 'TestCorp')
        self.assertIsInstance(result['salary'], dict)
        self.assertEqual(result['salary']['min'], 100000)
        self.assertIsInstance(result['provenance'], dict)
        self.assertEqual(result['provenance']['extraction_method'], 'json-ld')


class TestScrapeCLI(unittest.TestCase):
    """Test cases for the CLI interface"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Import CLI module
        sys.path.insert(0, str(Path(__file__).parent))
        import scrape_job
        self.scrape_job = scrape_job

    def test_validate_url(self):
        """Test URL validation"""
        valid_urls = [
            'https://example.com/job',
            'http://company.com/careers/123',
            'https://jobs.example.org/posting?id=456'
        ]
        
        invalid_urls = [
            'not-a-url',
            'ftp://example.com/job',
            'example.com/job',
            '',
            'https://',
            'javascript:alert(1)'
        ]
        
        for url in valid_urls:
            self.assertTrue(self.scrape_job.validate_url(url), f"Should be valid: {url}")
        
        for url in invalid_urls:
            self.assertFalse(self.scrape_job.validate_url(url), f"Should be invalid: {url}")

    def test_validate_output_path(self):
        """Test output path validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Valid paths
            valid_paths = [
                temp_path / "output.json",
                temp_path / "subdir" / "output.json",  # Will create subdir
                temp_path / "existing.json"
            ]
            
            for path in valid_paths:
                self.assertTrue(self.scrape_job.validate_output_path(str(path)),
                              f"Should be valid: {path}")

    @patch('job_scraper.JobScraper')
    async def test_scrape_and_save_success(self, mock_scraper_class):
        """Test successful scraping and saving"""
        # Mock scraper
        mock_scraper = Mock()
        mock_scraper_class.return_value = mock_scraper
        
        # Mock job posting
        mock_job = JobPosting(
            title="Test Job",
            company="Test Company",
            source_url="https://example.com/job",
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            description="Test description"
        )
        
        mock_scraper.scrape_job = AsyncMock(return_value=mock_job)
        mock_scraper.to_dict.return_value = {
            'title': 'Test Job',
            'company': 'Test Company',
            'source_url': 'https://example.com/job'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            try:
                result = await self.scrape_job.scrape_and_save(
                    url="https://example.com/job",
                    output_path=temp_file.name
                )
                
                self.assertTrue(result)
                
                # Verify file was written
                with open(temp_file.name, 'r') as f:
                    saved_data = json.load(f)
                    self.assertEqual(saved_data['title'], 'Test Job')
                    
            finally:
                os.unlink(temp_file.name)


class TestIntegration(unittest.TestCase):
    """Integration tests using mock pages"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scraper = JobScraper()

    @patch('job_scraper.async_playwright')
    async def test_extract_json_ld_integration(self, mock_playwright):
        """Test JSON-LD extraction with mocked browser"""
        # Mock page with JSON-LD script
        mock_page = Mock()
        mock_script = Mock()
        
        json_ld_content = json.dumps({
            "@type": "JobPosting",
            "title": "Frontend Developer",
            "hiringOrganization": {"name": "WebCorp"},
            "description": "Build amazing web applications"
        })
        
        mock_script.text_content = AsyncMock(return_value=json_ld_content)
        mock_page.query_selector_all = AsyncMock(return_value=[mock_script])
        
        result = await self.scraper._extract_json_ld(mock_page)
        
        self.assertEqual(result['title'], 'Frontend Developer')
        self.assertEqual(result['company'], 'WebCorp')
        self.assertEqual(result['description'], 'Build amazing web applications')

    @patch('job_scraper.async_playwright')
    async def test_extract_dom_selectors_integration(self, mock_playwright):
        """Test DOM selector extraction with mocked browser"""
        mock_page = Mock()
        
        # Mock title element
        mock_title = Mock()
        mock_title.text_content = AsyncMock(return_value="Software Engineer")
        
        # Mock company element
        mock_company = Mock()
        mock_company.text_content = AsyncMock(return_value="TechStartup")
        
        # Mock page methods
        mock_page.query_selector = AsyncMock(side_effect=lambda selector: {
            'h1[class*="job"]': mock_title,
            '.company-name': mock_company
        }.get(selector))
        
        mock_page.text_content = AsyncMock(return_value="Software Engineer at TechStartup")
        mock_page.query_selector_all = AsyncMock(return_value=[])
        
        result = await self.scraper._extract_dom_selectors(mock_page)
        
        self.assertEqual(result['title'], 'Software Engineer')
        self.assertEqual(result['company'], 'TechStartup')


def run_async_test(coro):
    """Helper to run async tests"""
    return asyncio.get_event_loop().run_until_complete(coro)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestJobScraper))
    suite.addTests(loader.loadTestsFromTestCase(TestScrapeCLI))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)