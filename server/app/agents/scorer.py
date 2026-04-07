"""Scorer Agent

Computes a score for a candidate profile/resume against a job posting using:
- embedding similarity (using `embedder`)
- keyword coverage (job keywords vs profile skills and text)
- ATS parse checks (presence of key fields)

Returns a dictionary with component scores and an aggregate score in [0,1].
"""
from __future__ import annotations

from typing import Dict, Any, List, Tuple
import re
import time
from app.agents.embedder import embed_texts
from app.agents.ats_comparison import compare_ats_scorers


def _cosine(a: List[float], b: List[float]) -> float:
    da = sum(x * x for x in a) ** 0.5
    db = sum(x * x for x in b) ** 0.5
    if da == 0 or db == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (da * db)


def _normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _normalize_for_match(text: str) -> Tuple[str, set[str]]:
    lowered = (text or "").lower()
    normalized = _normalize_spaces(re.sub(r"[^a-z0-9+#./\s]", " ", lowered))
    tokens = set(t for t in normalized.split(" ") if t)
    return normalized, tokens


def _keyword_coverage_details(
    keywords: List[str],
    profile_text: str,
    skills: List[str],
    normalized_skills: Any = None,
) -> Tuple[float, List[str], List[str]]:
    # Phrase-aware, case-insensitive matching with a skills fallback.
    pt_norm, pt_tokens = _normalize_for_match(profile_text)
    skills_norm = [s for s in (_normalize_spaces(x).lower() for x in (skills or [])) if s]
    skills_set = set(skills_norm)

    # Optionally incorporate canonical skills if available from normalizer.
    try:
        if isinstance(normalized_skills, dict) and isinstance(normalized_skills.get("skills"), list):
            for item in normalized_skills.get("skills"):
                if isinstance(item, dict) and item.get("canonical"):
                    skills_set.add(str(item.get("canonical")).strip().lower())
    except Exception:
        pass

    matched: List[str] = []
    missing: List[str] = []
    for k in (keywords or []):
        kw = _normalize_spaces(str(k)).lower()
        if not kw or len(kw) < 2:
            continue

        # If it's a multi-word phrase (or has punctuation like C++/Node.js), match as substring.
        if " " in kw or any(ch in kw for ch in ["+", "#", ".", "/"]):
            hit = (kw in pt_norm) or (kw in skills_set)
        else:
            hit = (kw in pt_tokens) or (kw in skills_set)

        if hit:
            matched.append(str(k))
        else:
            missing.append(str(k))

    cov = (len(matched) / max(1, (len(matched) + len(missing))))
    return cov, matched, missing


def _has_section(raw_text: str, headings: List[str]) -> bool:
    if not raw_text:
        return False
    for h in headings:
        if re.search(rf"^\s*{re.escape(h)}\b", raw_text, flags=re.IGNORECASE | re.MULTILINE):
            return True
    return False


def _ats_structure_checks(profile: Dict[str, Any]) -> Tuple[float, Dict[str, bool]]:
    # Avoid contact-info bias: focus on basic resume structure only.
    raw = str(profile.get("raw_text") or "")
    has_skills = bool(profile.get("skills")) or _has_section(raw, ["skills", "technical skills", "core competencies", "technologies"])
    has_experience = bool(profile.get("experience")) or _has_section(raw, ["experience", "work experience", "professional experience", "employment"])
    has_education = bool(profile.get("education")) or _has_section(raw, ["education", "academics"])
    total = 3
    score = (int(has_skills) + int(has_experience) + int(has_education)) / total
    return score, {"has_skills": has_skills, "has_experience": has_experience, "has_education": has_education}


def _bias_check(profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """Check for potential biases in scoring."""
    profile_text = (profile.get("raw_text") or "").lower()
    job_text = (job.get("text") or "").lower()
    
    # Simple bias indicators (expandable)
    biased_terms = {
        "gender": ["he", "she", "his", "her", "man", "woman", "male", "female"],
        "age": ["young", "old", "experienced", "junior", "senior"],
        "ethnicity": ["race", "ethnic", "nationality"],
    }
    
    bias_flags = {}
    for category, terms in biased_terms.items():
        profile_count = sum(1 for term in terms if term in profile_text)
        job_count = sum(1 for term in terms if term in job_text)
        bias_flags[category] = {"profile": profile_count, "job": job_count}
    
    # Overall bias score (0-1, higher means more potential bias)
    total_biased = sum(sum(counts.values()) for counts in bias_flags.values())
    bias_score = min(1.0, total_biased / 10.0)  # Normalize
    
    return {
        "bias_score": bias_score,
        "bias_flags": bias_flags,
        "recommendation": "Review for fairness" if bias_score > 0.5 else "Appears fair"
    }


def score_profile(profile: Dict[str, Any], job: Dict[str, Any], embed_model: str | None = None) -> Dict[str, Any]:
    """Compute component scores and an aggregate score.

    job: expects keys `text` and `keywords` (list).
    profile: expects `raw_text` and `skills` and may include `name`/`email`.
    """
    profile_text = profile.get("raw_text", "")
    job_text = job.get("text", "")
    keywords = job.get("keywords", [])

    # embeddings (clamped to [0,1] to avoid negative cosine edge cases)
    p_emb = embed_texts([profile_text], model_name=embed_model)[0]
    j_emb = embed_texts([job_text], model_name=embed_model)[0]
    emb_sim = max(0.0, min(1.0, _cosine(p_emb, j_emb)))

    kw_cov, matched_keywords, missing_keywords = _keyword_coverage_details(
        keywords=keywords,
        profile_text=profile_text,
        skills=profile.get("skills", []) or [],
        normalized_skills=profile.get("normalized_skills"),
    )

    # Calculate accuracy metrics
    total_keywords = len(keywords)
    true_positives = len(matched_keywords)
    false_negatives = len(missing_keywords)
    # Assuming all matched are correct (TP), missing are FN, no FP since we don't have ground truth
    precision = true_positives / max(1, true_positives)  # Since no FP, precision = 1 if any matches
    recall = true_positives / max(1, total_keywords)
    f1_score = 2 * precision * recall / max(1, precision + recall)

    structure, structure_details = _ats_structure_checks(profile)

    bias_info = _bias_check(profile, job)

    # aggregate: weighted sum
    # Bias mitigation: keep structure a small factor; do not score contact fields.
    agg = 0.6 * emb_sim + 0.3 * kw_cov + 0.1 * structure
    agg = max(0.0, min(1.0, agg))
    
    # Calculate overall score: ATS (50%) + Accuracy (30%) + Fairness (20%)
    fairness_score = 1.0 - bias_info.get("bias_score", 0.0)
    overall_score = (agg * 0.5) + (f1_score * 0.3) + (fairness_score * 0.2)
    overall_score = max(0.0, min(1.0, overall_score))
    
    # Convert overall score to 100-point scale for readability
    overall_score_100 = round(overall_score * 100, 2)
    ats_score_100 = round(agg * 100, 2)
    
    # Prepare scoring dict for comparison
    talentflow_score = {
        "embedding": emb_sim,
        "keyword_coverage": kw_cov,
        "fairness_score": fairness_score,
        "overall_score_100": overall_score_100,
        "structure": structure,
    }
    
    # Compare with open source ATS for effectiveness analysis
    try:
        comparison_result = compare_ats_scorers(profile, job, talentflow_score)
        ats_comparison = comparison_result.get("comparison", {})
    except Exception as e:
        ats_comparison = {"error": str(e), "comparison": "skipped"}
    
    return {
        "version": 2,
        "embedding": round(emb_sim, 3),
        "keyword_coverage": round(kw_cov, 3),
        "structure": round(structure, 3),
        "structure_details": structure_details,
        "keyword_hits": len(matched_keywords),
        "keyword_total": len(matched_keywords) + len(missing_keywords),
        "matched_keywords": matched_keywords[:50],
        "missing_keywords": missing_keywords[:50],
        "accuracy_metrics": {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1_score, 3),
        },
        "bias": bias_info,
        "aggregate": round(agg, 3),
        "ats_score_100": ats_score_100,
        "fairness_score": round(fairness_score, 3),
        "overall_score": round(overall_score, 3),
        "overall_score_100": overall_score_100,
        "ats_comparison": ats_comparison,
        "scoring_metadata": {
            "timestamp": time.time(),
            "profile_text_length": len(profile_text),
            "job_text_length": len(job_text),
            "keywords_evaluated": len(keywords),
            "model_used": embed_model or "default"
        }
    }
