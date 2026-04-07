"""ATS Comparison Module

Compares TalentFlow's custom ATS scorer with an open-source style ATS scorer.
This demonstrates the effectiveness of our embedding-based approach vs traditional
keyword-matching based approaches used by many open source ATS systems.
"""

from typing import Dict, Any, List, Tuple
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def _normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s+#./]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class BasicAtsScorer:
    """
    Open-source style ATS scorer using TF-IDF and keyword matching.
    Represents traditional ATS systems that don't use embeddings.
    """
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
    
    def score(self, profile_text: str, job_text: str, keywords: List[str]) -> Dict[str, Any]:
        """Score using TF-IDF cosine similarity (traditional ATS method)"""
        if not profile_text or not job_text:
            return {
                "method": "TF-IDF",
                "score": 0.0,
                "score_100": 0,
                "keyword_coverage": 0.0,
                "matched_keywords": [],
                "missing_keywords": keywords or [],
                "explanation": "Missing profile or job text"
            }
        
        # Normalize texts
        profile_norm = _normalize_text(profile_text)
        job_norm = _normalize_text(job_text)
        
        # TF-IDF similarity
        try:
            vectors = self.vectorizer.fit_transform([profile_norm, job_norm])
            tfidf_sim = float(cosine_similarity(vectors)[0][1])
        except:
            tfidf_sim = 0.0
        
        # Keyword matching (simple substring matching)
        matched = []
        missing = []
        for kw in (keywords or []):
            kw_norm = _normalize_text(kw)
            if kw_norm in profile_norm or any(w in profile_norm.split() for w in kw_norm.split()):
                matched.append(kw)
            else:
                missing.append(kw)
        
        keyword_cov = len(matched) / max(1, len(matched) + len(missing))
        
        # Simple weighted score (no embeddings, no bias checking)
        score = (tfidf_sim * 0.7) + (keyword_cov * 0.3)
        score = max(0.0, min(1.0, score))
        
        return {
            "method": "TF-IDF + Keyword Matching",
            "score": round(score, 3),
            "score_100": round(score * 100, 2),
            "tfidf_similarity": round(tfidf_sim, 3),
            "keyword_coverage": round(keyword_cov, 3),
            "matched_keywords": matched[:20],
            "missing_keywords": missing[:20],
            "components": {
                "tfidf_weight": 0.7,
                "keyword_weight": 0.3,
                "bias_check": "None (open source limitation)"
            },
            "explanation": "Traditional ATS: TF-IDF similarity + keyword matching (no embeddings)"
        }


def compare_ats_scorers(
    profile: Dict[str, Any],
    job: Dict[str, Any],
    talentflow_score: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compare TalentFlow custom scorer with open-source style ATS.
    
    Args:
        profile: Resume/profile dict with raw_text and skills
        job: Job dict with text and keywords
        talentflow_score: Pre-computed TalentFlow ATS score
    
    Returns:
        Comparison dict showing both scores and effectiveness metrics
    """
    profile_text = profile.get("raw_text", "")
    job_text = job.get("text", "")
    keywords = job.get("keywords", [])
    
    # Score with basic ATS
    basic_scorer = BasicAtsScorer()
    basic_score = basic_scorer.score(profile_text, job_text, keywords)
    
    # Calculate comparison metrics
    talentflow_overall = talentflow_score.get("overall_score_100", 0)
    basic_overall = basic_score.get("score_100", 0)
    
    # Difference metrics
    overall_diff = talentflow_overall - basic_overall
    embedding_advantage = talentflow_score.get("embedding", 0) - basic_score.get("tfidf_similarity", 0)
    fairness_advantage = talentflow_score.get("fairness_score", 0)  # Basic ATS has none
    
    # Effectiveness analysis
    effectiveness = {
        "overall_score_diff": round(overall_diff, 2),
        "embedding_advantage": round(embedding_advantage, 3),
        "fairness_advantage": round(fairness_advantage, 3),
        "has_bias_detection": True,  # TalentFlow advantage
        "basic_ats_limitations": [
            "No semantic understanding of skills",
            "No bias/fairness detection",
            "Simple keyword matching only",
            "No embedding-based similarity",
            "No accuracy metrics (precision/recall)",
            "Text length dependent"
        ],
        "talentflow_advantages": [
            "Semantic similarity via embeddings",
            "Comprehensive bias detection",
            "Accuracy metrics (precision/recall/F1)",
            "Fairness scoring integrated",
            "Better handling of synonyms",
            "Structure validation of resume",
            "Multi-factor scoring (ATS + Accuracy + Fairness)"
        ]
    }
    
    return {
        "comparison": {
            "talentflow_ats": {
                "overall_score_100": talentflow_overall,
                "components": {
                    "embedding_similarity": round(talentflow_score.get("embedding", 0) * 100, 2),
                    "keyword_coverage": round(talentflow_score.get("keyword_coverage", 0) * 100, 2),
                    "structure_validation": round(talentflow_score.get("structure", 0) * 100, 2),
                    "fairness_score": round(talentflow_score.get("fairness_score", 0) * 100, 2)
                },
                "method": "Embedding-based + Keyword Matching + Structure Validation + Bias Detection"
            },
            "opensource_ats": {
                "overall_score_100": basic_overall,
                "components": {
                    "tfidf_similarity": round(basic_score.get("tfidf_similarity", 0) * 100, 2),
                    "keyword_coverage": round(basic_score.get("keyword_coverage", 0) * 100, 2),
                    "structure_validation": 0,
                    "fairness_score": 0
                },
                "method": "TF-IDF + Keyword Matching (no embeddings, no bias detection)"
            },
            "effectiveness_metrics": effectiveness,
            "recommendation": _generate_recommendation(overall_diff, talentflow_score)
        }
    }


def _generate_recommendation(overall_diff: float, talentflow_score: Dict[str, Any]) -> str:
    """Generate recommendation based on score difference"""
    if overall_diff > 15:
        return f"""TalentFlow is SIGNIFICANTLY MORE EFFECTIVE (+{overall_diff:.1f} points).
Our embedding-based approach provides superior accuracy, especially for:
- Matching synonymous skills (e.g., "Python" vs "Py")
- Detecting skill context and relevance
- Ensuring fair and unbiased scoring
- Providing comprehensive accuracy metrics"""
    elif overall_diff > 5:
        return f"""TalentFlow is NOTICEABLY MORE EFFECTIVE (+{overall_diff:.1f} points).
Key advantages include semantic understanding of skills and bias detection."""
    elif overall_diff > 0:
        return f"""TalentFlow is SLIGHTLY MORE EFFECTIVE (+{overall_diff:.1f} points).
Mainly due to fairness scoring and structure validation."""
    else:
        return """Both systems provide similar scores for this profile.
However, TalentFlow provides additional fairness metrics and accuracy indicators."""


__all__ = [
    "BasicAtsScorer",
    "compare_ats_scorers"
]
