"""
Enhanced anti-bot detection and mitigation system based on industry best practices.
Implements techniques from: https://www.zyte.com/learn/how-to-work-around-anti-bots/
"""
from __future__ import annotations

import asyncio
import os
import time
import random
import json
import hashlib
from typing import Optional, Tuple, Dict, Any, List, Set
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class AntiBot:
    """
    Comprehensive anti-bot detection and mitigation system.
    """
    
    # Enhanced block detection patterns
    BLOCK_MARKERS = [
        # Cloudflare
        "checking your browser before accessing", "cloudflare", "ray id:", "cf-ray",
        "ddos protection", "attention required", "security check",
        
        # Captcha systems
        "captcha", "recaptcha", "hcaptcha", "are you a robot", "robot check",
        "verify you are human", "prove you are human", "i'm not a robot",
        
        # Access control
        "access denied", "forbidden", "error 403", "error 404", "error 429",
        "too many requests", "rate limit", "blocked", "banned",
        
        # Generic bot detection
        "suspicious activity", "automated requests", "unusual traffic",
        "bot detected", "please wait", "temporarily unavailable",
        
        # ATS-specific blocks
        "please enable javascript", "javascript required", "browser not supported",
        "session expired", "cookie required", "please refresh",
        
        # Challenge pages
        "challenge", "verification", "solve puzzle", "complete verification"
    ]
    
    # Enhanced User-Agent rotation with realistic diversity
    USER_AGENTS = [
        # Chrome Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        
        # Chrome macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
        
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    ]
    
    # Common referrers to appear more legitimate
    REFERRERS = [
        "https://www.google.com/",
        "https://www.linkedin.com/",
        "https://indeed.com/",
        "https://www.glassdoor.com/",
        "https://jobs.lever.co/",
        "https://boards.greenhouse.io/",
        "https://careers.workday.com/",
        "",  # No referrer sometimes
    ]
    
    def __init__(self):
        self.session_fingerprint = self._generate_session_fingerprint()
        self.request_history: List[Tuple[float, str]] = []
        self.blocked_domains: Set[str] = set()
        self.challenge_cache: Dict[str, Any] = {}
        
    def _generate_session_fingerprint(self) -> str:
        """Generate a consistent session fingerprint for this session"""
        return hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
    
    def detect_blocking(self, html: str, status: int, url: str = "") -> Optional[Dict[str, Any]]:
        """
        Enhanced bot detection with detailed analysis.
        Returns None if not blocked, or dict with block details.
        """
        block_info = {
            "blocked": False,
            "type": None,
            "confidence": 0.0,
            "markers": [],
            "suggested_action": None
        }
        
        # HTTP status-based detection
        if status in [403, 429, 503]:
            block_info.update({
                "blocked": True,
                "type": "http_status",
                "confidence": 0.9,
                "markers": [f"HTTP {status}"],
                "suggested_action": "retry_with_different_ip"
            })
            return block_info
        
        if status >= 400:
            block_info.update({
                "blocked": True,
                "type": "http_error",
                "confidence": 0.7,
                "markers": [f"HTTP {status}"],
                "suggested_action": "retry"
            })
            return block_info
        
        # Content-based detection
        if not html or len(html.strip()) < 100:
            block_info.update({
                "blocked": True,
                "type": "empty_response",
                "confidence": 0.8,
                "markers": ["empty_or_minimal_content"],
                "suggested_action": "retry_with_browser"
            })
            return block_info
        
        # Text analysis
        html_lower = html.lower()
        found_markers = []
        confidence = 0.0
        
        for marker in self.BLOCK_MARKERS:
            if marker in html_lower:
                found_markers.append(marker)
                if marker in ["cloudflare", "captcha", "recaptcha"]:
                    confidence += 0.3
                elif marker in ["access denied", "forbidden", "blocked"]:
                    confidence += 0.4
                else:
                    confidence += 0.2
        
        if found_markers:
            block_type = self._classify_block_type(found_markers, html_lower)
            action = self._get_suggested_action(block_type, found_markers)
            
            block_info.update({
                "blocked": True,
                "type": block_type,
                "confidence": min(confidence, 1.0),
                "markers": found_markers,
                "suggested_action": action
            })
            return block_info
        
        # Advanced detection patterns
        if self._detect_javascript_challenge(html):
            block_info.update({
                "blocked": True,
                "type": "javascript_challenge",
                "confidence": 0.8,
                "markers": ["javascript_required"],
                "suggested_action": "use_browser_automation"
            })
            return block_info
        
        if self._detect_honeypot(html):
            block_info.update({
                "blocked": True,
                "type": "honeypot",
                "confidence": 0.6,
                "markers": ["honeypot_detected"],
                "suggested_action": "avoid_suspicious_elements"
            })
            return block_info
        
        return None
    
    def _classify_block_type(self, markers: List[str], html: str) -> str:
        """Classify the type of blocking based on markers"""
        if any(m in ["cloudflare", "cf-ray", "ray id"] for m in markers):
            return "cloudflare"
        elif any(m in ["captcha", "recaptcha", "hcaptcha"] for m in markers):
            return "captcha"
        elif any(m in ["access denied", "forbidden", "error 403"] for m in markers):
            return "access_control"
        elif any(m in ["rate limit", "too many requests", "error 429"] for m in markers):
            return "rate_limiting"
        elif any(m in ["javascript required", "please enable javascript"] for m in markers):
            return "javascript_challenge"
        else:
            return "generic_block"
    
    def _get_suggested_action(self, block_type: str, markers: List[str]) -> str:
        """Get suggested action based on block type"""
        action_map = {
            "cloudflare": "use_browser_automation",
            "captcha": "use_captcha_solver",
            "access_control": "retry_with_different_ip",
            "rate_limiting": "wait_and_retry",
            "javascript_challenge": "use_browser_automation",
            "generic_block": "retry_with_different_strategy"
        }
        return action_map.get(block_type, "retry")
    
    def _detect_javascript_challenge(self, html: str) -> bool:
        """Detect JavaScript-based challenges"""
        js_patterns = [
            "please enable javascript",
            "javascript is required",
            "javascript disabled",
            "noscript",
            "document.cookie",
            "__cf_chl_jschl_tk__",
            "window.location.reload"
        ]
        html_lower = html.lower()
        return any(pattern in html_lower for pattern in js_patterns)
    
    def _detect_honeypot(self, html: str) -> bool:
        """Detect honeypot traps"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Hidden form fields that shouldn't be filled
            hidden_inputs = soup.find_all('input', {'type': 'hidden'})
            if len(hidden_inputs) > 10:  # Excessive hidden fields
                return True
            
            # Invisible elements (common honeypot technique)
            invisible_elements = soup.find_all(attrs={'style': lambda x: x and 'display:none' in x.replace(' ', '')})
            if len(invisible_elements) > 5:
                return True
            
            return False
        except Exception:
            return False
    
    def generate_realistic_headers(self, url: str, previous_url: str = None) -> Dict[str, str]:
        """
        Generate realistic browser headers with proper context.
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Select consistent user agent for this session
        ua_index = hash(self.session_fingerprint + domain) % len(self.USER_AGENTS)
        user_agent = self.USER_AGENTS[ua_index]
        
        # Determine browser type from user agent
        is_chrome = "Chrome" in user_agent
        is_firefox = "Firefox" in user_agent
        is_safari = "Safari" in user_agent and "Chrome" not in user_agent
        is_edge = "Edg" in user_agent
        
        # Base headers
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Browser-specific headers
        if is_chrome or is_edge:
            headers.update({
                "sec-ch-ua": '"Google Chrome";v="125", "Chromium";v="125", "Not=A?Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none" if not previous_url else "same-origin",
                "Sec-Fetch-User": "?1",
            })
        elif is_firefox:
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        
        # Add referer if we have a previous URL
        if previous_url:
            headers["Referer"] = previous_url
        else:
            # Sometimes add a realistic referrer
            if random.random() < 0.3:
                headers["Referer"] = random.choice(self.REFERRERS)
        
        # Randomize some optional headers
        if random.random() < 0.7:
            headers["Cache-Control"] = "max-age=0"
        
        if random.random() < 0.5:
            headers["Pragma"] = "no-cache"
        
        return headers
    
    def simulate_human_behavior(self) -> Dict[str, Any]:
        """
        Generate parameters to simulate human browsing behavior.
        """
        return {
            "delay_before_request": random.uniform(1.0, 3.0),
            "delay_after_request": random.uniform(0.5, 2.0),
            "scroll_behavior": {
                "enabled": random.random() < 0.7,
                "scroll_count": random.randint(2, 8),
                "scroll_delay": random.uniform(0.3, 1.5)
            },
            "mouse_movement": {
                "enabled": random.random() < 0.5,
                "move_count": random.randint(3, 12),
                "move_delay": random.uniform(0.1, 0.5)
            },
            "page_load_wait": random.uniform(2.0, 5.0)
        }
    
    def track_request(self, url: str) -> None:
        """Track request for pattern analysis"""
        now = time.time()
        self.request_history.append((now, url))
        
        # Keep only recent history (last hour)
        cutoff = now - 3600
        self.request_history = [(t, u) for t, u in self.request_history if t > cutoff]
    
    def get_request_pattern_analysis(self) -> Dict[str, Any]:
        """Analyze request patterns to detect if we're behaving too bot-like"""
        if not self.request_history:
            return {"risk_score": 0.0, "recommendations": []}
        
        now = time.time()
        recent_requests = [(t, u) for t, u in self.request_history if now - t < 300]  # Last 5 minutes
        
        if not recent_requests:
            return {"risk_score": 0.0, "recommendations": []}
        
        # Calculate metrics
        request_count = len(recent_requests)
        time_span = now - recent_requests[0][0] if recent_requests else 0
        avg_interval = time_span / max(request_count - 1, 1)
        
        # Calculate risk score
        risk_score = 0.0
        recommendations = []
        
        # Too many requests
        if request_count > 20:
            risk_score += 0.3
            recommendations.append("reduce_request_frequency")
        
        # Requests too regular (bot-like timing)
        if avg_interval < 2.0:
            risk_score += 0.4
            recommendations.append("add_random_delays")
        
        # Same domain repeatedly
        domains = [urlparse(u).netloc for _, u in recent_requests]
        if len(set(domains)) == 1 and request_count > 10:
            risk_score += 0.2
            recommendations.append("diversify_targets")
        
        return {
            "risk_score": min(risk_score, 1.0),
            "request_count": request_count,
            "avg_interval": avg_interval,
            "recommendations": recommendations
        }
    
    def should_rotate_identity(self) -> bool:
        """Determine if we should rotate our identity (IP, headers, etc.)"""
        analysis = self.get_request_pattern_analysis()
        return analysis["risk_score"] > 0.6 or len(self.blocked_domains) > 3
    
    def mark_domain_blocked(self, domain: str) -> None:
        """Mark a domain as currently blocking us"""
        self.blocked_domains.add(domain)
    
    def is_domain_blocked(self, domain: str) -> bool:
        """Check if a domain is currently blocking us"""
        return domain in self.blocked_domains
    
    async def solve_simple_challenge(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to solve simple challenges (non-CAPTCHA).
        Returns solution data or None if unsolvable.
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for simple math challenges
            math_challenge = self._find_math_challenge(soup)
            if math_challenge:
                return {"type": "math", "solution": math_challenge}
            
            # Look for hidden form tokens
            csrf_token = self._find_csrf_token(soup)
            if csrf_token:
                return {"type": "csrf", "token": csrf_token}
            
            return None
            
        except Exception as e:
            logger.warning(f"Challenge solving failed: {e}")
            return None
    
    def _find_math_challenge(self, soup: BeautifulSoup) -> Optional[str]:
        """Find and solve simple math challenges"""
        # Look for patterns like "What is 5 + 3?"
        text = soup.get_text().lower()
        import re
        
        math_pattern = r'what is (\d+) \+ (\d+)\?'
        match = re.search(math_pattern, text)
        if match:
            return str(int(match.group(1)) + int(match.group(2)))
        
        return None
    
    def _find_csrf_token(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract CSRF tokens from forms"""
        csrf_inputs = soup.find_all('input', {'name': lambda x: x and 'csrf' in x.lower()})
        if csrf_inputs:
            return csrf_inputs[0].get('value')
        
        meta_csrf = soup.find('meta', {'name': 'csrf-token'})
        if meta_csrf:
            return meta_csrf.get('content')
        
        return None

# Global anti-bot instance
antibot = AntiBot()