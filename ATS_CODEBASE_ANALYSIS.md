# TalentFlow ATS Scorer Implementation - Codebase Analysis

## Executive Summary

TalentFlow uses a **custom embedding-based ATS scorer** (NOT a traditional keyword-matching ATS) that combines semantic understanding with accuracy metrics and fairness/bias detection. The system processes resume text through multiple pipeline stages and outputs comprehensive scoring data.

---

## 1. ATS SCORER IMPLEMENTATION

### Main Implementation Files

#### **[server/app/agents/scorer.py](server/app/agents/scorer.py)**
- **Function:** `score_profile(profile: Dict[str, Any], job: Dict[str, Any], embed_model: str | None = None) -> Dict[str, Any]`
- **Purpose:** Core ATS scoring engine
- **Input:** 
  - `profile` dict with keys: `raw_text`, `skills`, `normalized_skills` (optional)
  - `job` dict with keys: `text`, `keywords` (list)
- **Output:** Comprehensive scoring dictionary (see ATS Output Structure below)

#### **[server/app/routers/ats.py](server/app/routers/ats.py)**
- **Endpoint:** `POST /api/ats`
- **Input Model:** `ATSRequest` with fields: `jdId`, `resumeId`, `text`
- **Output Model:** `ATSResponse` with fields: `score`, `reasons`, `sections`
- **Status:** Basic wrapper that delegates to scorer.py

---

## 2. OPEN-SOURCE LIBRARIES USED

### Primary Dependencies (from pyproject.toml)

| Library | Import Location | Usage |
|---------|------|-------|
| **scikit-learn** v1.3-2 | `server/app/agents/ats_comparison.py` | TF-IDF vectorization and cosine similarity for baseline ATS comparison |
| **sentence-transformers** | `server/app/agents/embedder.py` | Semantic embeddings for resume/job text |
| **sentence-transformers** | `server/app/agents/skill_normalizer.py` | Embedding-based skill normalization |
| **difflib** (Python stdlib) | `server/app/agents/skill_normalizer.py` | Fuzzy string matching for skills (`get_close_matches`) |
| **transformers** (HuggingFace) | `server/app/agents/parser_agent.py` | Optional NLP model for resume parsing (gracefully falls back if unavailable) |
| **beautifulsoup4** | `server/app/routers/pipelines_v2.py` | HTML parsing for JD extraction |

### NOT Used (Actively Avoided)
- ❌ `pylev` - Not used
- ❌ `thefuzz`/`fuzzy-wuzzy` - Not used (uses `difflib` instead)
- ❌ `rapidfuzz` - Not used
- ❌ `spacy` - Not used (uses `transformers` instead)

---

## 3. RESUME TEXT PROCESSING PIPELINE

### Pipeline Stages (server/app/routers/pipelines_v2.py)

```
Step 1: INTAKE
  └─ Record pipeline metadata

Step 2: JD EXTRACTION
  └─ Extract job description from URL or use manual text

Step 3: PROFILE EXTRACTION
  ├─ Extract resume text from manual:// URI or fetch from storage
  └─ Call: extract_profile_from_text(resume_text) from parser_agent.py
      └─ Returns: {name, email, phone, summary, skills[], experience[], education[], raw_text}

Step 4: SKILL NORMALIZATION
  ├─ Call: normalize_skills(profile['skills']) from skill_normalizer.py
  └─ Returns: {skills: [{input, canonical, score}]}

Step 5-7: GAPS, DIFFERENTIATORS, DRAFT
  └─ Placeholder steps in current pipeline

Step 8: ATS SCORING ⭐
  ├─ Input: parsed_profile (with raw_text), jd description, job keywords
  └─ Call: score_profile(profile_for_score, {"text": jd_text, "keywords": reqs})

Step 9: ACTIONS (GENERATE & OPTIMIZE)
  ├─ Call: generate_resume(profile, query=jd_context, collection=chroma)
  ├─ Call: optimize_experience_bullets(experience_list)
  └─ Store: resume_text and optimized_bullets in artifacts
```

### Resume Text Handling

**Where Resume Text is Stored:**
1. **Input:** `artifacts["resume"]["text"]` in pipeline state
2. **Extracted:** `artifacts["profile"]["parsed"]["raw_text"]` after parsing
3. **Generated:** `artifacts["generated"]["resume_text"]` after optimization

**Parsing Function Flow:**
```python
# From parser_agent.py
extract_profile_from_text(text: str, hf_model: Optional[str] = None) -> Dict[str, Any]:
    └─ ParserAgent.parse(text)
        ├─ If transformers available: LLM-based JSON extraction
        └─ Fallback: Rule-based extraction (regex + section detection)
            ├─ Extracts: name, email, phone, summary, skills, experience, education
            └─ Stores original text in: raw_text (ORIGINAL RESUME STORED HERE)
```

---

## 4. CURRENT ATS OUTPUT STRUCTURE

### Full Response from score_profile()

```python
{
    "version": 2,
    
    # Component Scores (0-1 range)
    "embedding": 0.754,           # Semantic similarity (60% weight)
    "keyword_coverage": 0.625,    # Required keywords matched (30% weight)
    "structure": 0.667,           # Resume sections detected (10% weight)
    "aggregate": 0.722,           # Weighted sum of above three
    
    # Keyword Matching Details
    "keyword_hits": 25,
    "keyword_total": 40,
    "matched_keywords": ["python", "aws", "docker", ...],  # Up to 50
    "missing_keywords": ["kubernetes", "terraform", ...],   # Up to 50
    
    # Resume Structure Analysis
    "structure_details": {
        "has_skills": true,
        "has_experience": true,
        "has_education": true
    },
    
    # Accuracy Metrics
    "accuracy_metrics": {
        "precision": 1.0,    # TP / (TP + FP)
        "recall": 0.625,     # TP / (TP + FN)
        "f1_score": 0.769    # Harmonic mean
    },
    
    # Fairness/Bias Detection
    "bias": {
        "bias_score": 0.1,   # 0-1, higher = more bias detected
        "bias_flags": {
            "gender": {"profile": 0, "job": 1},
            "age": {"profile": 0, "job": 0},
            "ethnicity": {"profile": 0, "job": 0}
        },
        "recommendation": "Appears fair"
    },
    
    # Composite Scores (0-100 scale)
    "fairness_score": 0.9,       # 1.0 - bias_score
    "ats_score_100": 72.2,       # aggregate * 100
    "overall_score": 0.763,      # (aggregate*0.5) + (f1*0.3) + (fairness*0.2)
    "overall_score_100": 76.3,   # overall_score * 100
    
    # Comparison with Traditional ATS
    "ats_comparison": {
        "comparison": {
            "talentflow_ats": {...},
            "basic_ats_score": {...}
        }
    },
    
    # Metadata
    "scoring_metadata": {
        "timestamp": 1695123456.789,
        "profile_text_length": 2847,
        "job_text_length": 1234,
        "keywords_evaluated": 40,
        "model_used": "default"
    }
}
```

### Pipeline-Level ATS Output (stored in artifacts["ats"])

The full scorer.py output is stored in the **PipelineV2 artifacts** along with:

```python
artifacts["ats"] = {
    # All fields from score_profile() above, PLUS:
    "updatedAt": 1695123456.789,
    "keywordsUsed": [first 50 keywords from job ...],
}
```

### Report Endpoint Output

**Endpoint:** `GET /pipelines-v2/{id}/report`
- Returns simplified report format:
  ```python
  {
      "score": 72.3,  # Overall score (0-100)
      "reasons": [
          "Semantic match: 75%",
          "Requirement coverage: 63%",
          "Missing key requirements: kubernetes, terraform, ..."
      ],
      "sections": {
          "summary": "Good match",
          "ats": {
              # Full score_profile() output here
          }
      }
  }
  ```

---

## 5. WHERE TO ADD RESUME TEXT TO OUTPUT

### Current Situation
- **Does NOT include original resume text in output** by design
- Resume text is stored in `artifacts["profile"]["parsed"]["raw_text"]`
- Generated resumed stored in `artifacts["generated"]["resume_text"]`

### Where to Make Changes

To add resume text to the ATS output, modify these files:

#### **Option 1: Report Endpoint** (Recommended for API)
**File:** [server/app/routers/pipelines_v2.py](server/app/routers/pipelines_v2.py#L40-L130)
- Function: `pipeline_report(id: str)`
- Current line ~87: `resume_text = (artifacts.get("resume") or {}).get("text") or ""`
- **Action:** Include `resume_text` in returned sections:
  ```python
  sections = {
      "summary": ("Good match" if pct >= 60 else "Needs improvement"),
      "ats": s,
      "resume_text": resume_text  # ADD THIS LINE
  }
  ```

#### **Option 2: ATS Scorer Function** (For All Uses)
**File:** [server/app/agents/scorer.py](server/app/agents/scorer.py#L130-L200)
- Function: `score_profile(profile, job, embed_model=None)`
- **Action:** Add to return dict:
  ```python
  return {
      # ... existing fields ...
      "profile_raw_text": profile.get("raw_text", ""),  # Original resume text
  }
  ```

#### **Option 3: ATS Router Endpoint**
**File:** [server/app/routers/ats.py](server/app/routers/ats.py#L16-L38)
- **Action:** Modify ATSResponse model to include optional `resume_text`:
  ```python
  class ATSResponse(BaseModel):
      score: float
      reasons: List[str]
      sections: Dict[str, str]
      resume_text: Optional[str] = None  # ADD THIS
  ```

#### **Option 4: Pipeline Run Output**
**File:** [server/app/routers/pipelines_v2.py](server/app/routers/pipelines_v2.py#L1335-L1370)
- Function: `run_pipeline_v2(id: str)` ATS step
- Current line ~1335: `artifacts["ats"] = score`
- **Action:** Add resume text to artifacts:
  ```python
  # In step == "ats":
  resume_text = (artifacts.get("profile") or {}).get("parsed", {}).get("raw_text", "")
  score["resume_text"] = resume_text  # ADD THIS
  artifacts["ats"] = score
  ```

---

## 6. SCORING CALCULATION FORMULA

### Multi-Factor Scoring System

```
┌─ OVERALL SCORE TABLE ─────────────────────────────────────────┐
│                                                                  │
│  Overall Score (0-100) = (ATS × 50%) + (Accuracy × 30%) +    │
│                          (Fairness × 20%)                      │
│                                                                  │
│  ATS Component (0-1) = (Embedding × 60%) +                    │
│                        (Keywords × 30%) +                      │
│                        (Structure × 10%)                       │
│                                                                  │
│  Accuracy = F1 Score = 2 × (Precision × Recall) /            │
│             (Precision + Recall)                              │
│                                                                  │
│  Fairness = 1.0 - Bias Score                                  │
│                                                                  │
└──────────────────────────────────────────────────────────────┘

Example:
  Embedding:       0.75 (75% semantic match)
  Keywords:        0.63 (63% of required keywords found)
  Structure:       0.67 (all 3 resume sections detected)
  
  ATS = (0.75 × 0.6) + (0.63 × 0.3) + (0.67 × 0.1)
      = 0.45 + 0.189 + 0.067
      = 0.706
  
  Accuracy (F1):   0.769
  Bias Score:      0.10
  Fairness:        0.90
  
  Overall = (0.706 × 0.5) + (0.769 × 0.3) + (0.90 × 0.2)
          = 0.353 + 0.231 + 0.18
          = 0.764 (76.4/100)
```

---

## 7. KEY FILES SUMMARY TABLE

| File | Purpose | Key Function |
|------|---------|--------------|
| [scorer.py](server/app/agents/scorer.py) | ATS scoring engine | `score_profile(profile, job, embed_model)` |
| [ats_comparison.py](server/app/agents/ats_comparison.py) | Baseline ATS benchmark | `compare_ats_scorers()` - compares vs TF-IDF |
| [embedder.py](server/app/agents/embedder.py) | Text embeddings | `embed_texts(texts, model_name)` |
| [skill_normalizer.py](server/app/agents/skill_normalizer.py) | Skill canonicalization | `normalize_skills(skills, model_name)` |
| [parser_agent.py](server/app/agents/parser_agent.py) | Resume extraction | `extract_profile_from_text(text, hf_model)` |
| [ats.py](server/app/routers/ats.py) | ATS API endpoint | `ats_score(body: ATSRequest)` |
| [pipelines_v2.py](server/app/routers/pipelines_v2.py) | Main pipeline orchestration | `run_pipeline_v2(id)` |

---

## 8. SCORE COMPONENT EXPLANATIONS

### Embedding (Semantic Similarity) - 60% Weight
- **What:** Uses sentence-transformers to encode resume and job description
- **How:** Calculates cosine similarity between embeddings
- **Range:** 0-1 (0 = completely different, 1 = identical)
- **Example:** Resume mentioning "Python programming" matches "Python development" with high similarity despite different wording

### Keyword Coverage - 30% Weight
- **What:** Percentage of job requirements found in resume
- **How:** Phrase-aware matching (substrings for multi-word skills like "Node.js", "C++")
- **Range:** 0-1 (0 = no keywords match, 1 = all keywords found)
- **Includes:** Fallback to parsed skills if available

### Structure Validation - 10% Weight
- **What:** Detects presence of resume sections
- **How:** Regex search for section headings
- **Sections Checked:** Skills, Experience, Education
- **Range:** 0-1 (each section = +0.333)

### Accuracy Metrics
- **Precision:** TP / (TP + FP) - How accurate are the matches?
- **Recall:** TP / (TP + FN) - How many required keywords were found?
- **F1 Score:** Harmonic mean - Balances precision and recall

### Bias Detection
- **What:** Flags potentially biased language in resume or JD
- **Categories:** Gender, Age, Ethnicity
- **Bias Score:** Normalized count (0-1)
- **Fairness Score:** 1.0 - Bias Score

---

## 9. DATA FLOW DIAGRAM

```
Resume Input (manual: URI or file)
    ↓
[parser_agent.py] extract_profile_from_text()
    ├─ HuggingFace transformers (if available)
    └─ Fallback: Regex-based extraction
    ↓
Profile Dict {raw_text, skills[], experience[], education[], ...}
    ↓
[skill_normalizer.py] normalize_skills()
    ├─ Uses sentence-transformers embeddings
    └─ Fallback: difflib fuzzy matching
    ↓
Artifacts["profile"] = {parsed, normalized_skills}
    ↓
JD Input (manual: URI or URL)
    ↓
[pipelines_v2.py] Extract key requirements using regex
    ↓
Job Dict {text, keywords[]}
    ↓
[scorer.py] score_profile(profile, job)
    ├─ [embedder.py] embed_texts() using sentence-transformers
    ├─ Keyword coverage matching (phrase-aware)
    ├─ Structure validation (section headings)
    ├─ Accuracy metrics (precision, recall, F1)
    ├─ Bias detection (biased term scan)
    └─ [ats_comparison.py] compare_ats_scorers() for benchmark
    ↓
Comprehensive Score Dict {embedding, keywords, structure, overall_score_100, ...}
    ↓
Artifacts["ats"] = score (stored in database)
    ↓
Pipeline Report Output {score, reasons, sections}
```

---

## 10. TECHNICAL NOTES

### Embedding Models Available
- **Default:** `sentence-transformers/all-MiniLM-L6-v2` (lightweight, ~22MB)
- **Configurable:** Any HuggingFace model via `embed_model` parameter
- **Fallback:** Basic cosine similarity if model unavailable

### Skill Normalization Fallback Chain
1. Sentence-transformers semantic matching (if available)
2. `difflib.get_close_matches()` with 0.5 cutoff (always available)
3. No match → original skill kept as-is

### Resume Parser Fallback Chain
1. HuggingFace transformers text-to-text model (if available)
2. Rule-based extraction using regex (always available)
3. Returns: `{name, email, phone, summary, skills[], experience[], education[], raw_text}`

### Why NOT Traditional ATS?
- Traditional ATS uses keyword matching + TF-IDF (implemented in `ats_comparison.py` for comparison)
- TalentFlow advantages:
  - ✅ Understands synonyms ("ML" ≈ "Machine Learning")
  - ✅ Semantic matching beyond exact keywords
  - ✅ Bias/fairness detection built-in
  - ✅ Accuracy metrics for quality assessment
  - ✅ No text length dependency

---

## 11. INTEGRATION POINTS

### Where ATS is Used
1. **Pipeline Step 8** → `run_pipeline_v2()` in pipelines_v2.py:1335
2. **Report Endpoint** → `pipeline_report()` in pipelines_v2.py:40
3. **Direct API call** → `POST /api/ats` via ats.py
4. **Manual Scoring** → `POST /agents/score` via agents.py:score_route()

### Related Endpoints
- `GET /pipelines-v2/{id}/report` - Most user-facing, includes ATS in full output
- `POST /pipelines-v2/{id}/run` - Runs full pipeline including ATS scoring
- `POST /api/ats` - Direct ATS scoring endpoint (simplified)

---

## 12. PERFORMANCE CONSIDERATIONS

### Bottlenecks
- **Embedding generation:** ~100ms per text (using all-MiniLM-L6-v2)
- **Skill normalization:** ~10ms if sentence-transformers available, ~1ms with difflib
- **Resume parsing:** ~50ms with HuggingFace model, ~5ms with regex fallback

### Optimization Opportunities
1. Cache embeddings for frequently scored resumes
2. Batch embed multiple resumes together
3. Use lighter model variant (all-MiniLM-L6-v2 is already minimal)
4. Pre-compute job description embeddings since it's stable

---

## CONCLUSION

TalentFlow's ATS scorer is a **sophisticated, embedding-based system** that goes far beyond traditional keyword-matching ATS. The system:

- ✅ Uses scikit-learn only for baseline comparison (not primary scoring)
- ✅ Stores resume raw_text in artifacts but doesn't include it in ATS output by default
- ✅ Processes resume through extraction → normalization → scoring pipeline
- ✅ Outputs comprehensive multi-factor scoring (ATS + Accuracy + Fairness)
- ✅ Can be enhanced to include resume text in output with minimal code changes

**To add resume text to output, modify Option 4 in Section 5** (Pipeline Run Output).
