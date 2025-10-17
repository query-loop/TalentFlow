from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import re
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ScoreRequest(BaseModel):
    jd_text: str
    resume_text: str
    jd_title: Optional[str] = None
    jd_requirements: Optional[List[str]] = None


class MatchDetail(BaseModel):
    keyword: str
    category: str
    found: bool
    context: Optional[str] = None
    score: float


class ScoreResponse(BaseModel):
    overall_score: float
    skills_score: float
    experience_score: float
    education_score: float
    keywords_score: float
    
    matched_skills: List[str]
    missing_skills: List[str]
    matched_keywords: List[str]
    missing_keywords: List[str]
    
    match_details: List[MatchDetail]
    recommendations: List[str]
    strengths: List[str]
    gaps: List[str]
    
    metadata: Dict[str, Any]


class ResumeScorer:
    """Intelligent resume-JD matching and scoring engine."""
    
    def __init__(self):
        self.skill_patterns = {
            # Programming languages
            'python': r'\b(python|django|flask|fastapi)\b',
            'javascript': r'\b(javascript|js|typescript|ts|node\.?js|react|vue|angular)\b',
            'java': r'\b(java|spring|hibernate)\b',
            'csharp': r'\b(c#|\.net|asp\.net)\b',
            'go': r'\b(golang|go)\b',
            'rust': r'\brust\b',
            'ruby': r'\b(ruby|rails)\b',
            'php': r'\b(php|laravel)\b',
            'sql': r'\b(sql|mysql|postgresql|postgres|oracle|mssql)\b',
            
            # Frameworks & Tools
            'docker': r'\b(docker|containers|containerization)\b',
            'kubernetes': r'\b(kubernetes|k8s)\b',
            'aws': r'\b(aws|amazon web services|ec2|s3|lambda)\b',
            'azure': r'\b(azure|microsoft azure)\b',
            'gcp': r'\b(gcp|google cloud)\b',
            'terraform': r'\b(terraform|infrastructure as code)\b',
            'ansible': r'\bansible\b',
            'jenkins': r'\bjenkins\b',
            'git': r'\b(git|github|gitlab|version control)\b',
            
            # Data & ML
            'machine_learning': r'\b(machine learning|ml|deep learning|neural networks)\b',
            'ai': r'\b(artificial intelligence|ai)\b',
            'data_science': r'\b(data science|data scientist|analytics)\b',
            'pandas': r'\bpandas\b',
            'numpy': r'\bnumpy\b',
            'tensorflow': r'\btensorflow\b',
            'pytorch': r'\bpytorch\b',
            'spark': r'\b(spark|apache spark)\b',
            
            # Soft Skills
            'communication': r'\b(communication|collaborate|collaboration|team player)\b',
            'leadership': r'\b(leadership|lead|led|manage|managed)\b',
            'problem_solving': r'\b(problem solving|analytical|critical thinking)\b',
            'agile': r'\b(agile|scrum|kanban)\b',
        }
        
        self.experience_keywords = [
            'years of experience', 'years experience', 'year of experience',
            'senior', 'lead', 'principal', 'staff', 'architect',
            'junior', 'entry level', 'intern'
        ]
        
        self.education_keywords = [
            'bachelor', 'master', 'phd', 'doctorate', 'mba',
            'computer science', 'engineering', 'cs degree',
            'university', 'college'
        ]
    
    def score_resume(self, jd_text: str, resume_text: str, 
                     jd_title: Optional[str] = None,
                     jd_requirements: Optional[List[str]] = None) -> ScoreResponse:
        """
        Comprehensive scoring of resume against JD.
        Returns detailed match analysis with scores and recommendations.
        """
        jd_lower = jd_text.lower()
        resume_lower = resume_text.lower()
        
        # Extract skills from both documents
        jd_skills = self._extract_skills(jd_lower)
        resume_skills = self._extract_skills(resume_lower)
        
        # Calculate skill matching
        matched_skills = list(jd_skills & resume_skills)
        missing_skills = list(jd_skills - resume_skills)
        
        skills_score = len(matched_skills) / len(jd_skills) if jd_skills else 0.0
        
        # Extract and match keywords from JD requirements
        jd_keywords = self._extract_keywords(jd_text, jd_requirements)
        matched_keywords = []
        missing_keywords = []
        match_details = []
        
        for keyword in jd_keywords:
            found = keyword.lower() in resume_lower
            context = self._find_context(resume_text, keyword) if found else None
            
            match_details.append(MatchDetail(
                keyword=keyword,
                category=self._categorize_keyword(keyword),
                found=found,
                context=context,
                score=1.0 if found else 0.0
            ))
            
            if found:
                matched_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        keywords_score = len(matched_keywords) / len(jd_keywords) if jd_keywords else 0.0
        
        # Analyze experience level
        experience_score = self._score_experience(jd_lower, resume_lower)
        
        # Analyze education
        education_score = self._score_education(jd_lower, resume_lower)
        
        # Calculate overall score (weighted average)
        overall_score = (
            skills_score * 0.35 +
            keywords_score * 0.25 +
            experience_score * 0.25 +
            education_score * 0.15
        )
        
        # Generate recommendations and analysis
        recommendations = self._generate_recommendations(
            matched_skills, missing_skills, missing_keywords, overall_score
        )
        
        strengths = self._identify_strengths(matched_skills, match_details)
        gaps = self._identify_gaps(missing_skills, missing_keywords)
        
        return ScoreResponse(
            overall_score=round(overall_score * 100, 2),
            skills_score=round(skills_score * 100, 2),
            experience_score=round(experience_score * 100, 2),
            education_score=round(education_score * 100, 2),
            keywords_score=round(keywords_score * 100, 2),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            match_details=match_details,
            recommendations=recommendations,
            strengths=strengths,
            gaps=gaps,
            metadata={
                'total_jd_skills': len(jd_skills),
                'total_resume_skills': len(resume_skills),
                'total_keywords': len(jd_keywords),
                'match_percentage': round((len(matched_skills) + len(matched_keywords)) / 
                                         (len(jd_skills) + len(jd_keywords)) * 100, 2) if (jd_skills or jd_keywords) else 0,
            }
        )
    
    def _extract_skills(self, text: str) -> set:
        """Extract technical skills from text using pattern matching."""
        skills = set()
        for skill_name, pattern in self.skill_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                skills.add(skill_name.replace('_', ' ').title())
        return skills
    
    def _extract_keywords(self, jd_text: str, requirements: Optional[List[str]] = None) -> List[str]:
        """Extract important keywords from JD."""
        keywords = []
        
        # Use provided requirements if available
        if requirements:
            keywords.extend(requirements)
        
        # Extract from JD text
        # Look for bullet points and requirements sections
        lines = jd_text.split('\n')
        for line in lines:
            line = line.strip()
            # Match lines that look like requirements (starting with bullets, numbers, etc.)
            if re.match(r'^[\•\-\*\d+\.)]\s*', line) and len(line) > 10:
                # Clean and extract
                cleaned = re.sub(r'^[\•\-\*\d+\.)]\s*', '', line).strip()
                if len(cleaned) > 5 and len(cleaned) < 150:
                    keywords.append(cleaned)
        
        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)
        
        return unique_keywords[:20]  # Limit to top 20
    
    def _find_context(self, text: str, keyword: str, context_length: int = 100) -> Optional[str]:
        """Find surrounding context for a keyword in text."""
        try:
            idx = text.lower().find(keyword.lower())
            if idx == -1:
                return None
            
            start = max(0, idx - context_length)
            end = min(len(text), idx + len(keyword) + context_length)
            
            context = text[start:end].strip()
            if start > 0:
                context = '...' + context
            if end < len(text):
                context = context + '...'
            
            return context
        except:
            return None
    
    def _categorize_keyword(self, keyword: str) -> str:
        """Categorize a keyword by type."""
        kw_lower = keyword.lower()
        
        if any(tech in kw_lower for tech in ['python', 'java', 'javascript', 'code', 'programming']):
            return 'technical'
        elif any(exp in kw_lower for exp in ['year', 'experience', 'senior', 'junior']):
            return 'experience'
        elif any(edu in kw_lower for edu in ['degree', 'bachelor', 'master', 'education']):
            return 'education'
        elif any(soft in kw_lower for soft in ['communication', 'leadership', 'team', 'collaborate']):
            return 'soft_skill'
        else:
            return 'general'
    
    def _score_experience(self, jd_text: str, resume_text: str) -> float:
        """Score experience level match."""
        score = 0.5  # Default neutral score
        
        # Extract years of experience required
        jd_years_match = re.search(r'(\d+)\+?\s*years?\s+(?:of\s+)?experience', jd_text)
        resume_years_matches = re.findall(r'(\d+)\+?\s*years?\s+(?:of\s+)?experience', resume_text)
        
        if jd_years_match:
            required_years = int(jd_years_match.group(1))
            if resume_years_matches:
                max_resume_years = max([int(y) for y in resume_years_matches])
                if max_resume_years >= required_years:
                    score = 1.0
                elif max_resume_years >= required_years * 0.7:
                    score = 0.8
                else:
                    score = 0.5
        
        # Check for seniority level keywords
        if 'senior' in jd_text and 'senior' in resume_text:
            score = min(1.0, score + 0.2)
        elif 'lead' in jd_text and ('lead' in resume_text or 'senior' in resume_text):
            score = min(1.0, score + 0.2)
        
        return score
    
    def _score_education(self, jd_text: str, resume_text: str) -> float:
        """Score education match."""
        score = 0.5  # Default neutral score
        
        # Check for degree requirements
        for edu_keyword in self.education_keywords:
            if edu_keyword in jd_text and edu_keyword in resume_text:
                score += 0.15
        
        return min(1.0, score)
    
    def _generate_recommendations(self, matched_skills: List[str], 
                                  missing_skills: List[str],
                                  missing_keywords: List[str],
                                  overall_score: float) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if overall_score < 0.6:
            recommendations.append("Consider highlighting more relevant experience that matches the JD requirements")
        
        if missing_skills:
            top_missing = missing_skills[:3]
            recommendations.append(f"Consider adding these skills to your resume: {', '.join(top_missing)}")
        
        if missing_keywords:
            recommendations.append("Incorporate more keywords from the job description into your resume")
        
        if matched_skills:
            recommendations.append(f"Strong match on: {', '.join(matched_skills[:5])} - emphasize these in your cover letter")
        
        if overall_score >= 0.8:
            recommendations.append("Excellent match! Make sure to highlight your top matching skills prominently")
        
        return recommendations
    
    def _identify_strengths(self, matched_skills: List[str], 
                           match_details: List[MatchDetail]) -> List[str]:
        """Identify candidate strengths."""
        strengths = []
        
        if len(matched_skills) > 5:
            strengths.append(f"Strong technical skill match ({len(matched_skills)} skills matched)")
        
        matched_count = sum(1 for md in match_details if md.found)
        if matched_count > len(match_details) * 0.7:
            strengths.append("High keyword coverage in resume")
        
        return strengths
    
    def _identify_gaps(self, missing_skills: List[str], 
                      missing_keywords: List[str]) -> List[str]:
        """Identify gaps in candidate profile."""
        gaps = []
        
        if len(missing_skills) > 5:
            gaps.append(f"Multiple required skills not found ({len(missing_skills)} missing)")
        
        if missing_keywords:
            critical_missing = [kw for kw in missing_keywords if 'required' in kw.lower() or 'must' in kw.lower()]
            if critical_missing:
                gaps.append(f"Critical requirements not addressed: {', '.join(critical_missing[:3])}")
        
        return gaps


# Global scorer instance
scorer = ResumeScorer()


@router.post("/score", response_model=ScoreResponse)
async def score_resume_against_jd(body: ScoreRequest) -> ScoreResponse:
    """
    Score a resume against a job description.
    Returns comprehensive matching analysis with scores and recommendations.
    """
    if not body.jd_text or not body.resume_text:
        raise HTTPException(status_code=400, detail="Both JD text and resume text are required")
    
    try:
        result = scorer.score_resume(
            jd_text=body.jd_text,
            resume_text=body.resume_text,
            jd_title=body.jd_title,
            jd_requirements=body.jd_requirements
        )
        return result
    except Exception as e:
        logger.error(f"Error scoring resume: {e}")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "resume-scoring"}
